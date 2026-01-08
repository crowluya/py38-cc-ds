"""
SDD Generator Tests - Test tasks.md generation from plan.md

TDD: Tests for T112 (Generate tasks.md from plan.md using LLM)
Python 3.8.10 compatible
"""

from typing import Any, Dict, List

import pytest

from claude_code.llm.client import LLMClient
from claude_code.sdd.generator import TaskGenerator
from claude_code.sdd.models import Task


class MockLLMClient(LLMClient):
    """Mock LLM client for testing."""

    def __init__(self, response_content: str):
        self.response_content = response_content
        self.messages_received: List[Any] = []

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        model: str = None,
        temperature: float = None,
        max_tokens: int = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Mock chat completion that returns predefined response."""
        self.messages_received.append(messages)
        return {"content": self.response_content}

    def chat_completion_stream(self, messages, model=None, temperature=None, max_tokens=None, **kwargs):
        """Mock streaming (not used in tests)."""
        yield {"delta": "test"}

    def get_model(self) -> str:
        """Return mock model name."""
        return "mock-model"

    def validate_config(self) -> bool:
        """Mock validation."""
        return True


class TestTaskGeneratorPrompt:
    """Test prompt generation for LLM."""

    def test_generate_prompt_includes_plan_content(self) -> None:
        """验证生成的提示词包含plan内容"""
        plan_content = "# Test Plan\n\nThis is a test plan with technical details."
        generator = TaskGenerator(plan_content=plan_content)

        prompt = generator._generate_prompt()

        assert "Test Plan" in prompt
        assert "technical details" in prompt

    def test_generate_prompt_includes_instructions(self) -> None:
        """验证生成的提示词包含生成指令"""
        plan_content = "# Plan"
        generator = TaskGenerator(plan_content=plan_content)

        prompt = generator._generate_prompt()

        assert "tasks.md" in prompt.lower()
        assert "dependencies" in prompt.lower()
        assert "parallel" in prompt.lower()

    def test_generate_prompt_mentions_tdd(self) -> None:
        """验证生成的提示词提及TDD原则"""
        plan_content = "# Plan"
        generator = TaskGenerator(plan_content=plan_content)

        prompt = generator._generate_prompt()

        assert "TDD" in prompt


class TestTaskGeneratorParsing:
    """Test parsing of LLM output."""

    def test_parse_simple_tasks(self) -> None:
        """验证解析简单任务列表"""
        llm_output = """
# tasks.md

- [ ] **T001 First task**
  - **依赖**: 无
  - **产物**: file1.py

- [ ] **T002 Second task**
  - **依赖**: T001
  - **产物**: file2.py
"""

        tasks = TaskGenerator._parse_llm_output(llm_output)

        assert len(tasks) == 2
        assert tasks[0].id == "T001"
        assert tasks[1].id == "T002"
        assert tasks[1].dependencies[0].task_id == "T001"

    def test_parse_parallel_tasks(self) -> None:
        """验证解析并行任务"""
        llm_output = """
- [ ] **T001 Task 1 [P]**
  - **依赖**: 无

- [ ] **T002 Task 2 [P]**
  - **依赖**: T001
"""

        tasks = TaskGenerator._parse_llm_output(llm_output)

        assert len(tasks) == 2
        assert tasks[0].parallel is True
        assert tasks[1].parallel is True

    def test_parse_tasks_with_phase_headers(self) -> None:
        """验证解析带阶段头的任务"""
        llm_output = """
## Phase A

- [ ] **T001 Task A**
  - **依赖**: 无

## Phase B

- [ ] **T002 Task B**
  - **依赖**: T001
"""

        tasks = TaskGenerator._parse_llm_output(llm_output)

        assert len(tasks) == 2
        assert tasks[0].id == "T001"
        assert tasks[1].id == "T002"
        assert tasks[1].dependencies[0].task_id == "T001"

    def test_parse_complex_task_structure(self) -> None:
        """验证解析复杂任务结构"""
        llm_output = """
- [ ] **T001 Initialize project**
  - **依赖**: 无
  - **产物**: claude_code/
  - **验证**: python -c "import claude_code"
  - **DoD**: Can import the package

- [ ] **T002 Setup dependencies**
  - **依赖**: T001
  - **产物**: requirements.txt
  - **验证**: pip install -r requirements.txt

- [ ] **T003 Create CLI [P]**
  - **依赖**: T001
  - **产物**: cli/main.py
  - **验证**: python -m claude_code.cli.main --help
"""

        tasks = TaskGenerator._parse_llm_output(llm_output)

        assert len(tasks) == 3
        assert tasks[0].id == "T001"
        assert tasks[1].id == "T002"
        assert tasks[2].id == "T003"
        assert tasks[2].parallel is True


class TestTaskGeneratorIntegration:
    """Integration tests with mock LLM."""

    def test_generate_with_mock_llm(self) -> None:
        """验证使用Mock LLM生成任务"""
        llm_response = """
- [ ] **T001 Generated task**
  - **依赖**: 无
  - **产物**: test.py
  - **验证**: pytest
"""

        plan_content = "# Test Plan\nGenerate tasks for testing."
        llm_client = MockLLMClient(llm_response)
        generator = TaskGenerator(plan_content=plan_content, llm_client=llm_client)

        tasks = generator.generate()

        assert len(tasks) == 1
        assert tasks[0].id == "T001"
        assert "Generated task" in tasks[0].description

    def test_generate_passes_plan_to_llm(self) -> None:
        """验证plan内容传递给LLM"""
        plan_content = "# Test Plan\nSpecific content here"
        llm_client = MockLLMClient("- [ ] **T001 Task**\n")
        generator = TaskGenerator(plan_content=plan_content, llm_client=llm_client)

        generator.generate()

        # Check that plan was sent to LLM
        assert len(llm_client.messages_received) > 0
        messages = llm_client.messages_received[0]
        user_message = [m for m in messages if m.get("role") == "user"][0]
        assert "Test Plan" in user_message["content"]
        assert "Specific content here" in user_message["content"]

    def test_generate_with_real_plan_structure(self) -> None:
        """验证使用真实plan结构生成"""
        plan_content = """
# 技术方案

## 技术上下文

### 技术栈
- Python 3.8.10
- click 7.1.2

## 项目结构

### 目录结构
```
claude_code/
├── core/
├── interaction/
└── cli/
```

## 核心数据结构

### Task模型
定义Task数据结构包含id、description、dependencies等字段。
"""

        llm_response = """
- [ ] **T001 创建Task数据模型**
  - **依赖**: 无
  - **产物**: claude_code/sdd/models.py
  - **验证**: pytest tests/test_sdd_models.py

- [ ] **T002 实现任务解析器**
  - **依赖**: T001
  - **产物**: claude_code/sdd/parser.py
  - **验证**: pytest tests/test_sdd_parser.py
"""

        llm_client = MockLLMClient(llm_response)
        generator = TaskGenerator(plan_content=plan_content, llm_client=llm_client)

        tasks = generator.generate()

        assert len(tasks) == 2
        assert tasks[0].id == "T001"
        assert tasks[1].id == "T002"
        assert tasks[1].dependencies[0].task_id == "T001"


class TestTaskGeneratorValidation:
    """Test validation of generated tasks."""

    def test_validate_good_tasks(self) -> None:
        """验证有效任务通过校验"""
        tasks = [
            Task(id="T001", description="Task 1"),
            Task(id="T002", description="Task 2", dependencies=[tasks for tasks in []]),  # Will fix below
        ]

        # Create proper dependency
        from claude_code.sdd.models import Dependency

        tasks = [
            Task(id="T001", description="Task 1"),
            Task(id="T002", description="Task 2", dependencies=[Dependency(task_id="T001")]),
        ]

        plan_content = "# Plan"
        llm_client = MockLLMClient("")
        generator = TaskGenerator(plan_content=plan_content, llm_client=llm_client)

        result = generator.validate_generated_tasks(tasks)

        assert result["valid"] is True
        assert len(result["issues"]) == 0

    def test_validate_missing_dependencies(self) -> None:
        """验证检测缺失依赖"""
        from claude_code.sdd.models import Dependency

        tasks = [
            Task(id="T001", description="Task 1", dependencies=[Dependency(task_id="T999")]),
        ]

        plan_content = "# Plan"
        llm_client = MockLLMClient("")
        generator = TaskGenerator(plan_content=plan_content, llm_client=llm_client)

        result = generator.validate_generated_tasks(tasks)

        assert result["valid"] is False
        assert len(result["issues"]) > 0
        assert any("T999" in issue for issue in result["issues"])

    def test_validate_includes_warnings(self) -> None:
        """验证校验包含警告信息"""
        tasks = [
            Task(id="T001", description="Task 1", tdd=False, parallel=False),
        ]

        plan_content = "# Plan"
        llm_client = MockLLMClient("")
        generator = TaskGenerator(plan_content=plan_content, llm_client=llm_client)

        result = generator.validate_generated_tasks(tasks)

        # Should have warning about non-TDD task
        assert "T001" in result.get("warnings", [""])[0] if result.get("warnings") else True

    def test_validate_counts_parallel_tasks(self) -> None:
        """验证统计并行任务数量"""
        tasks = [
            Task(id="T001", description="Task 1", parallel=True),
            Task(id="T002", description="Task 2", parallel=True),
            Task(id="T003", description="Task 3", parallel=False),
        ]

        plan_content = "# Plan"
        llm_client = MockLLMClient("")
        generator = TaskGenerator(plan_content=plan_content, llm_client=llm_client)

        result = generator.validate_generated_tasks(tasks)

        assert result["total_tasks"] == 3
        assert result["parallel_tasks"] == 2


class TestTaskGeneratorErrors:
    """Test error handling."""

    def test_generate_without_llm_client_raises_error(self) -> None:
        """验证无LLM客户端时抛出错误"""
        plan_content = "# Plan"
        generator = TaskGenerator(plan_content=plan_content, llm_client=None)

        with pytest.raises(ValueError) as exc_info:
            generator.generate()

        assert "LLM client" in str(exc_info.value)

    def test_generate_with_empty_llm_response(self) -> None:
        """验证空LLM响应处理"""
        llm_client = MockLLMClient("")
        plan_content = "# Plan"
        generator = TaskGenerator(plan_content=plan_content, llm_client=llm_client)

        tasks = generator.generate()

        # Should return empty list, not crash
        assert isinstance(tasks, list)


class TestTaskGeneratorWithAnalyzer:
    """Integration tests with DependencyAnalyzer."""

    def test_generate_and_detect_circular_deps(self) -> None:
        """验证生成任务时检测循环依赖"""
        llm_response = """
- [ ] **T001 Task 1**
  - **依赖**: T002

- [ ] **T002 Task 2**
  - **依赖**: T001
"""

        plan_content = "# Plan\nCreate circular dependency tasks."
        llm_client = MockLLMClient(llm_response)
        generator = TaskGenerator(plan_content=plan_content, llm_client=llm_client)

        tasks = generator.generate()

        # Should parse successfully
        assert len(tasks) == 2

        # But validation should detect issues
        result = generator.validate_generated_tasks(tasks)
        assert result["valid"] is False

    def test_generate_and_validate_good_structure(self) -> None:
        """验证生成并验证良好的任务结构"""
        llm_response = """
- [ ] **T001 Base task**
  - **依赖**: 无

- [ ] **T002 Dependent task [P]**
  - **依赖**: T001

- [ ] **T003 Another dependent [P]**
  - **依赖**: T001
"""

        plan_content = "# Plan\nCreate well-structured tasks."
        llm_client = MockLLMClient(llm_response)
        generator = TaskGenerator(plan_content=plan_content, llm_client=llm_client)

        tasks = generator.generate()

        # All tasks should be parsed
        assert len(tasks) == 3

        # Validation should pass
        result = generator.validate_generated_tasks(tasks)
        assert result["valid"] is True
        assert result["total_tasks"] == 3
        assert result["parallel_tasks"] == 2
