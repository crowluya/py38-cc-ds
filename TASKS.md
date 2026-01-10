# Claude Code Python MVP - 功能增强任务清单

> 目标: 实现类似 Claude Code 的完整 Tool Use 架构
> 基于现有代码结构进行增量开发，每完成一个任务即可测试验证

---

## Phase 1: Tool Use 基础框架

### T001 - 创建工具定义模块 `core/tools/base.py` ✅
- [x] 定义 `Tool` 抽象基类
  - `name: str` - 工具名称
  - `description: str` - 工具描述 (给 LLM 看)
  - `parameters: dict` - JSON Schema 参数定义
  - `execute(params: dict) -> ToolResult` - 执行方法
- [x] 定义 `ToolResult` 数据类 (复用现有 `core/agent.py` 中的)
- [x] 定义 `ToolError` 异常类
- **依赖**: 无
- **测试**: `tests/test_tools_base.py` ✅ 23 passed

### T002 - 创建工具注册表 `core/tools/registry.py` ✅
- [x] 实现 `ToolRegistry` 类
  - `register(tool: Tool)` - 注册工具
  - `get(name: str) -> Tool` - 获取工具
  - `list_tools() -> List[Tool]` - 列出所有工具
  - `get_tools_schema() -> List[dict]` - 获取 OpenAI functions 格式的 schema
- [x] 支持工具分组 (file, shell, search 等)
- **依赖**: T001
- **测试**: `tests/test_tools_registry.py` ✅ 24 passed

### T003 - 更新 LLM Client 支持 Tool Use ✅
- [x] 修改 `llm/client.py` 的 `chat_completion` 签名
  - 添加 `tools: Optional[List[dict]]` 参数
  - 添加 `tool_choice: Optional[str]` 参数 ("auto", "none", 工具名)
- [x] 修改 `llm/openai_client.py` 实现 functions 调用
- [x] 修改 `llm/requests_client.py` 实现 (DeepSeek 兼容)
- [x] 返回值增加 `tool_calls` 字段
- **依赖**: T001, T002
- **测试**: `tests/test_llm_tools.py` ✅ 12 passed

---

## Phase 2: 核心工具实现

### T004 - 实现 Read 工具 `core/tools/read.py` ✅
- [x] 读取文件内容
- [x] 支持 `offset` 和 `limit` 参数 (行号范围)
- [x] 支持图片文件 (返回 base64)
- [x] 路径安全检查 (防止路径穿越)
- [x] 文件不存在时返回友好错误
- **依赖**: T001, T002
- **测试**: `tests/test_tool_read.py` ✅ 22 passed

### T005 - 实现 Write 工具 `core/tools/write.py` ✅
- [x] 写入文件内容
- [x] 自动创建父目录
- [x] 支持 `overwrite` 参数
- [x] 路径安全检查
- [x] 权限检查集成
- **依赖**: T001, T002
- **测试**: `tests/test_tool_write.py` ✅ 16 passed

### T006 - 实现 Edit 工具 `core/tools/edit.py`
- [ ] 基于 `old_string` -> `new_string` 的精确替换
- [ ] 支持 `replace_all` 参数
- [ ] 唯一性检查 (old_string 必须唯一)
- [ ] 保留文件权限和编码
- [ ] 权限检查集成
- **依赖**: T001, T002
- **测试**: `tests/test_tool_edit.py`

### T007 - 实现 Bash 工具 `core/tools/bash.py`
- [ ] 执行 shell 命令 (复用 `core/executor.py`)
- [ ] 支持 `timeout` 参数
- [ ] 支持 `working_dir` 参数
- [ ] 危险命令检测 (rm -rf, etc.)
- [ ] 权限检查集成
- **依赖**: T001, T002
- **测试**: `tests/test_tool_bash.py`

### T008 - 实现 Glob 工具 `core/tools/glob.py`
- [ ] 文件模式匹配搜索
- [ ] 支持 `pattern` 参数 (如 `**/*.py`)
- [ ] 支持 `path` 参数 (搜索根目录)
- [ ] 返回匹配文件列表 (按修改时间排序)
- [ ] 限制返回数量
- **依赖**: T001, T002
- **测试**: `tests/test_tool_glob.py`

### T009 - 实现 Grep 工具 `core/tools/grep.py`
- [ ] 内容搜索 (正则表达式)
- [ ] 支持 `pattern`, `path`, `glob` 参数
- [ ] 支持 `-A`, `-B`, `-C` 上下文行
- [ ] 支持 `output_mode`: content/files_with_matches/count
- [ ] 限制返回数量
- **依赖**: T001, T002
- **测试**: `tests/test_tool_grep.py`

---

## Phase 3: Agent 工具循环

### T010 - 实现工具执行器 `core/tool_executor.py`
- [ ] `ToolExecutor` 类
  - `execute(tool_call: ToolCall) -> ToolResult`
  - 权限检查
  - 错误处理
  - 日志记录
- [ ] 支持并行执行多个工具
- **依赖**: T001-T009
- **测试**: `tests/test_tool_executor.py`

### T011 - 更新 Agent 支持工具循环
- [ ] 修改 `core/agent.py` 的 `process` 方法
- [ ] 实现工具循环:
  ```
  while True:
      response = llm.chat(messages, tools=tools)
      if no tool_calls:
          break
      for tool_call in response.tool_calls:
          result = executor.execute(tool_call)
          messages.append(tool_result_message)
  ```
- [ ] 添加 `max_tool_rounds` 限制 (防止无限循环)
- [ ] 添加工具调用回调 (用于 UI 显示)
- **依赖**: T010
- **测试**: `tests/test_agent_tool_loop.py`

### T012 - 更新 CLI 显示工具调用
- [ ] 修改 `cli/main.py` 显示工具调用过程
- [ ] 使用 `ToolBlock` 渲染每个工具调用
- [ ] 支持展开/折叠工具输出
- [ ] 显示工具执行状态 (成功/失败)
- **依赖**: T011
- **测试**: `tests/test_cli_tools.py`

---

## Phase 4: 高级功能

### T013 - 实现 TodoWrite 工具 `core/tools/todo.py`
- [ ] 任务列表管理
- [ ] 支持 pending/in_progress/completed 状态
- [ ] 持久化到会话
- [ ] CLI 显示任务列表
- **依赖**: T001, T002
- **测试**: `tests/test_tool_todo.py`

### T014 - 实现 Task 工具 (子代理) `core/tools/task.py`
- [ ] 启动子代理执行复杂任务
- [ ] 支持不同 agent 类型 (Explore, Plan, Bash 等)
- [ ] 子代理结果汇总
- [ ] 支持后台运行
- **依赖**: T011
- **测试**: `tests/test_tool_task.py`

### T015 - 实现 MCP 基础框架 `extensions/mcp/`
- [ ] MCP 协议解析
- [ ] 工具服务器连接
- [ ] 动态工具注册
- [ ] 配置文件支持
- **依赖**: T002
- **测试**: `tests/test_mcp.py`

---

## Phase 5: 集成与优化

### T016 - 权限系统集成
- [ ] 所有工具集成权限检查
- [ ] 工具级别的 allow/deny 规则
- [ ] 危险操作二次确认
- **依赖**: T004-T009
- **测试**: `tests/test_tools_permissions.py`

### T017 - 错误处理优化
- [ ] 统一错误格式
- [ ] 友好的错误提示
- [ ] 错误恢复建议
- **依赖**: T010
- **测试**: `tests/test_tools_errors.py`

### T018 - 性能优化
- [ ] 工具结果缓存
- [ ] 并行工具执行
- [ ] 大文件分块读取
- **依赖**: T010
- **测试**: `tests/test_tools_performance.py`

---

## 任务状态说明

- `[ ]` - 待开始
- `[x]` - 已完成
- `[~]` - 进行中
- `[-]` - 已跳过

## 开发顺序建议

```
T001 -> T002 -> T003 -> T004 -> T005 -> T006 -> T007 -> T008 -> T009
                                    \                              /
                                     +-----> T010 -> T011 -> T012
                                                        |
                                              T013, T014, T015
                                                        |
                                              T016, T017, T018
```

## 验收标准

每个任务完成后需要:
1. 单元测试通过
2. 集成测试通过 (如适用)
3. 代码符合 Python 3.8.10 兼容性要求
4. 更新本文档状态
5. Git commit 并 push
