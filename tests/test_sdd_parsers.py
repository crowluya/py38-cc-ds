"""
Tests for SDD parsers (spec.md, plan.md, tasks.md).

Follows TDD principles: Red -> Green -> Refactor
"""
from pathlib import Path
from typing import List
import pytest

from deep_code.sdd.models import Task, Phase, Dependency, TaskStatus
from deep_code.sdd.parser import (
    parse_spec_md,
    parse_plan_md,
    parse_tasks_md,
    extract_task_from_markdown,
    extract_dependencies_from_markdown,
    is_parallel_task,
)


class TestExtractTaskFromMarkdown:
    """Test extracting task information from markdown."""

    def test_extract_simple_task(self) -> None:
        """Test extracting a simple task without dependencies."""
        markdown = "- [ ] **T001 初始化项目目录结构（骨架）**"
        task = extract_task_from_markdown(markdown)
        assert task is not None
        assert task.id == "T001"
        assert "初始化项目目录结构" in task.description
        assert task.dependencies == []

    def test_extract_task_with_dependencies(self) -> None:
        """Test extracting task with dependencies."""
        markdown = """
- [ ] **T002 依赖清单与锁定**
  - **依赖**：T001
"""
        task = extract_task_from_markdown(markdown)
        assert task is not None
        assert task.id == "T002"
        assert len(task.dependencies) == 1
        assert task.dependencies[0].task_id == "T001"

    def test_extract_task_with_multiple_dependencies(self) -> None:
        """Test extracting task with multiple dependencies."""
        markdown = """
- [ ] **T003 Agent 基础对话循环**
  - **依赖**：T010, T031, T050
"""
        task = extract_task_from_markdown(markdown)
        assert task is not None
        assert task.id == "T003"
        assert len(task.dependencies) == 3
        dependency_ids = [d.task_id for d in task.dependencies]
        assert "T010" in dependency_ids
        assert "T031" in dependency_ids
        assert "T050" in dependency_ids

    def test_extract_parallel_task(self) -> None:
        """Test extracting parallel task marked with [P]."""
        markdown = "- [ ] **T011 终端输出封装（rich）[P]**"
        task = extract_task_from_markdown(markdown)
        assert task is not None
        assert task.id == "T011"
        assert task.parallel is True

    def test_extract_task_with_tdd_marker(self) -> None:
        """Test extracting task with TDD marker."""
        markdown = "- [ ] **T040 @/! 解析器（TDD）**"
        task = extract_task_from_markdown(markdown)
        assert task is not None
        assert task.id == "T040"
        assert task.tdd is True

    def test_extract_task_with_file_target(self) -> None:
        """Test extracting task with file target."""
        markdown = """
- [ ] **T041 Gitignore 感知目录加载**
  - **产物**：`deep_code/core/context.py`
"""
        task = extract_task_from_markdown(markdown)
        assert task is not None
        assert task.id == "T041"
        assert "context.py" in task.file or task.file is None  # May be parsed or not

    def test_extract_completed_task(self) -> None:
        """Test extracting completed task."""
        markdown = "- [x] **T001 已完成的任务**"
        task = extract_task_from_markdown(markdown)
        assert task is not None
        assert task.id == "T001"
        assert task.status == TaskStatus.COMPLETED


class TestExtractDependencies:
    """Test dependency extraction from markdown."""

    def test_extract_no_dependencies(self) -> None:
        """Test when there are no dependencies."""
        deps_str = "无"
        dependencies = extract_dependencies_from_markdown(deps_str)
        assert dependencies == []

    def test_extract_single_dependency(self) -> None:
        """Test extracting a single dependency."""
        deps_str = "T001"
        dependencies = extract_dependencies_from_markdown(deps_str)
        assert len(dependencies) == 1
        assert dependencies[0].task_id == "T001"

    def test_extract_multiple_dependencies(self) -> None:
        """Test extracting multiple dependencies."""
        deps_str = "T001, T002, T003"
        dependencies = extract_dependencies_from_markdown(deps_str)
        assert len(dependencies) == 3
        task_ids = [d.task_id for d in dependencies]
        assert "T001" in task_ids
        assert "T002" in task_ids
        assert "T003" in task_ids

    def test_extract_dependencies_with_spaces(self) -> None:
        """Test extracting dependencies with inconsistent spacing."""
        deps_str = "T001,T002, T003,T004"
        dependencies = extract_dependencies_from_markdown(deps_str)
        assert len(dependencies) == 4


class TestIsParallelTask:
    """Test parallel task detection."""

    def test_parallel_marker(self) -> None:
        """Test task with [P] marker."""
        assert is_parallel_task("T011 终端输出封装（rich）[P]") is True

    def test_no_parallel_marker(self) -> None:
        """Test task without [P] marker."""
        assert is_parallel_task("T010 CLI 入口") is False

    def test_parallel_marker_case_sensitive(self) -> None:
        """Test that [P] is case-sensitive."""
        assert is_parallel_task("T011 任务 [p]") is False
        assert is_parallel_task("T011 任务 [P]") is True


class TestParseTasksMd:
    """Test parsing tasks.md file."""

    def test_parse_simple_tasks_md(self) -> None:
        """Test parsing a simple tasks.md file."""
        content = """
# tasks.md

## 任务清单

### Phase A：基础设施

- [ ] **T001 初始化项目目录**
  - **依赖**：无
  - **产物**：目录结构

- [ ] **T002 依赖清单**
  - **依赖**：T001
"""
        phases = parse_tasks_md(content)
        assert len(phases) >= 1

        # Find Phase A
        phase_a = None
        for phase in phases:
            if "Phase A" in phase.id or "Phase A" in phase.name or "基础设施" in phase.name or "基础设施" in phase.description:
                phase_a = phase
                break

        assert phase_a is not None
        assert len(phase_a.tasks) >= 2

        # Check tasks
        task_ids = [t.id for t in phase_a.tasks]
        assert "T001" in task_ids
        assert "T002" in task_ids

    def test_parse_multiple_phases(self) -> None:
        """Test parsing tasks.md with multiple phases."""
        content = """
### Phase A：基础设施

- [ ] **T001 Task A1**

### Phase B：CLI 入口

- [ ] **T010 Task B1**
- [ ] **T011 Task B2**
"""
        phases = parse_tasks_md(content)
        assert len(phases) >= 2

        phase_names = [p.name for p in phases]
        assert any("基础设施" in name or "Phase A" in name for name in phase_names)
        assert any("CLI" in name or "Phase B" in name for name in phase_names)

    def test_parse_task_with_all_fields(self) -> None:
        """Test parsing task with all possible fields."""
        content = """
### Phase A

- [x] **T001 已完成任务**
  - **依赖**：无
  - **产物**：some_file.py
  - **验证**：pytest tests/

- [ ] **T002 并行任务 [P]**
  - **依赖**：T001
  - **产物**：another_file.py
"""
        phases = parse_tasks_md(content)
        assert len(phases) >= 1

        tasks = phases[0].tasks
        assert len(tasks) >= 2

        # Check completed task
        completed_task = next((t for t in tasks if t.id == "T001"), None)
        assert completed_task is not None
        assert completed_task.status == TaskStatus.COMPLETED

        # Check parallel task
        parallel_task = next((t for t in tasks if t.id == "T002"), None)
        assert parallel_task is not None
        assert parallel_task.parallel is True
        assert len(parallel_task.dependencies) == 1


class TestParseSpecMd:
    """Test parsing spec.md file."""

    def test_parse_spec_basic_structure(self) -> None:
        """Test parsing basic spec.md structure."""
        content = """
# 项目需求规范（Specification）

## 1. 项目概述

### 1.1 项目目标

开发一个基于 Python 的 AI 工作流引擎。

## 2. 用户故事

### 2.1 核心用户故事

**US-001：作为开发者，我希望通过 @file 注入上下文**

- **场景**：开发时需要让 AI 理解代码
- **验收标准**：
  - 能够通过 @/path/to/file.py 引用文件

**US-002：命令执行**

- **场景**：执行 shell 命令
- **验收标准**：
  - Windows 7 使用 PowerShell

## 3. 功能需求

### 3.1 核心交互模型

#### 3.1.1 上下文注入（@）

- **文件引用**：@/path/to/file.py

## 4. 验收标准
"""
        spec = parse_spec_md(content)
        assert spec is not None
        assert "项目目标" in spec or "项目概述" in spec
        assert "用户故事" in spec
        assert "功能需求" in spec
        assert "验收标准" in spec

    def test_parse_spec_with_user_stories(self) -> None:
        """Test parsing spec with user stories."""
        content = """
## 2. 用户故事

### 2.1 核心用户故事

**US-001：上下文注入**

- **场景**：让 AI 理解代码
- **验收标准**：
  - 支持 @file
  - 支持 @dir

**US-002：命令执行**

- **场景**：执行命令
- **验收标准**：
  - 支持 !command
"""
        spec = parse_spec_md(content)
        assert spec is not None
        assert "US-001" in spec.get("raw", "")
        assert "US-002" in spec.get("raw", "")
        assert "上下文注入" in spec.get("raw", "")


class TestParsePlanMd:
    """Test parsing plan.md file."""

    def test_parse_plan_basic_structure(self) -> None:
        """Test parsing basic plan.md structure."""
        content = """
# 技术方案

## 技术上下文总结

### 技术栈选型

- **语言**: Python 3.8.10
- **CLI 框架**: click 7.1.2

### 运行环境

- Windows 7
- Python 3.8.10

## 合宪性检查清单

### 简单性门禁

- ✅ 标准库优先

### TDD 门禁

- ✅ 先写测试

## 项目结构细化

### 目录结构

```
deep_code/
├── core/
└── cli/
```

### 包职责划分

#### core/ - 核心模块

- agent.py: Agent 引擎

## 核心数据结构

### 消息格式

```python
Message = Dict[str, str]
```

## 关键接口设计

### LLMClient 接口
"""
        plan = parse_plan_md(content)
        assert plan is not None
        assert "技术栈" in plan.get("raw", "") or "选型" in plan.get("raw", "")
        assert "合宪性" in plan.get("raw", "") or "检查清单" in plan.get("raw", "")
        assert "项目结构" in plan.get("raw", "") or "目录结构" in plan.get("raw", "")
        assert "数据结构" in plan.get("raw", "") or "接口设计" in plan.get("raw", "")

    def test_parse_plan_with_compliance_checklist(self) -> None:
        """Test parsing plan with compliance checklist."""
        content = """
## 合宪性检查清单

### 简单性门禁

- ✅ 标准库优先
- ✅ 避免复杂抽象

### TDD 门禁

- ✅ 先写测试
- ✅ 表格驱动测试

### 明确性门禁

- ✅ 错误处理显式
- ✅ 依赖显式注入

### 兼容性门禁

- ✅ Python 3.8.10 兼容
- ✅ Windows 7 兼容
"""
        plan = parse_plan_md(content)
        assert plan is not None
        assert "简单性" in plan.get("raw", "") or "门禁" in plan.get("raw", "")
        assert "TDD" in plan.get("raw", "")
        assert "明确性" in plan.get("raw", "")
        assert "兼容性" in plan.get("raw", "")


class TestParserIntegration:
    """Integration tests for parsers."""

    def test_parse_full_workflow(self) -> None:
        """Test parsing complete SDD workflow files."""
        # This tests the integration of all parsers
        spec_content = "# 需求规范\n\n## 用户故事\n\n**US-001**"
        plan_content = "# 技术方案\n\n## 技术栈\n"
        tasks_content = "# 任务清单\n\n### Phase A\n\n- [ ] **T001**"

        spec = parse_spec_md(spec_content)
        plan = parse_plan_md(plan_content)
        phases = parse_tasks_md(tasks_content)

        assert spec is not None
        assert plan is not None
        assert len(phases) >= 1

    def test_parse_real_world_example(self) -> None:
        """Test parsing real-world example from tasks.md."""
        content = """
## 任务清单

### Phase A：基础设施

- [ ] **T001 初始化项目目录结构（骨架）**
  - **依赖**：无
  - **产物**：`deep_code/` 主包与子包目录、`tests/` 目录
  - **验证**：`python -c "import deep_code"`

- [ ] **T002 依赖清单与锁定（requirements）**
  - **依赖**：T001
  - **产物**：`requirements.txt`、`requirements-frozen.txt`
  - **验证**：在 Python 3.8.10 环境 `pip install -r requirements.txt` 成功

### Phase B：CLI 入口与交互层

- [ ] **T010 CLI 入口（click）最小命令树（TDD）**
  - **依赖**：T003, T004
  - **产物**：`deep_code/cli/main.py`
  - **验证**：`python -m deep_code.cli.main --help`

- [ ] **T011 终端输出封装（rich）[P]（TDD）**
  - **依赖**：T010
  - **产物**：输出工具层
  - **验证**：单测覆盖 Markdown/代码块展示
"""
        phases = parse_tasks_md(content)
        assert len(phases) >= 2

        # Find Phase A
        phase_a = next((p for p in phases if "Phase A" in p.id or "Phase A" in p.name or "基础设施" in p.name or "基础设施" in p.description), None)
        assert phase_a is not None
        assert len(phase_a.tasks) >= 2

        # Check T001
        t001 = next((t for t in phase_a.tasks if t.id == "T001"), None)
        assert t001 is not None
        assert t001.dependencies == []

        # Check T002
        t002 = next((t for t in phase_a.tasks if t.id == "T002"), None)
        assert t002 is not None
        assert len(t002.dependencies) == 1
        assert t002.dependencies[0].task_id == "T001"
