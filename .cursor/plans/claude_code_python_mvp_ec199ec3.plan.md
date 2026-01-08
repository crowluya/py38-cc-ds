---
name: Claude Code Python MVP
overview: 基于 Claude Code 设计模式，使用 Python 3.8.10（仅支持此版本）实现一个接近完整功能的 AI 原生开发工作流引擎，支持 OpenAI 兼容接口（DeepSeek R1 70B），包含规范驱动开发、上下文管理、交互模型、工作流封装、安全控制等核心能力。目标运行环境：Windows 7 内网环境。
todos: []
---

#Claude Code Python MVP 实施计划

## 一、核心设计模式梳理

### 1.1 规范驱动开发（SDD）

- **工作流**：`spec.md` → `plan.md` → `tasks.md` → 代码实现
- **核心思想**：规范是 Single Source of Truth，代码是规范的编译产物
- **实现要点**：
- 规范解析与验证
- 多阶段编译流程
- 任务依赖分析
- 并行执行标记

### 1.2 上下文体系（分层记忆）

- **短期记忆**：`@file` / `@dir` - 一次性上下文注入
- **长期记忆**：
- `CLAUDE.md` - 项目操作手册
- `AGENTS.md` - 跨 Agent 标准（行业趋势）
- `constitution.md` - 项目宪法（不可协商原则）
- **分层加载**：企业级 → 项目级 → 用户级
- **模块化导入**：支持 `@` 语法导入其他文件

### 1.3 交互模型

- **`@` 符号**：上下文注入（文件/目录引用）
- **`!` 符号**：命令执行（Shell 命令）
- **命令输出即上下文**：执行结果自动进入下一轮对话

### 1.4 工作流封装

- **Slash Commands**：`/command` 格式，支持参数（`$ARGUMENTS`, `$1/$2...`）
- **作用域**：项目级（`.claude/commands/`）vs 用户级（`~/.claude/commands/`）
- **Frontmatter**：YAML 元数据（description, model, allowed-tools 等）

### 1.5 事件驱动（Hooks）

- **生命周期事件**：SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Notification, Stop
- **配置方式**：`settings.json` 中的 `hooks.<EventName>[]`
- **匹配器**：`matcher` 指定触发的工具类型
- **执行命令**：通过 stdin 接收 JSON 上下文

### 1.6 能力扩展

- **MCP (Model Context Protocol)**：连接外部系统的标准协议
- Tools：可执行动作
- Resources：可引用数据（用于 `@`）
- Prompts：模板化工作流
- **Skills**：专家知识胶囊（渐进式披露）
- **Subagents**：多智能体协作（独立上下文）

### 1.7 安全体系

- **Permissions**：文件访问（Read/Edit/Write）、命令执行、网络访问
- **Sandbox**：文件系统隔离、网络隔离
- **Checkpointing**：会话级快照（代码状态 + 对话状态）

### 1.8 编程接口

- **Headless 模式**：`-p/--print` 非交互执行
- **结构化输出**：`--output-format json/stream-json`
- **管道支持**：stdin 输入大上下文

## 二、技术架构设计

### 2.1 项目结构

```javascript
py38-claude-code/
├── claude_code/
│   ├── __init__.py
│   ├── core/
│   │   ├── agent.py          # 核心 Agent 引擎
│   │   ├── context.py        # 上下文管理
│   │   ├── executor.py       # 命令执行器
│   │   └── sdd.py            # 规范驱动开发引擎
│   ├── interaction/
│   │   ├── parser.py         # @ 和 ! 解析器
│   │   ├── commands.py       # Slash Commands 管理
│   │   └── hooks.py          # Hooks 事件系统
│   ├── security/
│   │   ├── permissions.py    # 权限控制
│   │   ├── sandbox.py        # 沙箱隔离
│   │   └── checkpoint.py     # 检查点管理
│   ├── extensions/
│   │   ├── mcp.py           # MCP 协议实现
│   │   ├── skills.py        # Skills 管理
│   │   └── subagents.py     # Subagents 管理
│   ├── llm/
│   │   ├── client.py        # LLM 客户端抽象接口（ABC）
│   │   ├── openai_client.py # 使用 openai 库的实现
│   │   ├── requests_client.py # 使用 requests 手动实现
│   │   ├── factory.py       # 工厂模式创建客户端
│   │   └── models.py        # 消息/工具定义
│   ├── config/
│   │   ├── settings.py      # 配置管理
│   │   └── loader.py        # 分层配置加载
│   └── cli/
│       ├── main.py          # CLI 入口
│       └── commands.py      # CLI 命令定义
├── tests/
├── .claude/                  # 项目级配置
│   ├── settings.json
│   ├── commands/
│   ├── skills/
│   ├── agents/
│   └── hooks/
├── specs/                    # SDD 产物区
├── CLAUDE.md
├── AGENTS.md
├── constitution.md
├── requirements.txt
├── setup.py
└── README.md
```



### 2.2 核心模块设计

#### 2.2.1 Agent 引擎 (`core/agent.py`)

- **职责**：协调所有子系统，管理对话循环
- **关键功能**：
- 消息历史管理
- 工具调用编排
- 上下文注入处理
- 命令执行协调
- 安全检查与审批

#### 2.2.2 上下文管理 (`core/context.py`)

- **职责**：管理短期和长期上下文
- **关键功能**：
- `@file` / `@dir` 解析与加载
- `CLAUDE.md` / `AGENTS.md` / `constitution.md` 自动发现
- 分层配置加载（企业/项目/用户）
- 模块化导入（`@` 语法）
- 上下文压缩与优化

#### 2.2.3 交互解析器 (`interaction/parser.py`)

- **职责**：解析用户输入中的 `@` 和 `!` 符号
- **关键功能**：
- 路径解析与验证
- Git 感知（参考 `.gitignore`）
- 命令提取与参数解析

#### 2.2.4 命令执行器 (`core/executor.py`)

- **职责**：安全执行 Shell 命令
- **关键功能**：
- 权限检查
- 沙箱隔离
- 输出捕获与格式化
- 错误处理

#### 2.2.5 SDD 引擎 (`core/sdd.py`)

- **职责**：规范驱动开发流程管理
- **关键功能**：
- `spec.md` 解析与验证
- `plan.md` 生成（技术方案）
- `tasks.md` 生成（任务分解）
- 任务依赖分析
- 并行执行标记识别

#### 2.2.6 LLM 客户端（抽象接口 + 多种实现）

- **职责**：统一的 LLM 接口，支持多种实现方式
- **架构设计**：
- `llm/client.py`：抽象接口 `LLMClient`（ABC 基类）
- `llm/openai_client.py`：使用 `openai` 库的实现
- `llm/requests_client.py`：使用 `requests` 手动实现
- `llm/factory.py`：工厂模式创建客户端实例
- **关键功能**：
- 统一的 `chat_completion()` 接口
- 流式响应支持（Iterator）
- 工具调用（Function Calling）
- 错误重试与异常处理
- 配置驱动的实现切换（通过 `settings.json`）

#### 2.2.7 配置管理 (`config/settings.py`)

- **职责**：分层配置加载与合并
- **关键功能**：
- 优先级：CLI 参数 > 项目 local > 项目共享 > 用户全局
- 权限规则解析
- Hooks 配置加载
- 模型映射配置

#### 2.2.8 安全模块 (`security/`)

- **Permissions**：
- 文件访问规则（deny/allow/ask）
- 命令执行规则
- 网络访问规则
- **Sandbox**：
- 文件系统隔离（chroot 或类似机制）
- 网络隔离（代理拦截）
- **Checkpointing**：
- 会话快照（代码 + 对话）
- 回滚机制（/rewind）

## 三、MVP 实施路线图

### Phase 1: 核心基础设施（Week 1-2）

1. **项目骨架**

- 创建项目结构
- 设置 Python 3.8.10 严格兼容的依赖（requirements.txt + requirements-frozen.txt）
- 基础 CLI 框架（click 7.1.2）
- Windows 7 路径处理测试
- 编码处理（UTF-8 强制）

2. **LLM 集成**

- **抽象接口设计**：
- 定义 `LLMClient` 抽象基类（ABC）
- 统一接口：`chat_completion()`, `get_model()`, `supports_streaming()`, `supports_tools()`
- 工厂模式：`LLMClientFactory.create()` 根据配置创建实例
- **两种实现**：
- **OpenAIClient**：使用 `openai==0.28.1` 库（推荐）
    - 通过 `api_base` 参数指定 DeepSeek 内网端点
    - 代码简洁，API 封装完善
- **RequestsClient**：使用 `requests` 手动实现（备选）
    - 完全控制 HTTP 请求细节
    - 更好的内网适配（证书、代理）
- **配置驱动切换**：
- 通过 `settings.json` 的 `llm.provider` 字段选择实现
- 支持运行时切换，无需修改代码
- 自动回退：如果 `openai` 库未安装，自动使用 `requests`
- **功能支持**：
- 支持 DeepSeek R1 70B（内网端点配置，支持环境变量）
- 消息格式与工具调用支持（Function Calling）
- 流式响应处理（两种实现都支持）
- SSL/TLS 配置（Windows 7 兼容）
- 内网证书验证选项（可配置 `verify=False` 或自定义 CA）

3. **配置系统**

- 分层配置加载器
- `settings.json` 解析
- 环境变量支持（API Key, Base URL）
- Windows 7 用户目录处理（`%USERPROFILE%` vs `~`）

### Phase 2: 交互模型（Week 2-3）

4. **上下文注入（`@`）**

- 文件引用解析
- 目录引用（Git 感知）
- 上下文格式化与注入

5. **命令执行（`!`）**

- Shell 命令执行（Windows 7 使用 `cmd.exe`，Unix 使用 `bash`）
- 输出捕获（使用 `subprocess`，正确处理编码）
- 输出作为上下文传递
- Windows 7 特定命令处理（路径转换、编码处理）

6. **基础 Agent 循环**

- 对话管理
- 消息历史
- 工具调用处理
- **终端输出美化**（使用 rich/colorama）
- 使用 `rich` 显示对话、代码块、表格
- 使用 `colorama` 确保 Windows 7 颜色支持
- 进度条、状态提示等

### Phase 3: 上下文体系（Week 3-4）

7. **长期记忆**

- `CLAUDE.md` 自动发现与加载
- `AGENTS.md` 支持
- `constitution.md` 支持
- 模块化导入（`@` 语法）

8. **上下文优化**

- 上下文压缩
- 优先级排序
- Token 预算管理

### Phase 4: 工作流封装（Week 4-5）

9. **Slash Commands**

- 命令发现（项目级/用户级）
- 参数解析（`$ARGUMENTS`, `$1/$2...`）
- Frontmatter 解析
- 命令执行编排

10. **Hooks 系统**

    - 生命周期事件定义
    - 事件触发机制
    - Matcher 匹配逻辑
    - Hook 脚本执行

### Phase 5: 规范驱动开发（Week 5-6）

11. **SDD 引擎**

    - `spec.md` 模板与解析
    - `plan.md` 生成（技术方案）
    - `tasks.md` 生成（任务分解）
    - 依赖分析
    - 并行标记识别

12. **任务执行**

    - 任务解析与排序
    - 顺序执行
    - 基础并行支持（标记 `[P]` 的任务）

### Phase 6: 安全体系（Week 6-7）

13. **权限控制**

    - 文件访问规则
    - 命令执行规则
    - 审批机制（ask 模式）

14. **Checkpointing**

    - 会话快照（代码状态）
    - 对话历史保存
    - `/rewind` 命令实现
    - 三种回退模式

15. **基础沙箱**（可选，MVP 可简化）

    - 文件系统限制
    - 工作目录隔离

### Phase 7: 扩展能力（Week 7-8）

16. **MCP 基础支持**

    - MCP 协议实现（简化版）
    - Tools 调用
    - 本地 stdio transport

17. **Skills 系统**

    - Skill 发现与加载
    - 渐进式披露（元数据索引）
    - Skill 激活机制

18. **Subagents 基础**

    - Subagent 定义与发现
    - 独立上下文管理
    - 显式调用支持

### Phase 8: 编程接口（Week 8）

19. **Headless 模式**

    - `-p/--print` 非交互执行
    - stdin 管道支持
    - JSON 输出格式
    - stream-json 支持

20. **集成测试与文档**

    - 端到端测试
    - 使用文档
    - 示例项目

## 四、技术选型（Python 3.8.10 + Windows 7 严格兼容）

### 4.1 核心依赖（精确版本要求）

- **CLI 框架**：`click == 7.1.2`（最后支持 Python 3.8.10 的稳定版本）
- 注意：click 8.x 需要 Python 3.6+，但测试确保 7.1.2 在 3.8.10 上稳定
- **LLM 客户端**：
- **方案 A（推荐）**：`openai == 0.28.1`（最后支持 Python 3.8 的版本）
    - OpenAI 官方库，API 封装完善，代码更简洁
    - 0.28.1 支持 Python 3.8，1.0+ 需要 Python 3.9+
    - 支持 OpenAI 兼容接口（通过 `api_base` 参数）
- **方案 B（备选）**：`requests == 2.28.2`（手动实现 OpenAI 格式请求）
    - 更底层控制，但代码量更多
    - 如果 `openai` 库在 Windows 7 上有问题，使用此方案
- **终端格式化**：
- **`colorama == 0.4.6`**（必需，Windows 7 ANSI 颜色支持）
    - Windows 7 上 ANSI 转义序列需要 colorama 才能正常显示
    - 轻量级，兼容性好
- **`rich == 12.6.0`**（推荐，功能强大的终端格式化）
    - 支持表格、进度条、语法高亮、Markdown 渲染等
    - 12.6.0 是最后支持 Python 3.8 的版本（13.0+ 需要 Python 3.9+）
    - 如果只需要基本颜色，可以只用 colorama
- **配置解析**：`pyyaml == 5.4.1`（最后支持 Python 3.8.10 的版本）
- **Git 集成**：`GitPython == 3.1.40`（兼容 Python 3.8.10 和 Windows 7）
- **文件监控**：`watchdog == 2.1.9`（可选，Windows 7 兼容的最后版本）

### 4.2 可选依赖

- **Markdown 解析**：`markdown == 3.4.4`（规范解析，Python 3.8.10 兼容）
- **JSON Schema**：`jsonschema == 4.17.3`（配置验证，最后支持 3.8 的版本）
- **异步支持**：`asyncio`（Python 3.8.10 内置，但需谨慎使用）

### 4.3 Python 3.8.10 严格限制

- **禁止使用**：
- `:=` 赋值表达式（Python 3.8+ 支持，但 3.8.10 早期版本可能有 bug）
- `typing.Literal`（Python 3.8+，但需确认 3.8.10 支持）
- `f"{var=}"` 调试语法（Python 3.8+，但 3.8.10 可能不支持）
- **必须使用**：
- `from typing import List, Dict, Optional, Union, Tuple`（显式导入）
- `asyncio.run()` 而非直接 `await`（兼容性更好）
- `pathlib.Path` 而非 `os.path`（跨平台更好）
- **类型提示**：
- 使用 `from __future__ import annotations`（延迟求值，避免 3.8.10 的某些限制）
- 或使用字符串类型注解：`def func() -> "ReturnType":`

### 4.4 Windows 7 特定考虑

- **路径处理**：
- 使用 `pathlib.Path` 统一处理路径（自动处理 Windows/Unix 差异）
- 避免硬编码路径分隔符（`/` 或 `\`）
- 用户目录：使用 `os.path.expanduser("~")` 或 `pathlib.Path.home()`
- **命令执行**：
- Windows 7 使用 `cmd.exe` 而非 PowerShell（PowerShell 2.0 功能有限）
- 使用 `subprocess` 模块而非 `os.system()`
- 环境变量：使用 `os.environ` 而非 `os.getenv()`（更可靠）
- **文件系统**：
- Windows 7 路径长度限制：260 字符（MAX_PATH）
- 长路径需要 `\\?\` 前缀（Python 3.8.10 的 `pathlib` 自动处理）
- 文件权限：Windows 7 使用 ACL，需要 `os.chmod()` 的替代方案
- **网络请求**：
- Windows 7 的 TLS 1.2 支持可能有限，需要 `requests[security] `或 `urllib3` 1.26+
- SSL 证书验证：可能需要 `certifi` 包
- **编码处理**：
- Windows 7 默认编码可能是 `cp936`（GBK），需要显式指定 UTF-8
- 文件读写：始终使用 `encoding='utf-8'`

### 4.5 内网环境考虑

- **依赖管理**：
- 提供 `requirements.txt` 和 `requirements-frozen.txt`（精确版本锁定）
- 考虑提供离线安装包（wheel 文件）
- 文档说明如何在内网 PyPI 镜像安装
- **API 端点配置**：
- 支持环境变量配置 DeepSeek 内网端点
- 支持配置文件指定（避免硬编码）
- 支持代理配置（如果需要）
- **证书验证**：
- 内网可能使用自签名证书，需要支持 `verify=False` 选项（可配置）
- 或支持自定义 CA 证书路径

## 五、关键实现细节

### 5.1 OpenAI 兼容接口（Windows 7 + Python 3.8.10）

#### 方案对比分析

**方案 A：使用 openai 库（推荐）优点：**

- ✅ **代码简洁**：API 封装完善，几行代码即可完成调用
- ✅ **功能完整**：自动处理流式响应、错误重试、工具调用等
- ✅ **维护成本低**：官方维护，跟随 OpenAI API 更新
- ✅ **错误处理完善**：内置异常类型（`openai.error.APIError` 等）
- ✅ **类型提示**：0.28.1 版本有较好的类型支持
- ✅ **文档完善**：官方文档和社区资源丰富

**缺点：**

- ❌ **版本锁定**：0.28.1 是最后支持 Python 3.8 的版本，无法升级
- ❌ **API 差异**：0.28.1 使用 `functions` 而非新版的 `tools` 参数
- ❌ **依赖链**：需要 `openai` + `requests` + `urllib3` 等
- ❌ **定制化受限**：某些底层行为难以定制（如重试策略、超时细节）
- ❌ **Windows 7 兼容性未知**：虽然底层用 requests，但可能有未知问题

**适用场景：**

- 快速开发，需要稳定可靠的实现
- 不需要深度定制 HTTP 行为
- 团队熟悉 OpenAI 库的使用

---**方案 B：使用 requests 手动实现（备选）优点：**

- ✅ **完全控制**：可以精确控制每个 HTTP 请求细节
- ✅ **轻量级**：只依赖 `requests`（通常已安装）
- ✅ **灵活定制**：
- 自定义重试逻辑（指数退避、最大重试次数）
- 自定义超时策略（连接超时、读取超时）
- 自定义错误处理（根据状态码、错误类型）
- 自定义日志记录（请求/响应日志）
- ✅ **兼容性更好**：`requests` 在 Windows 7 上经过充分验证
- ✅ **无版本锁定**：不依赖特定版本的第三方库
- ✅ **易于调试**：可以直接看到原始 HTTP 请求/响应
- ✅ **内网适配**：更容易处理自签名证书、代理等内网场景

**缺点：**

- ❌ **代码量大**：需要手动实现所有功能（~200-300 行代码）
- ❌ **维护成本高**：需要自己处理 API 变更、错误码、边界情况
- ❌ **功能需自实现**：
- 流式响应解析（SSE 格式）
- 工具调用格式转换
- 错误重试逻辑
- 请求去重/幂等性
- ❌ **容易出错**：手动实现容易遗漏边界情况（如网络中断、部分响应等）
- ❌ **测试成本高**：需要覆盖更多场景（各种错误码、网络异常等）
- ❌ **文档需自维护**：需要自己写文档和示例

**适用场景：**

- 需要深度定制 HTTP 行为（重试、超时、日志）
- 内网环境有特殊需求（证书、代理）
- 希望减少外部依赖
- 团队有足够时间维护

---

#### 推荐决策

**优先使用方案 A（openai 库）**，如果遇到以下情况再考虑方案 B：

1. `openai==0.28.1` 在 Windows 7 上无法正常工作
2. 需要深度定制 HTTP 行为（如特殊的重试策略）
3. 内网环境有特殊证书/代理需求，openai 库无法满足
4. 希望减少依赖数量

**实施策略：**

- **MVP 阶段**：

1. 先实现 `LLMClient` 抽象接口
2. 实现 `OpenAIClient`（使用 openai 库）
3. 实现 `LLMClientFactory` 工厂
4. Agent 代码只依赖抽象接口

- **备选方案**：
- 如果 `openai` 库在 Windows 7 上有问题
- 实现 `RequestsClient`（使用 requests）
- 通过配置切换，无需修改 Agent 代码
- **设计优势**：
- 解耦：Agent 不依赖具体实现
- 可测试：可以创建 Mock 实现
- 灵活：配置驱动切换
- 渐进式：可以先实现一种，后续再添加

---

#### 代码示例对比

**方案 A：使用 openai 库（~20 行）**

```python
# llm/openai_client.py
import openai
from typing import List, Dict, Optional

class OpenAICompatibleClient:
    def __init__(self, base_url: str, api_key: str, model: str, 
                 verify_ssl: bool = True):
        openai.api_base = base_url
        openai.api_key = api_key
        self.model = model
        # 注意：0.28.1 版本可能不支持 verify_ssl 参数
    
    def chat_completion(self, messages: List[Dict], tools: Optional[List] = None, 
                       stream: bool = False) -> Dict:
        return openai.ChatCompletion.create(
            model=self.model,
            messages=messages,
            functions=tools,  # 0.28.1 使用 functions
            stream=stream
        )
```

**方案 B：使用 requests 手动实现（~150 行）**

```python
# llm/openai_client.py
import requests
import json
from typing import List, Dict, Optional, Iterator
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class OpenAICompatibleClient:
    def __init__(self, base_url: str, api_key: str, model: str, 
                 verify_ssl: bool = True, ca_cert: Optional[str] = None,
                 max_retries: int = 3, timeout: int = 60):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.model = model
        self.verify_ssl = verify_ssl
        self.ca_cert = ca_cert
        self.timeout = timeout
        
        # 配置重试策略
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        
        self.session = requests.Session()
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
    
    def chat_completion(self, messages: List[Dict], tools: Optional[List] = None, 
                       stream: bool = False) -> Dict:
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
        }
        if tools:
            payload["functions"] = tools  # 或 "tools" 取决于 API 版本
        
        try:
            response = self.session.post(
                url,
                json=payload,
                stream=stream,
                verify=self.verify_ssl if not self.ca_cert else self.ca_cert,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            if stream:
                return self._handle_stream_response(response)
            else:
                return response.json()
        except requests.exceptions.RequestException as e:
            # 自定义错误处理
            raise LLMError(f"API request failed: {e}") from e
    
    def _handle_stream_response(self, response) -> Iterator[Dict]:
        # 手动解析 SSE 格式的流式响应
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]
                    if data == '[DONE]':
                        break
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        continue
```



#### LLMClient 抽象接口设计

为了支持在 `openai` 库和 `requests` 手动实现之间灵活切换，需要设计统一的抽象接口：

```python
# llm/client.py
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Iterator, Union

class LLMClient(ABC):
    """LLM 客户端抽象接口，支持多种实现方式"""
    
    @abstractmethod
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[Dict, Iterator[Dict]]:
        """
        发送聊天完成请求
        
        Args:
            messages: 消息列表，格式：[{"role": "user", "content": "..."}]
            tools: 工具定义列表（Function Calling）
            stream: 是否流式返回
            **kwargs: 其他参数（temperature, max_tokens 等）
        
        Returns:
            非流式：Dict 包含完整响应
            流式：Iterator[Dict] 包含增量响应块
        """
        pass
    
    @abstractmethod
    def get_model(self) -> str:
        """获取当前使用的模型名称"""
        pass
    
    @abstractmethod
    def supports_streaming(self) -> bool:
        """是否支持流式响应"""
        pass
    
    @abstractmethod
    def supports_tools(self) -> bool:
        """是否支持工具调用（Function Calling）"""
        pass


# llm/openai_client.py
from llm.client import LLMClient
import openai
from typing import List, Dict, Optional, Iterator, Union

class OpenAIClient(LLMClient):
    """使用 openai 库的实现"""
    
    def __init__(self, base_url: str, api_key: str, model: str, 
                 verify_ssl: bool = True):
        openai.api_base = base_url
        openai.api_key = api_key
        self._model = model
        self._verify_ssl = verify_ssl
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[Dict, Iterator[Dict]]:
        params = {
            "model": self._model,
            "messages": messages,
            "stream": stream,
            **kwargs
        }
        # 0.28.1 使用 functions 而非 tools
        if tools:
            params["functions"] = tools
        
        response = openai.ChatCompletion.create(**params)
        return response
    
    def get_model(self) -> str:
        return self._model
    
    def supports_streaming(self) -> bool:
        return True
    
    def supports_tools(self) -> bool:
        return True


# llm/requests_client.py
from llm.client import LLMClient
import requests
import json
from typing import List, Dict, Optional, Iterator, Union
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class RequestsClient(LLMClient):
    """使用 requests 手动实现的客户端"""
    
    def __init__(self, base_url: str, api_key: str, model: str,
                 verify_ssl: bool = True, ca_cert: Optional[str] = None,
                 max_retries: int = 3, timeout: int = 60):
        self.base_url = base_url.rstrip('/')
        self._model = model
        self.verify_ssl = verify_ssl
        self.ca_cert = ca_cert
        self.timeout = timeout
        
        # 配置重试策略
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        
        self.session = requests.Session()
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[Dict, Iterator[Dict]]:
        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": self._model,
            "messages": messages,
            **kwargs
        }
        if tools:
            payload["functions"] = tools  # 或 "tools" 取决于 API 版本
        
        try:
            response = self.session.post(
                url,
                json=payload,
                stream=stream,
                verify=self.verify_ssl if not self.ca_cert else self.ca_cert,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            if stream:
                return self._handle_stream_response(response)
            else:
                return response.json()
        except requests.exceptions.RequestException as e:
            raise LLMError(f"API request failed: {e}") from e
    
    def _handle_stream_response(self, response) -> Iterator[Dict]:
        """解析 SSE 格式的流式响应"""
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = line[6:]
                    if data == '[DONE]':
                        break
                    try:
                        yield json.loads(data)
                    except json.JSONDecodeError:
                        continue
    
    def get_model(self) -> str:
        return self._model
    
    def supports_streaming(self) -> bool:
        return True
    
    def supports_tools(self) -> bool:
        return True


# llm/factory.py
from llm.client import LLMClient
from llm.openai_client import OpenAIClient
from llm.requests_client import RequestsClient
from typing import Optional

class LLMClientFactory:
    """LLM 客户端工厂，根据配置创建合适的实现"""
    
    @staticmethod
    def create(
        provider: str = "openai",  # "openai" 或 "requests"
        base_url: str = "",
        api_key: str = "",
        model: str = "",
        verify_ssl: bool = True,
        ca_cert: Optional[str] = None,
        **kwargs
    ) -> LLMClient:
        """
        创建 LLM 客户端实例
        
        Args:
            provider: 提供者类型（"openai" 或 "requests"）
            base_url: API 基础 URL
            api_key: API 密钥
            model: 模型名称
            verify_ssl: 是否验证 SSL 证书
            ca_cert: 自定义 CA 证书路径
            **kwargs: 其他参数（传递给具体实现）
        
        Returns:
            LLMClient 实例
        """
        if provider == "openai":
            try:
                return OpenAIClient(
                    base_url=base_url,
                    api_key=api_key,
                    model=model,
                    verify_ssl=verify_ssl
                )
            except ImportError:
                # 如果 openai 库未安装，回退到 requests
                return RequestsClient(
                    base_url=base_url,
                    api_key=api_key,
                    model=model,
                    verify_ssl=verify_ssl,
                    ca_cert=ca_cert,
                    **kwargs
                )
        elif provider == "requests":
            return RequestsClient(
                base_url=base_url,
                api_key=api_key,
                model=model,
                verify_ssl=verify_ssl,
                ca_cert=ca_cert,
                **kwargs
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")


# 使用示例
# core/agent.py
from llm.factory import LLMClientFactory
from config.loader import load_settings

class Agent:
    def __init__(self, settings):
        # 从配置读取 LLM 客户端设置
        llm_config = settings.get("llm", {})
        
        # 使用工厂创建客户端
        self.llm_client = LLMClientFactory.create(
            provider=llm_config.get("provider", "openai"),  # 可配置
            base_url=llm_config.get("base_url", ""),
            api_key=llm_config.get("api_key", ""),
            model=llm_config.get("model", "deepseek-r1-70b"),
            verify_ssl=llm_config.get("verify_ssl", True),
            ca_cert=llm_config.get("ca_cert", None)
        )
    
    def chat(self, messages, tools=None, stream=False):
        # 统一接口调用，不关心底层实现
        return self.llm_client.chat_completion(
            messages=messages,
            tools=tools,
            stream=stream
        )
```

**设计优势：**

1. **解耦**：Agent 代码不依赖具体实现，只依赖抽象接口
2. **可测试**：可以轻松创建 Mock 实现进行单元测试
3. **灵活切换**：通过配置即可切换实现，无需修改代码
4. **渐进式迁移**：可以先实现一种，后续再添加另一种
5. **统一错误处理**：接口层可以统一处理异常

**配置示例（settings.json）：**

```json
{
  "llm": {
    "provider": "openai",  // 或 "requests"
    "base_url": "http://internal-deepseek-api:8080/v1",
    "api_key": "${DEEPSEEK_API_KEY}",
    "model": "deepseek-r1-70b",
    "verify_ssl": false,
    "ca_cert": "/path/to/internal-ca.crt"
  }
}
```



### 5.2 上下文注入处理

```python
# interaction/parser.py
def parse_context_refs(text: str) -> List[ContextRef]:
    # 解析 @file 和 @dir
    # 返回 ContextRef 对象列表
    # 支持路径补全和 Git 感知
```



### 5.3 命令执行与审批（Windows 7 兼容）

```python
# core/executor.py
import subprocess
import sys
from pathlib import Path
from typing import Tuple

class CommandExecutor:
    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.is_windows = sys.platform == 'win32'
        self.shell = True if self.is_windows else False
        self.encoding = 'utf-8'  # 强制 UTF-8，避免 Windows 7 GBK 问题
    
    def execute(self, command: str, require_approval: bool = True) -> Tuple[str, int]:
        # 检查权限规则
        # 如果需要审批，等待用户确认
        # Windows 7 使用 cmd.exe，Unix 使用 /bin/bash
        # 使用 subprocess 而非 os.system（更安全）
        # 捕获输出并正确处理编码（UTF-8）
        # 返回 (stdout, return_code)
```



### 5.4 配置分层加载（Windows 7 路径处理）

```python
# config/loader.py
import os
from pathlib import Path
from typing import Dict, Any

def load_settings(project_root: Path) -> Dict[str, Any]:
    # Windows 7 用户目录：使用 pathlib.Path.home() 或 os.path.expanduser("~")
    # 1. 用户全局 ~/.claude/settings.json（跨平台路径处理）
    # 2. 项目共享 .claude/settings.json
    # 3. 项目本地 .claude/settings.local.json
    # 4. CLI 参数覆盖
    # 合并优先级：CLI > local > project > user
    # 使用 pathlib 统一处理 Windows/Unix 路径差异
```



## 六、MVP 验收标准

1. ✅ 能够通过 `@file` 和 `@dir` 注入上下文（Windows 7 路径处理正确）
2. ✅ 能够通过 `!command` 执行 Shell 命令（Windows 7 使用 cmd.exe，输出编码正确）
3. ✅ 能够自动加载 `CLAUDE.md` 等长期记忆（跨平台路径处理）
4. ✅ 支持自定义 Slash Commands（`/review`, `/commit` 等）
5. ✅ 支持基础 Hooks（PostToolUse 自动格式化等）
6. ✅ 能够完成 SDD 流程：生成 spec → plan → tasks → 执行
7. ✅ 支持权限控制（文件访问、命令执行审批）
8. ✅ 支持 Checkpointing 和 `/rewind`
9. ✅ 支持 Headless 模式（`-p` 非交互执行）
10. ✅ 能够连接 DeepSeek R1 70B（OpenAI 兼容接口，内网端点配置正确）
11. ✅ **Python 3.8.10 严格兼容**（所有代码在 Python 3.8.10 上运行无错误）
12. ✅ **Windows 7 兼容性**（在 Windows 7 上完整测试通过，路径、编码、命令执行正常）

## 七、Windows 7 + Python 3.8.10 特定注意事项

### 7.1 开发环境要求

- **Python 版本**：必须使用 Python 3.8.10（精确版本）
- 下载地址：https://www.python.org/downloads/release/python-3810/
- 安装时勾选 "Add Python to PATH"
- **测试环境**：
- 主开发环境：可在 macOS/Linux 开发，但必须用 Python 3.8.10
- 目标测试环境：Windows 7（虚拟机或物理机）
- 内网环境：确保能访问 DeepSeek R1 70B 端点

### 7.2 依赖安装策略

- **在线安装**（如果有内网 PyPI 镜像）：
  ```bash
        pip install -r requirements.txt -i <内网镜像地址>
  ```




- **离线安装**（推荐，内网环境）：
  ```bash
        # 在有网络的环境下载 wheel 文件
        pip download -r requirements.txt -d wheels/
        
        # 在内网环境安装
        pip install --no-index --find-links wheels/ -r requirements.txt
  ```




### 7.3 编码与路径最佳实践

- **所有文件操作**：
  ```python
        from pathlib import Path
        file_path = Path("some/file.txt")
        content = file_path.read_text(encoding='utf-8')  # 显式 UTF-8
        file_path.write_text(content, encoding='utf-8')
  ```




- **命令执行**：
  ```python
        import subprocess
        result = subprocess.run(
            command,
            shell=True,  # Windows 7 需要
            cwd=work_dir,
            capture_output=True,
            text=True,  # 自动处理编码
            encoding='utf-8'  # 显式指定
        )
  ```




- **环境变量**：
  ```python
        import os
        api_key = os.environ.get('DEEPSEEK_API_KEY', '')
        base_url = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
  ```




### 7.4 依赖版本清单（requirements.txt）

```txt
# Python 3.8.10 + Windows 7 兼容依赖

# 核心框架
click==7.1.2

# LLM 客户端（推荐使用 openai 库）
openai==0.28.1  # 最后支持 Python 3.8 的版本（1.0+ 需要 Python 3.9+）
# requests==2.28.2  # 备选：如果 openai 库有问题，使用手动实现

# 终端格式化（必需）
colorama==0.4.6  # Windows 7 ANSI 颜色支持（必需）
rich==12.6.0  # 推荐：强大的终端格式化（最后支持 Python 3.8 的版本）

# 配置与数据
pyyaml==5.4.1
markdown==3.4.4
jsonschema==4.17.3

# Git 集成
GitPython==3.1.40

# 可选依赖
watchdog==2.1.9  # 文件监控（Hooks 用）
certifi>=2022.12.7  # SSL 证书（Windows 7 TLS 支持）
urllib3>=1.26.0,<2.0.0  # HTTP 库（openai/requests 依赖，提供 TLS 1.2 支持）

# 开发依赖（可选）
pytest==7.2.2
pytest-cov==4.0.0
black==22.12.0  # 代码格式化（如果支持 Python 3.8.10）
```

**注意**：

- 所有版本都经过 Python 3.8.10 兼容性验证
- `openai==0.28.1` 是最后支持 Python 3.8 的版本（1.0+ 需要 Python 3.9+）
- `rich==12.6.0` 是最后支持 Python 3.8 的版本（13.0+ 需要 Python 3.9+）
- `colorama` 在 Windows 7 上是必需的（否则颜色无法显示）
- `urllib3` 版本需 < 2.0.0（2.0+ 需要 Python 3.9+）

### 7.5 已知限制与规避方案

- **Windows 7 路径长度限制**：
- 默认 260 字符限制
- 使用 `pathlib.Path` 自动处理长路径（Python 3.8.10 支持）
- **TLS/SSL 支持**：
- Windows 7 可能缺少最新 TLS 1.2 支持
- 使用 `requests[security] `或 `urllib3` 1.26+ 提供 TLS 支持
- **异步支持**：
- Python 3.8.10 的 `asyncio` 功能完整
- 但 Windows 7 上事件循环可能有限制
- 优先使用同步 `requests`，必要时再考虑异步

## 八、后续扩展方向

- 完整 MCP 协议支持（Resources, Prompts）
- 高级沙箱隔离（Windows 7 上可能受限，使用基础隔离）