# Claude Code Python MVP - 需求规范（Specification）

**版本**: 1.0  
**日期**: 2024-12-19  
**状态**: 草案

## 1. 项目概述

### 1.1 项目目标

开发一个基于 Python 3.8.10 的 AI 原生开发工作流引擎，实现 Claude Code 的核心设计模式，支持在 Windows 7 内网环境中使用 DeepSeek R1 70B 模型进行 AI 辅助开发。

### 1.2 核心价值

- **规范驱动开发（SDD）**：从需求到实现的完整工作流
- **上下文管理**：解决 AI 协作中的上下文摩擦力
- **工作流封装**：将团队最佳实践固化为可复用资产
- **安全可控**：权限控制、沙箱隔离、检查点回滚

### 1.3 目标用户

- 内网环境下的 Python 开发者
- 需要在 Windows 7 上工作的开发团队
- 希望采用 AI 原生开发工作流的团队

## 2. 用户故事

### 2.1 核心用户故事

**US-001：作为开发者，我希望通过 `@file` 和 `@dir` 注入上下文，让 AI 理解我的代码库**

- **场景**：我在开发时，需要让 AI 理解某个文件或目录的代码
- **验收标准**：
  - 能够通过 `@/path/to/file.py` 引用单个文件
  - 能够通过 `@/path/to/dir/` 引用整个目录
  - 目录引用时自动忽略 `.gitignore` 中的文件
  - 上下文能够正确格式化并传递给 LLM

**US-002：作为开发者，我希望通过 `!command` 执行命令，让 AI 能够验证和操作我的环境**

- **场景**：我需要让 AI 执行测试、查看状态、运行构建等命令
- **验收标准**：
  - 能够通过 `! git status` 执行命令
  - Windows 7 上使用 PowerShell 执行
  - Unix 上使用 bash 执行
  - 命令输出能够作为上下文传递给下一轮对话
  - 输出编码正确处理（UTF-8）

**US-003：作为开发者，我希望 AI 能够记住项目的长期规范，不需要每次重复说明**

- **场景**：每次对话时，AI 应该自动了解项目的技术栈、编码规范、工作流程
- **验收标准**：
  - 自动发现并加载 `CLAUDE.md`（项目操作手册）
  - 自动发现并加载 `AGENTS.md`（跨 Agent 标准）
  - 自动发现并加载 `constitution.md`（项目宪法）
  - 支持模块化导入（`@` 语法导入其他文件）

**US-004：作为开发者，我希望通过自定义命令封装高频工作流**

- **场景**：我经常需要代码审查、生成提交信息、运行测试等工作流
- **验收标准**：
  - 能够定义 `/review` 命令进行代码审查
  - 能够定义 `/commit` 命令生成提交信息
  - 支持项目级命令（`.claude/commands/`）
  - 支持用户级命令（`~/.claude/commands/`）
  - 支持参数传递（`$ARGUMENTS`, `$1/$2...`）

**US-005：作为开发者，我希望通过规范驱动开发流程，从需求到实现**

- **场景**：我有一个新功能想法，希望从需求到实现完整走一遍 SDD 流程
- **验收标准**：
  - 能够生成 `spec.md`（需求规范）
  - 能够生成 `plan.md`（技术方案）
  - 能够生成 `tasks.md`（任务清单）
  - 能够按 tasks 自动执行实现
  - 支持任务依赖分析和并行执行

**US-006：作为开发者，我希望系统能够安全地执行操作，避免意外破坏**

- **场景**：AI 需要修改文件或执行命令时，应该有权限控制和审批机制
- **验收标准**：
  - 文件访问有权限规则（deny/allow/ask）
  - 命令执行有权限规则
  - 危险操作需要用户审批
  - 支持检查点回滚（`/rewind`）

### 2.2 未来用户故事（非 MVP）

- **US-007**：Web UI 界面（未来扩展）
- **US-008**：多 Agent 并行协作（未来扩展）
- **US-009**：完整的 MCP 协议支持（未来扩展）

## 3. 功能需求

### 3.1 核心交互模型

#### 3.1.1 上下文注入（`@`）

- **文件引用**：`@/path/to/file.py`
  - 支持相对路径和绝对路径
  - 支持路径补全
  - 文件内容读取并格式化
- **目录引用**：`@/path/to/dir/`
  - 自动读取目录结构
  - Git 感知（参考 `.gitignore`）
  - 忽略常见噪音目录（`node_modules`, `.git`, `__pycache__` 等）
- **模块化导入**：在 `CLAUDE.md` 中使用 `@` 导入其他文件

#### 3.1.2 命令执行（`!`）

- **命令格式**：`! <command>`
- **执行环境**：
  - Windows 7：使用 PowerShell（`powershell.exe -Command`）
  - Unix：使用 bash（`/bin/bash -c`）
- **输出处理**：
  - 捕获 stdout 和 stderr
  - 编码处理（UTF-8）
  - 输出作为上下文传递给下一轮对话

### 3.2 LLM 集成

#### 3.2.1 抽象接口

- **LLMClient 抽象基类**：
  - `chat_completion()`：统一的聊天完成接口
  - `get_model()`：获取模型名称
  - `supports_streaming()`：是否支持流式
  - `supports_tools()`：是否支持工具调用

#### 3.2.2 实现方式

- **方案 A（推荐）**：使用 `openai==0.28.1` 库
  - 支持 OpenAI 兼容接口（通过 `api_base`）
  - 支持 DeepSeek R1 70B 内网端点
  - 支持流式响应和工具调用
- **方案 B（备选）**：使用 `requests` 手动实现
  - 如果 openai 库在 Windows 7 上有问题，自动回退

#### 3.2.3 配置

- 支持环境变量：`DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`
- 支持 `settings.json` 配置
- 支持内网证书验证（`verify_ssl`, `ca_cert`）

### 3.3 上下文体系

#### 3.3.1 长期记忆文件

- **CLAUDE.md**：项目操作手册
  - 技术栈与环境
  - 编码规范
  - 工作流 SOP
  - Git 规范
- **AGENTS.md**：跨 Agent 标准
  - 项目语言与技术栈
  - 如何启动/构建
  - 如何跑测试与 lint
  - Git/PR 规范
- **constitution.md**：项目宪法
  - 不可协商的工程原则
  - 简单性、TDD、明确性等红线

#### 3.3.2 分层加载

- 企业级配置（如果存在）
- 项目级配置（`.claude/settings.json`）
- 用户级配置（`~/.claude/settings.json`）
- 优先级：CLI 参数 > 项目本地 > 项目共享 > 用户全局

### 3.4 工作流封装

#### 3.4.1 Slash Commands

- **命令格式**：`/command [args]`
- **参数支持**：
  - `$ARGUMENTS`：全部参数
  - `$1/$2/$3...`：位置参数
- **Frontmatter**：YAML 元数据
  - `description`：命令描述
  - `model`：指定模型
  - `allowed-tools`：工具权限
- **作用域**：
  - 项目级：`.claude/commands/`
  - 用户级：`~/.claude/commands/`

#### 3.4.2 Hooks 系统

- **生命周期事件**：
  - SessionStart / SessionEnd
  - UserPromptSubmit
  - PreToolUse / PostToolUse
  - Notification
  - Stop / SubagentStop
- **匹配器**：按工具类型匹配
- **执行方式**：通过 stdin 接收 JSON 上下文

### 3.5 规范驱动开发（SDD）

#### 3.5.1 工作流

```
spec.md → plan.md → tasks.md → 代码实现
```

#### 3.5.2 功能

- **spec.md 生成**：从需求澄清生成规范
- **plan.md 生成**：从规范生成技术方案
- **tasks.md 生成**：从方案生成任务清单
- **任务执行**：按 tasks 自动执行实现
- **依赖分析**：任务依赖关系分析
- **并行标记**：标记可并行执行的任务（`[P]`）

### 3.6 安全体系

#### 3.6.1 权限控制

- **文件访问**：Read/Edit/Write 权限规则
- **命令执行**：命令白名单/黑名单
- **网络访问**：域名白名单
- **审批机制**：ask 模式需要用户确认

#### 3.6.2 Checkpointing

- **会话快照**：代码状态 + 对话状态
- **回滚机制**：`/rewind` 命令
- **三种模式**：
  - Rewind code（只回退代码）
  - Rewind conversation（只回退对话）
  - Rewind code and conversation（全部回退）

### 3.7 编程接口

#### 3.7.1 Headless 模式

- **非交互执行**：`-p/--print` 参数
- **管道支持**：stdin 输入大上下文
- **结构化输出**：
  - `--output-format json`：JSON 格式
  - `--output-format stream-json`：流式 JSON

## 4. 非功能需求

### 4.1 兼容性要求

- **Python 版本**：必须支持 Python 3.8.10（仅此版本）
- **操作系统**：Windows 7（主要目标）+ Unix（支持）
- **内网环境**：支持内网部署和离线安装

### 4.2 性能要求

- **响应时间**：LLM 调用响应时间取决于模型服务
- **上下文管理**：支持 Token 预算管理
- **并发支持**：基础并行支持（标记 `[P]` 的任务）

### 4.3 安全要求

- **权限控制**：默认最小权限
- **审批机制**：危险操作必须审批
- **检查点回滚**：支持会话级回滚
- **内网适配**：支持自签名证书

### 4.4 可维护性要求

- **代码质量**：遵循 constitution.md 的工程原则
- **测试覆盖**：核心功能必须有测试
- **文档完整**：API 文档和使用文档

## 5. 验收标准

### 5.1 功能验收

1. ✅ 能够通过 `@file` 和 `@dir` 注入上下文（Windows 7 路径处理正确）
2. ✅ 能够通过 `!command` 执行 Shell 命令（Windows 7 使用 PowerShell，输出编码正确）
3. ✅ 能够自动加载 `CLAUDE.md` 等长期记忆（跨平台路径处理）
4. ✅ 支持自定义 Slash Commands（`/review`, `/commit` 等）
5. ✅ 支持基础 Hooks（PostToolUse 自动格式化等）
6. ✅ 能够完成 SDD 流程：生成 spec → plan → tasks → 执行
7. ✅ 支持权限控制（文件访问、命令执行审批）
8. ✅ 支持 Checkpointing 和 `/rewind`
9. ✅ 支持 Headless 模式（`-p` 非交互执行）
10. ✅ 能够连接 DeepSeek R1 70B（OpenAI 兼容接口，内网端点配置正确）

### 5.2 兼容性验收

11. ✅ **Python 3.8.10 严格兼容**（所有代码在 Python 3.8.10 上运行无错误）
12. ✅ **Windows 7 兼容性**（在 Windows 7 上完整测试通过，路径、编码、命令执行正常）

### 5.3 质量验收

- 所有核心功能有单元测试
- 测试覆盖率 ≥ 70%
- 代码符合 constitution.md 的工程原则
- 文档完整且准确

## 6. 输出示例

### 6.1 上下文注入示例

```
用户输入：@core/agent.py 请解释这个文件的作用

系统行为：
1. 读取 core/agent.py 文件内容
2. 格式化并注入上下文
3. LLM 基于文件内容回答
```

### 6.2 命令执行示例

```
用户输入：! git status

系统行为：
1. 执行 `powershell.exe -Command "git status"`（Windows 7）
2. 捕获输出
3. 将输出作为上下文传递给下一轮对话
```

### 6.3 Slash Command 示例

```
用户输入：/review core/agent.py

系统行为：
1. 查找 `.claude/commands/review.md` 或 `~/.claude/commands/review.md`
2. 读取命令定义
3. 执行命令逻辑（读取文件、运行检查、生成报告）
```

## 7. 约束与限制

### 7.1 技术约束

- **Python 版本**：仅支持 3.8.10
- **依赖版本**：所有依赖必须兼容 Python 3.8.10
- **Windows 7**：PowerShell 2.0 功能有限
- **内网环境**：可能使用自签名证书

### 7.2 功能约束

- **MVP 范围**：不包含 Web UI
- **并行执行**：基础支持，不包含完整的多 Agent 协作
- **沙箱隔离**：基础隔离，不包含高级沙箱（bubblewrap/socat）

### 7.3 性能约束

- **上下文大小**：受 LLM Token 限制
- **命令执行**：同步执行，不支持异步命令队列
- **并发任务**：基础并行，不包含复杂的任务调度

## 8. 后续扩展方向

- Web UI 界面
- 完整的多 Agent 并行协作
- 完整的 MCP 协议支持（Resources, Prompts）
- 高级沙箱隔离
- CI/CD 集成示例

---

**维护者**: 开发团队  
**最后更新**: 2024-12-19

