"""
Tests for SDD generators (spec.md -> plan.md).

Follows TDD principles: Red -> Green -> Refactor
Tests for T111: 从spec.md生成plan.md的工作流
"""
from typing import Dict
import pytest

from deep_code.llm.client import LLMClient
from deep_code.sdd.generator import PlanGenerator


class FakeLLMClient(LLMClient):
    """Fake LLM client for testing."""

    def __init__(self, response_content: str = "") -> None:
        self.response_content = response_content
        self.last_messages = None

    def chat_completion(self, messages, **kwargs):
        """Return fake response."""
        self.last_messages = messages
        return {"content": self.response_content}

    def chat_completion_stream(self, messages, **kwargs):
        """Return fake stream response."""
        self.last_messages = messages
        yield {"content": self.response_content}

    def validate_config(self) -> bool:
        """Validate fake config."""
        return True

    def get_model(self) -> str:
        """Return fake model name."""
        return "fake-model"

    def supports_streaming(self) -> bool:
        """Return False."""
        return False

    def supports_tools(self) -> bool:
        """Return False."""
        return False


class TestPlanGenerator:
    """Test PlanGenerator for generating plan.md from spec.md."""

    def test_plan_generator_init(self) -> None:
        """Test PlanGenerator initialization."""
        spec_content = "# 需求规范\n\n## 用户故事"
        generator = PlanGenerator(spec_content=spec_content)

        assert generator.spec_content == spec_content
        assert generator.llm_client is None

    def test_plan_generator_with_llm_client(self) -> None:
        """Test PlanGenerator with LLM client."""
        spec_content = "# 需求规范"
        llm_client = FakeLLMClient()

        generator = PlanGenerator(
            spec_content=spec_content,
            llm_client=llm_client
        )

        assert generator.llm_client is not None
        assert generator.llm_client == llm_client

    def test_generate_prompt_structure(self) -> None:
        """Test that generated prompt has correct structure."""
        spec_content = """
# 项目需求规范

## 1. 项目概述

开发一个基于 Python 的 AI 工作流引擎。

## 2. 用户故事

**US-001：上下文注入**

- **场景**：让 AI 理解代码
- **验收标准**：
  - 支持 @file

## 3. 功能需求

### 核心交互模型

- 上下文注入：@file
- 命令执行：!command
"""

        generator = PlanGenerator(spec_content=spec_content)
        prompt = generator._generate_prompt()

        # Check prompt contains key sections
        assert "spec.md" in prompt or "需求规范" in prompt
        assert "技术方案" in prompt or "plan.md" in prompt
        assert "合宪性检查清单" in prompt or "compliance" in prompt.lower()
        assert "项目结构" in prompt or "structure" in prompt.lower()
        assert "数据结构" in prompt or "data structure" in prompt.lower()
        assert "接口设计" in prompt or "interface" in prompt.lower()

    def test_generate_without_llm_client_raises_error(self) -> None:
        """Test that generate raises ValueError without LLM client."""
        spec_content = "# 需求规范"
        generator = PlanGenerator(spec_content=spec_content)

        with pytest.raises(ValueError, match="LLM client is required"):
            generator.generate()

    def test_generate_calls_llm(self) -> None:
        """Test that generate calls LLM client."""
        spec_content = "# 需求规范\n\n## 用户故事\n\n**US-001**"
        fake_response = """
# 技术方案

## 技术上下文总结

### 技术栈选型

- **语言**: Python 3.8.10

## 合宪性检查清单

### 简单性门禁

- ✅ 标准库优先
"""
        llm_client = FakeLLMClient(response_content=fake_response)
        generator = PlanGenerator(
            spec_content=spec_content,
            llm_client=llm_client
        )

        result = generator.generate()

        # Verify LLM was called
        assert llm_client.last_messages is not None
        assert len(llm_client.last_messages) >= 2

        # Verify result
        assert result is not None
        assert "技术方案" in result or "plan.md" in result

    def test_generate_returns_plan_content(self) -> None:
        """Test that generate returns valid plan content."""
        spec_content = "# 需求规范"
        plan_response = """
# 技术方案（Plan）

**版本**: 1.0
**日期**: 2024-12-19

## 1. 技术上下文总结

### 1.1 技术栈选型

- **语言**: Python 3.8.10
- **CLI 框架**: click 7.1.2

## 2. 合宪性检查清单

### 2.1 简单性门禁 ✅

- ✅ 标准库优先

## 3. 项目结构细化

### 3.1 目录结构

```
deep_code/
├── core/
└── cli/
```

## 4. 核心数据结构

### 4.1 消息格式

```python
Message = Dict[str, str]
```

## 5. 关键接口设计
"""

        llm_client = FakeLLMClient(response_content=plan_response)
        generator = PlanGenerator(
            spec_content=spec_content,
            llm_client=llm_client
        )

        result = generator.generate()

        # Verify result has expected sections
        assert "技术上下文" in result or "技术栈" in result
        assert "合宪性" in result or "检查清单" in result
        assert "项目结构" in result or "目录结构" in result
        assert "数据结构" in result or "接口设计" in result

    def test_validate_generated_plan(self) -> None:
        """Test validation of generated plan."""
        spec_content = "# 需求规范"
        valid_plan = """
# 技术方案

## 技术上下文总结

### 技术栈选型

### 运行环境

## 合宪性检查清单

### 简单性门禁

### TDD门禁

### 明确性门禁

### 兼容性门禁

## 项目结构细化

### 目录结构

### 包职责划分

## 核心数据结构

## 关键接口设计

## 技术选型说明

## 架构设计原则

## 关键技术决策

## 非功能设计

## 安全设计

## 测试策略

## 部署与分发

## 风险评估与缓解

## 后续扩展预留
"""

        generator = PlanGenerator(spec_content=spec_content)
        validation = generator.validate_generated_plan(valid_plan)

        assert validation["valid"] is True
        assert len(validation["missing_sections"]) == 0

    def test_validate_incomplete_plan(self) -> None:
        """Test validation detects missing sections."""
        spec_content = "# 需求规范"
        incomplete_plan = """
# 技术方案

## 技术栈

- Python 3.8.10
"""

        generator = PlanGenerator(spec_content=spec_content)
        validation = generator.validate_generated_plan(incomplete_plan)

        assert validation["valid"] is False
        assert len(validation["missing_sections"]) > 0
        # Should be missing many required sections

    def test_integration_spec_to_plan_workflow(self) -> None:
        """Test complete spec.md -> plan.md workflow."""
        spec_content = """
# 项目需求规范

## 1. 项目概述

开发一个基于 Python 3.8.10 的 AI 工作流引擎。

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

## 3. 功能需求

### 3.1 核心交互模型

#### 上下文注入（@）

- **文件引用**：@/path/to/file.py

#### 命令执行（!）

- **命令格式**：! <command>

## 4. 验收标准

1. 支持 @file
2. 支持 !command
"""

        plan_response = """
# 技术方案

## 技术上下文总结

### 技术栈选型

- Python 3.8.10
- click 7.1.2

## 合宪性检查清单

### 简单性门禁

- ✅ 标准库优先

### TDD门禁

- ✅ 先写测试

## 项目结构细化

### 目录结构

```
deep_code/
├── core/
└── interaction/
```

## 核心数据结构

### 上下文引用

```python
class ContextRef:
    path: Path
    ref_type: str
```

## 关键接口设计

### LLMClient 接口

- chat_completion()
- get_model()
"""

        llm_client = FakeLLMClient(response_content=plan_response)
        generator = PlanGenerator(
            spec_content=spec_content,
            llm_client=llm_client
        )

        # Generate plan
        plan = generator.generate()

        # Validate plan
        validation = generator.validate_generated_plan(plan)

        # Verify workflow completed
        assert plan is not None
        assert "技术方案" in plan
        # The fake response is minimal, so it will have missing sections
        # In real usage, LLM would generate a complete plan
        assert len(validation["missing_sections"]) >= 5  # Minimal example has at least 5 missing


class TestPlanGeneratorValidation:
    """Test PlanGenerator validation methods."""

    def test_has_required_sections_all_present(self) -> None:
        """Test has_required_sections with all sections present."""
        plan_content = """
# 技术方案

## 技术上下文总结
## 合宪性检查清单
## 项目结构细化
## 核心数据结构
## 关键接口设计
## 技术选型说明
## 架构设计原则
## 关键技术决策
## 非功能设计
## 安全设计
## 测试策略
## 部署与分发
## 风险评估与缓解
## 后续扩展预留
"""

        generator = PlanGenerator(spec_content="# Spec")
        assert generator.has_required_sections(plan_content) is True

    def test_has_required_sections_missing_some(self) -> None:
        """Test has_required_sections with missing sections."""
        plan_content = """
# 技术方案

## 技术栈

- Python 3.8.10
"""

        generator = PlanGenerator(spec_content="# Spec")
        assert generator.has_required_sections(plan_content) is False

    def test_extract_missing_sections(self) -> None:
        """Test extraction of missing sections."""
        plan_content = """
# 技术方案

## 技术栈

- Python 3.8.10

## 合宪性检查清单
"""

        generator = PlanGenerator(spec_content="# Spec")
        missing = generator.extract_missing_sections(plan_content)

        # Should have many missing sections
        assert len(missing) > 5
        assert "项目结构细化" in missing
        assert "核心数据结构" in missing
