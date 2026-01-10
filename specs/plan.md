# 技术方案（Plan）

**版本**: 1.0  
**日期**: 2024-12-19  
**状态**: 草案（待审查）  
**基于**: [spec.md](spec.md)

## 1. 技术上下文总结

### 1.1 技术栈选型

- **语言**: Python 3.8.10（仅支持此版本）
- **CLI 框架**: `click == 7.1.2`（最后支持 Python 3.8.10 的稳定版本）
- **LLM 客户端**: 
  - 方案 A（推荐）: `openai == 0.28.1`
  - 方案 B（备选）: `requests == 2.28.2`（手动实现）
- **终端美化**: 
  - `rich == 12.6.0`（Markdown、代码高亮、面板、进度条）
  - `prompt_toolkit == 3.0.39`（交互式输入、历史记录、自动补全）
  - `questionary == 1.10.0`（选择菜单、确认提示）
  - `colorama == 0.4.6`（Windows 7 ANSI 颜色支持）
- **配置解析**: `pyyaml == 5.4.1`
- **Git 集成**: `GitPython == 3.1.40`
- **其他**: `markdown == 3.4.4`, `jsonschema == 4.17.3`

### 1.2 运行环境

- **主要目标**: Windows 7 内网环境
- **Python 版本**: 3.8.10（精确版本）
- **命令执行**: Windows 7 使用 PowerShell 2.0，Unix 使用 bash
- **编码**: 所有操作强制 UTF-8

### 1.3 关键依赖

- **DeepSeek R1 70B**: 通过 OpenAI 兼容接口访问（内网端点）
- **内网环境**: 支持离线安装、自签名证书

## 2. 合宪性检查清单

### 2.1 简单性门禁 ✅

- ✅ **标准库优先**: 核心功能使用标准库，第三方库仅用于必需功能
- ✅ **避免复杂抽象**: 不使用复杂设计模式，优先简单函数和数据结构
- ✅ **只实现 spec 要求**: 严格按照 spec.md 实现，不添加额外功能

### 2.2 TDD 门禁 ✅

- ✅ **先写测试**: 所有功能遵循 Red-Green-Refactor 循环
- ✅ **表格驱动测试**: 核心逻辑使用表格驱动测试
- ✅ **覆盖多种场景**: 测试覆盖正常、边界、错误情况

### 2.3 明确性门禁 ✅

- ✅ **错误处理显式**: 所有错误显式处理，不使用 `_` 丢弃
- ✅ **依赖显式注入**: 通过构造函数或参数传递，避免全局状态
- ✅ **类型提示明确**: 所有公共 API 有类型提示，Python 3.8.10 兼容

### 2.4 兼容性门禁 ✅

- ✅ **Python 3.8.10 兼容**: 不使用 3.9+ 特性，使用兼容的类型注解
- ✅ **Windows 7 兼容**: 路径使用 `pathlib.Path`，命令使用 PowerShell
- ✅ **内网环境适配**: 支持离线安装、自签名证书配置

### 2.5 安全门禁 ✅

- ✅ **最小权限**: 默认只读，危险操作需要审批
- ✅ **审批机制**: 使用 `questionary` 做安全确认
- ✅ **检查点支持**: 支持会话级检查点和回滚

## 3. 项目结构细化

### 3.1 目录结构

```
py38-claude-code/
├── deep_code/              # 主包
│   ├── __init__.py
│   ├── core/                 # 核心模块
│   │   ├── __init__.py
│   │   ├── agent.py          # Agent 引擎
│   │   ├── context.py        # 上下文管理
│   │   ├── executor.py       # 命令执行器
│   │   └── sdd.py            # SDD 引擎
│   ├── interaction/          # 交互模块
│   │   ├── __init__.py
│   │   ├── parser.py         # @ 和 ! 解析器
│   │   ├── commands.py       # Slash Commands
│   │   └── hooks.py          # Hooks 系统
│   ├── security/             # 安全模块
│   │   ├── __init__.py
│   │   ├── permissions.py    # 权限控制
│   │   ├── sandbox.py        # 沙箱（MVP 简化）
│   │   └── checkpoint.py     # 检查点
│   ├── extensions/           # 扩展模块
│   │   ├── __init__.py
│   │   ├── mcp.py           # MCP 协议
│   │   ├── skills.py        # Skills
│   │   └── subagents.py     # Subagents
│   ├── llm/                 # LLM 客户端
│   │   ├── __init__.py
│   │   ├── client.py        # 抽象接口（ABC）
│   │   ├── openai_client.py # OpenAI 实现
│   │   ├── requests_client.py # Requests 实现
│   │   ├── factory.py       # 工厂模式
│   │   └── models.py        # 消息/工具定义
│   ├── config/              # 配置模块
│   │   ├── __init__.py
│   │   ├── settings.py      # 配置管理
│   │   └── loader.py        # 分层加载
│   └── cli/                 # CLI 模块
│       ├── __init__.py
│       ├── main.py          # CLI 入口
│       └── commands.py      # 命令定义
├── tests/                   # 测试目录
│   ├── __init__.py
│   ├── test_core/
│   ├── test_interaction/
│   ├── test_llm/
│   └── test_config/
├── .deepcode/                 # 项目配置
│   ├── settings.json
│   ├── commands/
│   ├── skills/
│   ├── agents/
│   └── hooks/
├── specs/                   # SDD 产物
│   ├── spec.md
│   ├── plan.md
│   └── tasks.md
├── CLAUDE.md               # 项目操作手册
├── AGENTS.md               # 跨 Agent 标准
├── constitution.md         # 项目宪法
├── requirements.txt        # 依赖清单
├── requirements-frozen.txt # 锁定版本
├── setup.py                # 安装配置
└── README.md               # 项目说明
```

### 3.2 包职责划分

#### core/ - 核心模块
- **agent.py**: Agent 引擎，协调所有子系统，管理对话循环
- **context.py**: 上下文管理，短期和长期记忆
- **executor.py**: 命令执行器，PowerShell/bash 执行
- **sdd.py**: 规范驱动开发引擎，spec → plan → tasks → 实现

#### interaction/ - 交互模块
- **parser.py**: 解析 `@` 和 `!` 符号
- **commands.py**: Slash Commands 管理（发现、解析、执行）
- **hooks.py**: Hooks 事件系统（生命周期事件触发）

#### security/ - 安全模块
- **permissions.py**: 权限控制（文件、命令、网络）
- **sandbox.py**: 沙箱隔离（MVP 简化版）
- **checkpoint.py**: 检查点管理（快照、回滚）

#### llm/ - LLM 客户端
- **client.py**: 抽象接口（ABC），定义统一接口
- **openai_client.py**: 使用 openai 库的实现
- **requests_client.py**: 使用 requests 手动实现（备选）
- **factory.py**: 工厂模式，根据配置创建客户端
- **models.py**: 消息格式、工具定义等数据模型

#### config/ - 配置模块
- **settings.py**: 配置数据结构和管理
- **loader.py**: 分层配置加载（用户/项目/CLI）

#### cli/ - CLI 模块
- **main.py**: CLI 入口点，使用 click
- **commands.py**: 命令定义和实现

## 4. 核心数据结构

### 4.1 消息格式

```python
# llm/models.py
from typing import List, Dict, Optional

Message = Dict[str, str]  # {"role": "user|assistant|system", "content": "..."}
Messages = List[Message]

ToolDefinition = Dict[str, any]  # OpenAI Function Calling 格式
Tools = List[ToolDefinition]
```

### 4.2 上下文引用

```python
# interaction/parser.py
from pathlib import Path
from typing import Optional

class ContextRef:
    path: Path
    ref_type: str  # "file" | "dir"
    line_range: Optional[tuple]  # (start, end) 可选
```

### 4.3 配置结构

```python
# config/settings.py
from typing import Dict, Optional, List

class Settings:
    llm: Dict[str, any]  # provider, base_url, api_key, model, verify_ssl, ca_cert
    permissions: Dict[str, any]  # 权限规则
    hooks: Dict[str, List[Dict]]  # 事件钩子
    default_model: str
    # ...
```

### 4.4 任务结构

```python
# core/sdd.py
from typing import List, Optional

class Task:
    id: str
    description: str
    phase: str
    dependencies: List[str]  # 依赖的任务 ID
    parallel: bool  # 是否可并行 [P]
    tdd: bool  # 是否 TDD（先测试）
    file: Optional[str]  # 目标文件
    function: Optional[str]  # 目标函数
```

## 5. 关键接口设计

### 5.1 LLMClient 抽象接口

```python
# llm/client.py
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Iterator, Union

class LLMClient(ABC):
    @abstractmethod
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        stream: bool = False,
        **kwargs
    ) -> Union[Dict, Iterator[Dict]]:
        """发送聊天完成请求"""
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
        """是否支持工具调用"""
        pass
```

### 5.2 CommandExecutor 接口

```python
# core/executor.py
from pathlib import Path
from typing import Tuple

class CommandExecutor:
    def __init__(self, work_dir: Path):
        """初始化命令执行器"""
        pass
    
    def execute(self, command: str, require_approval: bool = True) -> Tuple[str, int]:
        """
        执行命令
        
        Returns:
            (stdout, return_code)
        """
        pass
```

### 5.3 ContextManager 接口

```python
# core/context.py
from pathlib import Path
from typing import List, Dict

class ContextManager:
    def load_file(self, path: Path) -> str:
        """加载文件内容"""
        pass
    
    def load_directory(self, path: Path) -> str:
        """加载目录结构"""
        pass
    
    def load_long_term_memory(self) -> Dict[str, str]:
        """加载长期记忆（CLAUDE.md, AGENTS.md, constitution.md）"""
        pass
```

## 6. 技术选型说明

### 6.1 为什么选择 click 7.1.2？

- 最后支持 Python 3.8.10 的稳定版本
- 功能完整，满足 CLI 需求
- 社区成熟，文档完善

### 6.2 为什么选择 openai 0.28.1？

- 最后支持 Python 3.8 的版本
- API 封装完善，代码简洁
- 支持 OpenAI 兼容接口（通过 `api_base`）
- 如果 Windows 7 有问题，可回退到 requests

### 6.3 为什么选择 Rich/Prompt Toolkit/Questionary？

- **Rich**: Python 界最好看的终端库，Windows 7 完美支持
- **Prompt Toolkit**: 解决 Windows 7 上 `input()` 的不足（历史记录、补全）
- **Questionary**: 提供漂亮的交互式菜单，替代 `input()` 做确认

### 6.4 为什么使用 PowerShell 而非 cmd.exe？

- PowerShell 2.0 在 Windows 7 上可用
- 功能比 cmd.exe 更强大
- 支持脚本和 cmdlet
- 输出编码处理更可靠（UTF-8）

## 7. 架构设计原则

### 7.1 分层架构

- **接口层**: 抽象接口（LLMClient, CommandExecutor 等）
- **实现层**: 具体实现（OpenAIClient, RequestsClient 等）
- **协调层**: Agent 引擎协调所有子系统
- **配置层**: 分层配置加载和管理

### 7.2 依赖注入

- 所有依赖通过构造函数注入
- 避免全局状态和单例
- 便于测试和替换实现

### 7.3 模块化设计

- 每个模块职责单一
- 模块之间依赖清晰
- 核心模块不依赖扩展模块

## 8. 关键技术决策

### 8.1 LLM 客户端抽象

- **决策**: 使用抽象接口 + 工厂模式
- **原因**: 支持多种实现方式，便于切换和测试
- **实现**: ABC 抽象基类 + Factory 创建实例

### 8.2 配置分层加载

- **决策**: 用户全局 → 项目共享 → 项目本地 → CLI 参数
- **原因**: 支持团队统一配置和个人偏好
- **实现**: 配置合并，优先级覆盖

### 8.3 命令执行方式

- **决策**: Windows 7 使用 PowerShell，Unix 使用 bash
- **原因**: PowerShell 功能更强大，编码处理更可靠
- **实现**: 平台检测，选择对应的 shell

### 8.4 终端交互方式

- **决策**: 使用 Prompt Toolkit + Questionary 替代 `input()`
- **原因**: Windows 7 上 `input()` 功能有限，用户体验差
- **实现**: 统一使用 Prompt Toolkit/Questionary 做交互

## 9. 非功能设计

### 9.1 错误处理策略

- **原则**: 所有错误显式处理
- **策略**: 
  - 关键操作 try-except
  - 错误信息清晰可操作
  - 关键错误记录日志
- **实现**: 自定义异常类型，统一错误处理

### 9.2 日志策略

- **原则**: 结构化日志，关键操作记录
- **策略**: 
  - 使用 Python `logging` 模块
  - 日志级别可配置
  - 关键操作（命令执行、文件修改）记录
- **实现**: 配置日志格式和级别

### 9.3 性能考虑

- **原则**: MVP 阶段优先功能，性能次之
- **策略**: 
  - 上下文压缩（Token 预算管理）
  - 基础并行支持（标记 `[P]` 的任务）
  - 流式响应处理（不阻塞）
- **实现**: 异步处理流式响应，同步处理其他操作

## 10. 安全设计

### 10.1 权限模型

- **默认**: 最小权限（只读）
- **文件访问**: deny/allow/ask 规则
- **命令执行**: 白名单/黑名单 + ask 审批
- **网络访问**: 域名白名单

### 10.2 审批流程

- **触发**: ask 模式的权限规则
- **方式**: 使用 Questionary 做交互式确认
- **记录**: 审批历史可审计

### 10.3 检查点机制

- **时机**: 每次用户提交 prompt 前
- **内容**: 代码状态 + 对话状态
- **回滚**: `/rewind` 命令，三种模式

## 11. 测试策略

### 11.1 单元测试

- **范围**: 所有核心功能
- **方式**: 表格驱动测试
- **工具**: `pytest == 7.2.2`
- **覆盖率**: ≥ 70%

### 11.2 集成测试

- **范围**: 关键路径（上下文注入、命令执行、Agent 循环）
- **方式**: 端到端测试
- **环境**: Windows 7 + Python 3.8.10

### 11.3 兼容性测试

- **Python 版本**: 3.8.10（精确版本）
- **操作系统**: Windows 7（主要）+ Unix（支持）
- **内网环境**: 离线安装、自签名证书

## 12. 部署与分发

### 12.1 安装方式

- **在线安装**: `pip install -r requirements.txt`
- **离线安装**: 提供 wheel 文件，`pip install --no-index --find-links wheels/`
- **内网镜像**: 支持内网 PyPI 镜像

### 12.2 配置方式

- **环境变量**: API Key, Base URL 等
- **配置文件**: `settings.json`（分层加载）
- **CLI 参数**: 临时覆盖配置

## 13. 风险评估与缓解

### 13.1 技术风险

- **风险**: openai 库在 Windows 7 上可能有问题
- **缓解**: 提供 requests 手动实现作为备选，自动回退

- **风险**: PowerShell 2.0 功能有限
- **缓解**: 使用兼容的命令和语法，避免高级功能

### 13.2 兼容性风险

- **风险**: Python 3.8.10 特性限制
- **缓解**: 严格遵循兼容性要求，不使用新特性

- **风险**: Windows 7 编码问题
- **缓解**: 所有操作强制 UTF-8，不使用系统默认编码

### 13.3 安全风险

- **风险**: AI 执行危险命令
- **缓解**: 权限控制 + 审批机制 + 检查点回滚

## 14. 后续扩展预留

### 14.1 架构预留

- **Web UI**: 预留 `web/` 目录（非 MVP）
- **多 Agent**: 架构支持并行执行（标记 `[P]`）
- **MCP 扩展**: 接口设计支持完整 MCP 协议

### 14.2 功能预留

- **高级沙箱**: 当前简化版，后续可升级
- **完整 MCP**: 当前基础支持，后续完整实现
- **Skills/Subagents**: 架构支持，MVP 基础实现

---

**审查状态**: ⚠️ 待人工审查  
**审查重点**:
1. 是否真的符合宪法（不是"表面勾选"）
2. 包边界是否清晰、依赖是否合理
3. 关键数据结构是否覆盖了 spec 的所有字段
4. 是否引入不必要的复杂性/依赖

**维护者**: 开发团队  
**最后更新**: 2024-12-19

