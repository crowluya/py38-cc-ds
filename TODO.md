# DeepCode - 实施任务清单

基于 [实施计划](.cursor/plans/deep_code_python_mvp_ec199ec3.plan.md) 的任务跟踪清单。

## Phase 1: 核心基础设施（Week 1-2）

### 1. 项目骨架
- [ ] 创建项目目录结构
  - [ ] `deep_code/` 主包目录
  - [ ] `deep_code/core/` 核心模块
  - [ ] `deep_code/interaction/` 交互模块
  - [ ] `deep_code/security/` 安全模块
  - [ ] `deep_code/extensions/` 扩展模块
  - [ ] `deep_code/llm/` LLM 客户端模块
  - [ ] `deep_code/config/` 配置模块
  - [ ] `deep_code/cli/` CLI 模块
  - [ ] `tests/` 测试目录
- [ ] 设置 Python 3.8.10 严格兼容的依赖
  - [ ] 创建 `requirements.txt`（精确版本）
  - [ ] 创建 `requirements-frozen.txt`（锁定版本）
  - [ ] 验证所有依赖在 Python 3.8.10 上可用
- [ ] 基础 CLI 框架
  - [ ] 安装并配置 `click == 7.1.2`
  - [ ] 创建基础 CLI 入口（`cli/main.py`）
  - [ ] 实现基本命令结构
- [ ] 终端美化与交互库集成
  - [ ] 安装 `rich==12.6.0`（Markdown、代码高亮、面板、进度条）
  - [ ] 安装 `prompt_toolkit==3.0.39`（交互式输入、历史记录、自动补全）
  - [ ] 安装 `questionary==1.10.0`（选择菜单、确认提示）
  - [ ] 安装 `colorama==0.4.6`（Windows 7 ANSI 颜色支持）
  - [ ] 测试 Windows 7 兼容性
- [ ] Windows 7 兼容性测试
  - [ ] 路径处理测试（`pathlib.Path`）
  - [ ] 编码处理测试（UTF-8 强制）
  - [ ] 用户目录处理测试（`%USERPROFILE%` vs `~`）

### 2. LLM 集成
- [ ] 抽象接口设计
  - [ ] 定义 `LLMClient` 抽象基类（`llm/client.py`）
    - [ ] `chat_completion()` 方法
    - [ ] `get_model()` 方法
    - [ ] `supports_streaming()` 方法
    - [ ] `supports_tools()` 方法
  - [ ] 实现工厂模式（`llm/factory.py`）
    - [ ] `LLMClientFactory.create()` 方法
    - [ ] 配置驱动的实现选择
    - [ ] 自动回退机制
- [ ] OpenAIClient 实现（方案 A，推荐）
  - [ ] 实现 `OpenAIClient` 类（`llm/openai_client.py`）
  - [ ] 支持 `api_base` 参数（DeepSeek 内网端点）
  - [ ] 实现流式响应处理
  - [ ] 实现工具调用（Function Calling）
  - [ ] 错误处理与重试
  - [ ] Windows 7 SSL/TLS 兼容性测试
- [ ] RequestsClient 实现（方案 B，备选）
  - [ ] 实现 `RequestsClient` 类（`llm/requests_client.py`）
  - [ ] 手动实现 OpenAI 格式请求
  - [ ] 实现 SSE 流式响应解析
  - [ ] 实现重试策略（指数退避）
  - [ ] 实现工具调用格式转换
  - [ ] 内网证书验证支持
- [ ] 配置支持
  - [ ] 环境变量支持（`DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`）
  - [ ] `settings.json` 配置解析
  - [ ] 内网证书配置（`verify_ssl`, `ca_cert`）

### 3. 配置系统
- [ ] 分层配置加载器（`config/loader.py`）
  - [ ] 用户全局配置（`~/.pycc/settings.json`）
  - [ ] 项目共享配置（`.pycc/settings.json`）
  - [ ] 项目本地配置（`.pycc/settings.local.json`）
  - [ ] CLI 参数覆盖
  - [ ] 配置合并优先级实现
- [ ] `settings.json` 解析
  - [ ] JSON 解析与验证
  - [ ] 配置项类型检查
  - [ ] 默认值处理
- [ ] Windows 7 用户目录处理
  - [ ] `%USERPROFILE%` 环境变量支持
  - [ ] `~` 路径展开
  - [ ] 跨平台路径统一处理

## Phase 2: 交互模型（Week 2-3）

### 4. 上下文注入（`@`）
- [ ] 交互解析器（`interaction/parser.py`）
  - [ ] `@file` 文件引用解析
  - [ ] `@dir` 目录引用解析
  - [ ] 路径补全支持
  - [ ] 相对路径与绝对路径处理
- [ ] Git 感知
  - [ ] `.gitignore` 文件读取
  - [ ] 忽略文件过滤（`node_modules`, `.git` 等）
  - [ ] Git 仓库检测
- [ ] 上下文格式化与注入
  - [ ] 文件内容读取与格式化
  - [ ] 目录结构树生成
  - [ ] 上下文标记（文件路径、行号等）

### 5. 命令执行（`!`）
- [ ] 命令执行器（`core/executor.py`）
  - [ ] Shell 命令解析
  - [ ] Windows 7 使用 PowerShell（`powershell.exe -Command`），Unix 使用 `bash`
  - [ ] 支持 PowerShell 脚本和 cmdlet
  - [ ] 处理 PowerShell 2.0 的限制
  - [ ] 使用 `subprocess` 模块执行
  - [ ] 工作目录设置
- [ ] 输出捕获
  - [ ] stdout/stderr 捕获
  - [ ] 编码处理（UTF-8 强制）
  - [ ] 错误码处理
- [ ] 输出作为上下文传递
  - [ ] 命令输出格式化
  - [ ] 集成到对话上下文
- [ ] Windows 7 特定处理
  - [ ] 路径转换（`/` vs `\`）
  - [ ] 编码处理（PowerShell 输出 UTF-8）
  - [ ] PowerShell 2.0 兼容性测试
  - [ ] PowerShell 命令语法处理
  - [ ] 命令兼容性测试

### 6. 基础 Agent 循环
- [ ] Agent 引擎（`core/agent.py`）
  - [ ] 对话管理
    - [ ] 消息历史维护
    - [ ] 上下文管理
    - [ ] 会话状态保存
  - [ ] 工具调用处理
    - [ ] 工具定义解析
    - [ ] 工具调用编排
    - [ ] 工具结果处理
  - [ ] 安全检查与审批
    - [ ] 权限检查
    - [ ] 用户审批流程
- [ ] 终端输出美化
  - [ ] 集成 `rich` 库
    - [ ] 对话显示格式化
    - [ ] 代码块语法高亮（Python, JSON, YAML 等）
    - [ ] 表格显示（对齐、边框、颜色）
    - [ ] Markdown 渲染（在 Win7 上完美显示）
    - [ ] 面板（Panel）显示
    - [ ] 进度条（实时进度、多任务进度）
  - [ ] 集成 `colorama` 库
    - [ ] Windows 7 ANSI 颜色支持
    - [ ] 颜色初始化
  - [ ] 进度条与状态提示
    - [ ] 流式响应进度显示
    - [ ] 任务执行状态
- [ ] 交互式输入
  - [ ] 集成 `prompt_toolkit` 库
    - [ ] 替代 `input()` 实现交互式输入
    - [ ] 历史记录功能（上下箭头浏览）
    - [ ] 自动补全功能（Tab 键补全文件路径、命令等）
    - [ ] 多行输入支持（Shift+Enter）
    - [ ] 输入时实时语法高亮
    - [ ] 鼠标支持（点击、选择）
  - [ ] 集成 `questionary` 库
    - [ ] 安全确认提示（替代 `input()` 做 Y/n 确认）
    - [ ] 交互式单选菜单
    - [ ] 交互式多选菜单
    - [ ] 输入验证（必填、格式、范围等）
    - [ ] 密码输入（隐藏输入）
    - [ ] 文件/目录选择器
  - [ ] 用户审批流程
    - [ ] 命令执行前确认（使用 questionary）
    - [ ] 文件修改前确认
    - [ ] 批量操作确认

## Phase 3: 上下文体系（Week 3-4）

### 7. 长期记忆
- [ ] 上下文管理器（`core/context.py`）
  - [ ] `CLAUDE.md` 自动发现与加载
    - [ ] 项目根目录查找
    - [ ] 文件内容读取
    - [ ] 启动时自动加载
  - [ ] `AGENTS.md` 支持
    - [ ] 跨 Agent 标准格式解析
    - [ ] 项目信息提取
  - [ ] `constitution.md` 支持
    - [ ] 项目宪法加载
    - [ ] 不可协商原则解析
  - [ ] 模块化导入（`@` 语法）
    - [ ] 文件引用解析
    - [ ] 递归导入检测（避免循环）
    - [ ] 导入路径解析
- [ ] 分层加载机制
  - [ ] 企业级配置（如果存在）
  - [ ] 项目级配置
  - [ ] 用户级配置
  - [ ] 优先级合并

### 8. 上下文优化
- [ ] 上下文压缩
  - [ ] Token 计数
  - [ ] 内容压缩策略
  - [ ] 摘要生成
- [ ] 优先级排序
  - [ ] 上下文重要性评估
  - [ ] 排序算法实现
- [ ] Token 预算管理
  - [ ] 预算计算
  - [ ] 超预算处理策略
  - [ ] 动态调整

## Phase 4: 工作流封装（Week 4-5）

### 9. Slash Commands
- [ ] 命令管理器（`interaction/commands.py`）
  - [ ] 命令发现
    - [ ] 项目级命令（`.pycc/commands/`）
    - [ ] 用户级命令（`~/.pycc/commands/`）
    - [ ] 命令扫描与索引
  - [ ] 参数解析
    - [ ] `$ARGUMENTS` 全部参数捕获
    - [ ] `$1/$2/$3...` 位置参数解析
    - [ ] 参数验证
  - [ ] Frontmatter 解析
    - [ ] YAML Frontmatter 提取
    - [ ] 元数据解析（description, model, allowed-tools 等）
  - [ ] 命令执行编排
    - [ ] 命令模板渲染
    - [ ] 参数替换
    - [ ] 执行上下文准备
- [ ] 内置命令示例
  - [ ] `/review` 代码审查命令
  - [ ] `/commit` 提交信息生成命令
  - [ ] `/status` 状态查看命令

### 10. Hooks 系统
- [ ] Hooks 管理器（`interaction/hooks.py`）
  - [ ] 生命周期事件定义
    - [ ] SessionStart / SessionEnd
    - [ ] UserPromptSubmit
    - [ ] PreToolUse / PostToolUse
    - [ ] Notification
    - [ ] Stop / SubagentStop
  - [ ] 事件触发机制
    - [ ] 事件监听器注册
    - [ ] 事件分发
    - [ ] 异步执行支持
  - [ ] Matcher 匹配逻辑
    - [ ] 工具类型匹配
    - [ ] 文件路径匹配
    - [ ] 正则表达式匹配
  - [ ] Hook 脚本执行
    - [ ] 脚本调用（Python/Shell）
    - [ ] stdin JSON 上下文传递
    - [ ] 输出捕获与处理
- [ ] 示例 Hooks
  - [ ] PostToolUse 自动格式化（Go 文件）
  - [ ] PreToolUse 主分支保护
  - [ ] SessionStart 环境初始化

## Phase 5: 规范驱动开发（Week 5-6）

### 11. SDD 引擎
- [ ] SDD 引擎（`core/sdd.py`）
  - [ ] `spec.md` 模板与解析
    - [ ] Markdown 解析
    - [ ] 结构化提取（需求、验收标准等）
    - [ ] 模板验证
  - [ ] `plan.md` 生成（技术方案）
    - [ ] 技术选型分析
    - [ ] 架构设计生成
    - [ ] 合宪性检查清单
    - [ ] 项目结构细化
  - [ ] `tasks.md` 生成（任务分解）
    - [ ] 任务原子化
    - [ ] 依赖关系分析
    - [ ] 并行标记识别（`[P]`）
    - [ ] TDD 编排
  - [ ] 依赖分析
    - [ ] 任务依赖图构建
    - [ ] 拓扑排序
    - [ ] 循环依赖检测
- [ ] 规范产物管理
  - [ ] `specs/` 目录结构
  - [ ] 版本管理
  - [ ] 规范验证

### 12. 任务执行
- [ ] 任务执行器
  - [ ] 任务解析与排序
    - [ ] `tasks.md` 解析
    - [ ] 依赖排序
    - [ ] 执行顺序确定
  - [ ] 顺序执行
    - [ ] 任务逐个执行
    - [ ] 错误处理
    - [ ] 执行状态跟踪
  - [ ] 基础并行支持
    - [ ] `[P]` 标记识别
    - [ ] 并行任务调度
    - [ ] 结果合并

## Phase 6: 安全体系（Week 6-7）

### 13. 权限控制
- [ ] 权限管理器（`security/permissions.py`）
  - [ ] 文件访问规则
    - [ ] Read/Edit/Write 权限定义
    - [ ] 路径匹配规则（deny/allow/ask）
    - [ ] 敏感文件保护（`.env`, secrets 等）
  - [ ] 命令执行规则
    - [ ] 命令白名单/黑名单
    - [ ] 危险命令检测（`rm`, `git push --force` 等）
    - [ ] 命令前缀匹配
  - [ ] 网络访问规则
    - [ ] 域名白名单
    - [ ] WebFetch 权限控制
  - [ ] 审批机制（ask 模式）
    - [ ] 用户交互提示
    - [ ] 审批状态管理
    - [ ] 审批历史记录

### 14. Checkpointing
- [ ] 检查点管理器（`security/checkpoint.py`）
  - [ ] 会话快照（代码状态）
    - [ ] 文件状态捕获
    - [ ] 变更跟踪
    - [ ] 快照存储
  - [ ] 对话历史保存
    - [ ] 消息历史序列化
    - [ ] 上下文状态保存
  - [ ] `/rewind` 命令实现
    - [ ] 检查点列表显示
    - [ ] 回退操作
  - [ ] 三种回退模式
    - [ ] Rewind code（只回退代码）
    - [ ] Rewind conversation（只回退对话）
    - [ ] Rewind code and conversation（全部回退）

### 15. 基础沙箱（可选，MVP 可简化）
- [ ] 沙箱管理器（`security/sandbox.py`）
  - [ ] 文件系统限制
    - [ ] 工作目录隔离
    - [ ] 写权限限制
    - [ ] 读权限控制
  - [ ] 网络隔离
    - [ ] 网络请求拦截
    - [ ] 代理配置
    - [ ] 域名白名单

## Phase 7: 扩展能力（Week 7-8）

### 16. MCP 基础支持
- [ ] MCP 协议实现（`extensions/mcp.py`）
  - [ ] MCP 协议解析
    - [ ] 消息格式定义
    - [ ] 请求/响应处理
  - [ ] Tools 调用
    - [ ] 工具定义
    - [ ] 工具调用处理
    - [ ] 结果返回
  - [ ] 本地 stdio transport
    - [ ] stdin/stdout 通信
    - [ ] 进程管理
    - [ ] 错误处理
- [ ] MCP Server 示例
  - [ ] Hello World MCP Server
  - [ ] GitHub MCP Server 集成

### 17. Skills 系统
- [ ] Skills 管理器（`extensions/skills.py`）
  - [ ] Skill 发现与加载
    - [ ] 项目级 Skills（`.pycc/skills/`）
    - [ ] 用户级 Skills（`~/.pycc/skills/`）
    - [ ] `SKILL.md` 文件解析
  - [ ] 渐进式披露（元数据索引）
    - [ ] Level 1：元数据索引（description）
    - [ ] Level 2：核心指令（触发时加载）
    - [ ] Level 3+：辅助资源（按需加载）
  - [ ] Skill 激活机制
    - [ ] 语义匹配
    - [ ] 关键词触发
    - [ ] 显式调用

### 18. Subagents 基础
- [ ] Subagents 管理器（`extensions/subagents.py`）
  - [ ] Subagent 定义与发现
    - [ ] 项目级 Subagents（`.pycc/agents/`）
    - [ ] 用户级 Subagents（`~/.pycc/agents/`）
    - [ ] `.md` 文件解析（YAML Frontmatter）
  - [ ] 独立上下文管理
    - [ ] 上下文隔离
    - [ ] 独立消息历史
    - [ ] 独立工具权限
  - [ ] 调用支持
    - [ ] 隐式调用（根据 description）
    - [ ] 显式调用（用户指定）
    - [ ] 链式编排（多个 Subagent 协作）

## Phase 8: 编程接口（Week 8）

### 19. Headless 模式
- [ ] Headless 实现（`cli/commands.py`）
  - [ ] `-p/--print` 非交互执行
    - [ ] 命令行参数解析
    - [ ] 非交互模式标志
    - [ ] 单次执行流程
  - [ ] stdin 管道支持
    - [ ] 标准输入读取
    - [ ] 大上下文处理
    - [ ] 流式输入支持
  - [ ] JSON 输出格式
    - [ ] 结构化 JSON 输出
    - [ ] 执行报告格式
    - [ ] 错误信息格式
  - [ ] stream-json 支持
    - [ ] JSONL 格式输出
    - [ ] 实时流式输出
    - [ ] 进度信息输出

### 20. 集成测试与文档
- [ ] 端到端测试
  - [ ] 核心功能测试
  - [ ] 交互模型测试
  - [ ] 工作流测试
  - [ ] Windows 7 兼容性测试
  - [ ] Python 3.8.10 兼容性测试
- [ ] 使用文档
  - [ ] README.md 项目说明
  - [ ] 安装指南
  - [ ] 快速开始教程
  - [ ] API 文档
  - [ ] 配置说明
- [ ] 示例项目
  - [ ] 示例项目结构
  - [ ] 示例 `CLAUDE.md`
  - [ ] 示例 `constitution.md`
  - [ ] 示例 Slash Commands
  - [ ] 示例 Hooks

## 验收标准检查清单

- [ ] 能够通过 `@file` 和 `@dir` 注入上下文（Windows 7 路径处理正确）
- [ ] 能够通过 `!command` 执行 Shell 命令（Windows 7 使用 PowerShell，输出编码正确）
- [ ] 能够自动加载 `CLAUDE.md` 等长期记忆（跨平台路径处理）
- [ ] 支持自定义 Slash Commands（`/review`, `/commit` 等）
- [ ] 支持基础 Hooks（PostToolUse 自动格式化等）
- [ ] 能够完成 SDD 流程：生成 spec → plan → tasks → 执行
- [ ] 支持权限控制（文件访问、命令执行审批）
- [ ] 支持 Checkpointing 和 `/rewind`
- [ ] 支持 Headless 模式（`-p` 非交互执行）
- [ ] 能够连接 DeepSeek R1 70B（OpenAI 兼容接口，内网端点配置正确）
- [ ] **Python 3.8.10 严格兼容**（所有代码在 Python 3.8.10 上运行无错误）
- [ ] **Windows 7 兼容性**（在 Windows 7 上完整测试通过，路径、编码、命令执行正常）

## 技术债务与后续优化

- [ ] 性能优化（上下文压缩、缓存等）
- [ ] 错误处理完善（更详细的错误信息）
- [ ] 日志系统（结构化日志、日志级别）
- [ ] 监控与指标（执行时间、Token 消耗等）
- [ ] 完整 MCP 协议支持（Resources, Prompts）
- [ ] 高级沙箱隔离（bubblewrap/socat）
- [ ] 多 Agent 并行执行（worktree + 多会话）
- [ ] CI/CD 集成示例（GitHub Actions）

---

**最后更新**: 2024-12-19
**项目**: DeepCode
**目标环境**: Python 3.8.10 + Windows 7

