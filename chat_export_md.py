import argparse
import datetime
import html
import json
import logging
import os
import sys
import tempfile
import textwrap
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None


# 读取与基础工具
TEXTS: Dict[str, Dict[str, str]] = {
    "cli_description": {
        "en": "Convert exported conversation JSON to Markdown with optional fields.",
        "zh": "将导出的对话 JSON 转为 Markdown，并可以按需显示额外信息。",
    },
    "json_path_help": {
        "en": "Path to the input JSON file (e.g., new.json).",
        "zh": "输入的 JSON 文件路径（如 new.json）。",
    },
    "output_dir_help": {
        "en": "Output directory (default: readable_conversations).",
        "zh": "输出目录，默认 readable_conversations。",
    },
    "show_times_help": {
        "en": "Show timestamps for conversation and messages.",
        "zh": "展示对话与消息的时间戳。",
    },
    "show_ids_help": {
        "en": "Show conversation_id and message id.",
        "zh": "展示 conversation_id 与 message id。",
    },
    "show_author_help": {
        "en": "Show author name (if present).",
        "zh": "展示作者名称（若存在）。",
    },
    "show_content_type_help": {
        "en": "Show message content_type and related fields.",
        "zh": "展示消息的 content_type 等。",
    },
    "show_reasoning_title_help": {
        "en": "Show reasoning title / summary.",
        "zh": "展示思维链标题等摘要信息。",
    },
    "show_reasoning_body_help": {
        "en": "Show reasoning body / thoughts content.",
        "zh": "展示思维链具体内容。",
    },
    "show_system_prompt_help": {
        "en": "Show user_context_message_data and user_editable_context.",
        "zh": "展示 user_context_message_data 和 user_editable_context 内容。",
    },
    "show_search_help": {
        "en": "Show search queries/results (search_* fields).",
        "zh": "展示搜索查询、搜索结果等（search_* 字段）。",
    },
    "show_references_help": {
        "en": "Show citations/content_references.",
        "zh": "展示 citations / content_references 等引用信息。",
    },
    "show_metadata_help": {
        "en": "Show remaining metadata fields.",
        "zh": "展示其他剩余 metadata 字段。",
    },
    "show_conv_meta_help": {
        "en": "Show conversation-level metadata (model, flags, etc.).",
        "zh": "展示对话级别的元信息（模型、标记位等）。",
    },
    "include_all_roles_help": {
        "en": "Include tool/system and other non-user/assistant roles.",
        "zh": "包含 tool/system 等非 user/assistant 角色。",
    },
    "show_model_help": {
        "en": "Show model-related metadata (model_slug, thinking_effort...).",
        "zh": "展示模型相关字段（model_slug、thinking_effort 等）。",
    },
    "show_owner_help": {
        "en": "Show owner block (if present).",
        "zh": "展示 owner 块（若存在）。",
    },
    "show_all_help": {
        "en": "Enable all optional switches (includes include-all-roles).",
        "zh": "一次性开启所有可选开关（含 include-all-roles）。",
    },
    "all_branches_help": {
        "en": "Traverse all branches instead of only the path to current_node.",
        "zh": "遍历所有分支，而非仅 current_node 所在路径。",
    },
    "hide_code_help": {
        "en": "Hide code content_type messages (default is to show).",
        "zh": "隐藏 content_type 为 code 的消息（默认显示）。",
    },
    "tz_help": {
        "en": "Timezone for timestamps: utc (default), local, or IANA name like Asia/Taipei.",
        "zh": "时间戳时区：utc（默认）、local 或 IANA 名称如 Asia/Taipei。",
    },
    "log_level_help": {
        "en": "Logging level (DEBUG, INFO, WARNING, ERROR). Default INFO.",
        "zh": "日志级别（DEBUG, INFO, WARNING, ERROR），默认 INFO。",
    },
    "log_file_help": {
        "en": "Log file path (optional). If set, logs also go to file.",
        "zh": "日志文件路径（可选），指定后日志同时写入文件。",
    },
    "log_format_help": {
        "en": "Log format: text, jsonl, or both (default text).",
        "zh": "日志格式：text、jsonl 或 both（默认 text）。",
    },
    "diagnose_help": {
        "en": "Write a diagnose JSON with run stats and failure list.",
        "zh": "输出包含运行信息与失败列表的 diagnose JSON。",
    },
    "safe_markdown_help": {
        "en": "Render text in fenced/escaped blocks for safety (default off for readability).",
        "zh": "安全模式渲染文本（围栏+转义，默认关闭以便可读）。",
    },
    "traceback_help": {
        "en": "Traceback output mode for logs: short, full, or none (default short for console).",
        "zh": "日志 traceback 输出模式：short、full 或 none（默认 short）。",
    },
    "lang_help": {
        "en": "Language for Markdown and console output (default: en).",
        "zh": "生成的 Markdown 与控制台输出语言（默认 en）。",
    },
    "conversation_info_heading": {
        "en": "**Conversation Info**",
        "zh": "**对话信息**",
    },
    "create_time_label": {"en": "Created", "zh": "创建时间"},
    "update_time_label": {"en": "Updated", "zh": "更新时间"},
    "owner_label": {"en": "owner", "zh": "owner"},
    "no_messages": {
        "en": "_No messages to output_",
        "zh": "_（无可输出的消息）_",
    },
    "system_prompt_heading": {
        "en": "**System prompt (user_context_message_data)**",
        "zh": "**System prompt（user_context_message_data）**",
    },
    "search_heading": {
        "en": "**Search Info**",
        "zh": "**搜索信息**",
    },
    "references_heading": {
        "en": "**References**",
        "zh": "**引用标记**",
    },
    "other_metadata_heading": {
        "en": "**Other metadata**",
        "zh": "**其他 metadata**",
    },
    "hidden_reasoning": {
        "en": "_Reasoning hidden (use --show-reasoning-body)_",
        "zh": "_思维链已隐藏（使用 --show-reasoning-body 查看）_",
    },
    "hidden_system_prompt": {
        "en": "_System prompt hidden (use --show-system-prompt)_",
        "zh": "_system prompt 已隐藏（使用 --show-system-prompt 查看）_",
    },
    "reasoning_title_label": {
        "en": "**Reasoning title:**",
        "zh": "**思维链标题：**",
    },
    "reasoning_title_skipped": {
        "en": "**Reasoning title:** skipped",
        "zh": "**思维链标题：** 已跳过",
    },
    "search_description_label": {
        "en": "Search description",
        "zh": "搜索描述",
    },
    "search_queries_label": {
        "en": "**Search queries**",
        "zh": "**搜索查询**",
    },
    "search_results_label": {
        "en": "**Search results**",
        "zh": "**搜索结果**",
    },
    "user_instructions_heading": {
        "en": "**User instructions**",
        "zh": "**用户指令**",
    },
    "user_profile_heading": {
        "en": "**User profile**",
        "zh": "**用户画像**",
    },
    "about_model_label": {"en": "About model", "zh": "关于模型"},
    "about_user_label": {"en": "About user", "zh": "关于用户"},
    "model_info_label": {"en": "Model info", "zh": "模型信息"},
    "content_type_label": {"en": "Content type", "zh": "内容类型"},
    "author_label": {"en": "Author", "zh": "作者"},
    "duration_label": {"en": "Duration", "zh": "生成耗时"},
    "conversion_done": {
        "en": "Conversion finished, output files:",
        "zh": "转换完成，输出文件：",
    },
    "summary_heading": {"en": "Summary", "zh": "汇总"},
    "success_count": {"en": "Succeeded: {count}", "zh": "成功: {count}"},
    "failure_count": {"en": "Failed: {count}", "zh": "失败: {count}"},
    "failure_list_heading": {
        "en": "Failed conversations:",
        "zh": "失败的对话：",
    },
    "bad_json_error": {
        "en": "Failed to parse JSON file",
        "zh": "JSON 解析失败",
    },
    "skipped_conversation": {
        "en": "Skipped an invalid conversation entry",
        "zh": "跳过无效的对话条目",
    },
    "write_error": {"en": "Failed to write file", "zh": "写文件失败"},
    "all_branches_label": {
        "en": "All branches DFS",
        "zh": "遍历所有分支 DFS",
    },
    "current_branch_label": {
        "en": "Current branch path",
        "zh": "当前分支路径",
    },
    "tz_used_label": {"en": "Timezone", "zh": "时区"},
    "thought_title_fallback": {"en": "Thought {idx}", "zh": "思考 {idx}"},
    "diagnose_written": {
        "en": "Diagnose file written",
        "zh": "诊断文件已写入",
    },
}

logger = logging.getLogger(__name__)

STANDARD_ATTRS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "asctime",
    "taskName",
}

ERROR_CODES = {
    "E1001": "json_decode_error",
    "E1002": "input_not_found",
    "E1101": "conversation_invalid",
    "E2001": "conversation_render_error",
    "E2002": "message_extract_error",
    "E3001": "write_output_error",
}
WARNING_CODES = {
    "W1102": "unexpected_part_type",
}


def error_name(code: str) -> str:
    if code in ERROR_CODES:
        return ERROR_CODES[code]
    if code in WARNING_CODES:
        return WARNING_CODES[code]
    return "unknown"


def tr(key: str, lang: str) -> str:
    data = TEXTS.get(key, {})
    return data.get(lang) or data.get("en") or key


def bilingual(key: str) -> str:
    data = TEXTS.get(key, {})
    if not data:
        return key
    en = data.get("en", "")
    zh = data.get("zh", "")
    if en and zh:
        return f"{en} / {zh}"
    return en or zh or key


def validate_translations() -> None:
    for key, val in TEXTS.items():
        if not isinstance(val, dict):
            continue
        if "en" not in val or "zh" not in val:
            logger.warning(
                "Missing translation for key=%s", key, extra={"stage": "validate_translations"}
            )


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def decode_part_text(part: Any) -> str:
    if not isinstance(part, str):
        return ""
    return html.unescape(part)


def resolve_timezone(name: str) -> Optional[datetime.tzinfo]:
    if name.lower() == "utc":
        return datetime.timezone.utc
    if name.lower() == "local":
        return None
    if ZoneInfo is not None:
        try:
            return ZoneInfo(name)
        except Exception:
            logger.warning("Unknown timezone %s, fallback to local", name)
            return None
    logger.warning("zoneinfo not available, fallback to local")
    return None


def format_ts(ts: Any, tzinfo: Optional[datetime.tzinfo]) -> str:
    if ts is None:
        return "-"
    try:
        return datetime.datetime.fromtimestamp(float(ts), tz=tzinfo).isoformat()
    except Exception:
        return str(ts)


def safe_filename(title: str) -> str:
    cleaned = "".join(c for c in title if c.isalnum() or c in " _-").strip()
    cleaned = cleaned.rstrip(" .")
    if not cleaned:
        cleaned = "conversation"
    reserved = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }
    if cleaned.upper() in reserved:
        cleaned = f"{cleaned}_"
    max_len = 80
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len]
    return cleaned


def dumps(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return str(obj)


def safe_json_value(val: Any) -> Any:
    if isinstance(val, (str, int, float, bool)) or val is None:
        return val
    if isinstance(val, dict):
        return {str(k): safe_json_value(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [safe_json_value(v) for v in val]
    return repr(val)


def truncate_traceback(tb: str, mode: str) -> str:
    if not tb or mode == "none":
        return ""
    if mode == "full":
        return tb
    lines = tb.strip().splitlines()
    keep = 10
    if len(lines) <= keep:
        return tb
    return "\n".join(lines[-keep:])


def atomic_write_text(path: str, text: str) -> None:
    dir_ = os.path.dirname(path) or "."
    os.makedirs(dir_, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=dir_, delete=False
    ) as tf:
        tf.write(text)
        tmp = tf.name
    os.replace(tmp, path)


def max_backtick_run(text: str) -> int:
    longest = 0
    current = 0
    for ch in text:
        if ch == "`":
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def fenced_block(text: str, info: str = "", escape_html: bool = True) -> str:
    safe_text = text.replace("\r\n", "\n")
    if escape_html:
        safe_text = safe_text.replace("<", "&lt;").replace(">", "&gt;")
    fence_len = max(4, max_backtick_run(safe_text) + 1)
    fence = "`" * fence_len
    info_part = info.strip()
    header = f"{fence}{info_part}\n" if info_part else f"{fence}\n"
    return f"{header}{safe_text}\n{fence}"


class BufferWriter:
    def __init__(self) -> None:
        self.parts: List[str] = []

    def write(self, text: str) -> None:
        self.parts.append(text)

    def getvalue(self) -> str:
        return "".join(self.parts)


def generate_run_id() -> str:
    return uuid.uuid4().hex[:8]


def utc_now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def log_time(record: logging.LogRecord) -> str:
    dt = datetime.datetime.fromtimestamp(record.created, datetime.timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


class KeyValueFormatter(logging.Formatter):
    def __init__(self, traceback_mode: str = "short") -> None:
        super().__init__()
        self.traceback_mode = traceback_mode

    def format(self, record: logging.LogRecord) -> str:
        time_str = log_time(record)
        parts = [
            f"time={time_str}",
            f"level={record.levelname}",
        ]
        run_id = getattr(record, "run_id", None)
        if run_id:
            parts.append(f"run_id={run_id}")
        stage = getattr(record, "stage", None)
        if stage:
            parts.append(f"stage={stage}")
        conv_key = getattr(record, "conv_key", None)
        if conv_key:
            parts.append(f"conv_key=\"{conv_key}\"")
        error_code = getattr(record, "error_code", None)
        if error_code:
            parts.append(f"error_code={error_code}")
            parts.append(f"error_name={error_name(error_code)}")
        warning_code = getattr(record, "warning_code", None)
        if warning_code:
            parts.append(f"warning_code={warning_code}")
            parts.append(f"warning_name={error_name(warning_code)}")
        msg = record.getMessage()
        parts.append(f"msg={json.dumps(msg, ensure_ascii=False)}")
        hint = getattr(record, "hint", None)
        if hint:
            parts.append(f"hint={json.dumps(hint, ensure_ascii=False)}")
        if record.exc_info:
            tb_full = self.formatException(record.exc_info) if self.formatException else ""
            tb = truncate_traceback(tb_full, self.traceback_mode)
            if tb:
                tb_short = tb.replace("\n", "; ").strip()
                parts.append(f"traceback={json.dumps(tb_short, ensure_ascii=False)}")
        extra_fields = []
        for key, val in record.__dict__.items():
            if key in STANDARD_ATTRS or key in ("run_id", "stage", "conv_key", "error_code", "error_name", "warning_code", "warning_name", "hint", "message"):
                continue
            try:
                extra_fields.append(f"{key}={json.dumps(safe_json_value(val), ensure_ascii=False)}")
            except Exception:
                extra_fields.append(f"{key}={json.dumps(str(val), ensure_ascii=False)}")
        parts.extend(sorted(extra_fields))
        return " ".join(parts)


class JSONLFormatter(logging.Formatter):
    def __init__(self, traceback_mode: str = "full") -> None:
        super().__init__()
        self.traceback_mode = traceback_mode

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": log_time(record),
            "level": record.levelname,
            "run_id": getattr(record, "run_id", None),
            "stage": getattr(record, "stage", None),
            "msg": record.getMessage(),
        }
        for key in ("conv_key", "conv_id", "title", "error_code", "warning_code", "hint", "path", "out", "index", "total", "kept", "skipped_roles", "duration_ms", "exception_type"):
            val = getattr(record, key, None)
            if val is not None:
                payload[key] = val
        if record.exc_info:
            tb_full = self.formatException(record.exc_info) if self.formatException else ""
            tb = truncate_traceback(tb_full, self.traceback_mode)
            if tb:
                payload["traceback"] = tb
        if payload.get("error_code"):
            payload["error_name"] = error_name(payload["error_code"])
        if payload.get("warning_code"):
            payload["warning_name"] = error_name(payload["warning_code"])
        # capture any extra non-standard fields
        for key, val in record.__dict__.items():
            if key in payload or key in STANDARD_ATTRS:
                continue
            if key in ("args", "msg", "message", "name"):
                continue
            payload.setdefault("extra", {})[key] = val
        try:
            safe_payload = safe_json_value(payload)
            return json.dumps(safe_payload, ensure_ascii=False)
        except Exception:
            fallback = {
                "jsonl_format_failed": True,
                "raw": str(payload),
            }
            return json.dumps(fallback, ensure_ascii=False)


class CountingHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.warning_count = 0
        self.error_count = 0

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno >= logging.ERROR:
            self.error_count += 1
        elif record.levelno >= logging.WARNING:
            self.warning_count += 1


class MergingAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        extra = kwargs.get("extra", {})
        merged = {}
        merged.update(self.extra or {})
        merged.update(extra or {})
        kwargs["extra"] = merged
        return msg, kwargs


def ensure_log_dir(path: str) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
    except Exception:
        pass


def build_log_paths(log_format: str, log_file: Optional[str], output_dir: str, run_id: str) -> Dict[str, Optional[str]]:
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = log_file
    if not base:
        base = os.path.join(output_dir, "logs", f"run_{ts}_{run_id}")
    text_path = None
    jsonl_path = None
    if log_format in ("text", "both"):
        text_path = base if base.endswith(".log") else base + ".log"
    if log_format in ("jsonl", "both"):
        jsonl_path = base if base.endswith(".jsonl") else base + ".jsonl"
    return {"text": text_path, "jsonl": jsonl_path}


def setup_logging(opts: "RenderOptions") -> CountingHandler:
    counting = CountingHandler()
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.DEBUG)

    stream_formatter = KeyValueFormatter(traceback_mode=opts.traceback_mode)
    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setLevel(getattr(logging, opts.log_level.upper(), logging.INFO))
    stream_handler.setFormatter(stream_formatter)
    root.addHandler(stream_handler)

    if opts.log_paths:
        if opts.log_paths.get("text"):
            ensure_log_dir(opts.log_paths["text"])
            try:
                fh = logging.FileHandler(opts.log_paths["text"], encoding="utf-8")
                fh.setLevel(getattr(logging, opts.log_level.upper(), logging.INFO))
                # File log keeps fuller traceback unless user requested none/full explicitly
                file_tb_mode = "full" if opts.traceback_mode == "short" else opts.traceback_mode
                fh.setFormatter(KeyValueFormatter(traceback_mode=file_tb_mode))
                root.addHandler(fh)
            except Exception as exc:
                print(f"Failed to open log file {opts.log_paths['text']}: {exc}, fallback to console only", file=sys.stderr)
        if opts.log_paths.get("jsonl"):
            ensure_log_dir(opts.log_paths["jsonl"])
            try:
                jh = logging.FileHandler(opts.log_paths["jsonl"], encoding="utf-8")
                jh.setLevel(getattr(logging, opts.log_level.upper(), logging.INFO))
                jh.setFormatter(JSONLFormatter(traceback_mode="full" if opts.traceback_mode != "none" else "none"))
                root.addHandler(jh)
            except Exception as exc:
                print(f"Failed to open jsonl log file {opts.log_paths['jsonl']}: {exc}, fallback to console only", file=sys.stderr)

    counting.setLevel(logging.WARNING)
    root.addHandler(counting)
    return counting


def log_exception(
    logger_obj: logging.Logger,
    error_code: str,
    stage: str,
    exc: Exception,
    hint: str = "",
    **extra: Any,
) -> None:
    logger_obj.error(
        str(exc),
        extra={
            "error_code": error_code,
            "error_name": error_name(error_code),
            "stage": stage,
            "hint": hint,
            "exception_type": exc.__class__.__name__,
            **extra,
        },
        exc_info=True,
    )


@dataclass
class RenderOptions:
    show_times: bool = False
    show_ids: bool = False
    show_author: bool = False
    show_content_type: bool = False
    show_reasoning_title: bool = False
    show_reasoning_body: bool = False
    show_system_prompt: bool = False
    show_search: bool = False
    show_references: bool = False
    show_metadata: bool = False
    show_conv_meta: bool = False
    include_all_roles: bool = False
    show_model: bool = False
    show_owner: bool = False
    lang: str = "en"
    all_branches: bool = False
    hide_code: bool = False
    tzinfo: Optional[datetime.tzinfo] = None
    tz_name: str = "utc"
    log_level: str = "INFO"
    log_file: Optional[str] = None
    log_format: str = "text"
    diagnose: bool = False
    run_id: str = ""
    log_paths: Dict[str, Optional[str]] = None
    safe_markdown: bool = False
    traceback_mode: str = "short"

    def enable_all(self) -> None:
        for field in (
            "show_times",
            "show_ids",
            "show_author",
            "show_content_type",
            "show_reasoning_title",
            "show_reasoning_body",
            "show_system_prompt",
            "show_search",
            "show_references",
            "show_metadata",
            "show_conv_meta",
            "include_all_roles",
            "show_model",
            "show_owner",
            "all_branches",
        ):
            setattr(self, field, True)


def parse_args() -> Tuple[argparse.Namespace, RenderOptions]:
    parser = argparse.ArgumentParser(
        description=bilingual("cli_description")
    )
    parser.add_argument("json_path", help=bilingual("json_path_help"))
    parser.add_argument(
        "-o",
        "--output-dir",
        default="readable_conversations",
        help=bilingual("output_dir_help"),
    )
    parser.add_argument(
        "--show-times", action="store_true", help=bilingual("show_times_help")
    )
    parser.add_argument(
        "--show-ids", action="store_true", help=bilingual("show_ids_help")
    )
    parser.add_argument(
        "--show-author", action="store_true", help=bilingual("show_author_help")
    )
    parser.add_argument(
        "--show-content-type",
        action="store_true",
        help=bilingual("show_content_type_help"),
    )
    parser.add_argument(
        "--show-reasoning-title",
        action="store_true",
        help=bilingual("show_reasoning_title_help"),
    )
    parser.add_argument(
        "--show-reasoning-body",
        action="store_true",
        help=bilingual("show_reasoning_body_help"),
    )
    parser.add_argument(
        "--show-system-prompt",
        action="store_true",
        help=bilingual("show_system_prompt_help"),
    )
    parser.add_argument(
        "--show-search",
        action="store_true",
        help=bilingual("show_search_help"),
    )
    parser.add_argument(
        "--show-references", action="store_true", help=bilingual("show_references_help")
    )
    parser.add_argument(
        "--show-metadata", action="store_true", help=bilingual("show_metadata_help")
    )
    parser.add_argument(
        "--show-conv-meta",
        action="store_true",
        help=bilingual("show_conv_meta_help"),
    )
    parser.add_argument(
        "--include-all-roles",
        action="store_true",
        help=bilingual("include_all_roles_help"),
    )
    parser.add_argument(
        "--show-model", action="store_true", help=bilingual("show_model_help")
    )
    parser.add_argument(
        "--show-owner", action="store_true", help=bilingual("show_owner_help")
    )
    parser.add_argument(
        "--lang",
        choices=["en", "zh"],
        default="en",
        help=bilingual("lang_help"),
    )
    parser.add_argument(
        "--all-branches",
        action="store_true",
        help=bilingual("all_branches_help"),
    )
    parser.add_argument(
        "--hide-code",
        action="store_true",
        help=bilingual("hide_code_help"),
    )
    parser.add_argument(
        "--tz",
        default="utc",
        help=bilingual("tz_help"),
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help=bilingual("log_level_help"),
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help=bilingual("log_file_help"),
    )
    parser.add_argument(
        "--log-format",
        choices=["text", "jsonl", "both"],
        default="text",
        help=bilingual("log_format_help"),
    )
    parser.add_argument(
        "--diagnose",
        action="store_true",
        help=bilingual("diagnose_help"),
    )
    parser.add_argument(
        "--safe-markdown",
        action="store_true",
        help=bilingual("safe_markdown_help"),
    )
    parser.add_argument(
        "--traceback",
        choices=["short", "full", "none"],
        default="short",
        help=bilingual("traceback_help"),
    )
    parser.add_argument(
        "--show-all",
        action="store_true",
        help=bilingual("show_all_help"),
    )
    args = parser.parse_args()
    opts = RenderOptions(
        show_times=args.show_times,
        show_ids=args.show_ids,
        show_author=args.show_author,
        show_content_type=args.show_content_type,
        show_reasoning_title=args.show_reasoning_title,
        show_reasoning_body=args.show_reasoning_body,
        show_system_prompt=args.show_system_prompt,
        show_search=args.show_search,
        show_references=args.show_references,
        show_metadata=args.show_metadata,
        show_conv_meta=args.show_conv_meta,
        include_all_roles=args.include_all_roles,
        show_model=args.show_model,
        show_owner=args.show_owner,
        lang=args.lang,
        all_branches=args.all_branches,
        hide_code=args.hide_code,
        tzinfo=resolve_timezone(args.tz),
        tz_name=args.tz,
        log_level=args.log_level,
        log_file=args.log_file,
        log_format=args.log_format,
        diagnose=args.diagnose,
        safe_markdown=args.safe_markdown,
        traceback_mode=args.traceback,
    )
    if args.show_all:
        opts.enable_all()
        opts.lang = args.lang
        opts.tzinfo = resolve_timezone(args.tz)
        opts.tz_name = args.tz
        opts.hide_code = args.hide_code
    return args, opts


def load_conversations(json_path: str, logger_obj: logging.Logger, lang: str) -> List[Dict[str, Any]]:
    data = load_json(json_path)
    candidates: List[Any]
    if isinstance(data, list):
        candidates = data
    elif isinstance(data, dict) and isinstance(data.get("conversations"), list):
        candidates = data["conversations"]
    else:
        candidates = [data]
    conversations: List[Dict[str, Any]] = []
    for conv in candidates:
        if isinstance(conv, dict):
            conversations.append(conv)
        else:
            logger_obj.warning(
                tr("skipped_conversation", lang),
                extra={"stage": "parse_conversations"},
            )
    return conversations


def normalize_text_parts(
    parts: Iterable[Any],
    logger_obj: Optional[logging.Logger] = None,
    conv_key: Optional[str] = None,
) -> str:
    texts: List[str] = []
    for part in parts or []:
        if not isinstance(part, str):
            if logger_obj:
                logger_obj.warning(
                    "unexpected part type; coerced to string",
                    extra={
                        "stage": "normalize",
                        "conv_key": conv_key,
                        "warning_code": "W1102",
                        "item_type": type(part).__name__,
                    },
                )
            part = str(part)
        decoded = decode_part_text(part)
        if decoded.strip():
            texts.append(decoded)
    return "\n\n".join(texts)


def message_timestamp(node: Dict[str, Any]) -> float:
    msg = node.get("message") if isinstance(node, dict) else None
    if not isinstance(msg, dict):
        return 0.0
    ts = msg.get("create_time") or msg.get("update_time")
    try:
        return float(ts or 0.0)
    except Exception:
        return 0.0


def sorted_children_ids(node_id: str, mapping: Dict[str, Any]) -> List[str]:
    node = mapping.get(node_id) or {}
    children = node.get("children") or []
    if not isinstance(children, list):
        return []
    valid_children = [cid for cid in children if cid in mapping]
    return sorted(valid_children, key=lambda cid: (message_timestamp(mapping[cid]), cid))


def find_root_ids(mapping: Dict[str, Any]) -> List[str]:
    roots: List[str] = []
    for node_id, node in mapping.items():
        parent = node.get("parent") if isinstance(node, dict) else None
        if not parent or parent not in mapping:
            roots.append(node_id)
    return sorted(roots, key=lambda nid: (message_timestamp(mapping.get(nid, {})), nid))


def build_path_to_current(conv: Dict[str, Any], mapping: Dict[str, Any]) -> List[str]:
    current = conv.get("current_node")
    if not current or current not in mapping:
        return []
    path: List[str] = []
    seen = set()
    node_id = current
    while node_id and node_id in mapping and node_id not in seen:
        path.append(node_id)
        seen.add(node_id)
        parent = mapping.get(node_id, {}).get("parent")
        if not parent:
            break
        node_id = parent
    return list(reversed(path))


def dfs_all_nodes(mapping: Dict[str, Any]) -> List[str]:
    order: List[str] = []
    roots = find_root_ids(mapping)

    def walk(node_id: str) -> None:
        if node_id not in mapping:
            return
        order.append(node_id)
        for cid in sorted_children_ids(node_id, mapping):
            walk(cid)

    for rid in roots:
        walk(rid)
    return order


def ordered_node_ids(conv: Dict[str, Any], all_branches: bool) -> List[str]:
    mapping = conv.get("mapping") or {}
    if not isinstance(mapping, dict):
        return []
    if all_branches:
        ids = dfs_all_nodes(mapping)
        if ids:
            return ids
    path = build_path_to_current(conv, mapping)
    if path:
        return path
    return dfs_all_nodes(mapping)


def format_thoughts(content: Dict[str, Any], lang: str) -> str:
    thoughts = content.get("thoughts") or []
    lines: List[str] = []
    for idx, thought in enumerate(thoughts, 1):
        if not isinstance(thought, dict):
            continue
        summary = thought.get("summary") or ""
        body = thought.get("content") or ""
        chunk_preview = "; ".join(thought.get("chunks") or [])
        title = summary or chunk_preview or tr("thought_title_fallback", lang).format(
            idx=idx
        )
        lines.append(f"- {idx}. {title}")
        detail_parts = []
        if summary and summary != title:
            detail_parts.append(summary)
        if body:
            detail_parts.append(body)
        if detail_parts:
            lines.append(textwrap.indent("\n\n".join(detail_parts), "  "))
    return "\n".join(lines).strip()


def format_user_context(meta: Dict[str, Any], lang: str) -> str:
    uc = meta.get("user_context_message_data") or {}
    if not isinstance(uc, dict) or not uc:
        return ""
    blocks: List[str] = []
    for label_key, key in (
        ("about_model_label", "about_model_message"),
        ("about_user_label", "about_user_message"),
    ):
        val = uc.get(key)
        if val:
            blocks.append(
                f"**{tr(label_key, lang)}:**\n\n> " + val.replace("\n", "\n> ")
            )
    return "\n\n".join(blocks)


def format_user_editable_context(content: Dict[str, Any], lang: str) -> str:
    pieces: List[str] = []
    instructions = content.get("user_instructions")
    profile = content.get("user_profile")
    if instructions:
        pieces.append(tr("user_instructions_heading", lang) + "\n\n> " + instructions.replace("\n", "\n> "))
    if profile:
        pieces.append(tr("user_profile_heading", lang) + "\n\n> " + profile.replace("\n", "\n> "))
    return "\n\n".join(pieces)


def format_search(meta: Dict[str, Any], lang: str) -> str:
    lines: List[str] = []
    queries = meta.get("search_queries") or meta.get("search_model_queries") or []
    display = meta.get("search_display_string") or meta.get("searched_display_string")
    if display:
        lines.append(f"{tr('search_description_label', lang)}: {display}")
    if queries:
        lines.append(tr("search_queries_label", lang))
        for q in queries:
            if isinstance(q, dict):
                query_text = q.get("q") or q.get("query") or dumps(q)
                recency = q.get("recency")
                tail = f" (recency={recency})" if recency is not None else ""
                lines.append(f"- {query_text}{tail}")
            else:
                lines.append(f"- {q}")
    groups = meta.get("search_result_groups") or []
    if groups:
        lines.append(tr("search_results_label", lang))
        for group in groups:
            domain = group.get("domain") or "results"
            lines.append(f"- {domain}")
            for entry in group.get("entries") or []:
                if not isinstance(entry, dict):
                    continue
                title = entry.get("title") or entry.get("url") or "result"
                url = entry.get("url")
                snippet = entry.get("snippet")
                line = f"  - {title}"
                if url:
                    line += f" ({url})"
                lines.append(line)
                if snippet:
                    lines.append("    " + snippet.replace("\n", " ").strip())
    return "\n".join(lines).strip()


def format_references(meta: Dict[str, Any], lang: str) -> str:
    lines: List[str] = []
    citations = meta.get("citations") or []
    content_refs = meta.get("content_references") or []
    if citations:
        lines.append(tr("references_heading", lang) + " (citations)")
        for cite in citations:
            lines.append(f"- {dumps(cite)}")
    if content_refs:
        lines.append(tr("references_heading", lang) + " (content_references)")
        for ref in content_refs:
            lines.append(f"- {dumps(ref)}")
    return "\n".join(lines).strip()


def build_output_path(conv: Dict[str, Any], output_dir: str) -> Tuple[str, str]:
    title = conv.get("title") or "untitled"
    base_name = safe_filename(title)
    conv_id = conv.get("conversation_id") or conv.get("id")
    suffix = ""
    if conv_id:
        suffix = f"_{str(conv_id)[:8]}"
    max_total = 90
    allowed_base = max(1, max_total - len(suffix))
    fname = base_name[:allowed_base] + suffix
    return os.path.join(output_dir, f"{fname}.md"), title


def build_conv_key(conv: Dict[str, Any], idx: int) -> str:
    conv_id = conv.get("conversation_id") or conv.get("id") or f"idx{idx}"
    short_id = str(conv_id)[:8]
    title = conv.get("title") or "untitled"
    safe_title = safe_filename(title)[:40]
    return f"{short_id}|{safe_title}"


def extract_messages(conv: Dict[str, Any], opts: RenderOptions, logger_obj: logging.Logger, conv_key: str) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    mapping = conv.get("mapping", {}) or {}
    if not isinstance(mapping, dict):
        logger_obj.warning(
            "Invalid mapping in conversation, skip messages",
            extra={"stage": "extract_msgs", "conv_key": conv_key},
        )
        return [], {"total": 0, "kept": 0, "skipped_roles": 0}
    ordered_ids = ordered_node_ids(conv, opts.all_branches)
    messages: List[Dict[str, Any]] = []
    total = 0
    skipped_roles = 0
    for idx, node_id in enumerate(ordered_ids):
        node = mapping.get(node_id)
        if not isinstance(node, dict):
            continue
        msg = node.get("message")
        if not isinstance(msg, dict):
            continue
        author = msg.get("author") or {}
        role = author.get("role", "unknown")
        total += 1
        if not opts.include_all_roles and role not in ("user", "assistant"):
            skipped_roles += 1
            continue
        messages.append(
            {
                "role": role,
                "status": msg.get("status") or "",
                "timestamp": msg.get("create_time") or msg.get("update_time"),
                "id": msg.get("id"),
                "author": author,
                "content": msg.get("content") or {},
                "metadata": msg.get("metadata") or {},
                "order": idx,
                "conv_key": conv_key,
            }
        )
    stats = {"total": total, "kept": len(messages), "skipped_roles": skipped_roles}
    logger_obj.info(
        "messages extracted",
        extra={
            "stage": "extract_msgs",
            "total": stats["total"],
            "kept": stats["kept"],
            "skipped_roles": stats["skipped_roles"],
        },
    )
    return messages, stats


def render_conversation_meta(f, conv: Dict[str, Any], opts: RenderOptions) -> None:
    lines: List[str] = []
    if opts.show_ids and conv.get("conversation_id"):
        lines.append(f"- conversation_id: `{conv['conversation_id']}`")
    if opts.show_ids and conv.get("id"):
        lines.append(f"- id: `{conv['id']}`")
    if opts.show_times:
        if conv.get("create_time") is not None:
            lines.append(f"- {tr('create_time_label', opts.lang)}: {format_ts(conv.get('create_time'), opts.tzinfo)}")
        if conv.get("update_time") is not None:
            lines.append(f"- {tr('update_time_label', opts.lang)}: {format_ts(conv.get('update_time'), opts.tzinfo)}")
        lines.append(f"- {tr('tz_used_label', opts.lang)}: {opts.tz_name}")
    if opts.show_owner and conv.get("owner") is not None:
        lines.append(f"- {tr('owner_label', opts.lang)}: {dumps(conv.get('owner'))}")
    if opts.show_conv_meta:
        for key in (
            "default_model_slug",
            "conversation_origin",
            "plugin_ids",
            "gizmo_id",
            "gizmo_type",
            "is_archived",
            "is_starred",
            "is_read_only",
            "voice",
            "async_status",
            "disabled_tool_ids",
            "is_do_not_remember",
            "memory_scope",
            "context_scopes",
            "sugar_item_id",
            "sugar_item_visible",
            "pinned_time",
            "is_study_mode",
            "safe_urls",
            "blocked_urls",
        ):
            if key in conv and conv.get(key) not in (None, {}):
                lines.append(f"- {key}: {dumps(conv.get(key))}")
    if lines:
        f.write(tr("conversation_info_heading", opts.lang) + "\n")
        for line in lines:
            f.write(f"{line}\n")
        f.write("\n")


def core_text_for_message(content: Dict[str, Any], opts: RenderOptions, logger_obj: Optional[logging.Logger], conv_key: Optional[str]) -> str:
    def maybe_fence(text: str, info: str = "", escape: bool = True) -> str:
        if opts.safe_markdown:
            return fenced_block(text, info=info, escape_html=escape)
        # auto-detect hazardous markdown
        lines = text.splitlines()
        if "```" in text:
            return fenced_block(text, info=info, escape_html=escape)
        if any(line.startswith("# ") for line in lines[:10]):
            return fenced_block(text, info=info, escape_html=escape)
        if any("|---" in line or "---|" in line for line in lines[:10]):
            return fenced_block(text, info=info, escape_html=escape)
        return text

    ctype = content.get("content_type")
    if ctype == "text":
        text = normalize_text_parts(content.get("parts"), logger_obj, conv_key)
        if not text:
            return ""
        return maybe_fence(text, escape=True)
    if ctype == "reasoning_recap":
        text = content.get("content") or ""
        if not opts.show_reasoning_body:
            return ""
        if not text:
            return ""
        return maybe_fence(str(text), escape=True)
    if ctype == "thoughts":
        return format_thoughts(content, opts.lang) if opts.show_reasoning_body else ""
    if ctype == "user_editable_context":
        return (
            format_user_editable_context(content, opts.lang)
            if opts.show_system_prompt
            else ""
        )
    if ctype == "code":
        if opts.hide_code:
            return ""
        lang = content.get("language") or ""
        text = content.get("text") or normalize_text_parts(content.get("parts"), logger_obj, conv_key)
        if not text:
            return ""
        return fenced_block(str(text), info=lang, escape_html=False)
    # 兜底：尝试 parts 或 text
    if isinstance(content, dict):
        if content.get("parts"):
            text = normalize_text_parts(content.get("parts"), logger_obj, conv_key)
            if not text:
                return ""
            return maybe_fence(text, escape=True)
        if content.get("text"):
            text = str(content.get("text"))
            if not text:
                return ""
            return maybe_fence(text, escape=True)
    # 未知类型不静默丢弃
    return fenced_block(dumps(content), escape_html=True)


def render_message(
    f, msg: Dict[str, Any], index: int, opts: RenderOptions, logger_obj: Optional[logging.Logger]
) -> None:
    content = msg.get("content") or {}
    meta = msg.get("metadata") or {}
    consumed_meta_keys = set()
    conv_key = msg.get("conv_key")

    header_bits = [f"{index}. {msg.get('role', 'unknown')}"]
    if msg.get("status"):
        header_bits.append(msg["status"])
    if opts.show_times and msg.get("timestamp") is not None:
        header_bits.append(format_ts(msg.get("timestamp"), opts.tzinfo))
    if opts.show_ids and msg.get("id"):
        header_bits.append(f"id={msg['id']}")
    f.write("### " + " | ".join(header_bits) + "\n\n")

    detail_lines: List[str] = []
    if opts.show_author:
        author_name = (msg.get("author") or {}).get("name")
        if author_name:
            detail_lines.append(f"{tr('author_label', opts.lang)}: {author_name}")
    if opts.show_content_type:
        ct_bits = []
        ctype = content.get("content_type")
        if ctype:
            ct_bits.append(ctype)
        if content.get("language"):
            ct_bits.append(f"lang={content['language']}")
        if content.get("response_format_name"):
            ct_bits.append(f"format={content['response_format_name']}")
        if ct_bits:
            detail_lines.append(f"{tr('content_type_label', opts.lang)}: " + ", ".join(ct_bits))
    if opts.show_model:
        model_bits = []
        for key in (
            "model_slug",
            "default_model_slug",
            "thinking_effort",
            "message_type",
            "reasoning_status",
        ):
            if key in meta and meta.get(key) is not None:
                model_bits.append(f"{key}={meta.get(key)}")
                consumed_meta_keys.add(key)
        if meta.get("finish_details"):
            model_bits.append(f"finish_details={dumps(meta.get('finish_details'))}")
            consumed_meta_keys.add("finish_details")
        if model_bits:
            detail_lines.append(f"{tr('model_info_label', opts.lang)}: " + "; ".join(model_bits))
    if opts.show_times and meta.get("finished_duration_sec") is not None:
        detail_lines.append(f"{tr('duration_label', opts.lang)}: {meta.get('finished_duration_sec')}s")
        consumed_meta_keys.add("finished_duration_sec")
    if detail_lines:
        for line in detail_lines:
            f.write(f"- {line}\n")
        f.write("\n")

    core_text = core_text_for_message(content, opts, logger_obj, conv_key)
    if core_text:
        f.write(core_text.strip() + "\n\n")
    elif content.get("content_type") == "thoughts" and opts.show_reasoning_body is False:
        f.write(tr("hidden_reasoning", opts.lang) + "\n\n")
    elif content.get("content_type") == "user_editable_context" and not opts.show_system_prompt:
        f.write(tr("hidden_system_prompt", opts.lang) + "\n\n")

    if opts.show_reasoning_title:
        if "reasoning_title" in meta and meta.get("reasoning_title"):
            f.write(f"{tr('reasoning_title_label', opts.lang)} {meta.get('reasoning_title')}\n\n")
            consumed_meta_keys.add("reasoning_title")
        if meta.get("skip_reasoning_title"):
            f.write(tr("reasoning_title_skipped", opts.lang) + "\n\n")
            consumed_meta_keys.add("skip_reasoning_title")

    if opts.show_system_prompt:
        system_block = format_user_context(meta, opts.lang)
        if system_block:
            f.write(tr("system_prompt_heading", opts.lang) + "\n\n")
            f.write(system_block + "\n\n")
            consumed_meta_keys.add("user_context_message_data")

    if opts.show_search:
        search_block = format_search(meta, opts.lang)
        if search_block:
            f.write(tr("search_heading", opts.lang) + "\n\n")
            f.write(search_block + "\n\n")
            consumed_meta_keys.update(
                {
                    "search_queries",
                    "search_model_queries",
                    "search_display_string",
                    "searched_display_string",
                    "search_result_groups",
                }
            )

    if opts.show_references:
        ref_block = format_references(meta, opts.lang)
        if ref_block:
            f.write(tr("references_heading", opts.lang) + "\n\n")
            f.write(ref_block + "\n\n")
            consumed_meta_keys.update({"citations", "content_references"})

    if opts.show_metadata:
        remaining_meta = {
            k: v for k, v in meta.items() if k not in consumed_meta_keys
        }
        if remaining_meta:
            f.write(tr("other_metadata_heading", opts.lang) + "\n\n")
            f.write("```json\n")
            f.write(json.dumps(remaining_meta, ensure_ascii=False, indent=2))
            f.write("\n```\n\n")


def conversation_to_markdown(
    conv: Dict[str, Any], output_dir: str, opts: RenderOptions, logger_obj: logging.Logger, conv_ctx: Dict[str, Any]
) -> Tuple[str, Dict[str, int], int]:
    output_path, title = build_output_path(conv, output_dir)
    writer = BufferWriter()
    writer.write(f"# {title}\n\n")
    render_conversation_meta(writer, conv, opts)

    messages, stats = extract_messages(conv, opts, logger_obj, conv_ctx.get("conv_key", ""))
    if not messages:
        writer.write(tr("no_messages", opts.lang) + "\n")
        content = writer.getvalue()
        atomic_write_text(output_path, content)
        logger_obj.info(
            "markdown rendered",
            extra={"stage": "render_md", "chars": len(content)},
        )
        logger_obj.info(
            "written",
            extra={"stage": "write_output", "out": output_path, "atomic": True},
        )
        return output_path, stats, len(content)
    for idx, msg in enumerate(messages, 1):
        render_message(writer, msg, idx, opts, logger_obj)
    content = writer.getvalue()
    atomic_write_text(output_path, content)
    logger_obj.info(
        "markdown rendered",
        extra={"stage": "render_md", "chars": len(content)},
    )
    logger_obj.info(
        "written",
        extra={"stage": "write_output", "out": output_path, "atomic": True},
    )
    return output_path, stats, len(content)


def ensure_output_dir(out_dir: str, logger_obj: logging.Logger) -> None:
    try:
        os.makedirs(out_dir, exist_ok=True)
    except Exception as exc:
        log_exception(
            logger_obj,
            "E3001",
            "init_output_dir",
            exc,
            hint="check output directory permissions or path length",
            out=out_dir,
        )
        sys.exit(1)


def convert_all(
    conversations: List[Dict[str, Any]],
    json_path: str,
    out_dir: str,
    opts: RenderOptions,
) -> Tuple[List[str], List[Dict[str, Any]]]:
    ensure_output_dir(out_dir, logger)
    outputs: List[str] = []
    failures: List[Dict[str, Any]] = []
    total = len(conversations)
    for idx, conv in enumerate(conversations):
        title = conv.get("title") or f"conversation_{idx}"
        conv_id = conv.get("conversation_id") or conv.get("id") or f"idx{idx}"
        conv_key = build_conv_key(conv, idx)
        conv_logger = MergingAdapter(
            logging.getLogger(__name__),
            {"run_id": opts.run_id, "conv_key": conv_key, "conv_id": conv_id, "title": title, "lang": opts.lang},
        )
        conv_logger.info(
            "processing conversation",
            extra={"stage": "conv_start", "index": idx + 1, "total": total},
        )
        start = time.monotonic()
        try:
            path, stats, char_count = conversation_to_markdown(
                conv, out_dir, opts, conv_logger, {"conv_key": conv_key}
            )
            outputs.append(path)
        except PermissionError as exc:
            log_exception(
                conv_logger,
                "E3001",
                "write_output",
                exc,
                hint="check output directory permissions or choose another -o directory",
                out=out_dir,
            )
            failures.append(
                {
                    "title": title,
                    "conv_id": conv_id,
                    "conv_key": conv_key,
                    "error_code": "E3001",
                    "error_name": error_name("E3001"),
                    "stage": "write_output",
                    "hint": "check output directory permissions or choose another -o directory",
                }
            )
            conv_logger.info(
                "conversation skipped due to error",
                extra={"stage": "conv_skip", "action": "continue"},
            )
            continue
        except OSError as exc:
            log_exception(
                conv_logger,
                "E3001",
                "write_output",
                exc,
                hint="check disk space, path length, or output directory permissions",
                out=out_dir,
            )
            failures.append(
                {
                    "title": title,
                    "conv_id": conv_id,
                    "conv_key": conv_key,
                    "error_code": "E3001",
                    "error_name": error_name("E3001"),
                    "stage": "write_output",
                    "hint": "check disk space, path length, or output directory permissions",
                }
            )
            conv_logger.info(
                "conversation skipped due to error",
                extra={"stage": "conv_skip", "action": "continue"},
            )
            continue
        except Exception as exc:
            log_exception(
                conv_logger,
                "E2001",
                "render_conversation",
                exc,
                hint="enable --log-level DEBUG for more details",
            )
            failures.append(
                {
                    "title": title,
                    "conv_id": conv_id,
                    "conv_key": conv_key,
                    "error_code": "E2001",
                    "error_name": error_name("E2001"),
                    "stage": "render_conversation",
                    "hint": "enable --log-level DEBUG for more details",
                }
            )
            conv_logger.info(
                "conversation skipped due to error",
                extra={"stage": "conv_skip", "action": "continue"},
            )
            continue
        finally:
            duration = int((time.monotonic() - start) * 1000)
            conv_logger.info(
                "done",
                extra={"stage": "conv_done", "duration_ms": duration},
            )
    return outputs, failures


def write_diagnose(
    opts: RenderOptions,
    started_at: datetime.datetime,
    finished_at: datetime.datetime,
    args: argparse.Namespace,
    conversations: List[Dict[str, Any]],
    outputs: List[str],
    failures: List[Dict[str, Any]],
    counting: CountingHandler,
    input_size: Optional[int],
) -> str:
    diag = {
        "run_id": opts.run_id,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "argv": " ".join(sys.argv[1:]),
        "environment": {
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "cwd": os.getcwd(),
        },
        "input": {
            "path": args.json_path,
            "size_bytes": input_size,
            "conversations_detected": len(conversations),
        },
        "result": {
            "ok": len(outputs),
            "failed": len(failures),
            "warnings": counting.warning_count,
            "errors": counting.error_count,
            "outputs_dir": args.output_dir,
        },
        "failures": failures,
        "logs": {
            "text": opts.log_paths.get("text") if opts.log_paths else None,
            "jsonl": opts.log_paths.get("jsonl") if opts.log_paths else None,
        },
        "error_codes": ERROR_CODES,
        "warning_codes": WARNING_CODES,
    }
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    diag_path = os.path.join(args.output_dir, f"diagnose_{ts}_{opts.run_id}.json")
    atomic_write_text(diag_path, json.dumps(diag, ensure_ascii=False, indent=2))
    return diag_path


def main() -> None:
    args, opts = parse_args()
    opts.run_id = generate_run_id()
    opts.log_paths = build_log_paths(opts.log_format, opts.log_file, args.output_dir, opts.run_id)
    counting = setup_logging(opts)
    global logger
    logger = MergingAdapter(logging.getLogger(__name__), {"run_id": opts.run_id, "lang": opts.lang})
    validate_translations()

    run_start_time = datetime.datetime.now(datetime.timezone.utc)
    run_start_monotonic = time.monotonic()
    argv_str = " ".join(sys.argv[1:])
    logger.info(
        "start conversion",
        extra={
            "stage": "run_start",
            "argv": argv_str,
            "output_dir": args.output_dir,
            "log_format": opts.log_format,
            "log_paths": opts.log_paths,
        },
    )
    logger.info(
        "environment",
        extra={
            "stage": "env",
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "cwd": os.getcwd(),
        },
    )

    input_size = None
    try:
        input_size = os.path.getsize(args.json_path)
    except Exception:
        input_size = None
    logger.info(
        "loading json",
        extra={
            "stage": "load_input",
            "path": args.json_path,
            "size_bytes": input_size,
        },
    )

    try:
        conversations = load_conversations(args.json_path, logger, opts.lang)
    except FileNotFoundError as exc:
        log_exception(
            logger,
            "E1002",
            "load_input",
            exc,
            hint="check input path",
            path=args.json_path,
        )
        sys.exit(1)
    except json.JSONDecodeError as exc:
        log_exception(
            logger,
            "E1001",
            "load_input",
            exc,
            hint="ensure the JSON is valid UTF-8",
            path=args.json_path,
        )
        sys.exit(1)
    except Exception as exc:
        log_exception(
            logger,
            "E1001",
            "load_input",
            exc,
            hint="enable --log-level DEBUG for details",
            path=args.json_path,
        )
        sys.exit(1)

    logger.info(
        "conversations detected",
        extra={
            "stage": "parse_convs",
            "count": len(conversations),
            "input_size": input_size,
            "path": args.json_path,
        },
    )

    outputs, failures = convert_all(conversations, args.json_path, args.output_dir, opts)

    duration_ms = int((time.monotonic() - run_start_monotonic) * 1000)
    logger.info(
        "finished",
        extra={
            "stage": "run_summary",
            "conversations_total": len(conversations),
            "conversations_ok": len(outputs),
            "conversations_failed": len(failures),
            "warnings": counting.warning_count,
            "errors": counting.error_count,
            "duration_ms": duration_ms,
        },
    )
    if opts.log_paths and (opts.log_paths.get("text") or opts.log_paths.get("jsonl")):
        logger.info(
            "log saved",
            extra={
                "stage": "run_end",
                "text_log": opts.log_paths.get("text"),
                "jsonl_log": opts.log_paths.get("jsonl"),
            },
        )

    if opts.diagnose:
        diag_path = write_diagnose(
            opts,
            run_start_time,
            datetime.datetime.now(datetime.timezone.utc),
            args,
            conversations,
            outputs,
            failures,
            counting,
            input_size,
        )
        logger.info(
            tr("diagnose_written", opts.lang),
            extra={"stage": "run_end", "path": diag_path},
        )

    print(tr("conversion_done", opts.lang))
    for path in outputs:
        print(f"- {path}")
    print(tr("summary_heading", opts.lang))
    print(tr("success_count", opts.lang).format(count=len(outputs)))
    print(tr("failure_count", opts.lang).format(count=len(failures)))
    if failures:
        print(tr("failure_list_heading", opts.lang))
        for failure in failures:
            hint = failure.get("hint", "")
            stage = failure.get("stage", "")
            print(f"- {failure.get('title')} ({failure.get('error_code')} @ {stage}) {hint}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
