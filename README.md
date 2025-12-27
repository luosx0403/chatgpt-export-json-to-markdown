# Chat Export to Markdown

[中文说明](README_zh.md)

Convert exported ChatGPT JSON conversations to readable Markdown with robust parsing, logging, and diagnostics.

## Highlights
- Tree-based traversal (current branch or full DFS) for stable message order; tolerates missing timestamps and mixed content types.
- Optional rich output: timestamps, IDs, model info, reasoning, system prompts, search results, references, metadata, owner info.
- Safe filenames (truncation, reserved-name guard, ID suffix) and atomic writes to avoid partial files.
- Logging to stderr + files (text/JSONL) with run_id, stage/error codes, optional tracebacks, and per-conversation isolation; diagnostics bundle via `--diagnose`.
- Markdown safety: auto-fencing risky content; `--safe-markdown` for fully fenced/escaped text; `--hide-code` if needed.
- Timezone-aware timestamps (`--tz`), bilingual UI (`--lang en|zh`), configurable traversal (`--all-branches`).

## Requirements
- Python 3.10+ (uses `zoneinfo` when available; on Windows without IANA zones, falls back to local time).
- No third-party dependencies.
- For consistent UTF-8 console output, consider running with `PYTHONUTF8=1` or `python -X utf8` if your locale is not UTF-8.

## Usage
```bash
# Minimal (English UI)
python chat_export_md.py new.json -o readable_conversations

# Chinese UI with all optional fields
python chat_export_md.py new.json -o readable_conversations --show-all --lang zh

# Full logs (text + JSONL) and diagnose bundle
python chat_export_md.py new.json -o readable_conversations \
  --show-all --diagnose --log-format both

# Safer rendering and full tracebacks
python chat_export_md.py new.json -o readable_conversations \
  --safe-markdown --traceback full
```

## How to export ChatGPT history
Follow the official guide: https://help.openai.com/en/articles/7260999-how-do-i-export-my-chatgpt-history-and-data

## Key Options
- Output & traversal
  - `-o, --output-dir DIR` target directory (default: `readable_conversations`)
  - `--all-branches` traverse the entire mapping tree (default: current branch)
- Visibility toggles (all off by default; `--show-all` enables all)
  - `--show-times` `--show-ids` `--show-author` `--show-content-type`
  - `--show-reasoning-title` `--show-reasoning-body`
  - `--show-system-prompt` (user_context_message_data / user_editable_context)
  - `--show-search` `--show-references` `--show-metadata`
  - `--show-conv-meta` `--show-model` `--show-owner`
  - `--include-all-roles` (include tool/system, not just user/assistant)
- Rendering & safety
  - `--safe-markdown` fence/escape text; auto-fencing is applied when risky patterns are detected
  - `--hide-code` suppress `content_type=code` blocks
  - `--tz utc|local|IANA` timestamp timezone (default: utc)
  - `--lang en|zh` UI language (default: en)
- Logging & diagnostics
  - `--log-level LEVEL` (DEBUG, INFO, WARNING, ERROR; default INFO)
  - `--log-file PATH` custom log base name; defaults under `output/logs`
  - `--log-format text|jsonl|both` (default text)
  - `--traceback short|full|none` (default short for console; files/jsonl follow mode)
  - `--diagnose` write a diagnose JSON (run info, counts, failures, log paths)

## Output
- Markdown files: `Title_<conv_id-prefix>.md` under the output directory.
- Logs: `output/logs/run_<timestamp>_<runid>.log` (and `.jsonl` when enabled).
- Diagnose: `output/diagnose_<timestamp>_<runid>.json` (when `--diagnose`).

## Logging & Error Codes
- Structured context on every line: `run_id`, `stage`, `conv_key`, `error_code`/`warning_code`, hints.
- Error codes map: `E1001` (JSON decode), `E1002` (input not found), `E1101` (invalid conversation), `E2001` (render error), `E2002` (message extract error), `E3001` (write/output/init dir error).
- Warning code: `W1102` (non-string content part coerced).
- Tracebacks: short/omitted/full per `--traceback`; JSONL always safe to parse.

## Notes on Timezones and Platforms
- `--tz` uses IANA names when available; on Windows without IANA data, the tool falls back to local time with a warning.
- Filenames are truncated and sanitized to avoid Windows reserved names; very long titles are shortened but keep an ID suffix for uniqueness.

## Tips
- Prefer `--safe-markdown` (or rely on auto-fencing) if your content includes heavy Markdown to avoid layout interference.
- Keep stdout clean for summaries; logs are always sent to stderr and files.
- For massive JSON exports, consider running with higher log level only when needed to reduce noise. The tool skips invalid conversations and continues processing others.
