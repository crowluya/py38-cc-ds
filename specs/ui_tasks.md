# CLI UI 改进任务清单

> 目标：改进 deep_code CLI 终端界面，实现可滚动输出区域和编辑器化输入框
>
> 参考：Claude Code 终端界面特点
>
> 改动文件：`deep_code/cli/main.py` (`_run_prompt_toolkit_chat` 函数)

## 问题分析

### 当前问题
1. **输出区域滚动失效** - 内容填满后看不到新内容，无法手动滚动
2. **输入框单行限制** - 只能输入单行，长命令不方便编辑
3. **缺少滚动快捷键** - 无法用键盘滚动查看历史输出

### 目标布局
```
┌─────────────────────────────────────────────────────────┐
│  Header (固定 8 行)                                      │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Output Area (可滚动)                                    │
│  - Page Up/Down 滚动                                    │
│  - 鼠标滚轮支持                                          │
│  - Ctrl+Home/End 跳转                                   │
│                                                         │
├─────────────────────────────────────────────────────────┤
│  Status: * Thinking...                                  │
├─────────────────────────────────────────────────────────┤
│  ─────────────────────────────────────────────────────  │
│  > [default]                                            │
│  │ 多行输入区域 (3-10 行动态高度)                         │
│  │ Enter 换行, Ctrl+Enter 提交                           │
│  ─────────────────────────────────────────────────────  │
├─────────────────────────────────────────────────────────┤
│  Page Up/Down: scroll | Ctrl+O: expand | ?: help        │
└─────────────────────────────────────────────────────────┘
```

## 任务清单

### Phase 1: 输出区域可滚动 (P0)

- [x] **UI-001 配置 output_win 支持滚动**
  - **改动点**: `main.py` 的 `output_win` Window 配置
  - **内容**:
    - 使用 `ScrollablePane` 或配置 `scroll_offsets`
    - 确保内容超出时可以滚动
  - **验证**: 大量输出时可以看到所有内容

- [x] **UI-002 添加 Page Up/Down 键绑定**
  - **改动点**: `main.py` 的 KeyBindings
  - **内容**:
    - Page Up: 向上滚动一页
    - Page Down: 向下滚动一页
  - **验证**: 按键可以滚动输出区域

- [x] **UI-003 添加 Ctrl+Home/End 键绑定**
  - **改动点**: `main.py` 的 KeyBindings
  - **内容**:
    - Ctrl+Home: 跳到输出顶部
    - Ctrl+End: 跳到输出底部
  - **验证**: 按键可以跳转到顶部/底部

- [x] **UI-004 保持自动滚动到底部**
  - **改动点**: `main.py` 的 `_refresh_output()`
  - **内容**: 新内容时自动滚动到底部，但用户手动滚动后不强制
  - **验证**: 新输出时自动显示最新内容

### Phase 2: 输入框编辑器化 (P0)

- [x] **UI-005 改为多行输入 Buffer**
  - **改动点**: `main.py` 的 `input_buf` 配置
  - **内容**: `Buffer(multiline=True, ...)`
  - **验证**: 可以输入多行内容

- [x] **UI-006 动态高度输入窗口**
  - **改动点**: `main.py` 的 `input_win` 配置
  - **内容**:
    - 最小高度 3 行
    - 最大高度 10 行
    - 根据内容自动调整
  - **验证**: 输入多行时窗口自动扩展

- [x] **UI-007 修改提交方式为 Ctrl+Enter**
  - **改动点**: `main.py` 的 KeyBindings 和 accept_handler
  - **内容**:
    - Enter: 换行
    - Ctrl+Enter: 提交输入
  - **验证**: Enter 换行，Ctrl+Enter 提交

### Phase 3: 增强功能 (P1)

- [x] **UI-008 添加 Ctrl+L 清屏**
  - **改动点**: `main.py` 的 KeyBindings
  - **内容**: 清空 blocks 列表，刷新显示
  - **验证**: Ctrl+L 清除输出历史

- [x] **UI-009 添加鼠标滚轮支持**
  - **改动点**: `main.py` 的 Application 配置
  - **内容**: `mouse_support=True`
  - **验证**: 鼠标滚轮可以滚动输出区域

- [x] **UI-010 更新底部快捷键提示**
  - **改动点**: `main.py` 的 `_footer_text()`
  - **内容**: 显示新的快捷键提示
  - **验证**: 底部显示正确的快捷键

### Phase 4: 测试验证

- [ ] **UI-011 编写 UI 功能测试**
  - **改动点**: `tests/test_cli_ui.py`
  - **内容**: 测试滚动、输入、快捷键功能
  - **验证**: 所有测试通过

- [ ] **UI-012 手动测试验证**
  - **内容**:
    - 大量输出滚动测试
    - 多行输入测试
    - 所有快捷键测试
  - **验证**: 功能正常工作

## 技术参考

### prompt_toolkit 滚动配置
```python
from prompt_toolkit.layout.containers import ScrollablePane, Window
from prompt_toolkit.layout.dimension import Dimension

# 方案1: ScrollablePane
output_container = ScrollablePane(
    Window(content=output_ctl, wrap_lines=True)
)

# 方案2: Window with scroll_offsets
output_win = Window(
    content=output_ctl,
    scroll_offsets=ScrollOffsets(top=1, bottom=1),
    allow_scroll_beyond_bottom=True,
)
```

### 多行输入配置
```python
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout.dimension import Dimension

input_buf = Buffer(
    multiline=True,
    accept_handler=_accept,
    history=InMemoryHistory(),
)

input_win = Window(
    content=BufferControl(buffer=input_buf),
    height=Dimension(min=3, max=10, preferred=3),
)
```

### 键绑定示例
```python
from prompt_toolkit.key_binding import KeyBindings

kb = KeyBindings()

@kb.add('pageup')
def _(event):
    # 向上滚动
    output_win.vertical_scroll = max(0, output_win.vertical_scroll - 10)

@kb.add('pagedown')
def _(event):
    # 向下滚动
    output_win.vertical_scroll += 10

@kb.add('c-enter')
def _(event):
    # 提交输入
    event.current_buffer.validate_and_handle()
```

## 完成记录

| 任务 | 状态 | 完成时间 | 备注 |
|------|------|----------|------|
| UI-001 | ✅ 完成 | 2026-01-10 | scroll_state + allow_scroll_beyond_bottom |
| UI-002 | ✅ 完成 | 2026-01-10 | Page Up/Down 键绑定 |
| UI-003 | ✅ 完成 | 2026-01-10 | Ctrl+Home/End 键绑定 |
| UI-004 | ✅ 完成 | 2026-01-10 | auto_scroll 状态管理 |
| UI-005 | ✅ 完成 | 2026-01-10 | Buffer(multiline=True) |
| UI-006 | ✅ 完成 | 2026-01-10 | Dimension(min=3, max=10) |
| UI-007 | ✅ 完成 | 2026-01-10 | Ctrl+Enter / Escape+Enter 提交 |
| UI-008 | ✅ 完成 | 2026-01-10 | Ctrl+L 清屏 |
| UI-009 | ✅ 完成 | 2026-01-10 | mouse_support=True |
| UI-010 | ✅ 完成 | 2026-01-10 | 更新 footer 快捷键提示 |
| UI-011 | ⬜ 待开始 | | |
| UI-012 | ⬜ 待开始 | | |
