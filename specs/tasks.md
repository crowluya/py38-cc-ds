# tasks.md

> 目的：将 `specs/spec.md` + `specs/plan.md` 的 MVP 范围，拆成可执行的原子任务清单（含依赖、并行标记 `[P]`、验证方式）。
> 
> 参考：`TODO.md`（更长的周计划/分阶段清单）、`DEVELOPMENT_WORKFLOW.md`（SDD/TDD 操作流程）、`constitution.md`（不可协商红线）。

## 0. 上下文梳理（给执行者的最小共识）

- **目标**：在 **Python 3.8.10** 上实现 Claude Code 核心工作流能力，重点兼容 **Windows 7 内网** + DeepSeek R1 70B（OpenAI 兼容接口）。
- **MVP 核心能力**：
  - `@file` / `@dir` 上下文注入（Gitignore 感知、噪音目录过滤）。
  - `!command` 命令执行（Win7 PowerShell 2.0 / Unix bash），输出可进入下一轮上下文。
  - 长期记忆文件自动加载：`CLAUDE.md` / `AGENTS.md` / `constitution.md`（含 `@` 模块化导入）。
  - Slash Commands（`.deepcode/commands/` 与 `~/.deepcode/commands/`）与基础 Hooks。
  - 安全：权限规则（deny/allow/ask）、危险操作审批、checkpoint + `/rewind`。
  - Headless 模式（`-p/--print`、JSON 输出）。
- **工程红线**：
  - **严格 TDD**：Red → Green → Refactor。
  - **YAGNI**：只做 spec 明确要求。
  - **显式错误处理**、依赖注入、Python 3.8.10 兼容类型注解。

## 1. 里程碑（Milestones）

- **M1**：项目骨架 + 依赖锁定 + 测试基座可运行
- **M2**：CLI 入口 + 基础交互（Rich/Prompt Toolkit/Questionary）
- **M3**：配置系统（分层加载）+ LLM 客户端抽象 + 至少一种实现可用
- **M4**：交互模型（`@` + `!`）核心逻辑可用（含 Windows 7 兼容性测试）
- **M5**：Agent 基础循环联通关键路径（上下文→LLM→工具→回写上下文）
- **M6**：安全体系（permissions + approval）+ checkpoint + `/rewind`
- **M7**：Slash Commands + Hooks + Headless + 文档/集成测试

## 1.1 需求追踪（User Stories → Tasks）

| User Story | 描述（摘自 spec） | 覆盖任务 |
|---|---|---|
| **US-001** | `@file` / `@dir` 注入上下文（含 `.gitignore` 感知） | T040, T041, T042, T050 |
| **US-002** | `!command` 执行命令并把输出带入下一轮 | T043, T044 |
| **US-003** | 自动加载长期规范（`CLAUDE.md`/`AGENTS.md`/`constitution.md` + 模块化导入） | T051, T052 |
| **US-004** | 自定义 Slash Commands（项目级/用户级、参数、frontmatter） | T080, T081 |
| **US-005** | SDD：`spec.md → plan.md → tasks.md → 执行` | T110, T111, T112, T113, T114 |
| **US-006** | 安全可控：权限、审批、checkpoint、`/rewind` | T070, T071, T072, T073 |

## 2. 任务清单（带依赖/并行标记）

### Phase A：基础设施（骨架/依赖/测试）

- [ ] **T001 初始化项目目录结构（骨架）**
  - **依赖**：无
  - **产物**：`deep_code/` 主包与子包目录、`tests/` 目录、必要的 `__init__.py`
  - **验证**：`python -c "import deep_code"`

- [ ] **T002 依赖清单与锁定（requirements）**
  - **依赖**：T001
  - **产物**：`requirements.txt`、`requirements-frozen.txt`（精确版本，符合 plan.md）
  - **验证**：在 Python 3.8.10 环境 `pip install -r requirements.txt` 成功

- [ ] **T003 测试框架基座（pytest）**
  - **依赖**：T002
  - **产物**：`pytest` 可运行（含基础配置，如最小 `tests/test_smoke.py`）
  - **验证**：`pytest -q` 全绿

- [ ] **T004 安装/分发骨架（setup.py 或等价方案）**
  - **依赖**：T001
  - **产物**：可 `pip install -e .`（以 Windows 7 友好为准）
  - **验证**：可导入、可执行 CLI 入口（后续任务会补齐）

### Phase B：CLI 入口与交互层

- [ ] **T010 CLI 入口（click）最小命令树（TDD）**
  - **依赖**：T003, T004
  - **产物**：`deep_code/cli/main.py`（或等价入口），`--help` 工作
  - **验证**：`python -m deep_code.cli.main --help`

- [ ] **T011 终端输出封装（rich）[P]（TDD）**
  - **依赖**：T010
  - **产物**：输出工具层（如 `Console` 单例/工厂，但避免全局不可测状态）
  - **验证**：单测覆盖 Markdown/代码块展示的基本路径

- [ ] **T012 交互式输入封装（prompt_toolkit）[P]（TDD）**
  - **依赖**：T010
  - **产物**：输入层封装（历史记录、多行输入基础能力）
  - **验证**：单测覆盖“可构造会话对象/可注入依赖”的关键路径

- [ ] **T013 审批/选择交互封装（questionary + colorama）[P]（TDD）**
  - **依赖**：T010
  - **产物**：确认提示组件（Y/n）与 Windows 7 ANSI 初始化
  - **验证**：单测覆盖“审批被拒绝/通过”的分支

### Phase C：配置系统（分层加载）

- [ ] **T020 Settings 数据结构与默认值（TDD）**
  - **依赖**：T003
  - **产物**：`deep_code/config/settings.py`（按 plan.md 的字段：llm/permissions/hooks/default_model...）
  - **验证**：单测覆盖默认值与类型校验（Python 3.8 类型注解兼容）

- [ ] **T021 分层配置加载器（TDD）**
  - **依赖**：T020
  - **产物**：`deep_code/config/loader.py` 支持：用户全局、项目共享、本地覆盖、CLI 覆盖
  - **验证**：表格驱动测试覆盖优先级合并

- [ ] **T022 Windows 7 用户目录与路径展开（TDD）**
  - **依赖**：T021
  - **产物**：`~` 与 `%USERPROFILE%` 兼容策略（集中在一个工具函数/模块）
  - **验证**：单测覆盖多平台路径样例

### Phase D：LLM 集成

- [ ] **T030 定义 `LLMClient` 抽象接口（TDD）**
  - **依赖**：T003
  - **产物**：`deep_code/llm/client.py`（chat_completion/get_model/supports_streaming/supports_tools）
  - **验证**：单测覆盖接口契约（例如最小 fake 实现）

- [ ] **T031 LLM Factory（TDD）**
  - **依赖**：T030, T021
  - **产物**：`deep_code/llm/factory.py` 根据配置选择实现，支持回退策略
  - **验证**：单测覆盖 provider 切换与回退

- [ ] **T032 OpenAIClient 实现（openai==0.28.1）（TDD）**
  - **依赖**：T030, T021
  - **产物**：`deep_code/llm/openai_client.py` 支持 `api_base`、基本错误处理、非流式调用
  - **验证**：单测（用 fake server 或注入方式）覆盖请求构造；不硬编码 key

- [ ] **T033 RequestsClient 备选实现（requests==2.28.2）[P]（TDD）**
  - **依赖**：T030, T021
  - **产物**：`deep_code/llm/requests_client.py`（OpenAI 兼容协议）
  - **验证**：单测覆盖超时/重试/证书配置分支

### Phase E：交互模型（`@` + `!`）

- [ ] **T040 `@`/`!` 解析器（TDD）**
  - **依赖**：T003
  - **产物**：`deep_code/interaction/parser.py`（识别 `@file`、`@dir`、`!command`）
  - **改动点**：`deep_code/interaction/parser.py`，`tests/test_parser.py`
  - **验证**：`pytest -q tests/test_parser.py`
  - **DoD**：`tests/test_parser.py` 覆盖正常/边界/错误三类场景，且全绿

- [ ] **T041 Gitignore 感知目录加载（TDD）**
  - **依赖**：T040
  - **产物**：目录引用时过滤 `.gitignore` + 常见噪音目录（`.git`, `node_modules`, `__pycache__`...）
  - **改动点**：`deep_code/core/context.py` 或 `deep_code/interaction/parser.py`（以最终职责归属为准），`tests/test_parser.py`
  - **验证**：`pytest -q tests/test_parser.py`
  - **DoD**：测试用例显式构造 `.gitignore` + 噪音目录，断言过滤结果正确

- [ ] **T042 上下文格式化（文件/目录树）（TDD）**
  - **依赖**：T040, T041
  - **产物**：统一的上下文片段格式（含路径标识、必要时行号范围）
  - **改动点**：`deep_code/core/context.py`，`tests/test_context.py`
  - **验证**：`pytest -q tests/test_context.py`
  - **DoD**：输出格式至少包含：路径标识、内容边界（开始/结束），且对超长内容有可预测的裁剪策略（通过测试约束）

- [ ] **T043 命令执行器 `CommandExecutor`（TDD）**
  - **依赖**：T003
  - **产物**：`deep_code/core/executor.py`：Windows 7 PowerShell / Unix bash，捕获 stdout/stderr，UTF-8 处理
  - **改动点**：`deep_code/core/executor.py`，`tests/test_executor.py`
  - **验证**：`pytest -q tests/test_executor.py`
  - **DoD**：测试覆盖 return code、stdout/stderr、工作目录、编码参数设置（UTF-8）分支

- [ ] **T044 命令输出注入下一轮上下文（TDD）**
  - **依赖**：T043
  - **产物**：将 `!command` 输出封装为上下文片段并回写对话历史
  - **改动点**：`deep_code/core/agent.py`（或消息历史管理模块），`tests/test_agent.py`
  - **验证**：`pytest -q tests/test_agent.py`
  - **DoD**：在一次回合内执行 `!command` 后，messages 中出现结构化的 tool 结果片段（通过断言约束）

### Phase F：长期记忆与上下文管理

- [ ] **T050 ContextManager：加载文件/目录（TDD）**
  - **依赖**：T042
  - **产物**：`deep_code/core/context.py`：`load_file`/`load_directory`
  - **验证**：单测覆盖读取失败、编码指定为 UTF-8

- [ ] **T051 长期记忆文件自动发现与加载（TDD）**
  - **依赖**：T050
  - **产物**：启动时加载 `CLAUDE.md`/`AGENTS.md`/`constitution.md`（存在则加载，不存在则明确提示）
  - **改动点**：`deep_code/core/context.py`，`tests/test_context.py`
  - **验证**：`pytest -q tests/test_context.py`
  - **DoD**：缺失文件时不崩溃且返回可操作提示；存在文件时内容被加载进长期记忆结构

- [ ] **T052 `CLAUDE.md` 模块化导入（`@` 引用其他文件）（TDD）**
  - **依赖**：T051, T040
  - **产物**：支持 `@` 在记忆文件中递归导入；检测循环引用
  - **改动点**：`deep_code/core/context.py`（或独立的 loader），`tests/test_context.py`
  - **验证**：`pytest -q tests/test_context.py`
  - **DoD**：支持多层导入；循环时给出明确错误（包含导入链路），并由测试固定行为

### Phase G：Agent 引擎（最小闭环）

- [ ] **T060 Agent 基础对话循环（TDD）**
  - **依赖**：T010, T031, T050, T044
  - **产物**：`deep_code/core/agent.py`：维护 messages、调用 LLM、处理工具结果、输出
  - **验证**：集成测试（用 fake LLMClient）覆盖一次完整回合

- [ ] **T061 工具调用编排（仅 MVP 必要）（TDD）**
  - **依赖**：T060
  - **产物**：当 LLM 触发“需要执行命令/需要读取文件”时，走统一编排路径（具体工具协议后续可演进）
  - **验证**：单测覆盖：工具请求→执行→结果回传

### Phase H：安全体系（权限/审批/回滚）

- [ ] **T070 权限规则模型（deny/allow/ask）（TDD）**
  - **依赖**：T020, T013
  - **产物**：`deep_code/security/permissions.py`：文件/命令/网络访问规则
  - **改动点**：`deep_code/security/permissions.py`，`tests/test_permissions.py`
  - **验证**：`pytest -q tests/test_permissions.py`
  - **DoD**：表格驱动测试覆盖 allow/deny/ask、默认最小权限、优先级（更具体规则覆盖更泛规则）

- [ ] **T071 文件读/写与命令执行的审批接入（TDD）**
  - **依赖**：T070, T043, T050
  - **产物**：在执行敏感操作前走审批；拒绝时返回可操作错误
  - **改动点**：`deep_code/security/permissions.py` + 调用方（`core/executor.py`/`core/context.py`），`tests/test_permissions.py`, `tests/test_executor.py`, `tests/test_context.py`
  - **验证**：`pytest -q tests/test_permissions.py tests/test_executor.py tests/test_context.py`
  - **DoD**：ask=拒绝时不执行实际动作；ask=通过时动作执行且有审计信息（至少在返回结构中可见）

- [ ] **T072 Checkpoint 管理器（快照/回滚元数据）（TDD）**
  - **依赖**：T070
  - **产物**：`deep_code/security/checkpoint.py`：会话级 checkpoint 数据结构与持久化方案（MVP 简化）
  - **改动点**：`deep_code/security/checkpoint.py`，`tests/test_checkpoint.py`
  - **验证**：`pytest -q tests/test_checkpoint.py`
  - **DoD**：支持创建/列出/选择 checkpoint；持久化目录可配置且默认在项目内可控位置

- [ ] **T073 `/rewind` 命令：回滚 code / conversation / both（TDD）**
  - **依赖**：T072, T010
  - **产物**：CLI 子命令或交互命令实现 `/rewind`
  - **改动点**：`deep_code/cli/commands.py`（或等价命令模块），`tests/test_rewind.py`
  - **验证**：`pytest -q tests/test_rewind.py`
  - **DoD**：三种模式都可选择且行为可预测；失败时给出明确错误（例如 checkpoint 不存在）

### Phase I：工作流封装（Slash Commands + Hooks）

- [ ] **T080 Slash Commands 发现与解析（TDD）**
  - **依赖**：T021
  - **产物**：`deep_code/interaction/commands.py` 扫描 `.deepcode/commands/` 与 `~/.deepcode/commands/`
  - **改动点**：`deep_code/interaction/commands.py`，`tests/test_commands.py`
  - **验证**：`pytest -q tests/test_commands.py`
  - **DoD**：项目级命令覆盖用户级同名命令；无命令时表现稳定（不崩溃、有提示）

- [ ] **T081 Slash Commands frontmatter + 参数替换（TDD）**
  - **依赖**：T080
  - **产物**：支持 `description/model/allowed-tools`，支持 `$ARGUMENTS`/`$1..$n`
  - **改动点**：`deep_code/interaction/commands.py`，`tests/test_commands.py`
  - **验证**：`pytest -q tests/test_commands.py`
  - **DoD**：frontmatter 解析失败时给出明确错误；参数替换对空参数/多参数都有测试约束

- [ ] **T082 Hooks 系统（事件定义 + 分发 + 脚本执行）（TDD）**
  - **依赖**：T021, T070
  - **产物**：`deep_code/interaction/hooks.py`：SessionStart/PreToolUse/PostToolUse 等最小闭环
  - **改动点**：`deep_code/interaction/hooks.py`，`tests/test_hooks.py`
  - **验证**：`pytest -q tests/test_hooks.py`
  - **DoD**：至少覆盖 1 个事件 + 1 种 matcher + 1 次脚本执行（可用 fake runner 注入）

### Phase J：Headless 模式与输出格式

- [ ] **T090 Headless：`-p/--print` 与 stdin 管道（TDD）**
  - **依赖**：T010, T060
  - **产物**：非交互执行单次 prompt；支持从 stdin 读大文本
  - **验证**：集成测试覆盖：stdin 输入→stdout 输出

- [ ] **T091 JSON / stream-json 输出格式（TDD）**
  - **依赖**：T090
  - **产物**：`--output-format json|stream-json` 输出结构化结果
  - **验证**：单测覆盖 JSON schema 关键字段存在

### Phase K：文档与兼容性验证

- [ ] **T100 Windows 7 兼容性测试清单落地（测试用例优先）**
  - **依赖**：T022, T043
  - **产物**：聚合测试：路径/编码/PowerShell 命令包装
  - **验证**：在 Win7 环境跑过（可先用模拟测试兜底）

- [ ] **T101 DeepSeek 内网端点配置说明（文档）**
  - **依赖**：T032 或 T033
  - **产物**：明确 `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL`、证书配置项
  - **验证**：文档示例可直接复制使用

- [ ] **T102 最小 README（安装/运行/示例）**
  - **依赖**：T010, T060
  - **产物**：快速开始：一次对话、一次 `@file`、一次 `!command`
  - **验证**：按 README 步骤能跑通

### Phase L：SDD 引擎（spec → plan → tasks → 执行）

- [ ] **T110 SDD 任务模型与解析器骨架（TDD）**
  - **依赖**：T003
  - **目标**：定义 `Task` 数据结构与 `tasks.md` 的最小解析规则（支持 dependencies、`[P]`、TDD 标记）
  - **改动点**：`deep_code/core/sdd.py`，`tests/test_sdd.py`
  - **验证**：`pytest -q tests/test_sdd.py`
  - **DoD**：给定一段最小 tasks 文本，能解析出稳定的结构化 Task 列表（含依赖）

- [ ] **T111 从 `spec.md` 生成 `plan.md` 的最小工作流（TDD）**
  - **依赖**：T031
  - **目标**：提供一个 CLI/交互入口，调用 LLM 将 spec 转换为 plan（以模板+LLM 输出为主，MVP 不做复杂解析）
  - **改动点**：`deep_code/core/sdd.py` + CLI 命令模块，`tests/test_sdd_flow.py`
  - **验证**：`pytest -q tests/test_sdd_flow.py`
  - **DoD**：在 fake LLM 下，能把输入 spec 文本写出 plan 文件（路径可配置），且文件写入受权限控制

- [ ] **T112 从 `plan.md` 生成 `tasks.md` 的最小工作流（TDD）**
  - **依赖**：T111
  - **目标**：调用 LLM 将 plan 转换为 tasks（要求任务原子化、含依赖、含 `[P]`）
  - **改动点**：`deep_code/core/sdd.py` + CLI 命令模块，`tests/test_sdd_flow.py`
  - **验证**：`pytest -q tests/test_sdd_flow.py`
  - **DoD**：生成的 tasks 至少包含：任务 ID、依赖字段、验证字段（通过测试做关键字段断言）

- [ ] **T113 任务依赖分析（拓扑排序/循环检测）（TDD）**
  - **依赖**：T110
  - **目标**：构建依赖图，支持拓扑排序；遇到循环依赖报错并给出循环链路
  - **改动点**：`deep_code/core/sdd.py`，`tests/test_sdd.py`
  - **验证**：`pytest -q tests/test_sdd.py`
  - **DoD**：至少覆盖：线性依赖、分叉依赖、循环依赖三类用例

- [ ] **T114 任务执行器（顺序执行 + 最小并行标记识别）（TDD）**
  - **依赖**：T113, T060
  - **目标**：按拓扑顺序执行 tasks；对标 `[P]` 的任务仅做“可并行分组”输出（MVP 不实现复杂调度）
  - **改动点**：`deep_code/core/sdd.py`（或独立 executor），`tests/test_task_runner.py`
  - **验证**：`pytest -q tests/test_task_runner.py`
  - **DoD**：在 fake 执行器注入下，能按依赖顺序调用；并输出可并行分组信息

## 3. 风险点（执行时持续关注）

- **Windows 7 + TLS/证书**：`openai` 库可能受系统 TLS 影响，需保留 `requests` 备选与 `verify_ssl/ca_cert`。
- **PowerShell 2.0 限制**：避免依赖新语法；命令包装与编码设置要明确。
- **TDD 纪律**：任何“先写实现再补测试”都视为违宪；遇到不确定行为先固化为测试。

## 4. 任务执行约定

- **每个任务必须做到**：
  - 写清楚“目标文件/目标函数/可验证命令”。
  - 提供至少一个失败→通过的测试用例。
- **并行策略**：仅对标记 `[P]` 的任务并行；并行前确认不会踩同一模块/同一抽象边界。
