# CLI 命令增强任务清单

> 目标：实现 Claude Code 核心 CLI 功能
>
> 参考：Claude Code 官方 CLI 方案
>
> 改动文件：`deep_code/cli/main.py`, `deep_code/cli/session.py`, `deep_code/cli/completion.py`

## 功能概述

### 1. 会话管理 (Session Management)
- `--resume` 恢复上次会话
- `--continue` 继续最近对话
- 会话历史持久化

### 2. Tab 补全 (File Completion)
- `@` 触发文件/目录补全
- 支持相对路径和绝对路径
- 模糊匹配

### 3. 项目初始化 (Init Command)
- `init` 命令创建 CLAUDE.md
- 自动检测项目类型
- 生成配置文件

### 4. Token 统计 (Token Statistics)
- 显示每次请求的 token 使用量
- 累计统计
- 成本估算

## 任务清单

### Phase 1: 会话管理 (P0)

- [ ] **CMD-001 创建会话存储模块**
  - **文件**: `deep_code/cli/session.py`
  - **内容**:
    - Session 数据类 (id, messages, created_at, updated_at)
    - SessionStore 类 (save, load, list, delete)
    - 存储位置: `.deepcode/sessions/`
  - **验证**: 能保存和加载会话

- [ ] **CMD-002 添加 --resume 参数**
  - **文件**: `deep_code/cli/main.py`
  - **内容**:
    - 添加 `--resume [SESSION_ID]` 参数
    - 无 ID 时恢复最近会话
    - 加载历史消息到上下文
  - **验证**: `chat --resume` 恢复上次对话

- [ ] **CMD-003 添加 --continue 参数**
  - **文件**: `deep_code/cli/main.py`
  - **内容**:
    - 添加 `-c, --continue` 参数
    - 自动继续最近一次会话
    - 与 --resume 的区别：不需要 ID
  - **验证**: `chat -c` 继续最近对话

- [ ] **CMD-004 会话自动保存**
  - **文件**: `deep_code/cli/main.py`
  - **内容**:
    - 每次对话后自动保存会话
    - 保存消息历史和上下文
    - 会话过期清理 (7天)
  - **验证**: 对话自动持久化

### Phase 2: Tab 补全 (P0)

- [ ] **CMD-005 创建补全模块**
  - **文件**: `deep_code/cli/completion.py`
  - **内容**:
    - FileCompleter 类
    - 支持 `@` 前缀触发
    - 目录和文件补全
  - **验证**: 输入 `@` 后显示文件列表

- [ ] **CMD-006 集成到输入框**
  - **文件**: `deep_code/cli/main.py`
  - **内容**:
    - 将 FileCompleter 添加到 BufferControl
    - 支持 Tab 键触发
    - 补全菜单显示
  - **验证**: Tab 键触发文件补全

- [ ] **CMD-007 模糊匹配支持**
  - **文件**: `deep_code/cli/completion.py`
  - **内容**:
    - 模糊匹配算法
    - 按相关度排序
    - 支持驼峰/下划线匹配
  - **验证**: 输入部分字符能匹配文件

### Phase 3: Init 命令 (P1 [ ] **CMD-008 添加 init 命令**
  - **文件**: `deep_code/cli/main.py`
  - **内容**:
    - `init` 子命令
    - 创建 `.deepcode/` 目录
    - 生成默认 `settings.json`
  - **验证**: `init` 创建配置目录

- [ ] **CMD-009 生成 CLAUDE.md**
  - **文件**: `deep_code/cli/main.py`
  - **内容**:
    - 检测项目类型 (Python/Node/Go 等)
    - 生成项目描述模板
    - 包含常用命令提示
  - **验证**: 生成适合项目的 CLAUDE.md

- [ ] **CMD-010 交互式初始化**
  - **文件**: `deep_code/cli/main.py`
  - **内容**:
    - 询问项目名称
    - 选择项目类型
    - 配置 LLM 设置
  - **验证**: 交互式完成初始化

### Phase 4: Token 统计 (P1)

- [ ] **CMD-011 Token 计数器**
  - **文件**: `deep_code/cli/token_stats.py`
  - **内容**:
    - TokenStats 类
    - 记录 prompt_tokens, completion_tokens
    - 累计统计
  - **验证**: 能统计 token 使用量

- [ ] **CMD-012 显示 Token 统计**
  - **文件**: `deep_code/cli/main.py`
  - **内容**:
    - 每次响应后显示 token 数
    - 格式: `[tokens: 123 in / 456 out]`
    - 可通过设置关闭
  - **验证**: 响应后显示 token 统计

- [ ] **CMD-013 成本估算**
  - **文件**: `deep_code/cli/token_stats.py`
  - **内容**:
    - 根据模型计算成本
    - 支持自定义价格配置
    - 会话累计成本
  - **验证**: 显示估算成本

### Phase 5: 测试

- [ ] **CMD-014 编写单元测试**
  - **文件**: `tests/test_cli_session.py`, `tests/test_cli_completion.py`
  - **内容**: 测试会话、补全、统计功能
  - **验证**: 所有测试通过

## 技术参考

### 会话存储格式
```json
{
  "id": "uuid",
  "created_at": "ISO8601",
  "updated_at": "ISO8601",
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ],
  "context": {
    "project_root": "/path/to/project",
    "mode": "default"
  },
  "stats": {
    "total_tokens": 1234,
    "prompt_tokens": 567,
    "completion_tokens": 667
  }
}
```

### 文件补全实现
```python
from prompt_toolkit.completion import Completer, Completion

class FileCompleter(Completer):
    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        # 检测 @ 前缀
        if '@' in text:
            prefix = text.rsplit('@', 1)[-1]
            # 列出匹配的文件
            for path in glob.glob(prefix + '*'):
                yield Completion(path, start_position=-len(prefix))
```

### Token 统计显示
```python
def _format_token_stats(stats: TokenStats) -> str:
    return f"[tokens: {stats.prompt_tokens} in / {stats.completion_tokens} out | ${stats.cost:.4f}]"
```

## 完成记录

| 任务 | 状态 | 完成时间 | 备注 |
|------|------|----------|------|
| CMD-001 | ✅ 完成 | 2026-01-11 | session.py 模块 |
| CMD-002 | ✅ 完成 | 2026-01-11 | --resume 参数 |
| CMD-003 | ✅ 完成 | 2026-01-11 | --continue 参数 |
| CMD-004 | ✅ 完成 | 2026-01-11 | 自动保存会话 |
| CMD-005 | ✅ 完成 | 2026-01-11 | completion.py 模块 |
| CMD-006 | ✅ 完成 | 2026-01-11 | Buffer completer 集成 |
| CMD-007 | ✅ 完成 | 2026-01-11 | fuzzy_match 函数 |
| CMD-008 | ✅ 完成 | 2026-01-11 | init 命令 |
| CMD-009 | ✅ 完成 | 2026-01-11 | CLAUDE.md 模板生成 |
| CMD-010 | ✅ 完成 | 2026-01-11 | 交互式项目初始化 |
| CMD-011 | ✅ 完成 | 2026-01-11 | token_stats.py 模块 |
| CMD-012 | ✅ 完成 | 2026-01-11 | format_stats 方法 |
| CMD-013 | ✅ 完成 | 2026-01-11 | calculate_cost 方法 |
| CMD-014 | ⬜ 待开始 | | |
