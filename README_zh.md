# Chat 导出转 Markdown

转换导出的 ChatGPT JSON 对话为可读的 Markdown，具备稳健的解析、日志与诊断能力。

## 亮点
- 基于树的遍历（当前分支或全量 DFS），消息顺序稳定；容忍缺失时间戳和混合 content_type。
- 可选信息丰富：时间戳、ID、模型信息、思维链、system prompt、搜索结果、引用、metadata、owner 等。
- 安全文件名（截断、保留名防护、ID 后缀）与原子写入，避免半截文件。
- 日志输出到 stderr + 文件（text/JSONL），包含 run_id、阶段/错误码、可选 traceback、对话级隔离；`--diagnose` 生成诊断包。
- Markdown 安全：自动围栏风险内容；`--safe-markdown` 全量围栏/转义；需要时可 `--hide-code`。
- 时区可选（`--tz`）、双语界面（`--lang en|zh`）、可切换遍历模式（`--all-branches`）。

## 环境需求
- Python 3.10+（使用 `zoneinfo`；Windows 无 IANA 区域时自动退回本地时区）。
- 无第三方依赖。
- 若终端非 UTF-8，建议使用 `PYTHONUTF8=1` 或 `python -X utf8`。

## 使用方法
```bash
# 英文界面，最小输出
python chat_export_md.py conversations.json -o readable_conversations

# 中文界面，开启所有可选字段
python chat_export_md.py conversations.json -o readable_conversations --show-all --lang zh

# 完整日志（text + JSONL）和诊断包
python chat_export_md.py conversations.json -o readable_conversations \
  --show-all --diagnose --log-format both

# 更安全的渲染与完整 traceback
python chat_export_md.py conversations.json -o readable_conversations \
  --safe-markdown --traceback full
```

> **关于分片导出文件的说明**  
> 如果导出的数据被拆分为多个文件（例如 `conversations-000.json`、`conversations-001.json` 等），在运行本工具之前，建议先将它们合并为一个单一的 JSON 文件。例如：
> ```bash
> jq -s 'add' conversations-*.json > conversations.json
> ```
> 这样可以确保解析器能够在一次处理过程中完整读取所有对话数据。

## 如何导出 ChatGPT 历史聊天记录
参阅官方指南：https://help.openai.com/en/articles/7260999-how-do-i-export-my-chatgpt-history-and-data

## 主要参数
- 输出与遍历
  - `-o, --output-dir DIR` 输出目录（默认 `readable_conversations`）
  - `--all-branches` 遍历整个 mapping 树（默认当前分支）
- 可见性开关（默认关闭；`--show-all` 全开）
  - `--show-times` `--show-ids` `--show-author` `--show-content-type`
  - `--show-reasoning-title` `--show-reasoning-body`
  - `--show-system-prompt`（user_context_message_data / user_editable_context）
  - `--show-search` `--show-references` `--show-metadata`
  - `--show-conv-meta` `--show-model` `--show-owner`
  - `--include-all-roles`（包含 tool/system 等）
- 渲染与安全
  - `--safe-markdown` 围栏/转义文本；检测到风险时自动围栏
  - `--hide-code` 隐藏 `content_type=code`
  - `--tz utc|local|IANA` 时间戳时区（默认 utc）
  - `--lang en|zh` 界面语言（默认 en）
- 日志与诊断
  - `--log-level LEVEL`（DEBUG/INFO/WARNING/ERROR，默认 INFO）
  - `--log-file PATH` 自定义日志基名，默认写到 `output/logs`
  - `--log-format text|jsonl|both`（默认 text）
  - `--traceback short|full|none`（默认 short；文件/JSONL 依据该模式）
  - `--diagnose` 输出诊断 JSON（运行信息、计数、失败、日志路径）

## 输出结构
- Markdown 文件：`标题_<conv_id前缀>.md` 存放在输出目录。
- 日志：`output/logs/run_<timestamp>_<runid>.log`（启用时生成 `.jsonl`）。
- 诊断：`output/diagnose_<timestamp>_<runid>.json`（开启 `--diagnose` 时生成）。

## 日志与错误码
- 每行包含结构化上下文：`run_id`、`stage`、`conv_key`、`error_code`/`warning_code`、hint。
- 错误码：`E1001`（JSON 解析失败）、`E1002`（输入不存在）、`E1101`（非法对话）、`E2001`（渲染错误）、`E2002`（抽取错误）、`E3001`（写入/初始化目录失败）。
- 警告码：`W1102`（非字符串内容被强制转为字符串）。
- Traceback：按 `--traceback` 控制；JSONL 始终可安全解析。

## 时区与平台提示
- `--tz` 使用 IANA 名称；Windows 无 IANA 时会警告并退回本地时区。
- 文件名已做截断与保留名防护；超长标题会缩短但保留 ID 后缀以确保唯一。

## 使用建议
- 当内容包含大量 Markdown 时，启用 `--safe-markdown`（或依赖自动围栏）避免排版被劫持。
  - 日志始终写入 stderr 与文件，stdout 仅用于摘要与输出列表。
- 处理巨大 JSON 导出时，可保持默认 INFO 以减少噪音；工具会跳过无效对话并继续处理其他对话。
