"""
SDD Generator - Generate plan.md and tasks.md using LLM.

Python 3.8.10 compatible
T111: 从spec.md生成plan.md的工作流
T112: 从plan.md生成tasks.md的工作流

Features:
- Uses LLM to transform spec to plan
- Uses LLM to decompose plan into atomic tasks
- Ensures tasks have proper dependencies
- Marks parallel tasks with [P]
- Follows TDD principles
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from deep_code.llm.client import LLMClient
from deep_code.sdd.models import Task
from deep_code.sdd.parser import parse_tasks_markdown


class PlanGenerator:
    """
    Generate plan.md from spec.md using LLM.

    This class implements T111: 从spec.md生成plan.md的工作流
    """

    def __init__(
        self,
        spec_content: str,
        llm_client: Optional[LLMClient] = None,
    ):
        """
        Initialize plan generator.

        Args:
            spec_content: Content of spec.md
            llm_client: LLM client for generation (optional, for testing)
        """
        self.spec_content = spec_content
        self.llm_client = llm_client

    def _generate_prompt(self) -> str:
        """
        Generate prompt for LLM to create plan.md.

        Returns:
            Prompt string for LLM
        """
        return f"""You are a senior software architect specializing in Spec-Driven Development (SDD).

Your task is to generate a plan.md file based on the provided spec.md.

# Input: spec.md

{self.spec_content}

# Output Requirements

Generate a plan.md file with the following structure:

# 技术方案

## 1. 技术上下文总结

### 1.1 技术栈选型

### 1.2 运行环境

### 1.3 关键依赖

## 2. 合宪性检查清单

### 2.1 简单性门禁 ✅

### 2.2 TDD 门禁 ✅

### 2.3 明确性门禁 ✅

### 2.4 兼容性门禁 ✅

### 2.5 安全门禁 ✅

## 3. 项目结构细化

### 3.1 目录结构

### 3.2 包职责划分

## 4. 核心数据结构

## 5. 关键接口设计

## 6. 技术选型说明

## 7. 架构设计原则

## 8. 关键技术决策

## 9. 非功能设计

### 9.1 错误处理策略

### 9.2 日志策略

### 9.3 性能考虑

## 10. 安全设计

### 10.1 权限模型

### 10.2 审批流程

### 10.3 检查点机制

## 11. 测试策略

### 11.1 单元测试

### 11.2 集成测试

### 11.3 兼容性测试

## 12. 部署与分发

### 12.1 安装方式

### 12.2 配置方式

## 13. 风险评估与缓解

### 13.1 技术风险

### 13.2 兼容性风险

### 13.3 安全风险

## 14. 后续扩展预留

### 14.1 架构预留

### 14.2 功能预留

# Guidelines

1. The plan MUST comply with the constitution (合宪性)
2. Use Python 3.8.10 compatible syntax and types
3. Follow YAGNI principles (only implement what spec requires)
4. Design for testability (TDD is mandatory)
5. All dependencies must be explicit
6. Standard library preferred over third-party
7. Windows 7 compatibility must be considered
8. All designs must support offline/internal network deployment

Please generate the complete plan.md file now:"""

    def generate(self) -> str:
        """
        Generate plan from spec.md using LLM.

        Returns:
            Generated plan.md content

        Raises:
            ValueError: If LLM client is not configured
        """
        if not self.llm_client:
            raise ValueError("LLM client is required for generation")

        # Generate prompt
        prompt = self._generate_prompt()

        # Call LLM
        messages = [
            {"role": "system", "content": "You are a senior software architect."},
            {"role": "user", "content": prompt},
        ]

        response = self.llm_client.chat_completion(
            messages=messages,
            temperature=0.7,
        )

        # Extract content
        content = response.get("content", "")

        return content

    def validate_generated_plan(self, plan_content: str) -> Dict[str, Any]:
        """
        Validate generated plan for completeness.

        Args:
            plan_content: Generated plan.md content

        Returns:
            Dict with validation results
        """
        has_sections = self.has_required_sections(plan_content)
        missing = self.extract_missing_sections(plan_content) if not has_sections else []

        return {
            "valid": has_sections,
            "missing_sections": missing,
        }

    def has_required_sections(self, plan_content: str) -> bool:
        """
        Check if plan has all required sections.

        Args:
            plan_content: Plan.md content to check

        Returns:
            True if all required sections are present
        """
        required_sections = [
            "技术上下文总结",
            "合宪性检查清单",
            "项目结构细化",
            "核心数据结构",
            "关键接口设计",
            "技术选型说明",
            "架构设计原则",
            "关键技术决策",
            "非功能设计",
            "安全设计",
            "测试策略",
            "部署与分发",
            "风险评估与缓解",
            "后续扩展预留",
        ]

        for section in required_sections:
            if section not in plan_content:
                return False

        return True

    def extract_missing_sections(self, plan_content: str) -> List[str]:
        """
        Extract list of missing required sections.

        Args:
            plan_content: Plan.md content to check

        Returns:
            List of missing section names
        """
        required_sections = [
            "技术上下文总结",
            "合宪性检查清单",
            "项目结构细化",
            "核心数据结构",
            "关键接口设计",
            "技术选型说明",
            "架构设计原则",
            "关键技术决策",
            "非功能设计",
            "安全设计",
            "测试策略",
            "部署与分发",
            "风险评估与缓解",
            "后续扩展预留",
        ]

        missing = []
        for section in required_sections:
            if section not in plan_content:
                missing.append(section)

        return missing


class TaskGenerator:
    """
    Generate tasks.md from plan.md using LLM.

    This class implements T112: 从plan.md生成tasks.md的工作流
    """

    def __init__(
        self,
        plan_content: str,
        llm_client: Optional[LLMClient] = None,
    ):
        """
        Initialize task generator.

        Args:
            plan_content: Content of plan.md
            llm_client: LLM client for generation (optional, for testing)
        """
        self.plan_content = plan_content
        self.llm_client = llm_client

    def _generate_prompt(self) -> str:
        """
        Generate prompt for LLM to create tasks.md.

        Returns:
            Prompt string for LLM
        """
        return f"""You are a senior software architect specializing in Spec-Driven Development (SDD).

Your task is to generate a tasks.md file based on the provided plan.md.

# Input: plan.md

{self.plan_content}

# Output Requirements

Generate a tasks.md file with the following structure:

## 任务清单（带依赖/并行标记）

### Phase X: [Phase Name]

- [ ] **TXXX Task description** [P] (if parallel)
  - **依赖**: Task IDs or "无"
  - **产物**: Target files
  - **改动点**: Changed files
  - **验证**: Validation commands
  - **DoD**: Definition of Done

# Guidelines

1. Task IDs should be sequential (T001, T002, etc.)
2. Each task must be atomic (one file/function/feature)
3. Mark parallel tasks with [P]
4. All dependencies must be explicit
5. Follow TDD principles
6. Tasks should be verifiable
7. Group related tasks into phases

Please generate the complete tasks.md file now:"""

    def generate(self) -> List[Task]:
        """
        Generate tasks from plan.md using LLM.

        Returns:
            List of generated Task objects

        Raises:
            ValueError: If LLM client is not configured
            TaskParseError: If LLM output cannot be parsed
        """
        if not self.llm_client:
            raise ValueError("LLM client is required for generation")

        # Generate prompt
        prompt = self._generate_prompt()

        # Call LLM
        messages = [
            {"role": "system", "content": "You are a senior software architect."},
            {"role": "user", "content": prompt},
        ]

        response = self.llm_client.chat_completion(
            messages=messages,
            temperature=0.7,
        )

        # Extract content
        content = response.get("content", "")

        # Parse tasks from LLM output
        tasks = self._parse_llm_output(content)

        return tasks

    @staticmethod
    def _parse_llm_output(output: str) -> List[Task]:
        """
        Parse tasks from LLM-generated markdown.

        Args:
            output: LLM output containing tasks.md content

        Returns:
            List of parsed Task objects
        """
        # Extract the tasks section
        # Look for task markers: - [ ] **TXXX
        return parse_tasks_markdown(output)

    def validate_generated_tasks(self, tasks: List[Task]) -> Dict[str, Any]:
        """
        Validate generated tasks for quality.

        Checks:
        - All tasks have IDs
        - All tasks have descriptions
        - Dependencies reference valid tasks
        - No circular dependencies

        Args:
            tasks: List of generated tasks

        Returns:
            Dict with validation results
        """
        from deep_code.sdd.analyzer import DependencyAnalyzer

        issues: List[str] = []
        warnings: List[str] = []

        # Check basic structure
        for task in tasks:
            if not task.id:
                issues.append(f"Task missing ID: {task.description}")

            if not task.description:
                issues.append(f"Task {task.id} missing description")

        # Check dependencies
        analyzer = DependencyAnalyzer(tasks)
        missing_deps = analyzer.validate_dependencies()

        if missing_deps:
            issues.append(f"Missing dependencies: {', '.join(missing_deps)}")

        # Check for circular dependencies
        try:
            analyzer.topological_sort()
        except Exception as e:
            issues.append(f"Dependency error: {str(e)}")

        # Check TDD compliance
        non_tdd = [t.id for t in tasks if not t.tdd]
        if non_tdd:
            warnings.append(f"Non-TDD tasks: {', '.join(non_tdd)}")

        # Check parallel task distribution
        parallel_count = sum(1 for t in tasks if t.parallel)
        if parallel_count == 0:
            warnings.append("No parallel tasks identified")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "total_tasks": len(tasks),
            "parallel_tasks": parallel_count,
        }
