# MCP 和 Skills 功能任务清单

> 目标：实现 DeepCode 的 MCP (Model Context Protocol) 和 Skills 功能
>
> 参考：Claude Code 官方 MCP 和 Skills 方案
>
> 改动文件：`deep_code/extensions/mcp/`, `deep_code/extensions/skills/`
>
> **重要**：DeepCode 使用独立配置路径，避免与 Claude Code 冲突：
> - 配置目录：`.deepcode/` (项目) 和 `~/.deepcode/` (用户)
> - MCP 配置：`.deepcode/mcp.json`
> - Skills 目录：`.deepcode/skills/`
> - CLI 命令：`deepcode mcp ...` (不是 `claude mcp ...`)

## 功能概述

### 1. MCP (Model Context Protocol)
- MCP 客户端实现（stdio/http/sse）
- MCP 服务器连接管理
- 工具/资源/提示发现和调用
- 配置文件解析和管理

### 2. Skills
- Skills 发现和加载
- 自动任务匹配
- 工具权限限制
- 上下文注入

## 任务清单

### Phase 7: MCP 基础架构 (P0)

- [ ] **MCP-001 创建 MCP 协议基础模块**
  - **文件**: `deep_code/extensions/mcp/protocol.py`
  - **内容**:
    - MCPMessage 数据类（request/response/notification）
    - MCPTransport 抽象基类
    - JSON-RPC 2.0 消息编解码
  - **验证**: 能编码/解码 MCP 消息

- [ ] **MCP-002 实现 stdio 传输**
  - **文件**: `deep_code/extensions/mcp/transport_stdio.py`
  - **内容**:
    - StdioTransport 类
    - 子进程管理（启动/停止）
    - 双向消息传输（stdin/stdout）
  - **验证**: 能启动本地 MCP 服务器并通信

- [ ] **MCP-003 实现 HTTP 传输**
  - **文件**: `deep_code/extensions/mcp/transport_http.py`
  - **内容**:
    - HttpTransport 类
    - HTTP POST 请求/响应
    - 认证头支持
  - **验证**: 能连接远程 HTTP MCP 服务器

- [ ] **MCP-004 实现 SSE 传输**
  - **文件**: `deep_code/extensions/mcp/transport_sse.py`
  - **内容**:
    - SseTransport 类
    - Server-Sent Events 流式接收
    - 长连接管理
  - **验证**: 能连接 SSE MCP 服务器

- [ ] **MCP-005 MCP 客户端核心**
  - **文件**: `deep_code/extensions/mcp/client.py`
  - **内容**:
    - MCPClient 类
    - initialize/shutdown 握手
    - 请求/响应匹配（request_id）
    - 超时处理
  - **验证**: 能完成完整的 MCP 会话

### Phase 8: MCP 能力发现 (P0)

- [ ] **MCP-006 工具发现**
  - **文件**: `deep_code/extensions/mcp/capabilities.py`
  - **内容**:
    - tools/list 请求
    - MCPTool 数据类（name, description, inputSchema）
    - 工具列表缓存
  - **验证**: 能列出 MCP 服务器的所有工具

- [ ] **MCP-007 资源发现**
  - **文件**: `deep_code/extensions/mcp/capabilities.py`
  - **内容**:
    - resources/list 请求
    - MCPResource 数据类（uri, name, mimeType）
    - 资源读取（resources/read）
  - **验证**: 能列出和读取 MCP 资源

- [ ] **MCP-008 提示发现**
  - **文件**: `deep_code/extensions/mcp/capabilities.py`
  - **内容**:
    - prompts/list 请求
    - MCPPrompt 数据类（name, description, arguments）
    - 提示获取（prompts/get）
  - **验证**: 能列出和获取 MCP 提示

- [ ] **MCP-009 动态更新支持**
  - **文件**: `deep_code/extensions/mcp/client.py`
  - **内容**:
    - notifications/tools/list_changed 处理
    - notifications/resources/list_changed 处理
    - 自动重新发现
  - **验证**: 服务器更新时自动刷新能力列表

### Phase 9: MCP 配置管理 (P0)

- [ ] **MCP-010 配置文件解析**
  - **文件**: `deep_code/extensions/mcp/config.py`
  - **内容**:
    - 解析 `.deepcode/mcp.json` 格式
    - MCPServerConfig 数据类
    - 环境变量展开（`${VAR}`, `${VAR:-default}`）
  - **验证**: 能解析配置文件

- [ ] **MCP-011 配置作用域**
  - **文件**: `deep_code/extensions/mcp/config.py`
  - **内容**:
    - 用户级配置（`~/.deepcode/mcp.json`）
    - 项目级配置（`.deepcode/mcp.json`）
    - 本地配置（`.deepcode/mcp.local.json`）
    - 优先级合并
  - **验证**: 多层配置正确合并

- [ ] **MCP-012 MCP 服务器管理器**
  - **文件**: `deep_code/extensions/mcp/manager.py`
  - **内容**:
    - MCPManager 类
    - 服务器启动/停止
    - 连接池管理
    - 健康检查
  - **验证**: 能管理多个 MCP 服务器

### Phase 10: MCP 工具集成 (P0)

- [ ] **MCP-013 MCP 工具包装器**
  - **文件**: `deep_code/extensions/mcp/tools.py`
  - **内容**:
    - MCPToolWrapper 类（继承 BaseTool）
    - 将 MCP 工具转换为 DeepCode 工具
    - 参数验证（JSON Schema）
  - **验证**: MCP 工具可被 Agent 调用

- [ ] **MCP-014 工具调用路由**
  - **文件**: `deep_code/extensions/mcp/tools.py`
  - **内容**:
    - tools/call 请求
    - 结果解析和错误处理
    - 输出限制（10k/25k tokens）
  - **验证**: 工具调用返回正确结果

- [ ] **MCP-015 资源引用支持**
  - **文件**: `deep_code/extensions/mcp/resources.py`
  - **内容**:
    - `@mcp:server:resource` 语法解析
    - 资源内容注入到上下文
    - MIME 类型处理
  - **验证**: `@mcp:notion:project-notes` 能加载资源

### Phase 11: MCP CLI 命令 (P1)

- [ ] **MCP-016 deepcode mcp add 命令**
  - **文件**: `deep_code/cli/main.py`
  - **内容**:
    - `deepcode mcp add` 子命令
    - 支持 --transport stdio/http/sse
    - 支持 --env 环境变量
    - 写入 `.deepcode/mcp.json`
  - **验证**: `deepcode mcp add --transport stdio fs -- npx ...` 添加服务器

- [ ] **MCP-017 deepcode mcp list/get/remove 命令**
  - **文件**: `deep_code/cli/main.py`
  - **内容**:
    - `deepcode mcp list` 列出所有服务器
    - `deepcode mcp get <name>` 查看详情
    - `deepcode mcp remove <name>` 移除服务器
  - **验证**: 能管理 MCP 服务器配置

- [ ] **MCP-018 /mcp 交互命令**
  - **文件**: `deep_code/cli/main.py`
  - **内容**:
    - `/mcp` 显示服务器状态
    - 认证流程（OAuth 2.0）
    - 服务器重连
  - **验证**: `/mcp` 显示连接状态

### Phase 12: Skills 基础架构 (P1)

- [ ] **SKILL-001 Skills 目录扫描**
  - **文件**: `deep_code/extensions/skills/loader.py`
  - **内容**:
    - 扫描 `.deepcode/skills/` 目录
    - 扫描 `~/.deepcode/skills/` 目录
    - 递归查找 SKILL.md 文件
  - **验证**: 能发现所有 skill 目录

- [ ] **SKILL-002 SKILL.md 解析**
  - **文件**: `deep_code/extensions/skills/parser.py`
  - **内容**:
    - Frontmatter 解析（YAML）
    - Skill 数据类（name, description, allowed-tools, model, color）
    - Markdown body 提取
  - **验证**: 能解析 SKILL.md 文件

- [ ] **SKILL-003 Skills 索引构建**
  - **文件**: `deep_code/extensions/skills/registry.py`
  - **内容**:
    - SkillRegistry 类
    - 按 name 索引
    - 按 description 关键词索引
    - 热加载支持
  - **验证**: 能快速查找 skill

### Phase 13: Skills 自动匹配 (P1)

- [ ] **SKILL-004 任务匹配算法**
  - **文件**: `deep_code/extensions/skills/matcher.py`
  - **内容**:
    - 基于 description 的相似度匹配
    - 关键词提取和匹配
    - 匹配分数计算
  - **验证**: 能找到最相关的 skill

- [ ] **SKILL-005 Skill 工具实现**
  - **文件**: `deep_code/core/tools/skill.py`
  - **内容**:
    - SkillTool 类（继承 BaseTool）
    - 参数：skill_name
    - 返回：skill 指令和基础路径
  - **验证**: Agent 能调用 Skill 工具

- [ ] **SKILL-006 上下文注入**
  - **文件**: `deep_code/extensions/skills/executor.py`
  - **内容**:
    - 注入 skill 基础路径
    - 注入 SKILL.md 内容（去除 frontmatter）
    - 注入辅助文件列表
  - **验证**: Claude 能访问 skill 文件

### Phase 14: Skills 工具限制 (P1)

- [ ] **SKILL-007 allowed-tools 白名单**
  - **文件**: `deep_code/extensions/skills/executor.py`
  - **内容**:
    - 解析 allowed-tools 列表
    - 工具调用拦截
    - 权限检查
  - **验证**: skill 只能使用允许的工具

- [ ] **SKILL-008 模型选择支持**
  - **文件**: `deep_code/extensions/skills/executor.py`
  - **内容**:
    - 解析 model 字段
    - 切换到指定模型
    - 恢复原模型
  - **验证**: skill 能使用指定模型

- [ ] **SKILL-009 Skills 可用性列表**
  - **文件**: `deep_code/core/tools/skill.py`
  - **内容**:
    - 在 Skill 工具描述中嵌入 `<available_skills>`
    - 包含 name, description, location
    - 动态更新
  - **验证**: Claude 能看到所有可用 skills

### Phase 15: 集成和测试 (P1)

- [ ] **MCP-019 MCP 集成到 Agent**
  - **文件**: `deep_code/core/agent.py`
  - **内容**:
    - 启动时初始化 MCP 管理器
    - 注册 MCP 工具到工具注册表
    - 处理 MCP 资源引用
  - **验证**: Agent 能使用 MCP 工具

- [ ] **SKILL-010 Skills 集成到 Agent**
  - **文件**: `deep_code/core/agent.py`
  - **内容**:
    - 启动时加载 skills
    - 注册 Skill 工具
    - 自动匹配和应用
  - **验证**: Agent 能自动应用 skills

- [ ] **MCP-020 编写单元测试**
  - **文件**: `tests/test_mcp_*.py`
  - **内容**:
    - 测试 MCP 协议编解码
    - 测试各种传输方式
    - 测试配置解析
    - 测试工具调用
  - **验证**: 所有 MCP 测试通过

- [ ] **SKILL-011 编写单元测试**
  - **文件**: `tests/test_skills_*.py`
  - **内容**:
    - 测试 SKILL.md 解析
    - 测试任务匹配
    - 测试工具限制
    - 测试上下文注入
  - **验证**: 所有 Skills 测试通过

## 技术参考

### MCP 消息格式

**Request**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```

**Response**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "read_file",
        "description": "Read a file from the filesystem",
        "inputSchema": {
          "type": "object",
          "properties": {
            "path": { "type": "string" }
          },
          "required": ["path"]
        }
      }
    ]
  }
}
```

**Notification**:
```json
{
  "jsonrpc": "2.0",
  "method": "notifications/tools/list_changed"
}
```

### MCP 配置格式

**DeepCode 配置文件** (`.deepcode/mcp.json`):
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"],
      "env": {
        "API_KEY": "${API_KEY}"
      }
    },
    "github": {
      "type": "http",
      "url": "https://api.githubcopilot.com/mcp/",
      "headers": {
        "Authorization": "Bearer ${GITHUB_TOKEN}"
      }
    },
    "asana": {
      "type": "sse",
      "url": "https://mcp.asana.com/sse"
    }
  }
}
```

**配置位置**:
- 用户级：`~/.deepcode/mcp.json`
- 项目级：`<project>/.deepcode/mcp.json`
- 本地级：`<project>/.deepcode/mcp.local.json` (不提交到 git)

### SKILL.md 格式

**DeepCode Skills 目录结构**:
```
.deepcode/skills/
├── pdf/
│   ├── SKILL.md              # 必需
│   ├── extract_text.py       # 辅助脚本
│   └── templates/
│       └── summary.html
└── dexie-expert/
    ├── SKILL.md
    ├── PATTERNS.md           # 参考文档
    └── scripts/
        └── validate-schema.ts
```

**SKILL.md 内容**:
```markdown
---
name: pdf
description: Extract and analyze text from PDF documents. Use when users ask to process or read PDFs.
allowed-tools: Read, Grep, Glob, Bash, WebFetch
model: opus
color: orange
---

# PDF Processing Skill

Use the extract_text.py script in this folder to extract text from PDFs:

    python3 extract_text.py <input_file>

After extraction, summarize the key points in a structured format.

## Available Scripts

- `extract_text.py`: Extract text from PDF
- `summarize.py`: Generate summary from text

## Templates

- `templates/summary.html`: HTML summary template
```

### Skill 工具描述

```xml
<available_skills>
  <skill>
    <name>pdf</name>
    <description>
      Extract and analyze text from PDF documents. Use when users
      ask to process or read PDFs.
    </description>
    <location>user</location>
  </skill>
  <skill>
    <name>dexie-expert</name>
    <description>
      Dexie.js database guidance. Use when working with IndexedDB,
      schemas, queries, liveQuery, or database migrations.
    </description>
    <location>project</location>
  </skill>
</available_skills>
```

## 完成记录

| 任务 | 状态 | 完成时间 | 备注 |
|------|------|----------|------|
| MCP-001 | ✅ 完成 | 2026-01-11 | protocol.py 模块 |
| MCP-002 | ✅ 完成 | 2026-01-11 | transport_stdio.py 模块 |
| MCP-003 | ✅ 完成 | 2026-01-11 | transport_http.py 模块 |
| MCP-004 | ✅ 完成 | 2026-01-11 | transport_sse.py 模块 |
| MCP-005 | ✅ 完成 | 2026-01-11 | client.py 模块 |
| MCP-006 | ✅ 完成 | 2026-01-11 | capabilities.py 模块 |
| MCP-007 | ✅ 完成 | 2026-01-11 | MCPResource 数据类 |
| MCP-008 | ✅ 完成 | 2026-01-11 | MCPPrompt 数据类 |
| MCP-009 | ✅ 完成 | 2026-01-11 | 动态更新通知处理 |
| MCP-010 | ✅ 完成 | 2026-01-11 | config.py 环境变量展开 |
| MCP-011 | ✅ 完成 | 2026-01-11 | 配置作用域合并 |
| MCP-012 | ✅ 完成 | 2026-01-11 | manager.py 服务器管理 |
| MCP-013 | ✅ 完成 | 2026-01-11 | MCPToolWrapper JSON Schema验证 |
| MCP-014 | ✅ 完成 | 2026-01-11 | MCPToolRouter 工具路由 |
| MCP-015 | ✅ 完成 | 2026-01-11 | resources.py 资源引用 |
| MCP-016 | ✅ 完成 | 2026-01-11 | deepcode mcp add 命令 |
| MCP-017 | ✅ 完成 | 2026-01-11 | mcp list/get/remove 命令 |
| MCP-018 | ✅ 完成 | 2026-01-11 | /mcp 交互命令 |
| MCP-019 | ✅ 完成 | 2026-01-11 | Agent MCP 集成 |
| MCP-020 | ✅ 完成 | 2026-01-11 | 48个单元测试通过 |
| SKILL-001 | ⬜ 待开始 | | |
| SKILL-002 | ⬜ 待开始 | | |
| SKILL-003 | ⬜ 待开始 | | |
| SKILL-004 | ⬜ 待开始 | | |
| SKILL-005 | ⬜ 待开始 | | |
| SKILL-006 | ⬜ 待开始 | | |
| SKILL-007 | ⬜ 待开始 | | |
| SKILL-008 | ⬜ 待开始 | | |
| SKILL-009 | ⬜ 待开始 | | |
| SKILL-010 | ⬜ 待开始 | | |
| SKILL-011 | ⬜ 待开始 | | |
