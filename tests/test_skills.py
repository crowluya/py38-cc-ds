"""
Tests for Skills Extension

Python 3.8.10 compatible
Tests for SKILL-001 through SKILL-011 implementations.
"""

import pytest
import os
from pathlib import Path
from typing import Dict, List
from unittest.mock import Mock, patch


class TestSkillLoader:
    """Tests for skill directory scanning (SKILL-001)."""

    def test_get_user_skill_path(self):
        """Test getting user skill path."""
        from deep_code.extensions.skills.loader import get_user_skill_path

        path = get_user_skill_path()

        assert path.name == "skills"
        assert path.parent.name == ".deepcode"

    def test_get_project_skill_path(self):
        """Test getting project skill path."""
        from deep_code.extensions.skills.loader import get_project_skill_path

        project_root = Path("/tmp/test_project")
        path = get_project_skill_path(project_root)

        assert path == project_root / ".deepcode" / "skills"

    def test_get_default_skill_paths(self):
        """Test getting default skill paths."""
        from deep_code.extensions.skills.loader import get_default_skill_paths

        paths = get_default_skill_paths()

        assert "user" in paths
        assert "project" in paths

    def test_skill_location(self):
        """Test SkillLocation dataclass."""
        from deep_code.extensions.skills.loader import SkillLocation

        location = SkillLocation(
            path=Path("/tmp/skills/pdf"),
            scope="project",
            name="pdf",
        )

        assert location.name == "pdf"
        assert location.scope == "project"
        assert location.skill_file == Path("/tmp/skills/pdf/SKILL.md")

    def test_find_skill_directories(self, tmp_path):
        """Test finding skill directories."""
        from deep_code.extensions.skills.loader import find_skill_directories

        # Create test skill directory
        skill_dir = tmp_path / "pdf"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: pdf\n---\n", encoding="utf-8")

        skills = find_skill_directories(tmp_path, scope="project")

        assert len(skills) == 1
        assert skills[0].name == "pdf"
        assert skills[0].scope == "project"

    def test_find_nested_skill_directories(self, tmp_path):
        """Test finding nested skill directories."""
        from deep_code.extensions.skills.loader import find_skill_directories

        # Create nested skill directory
        nested_dir = tmp_path / "category" / "nested-skill"
        nested_dir.mkdir(parents=True)
        (nested_dir / "SKILL.md").write_text("---\nname: nested\n---\n", encoding="utf-8")

        skills = find_skill_directories(tmp_path, scope="project")

        assert len(skills) == 1
        assert "nested-skill" in skills[0].name

    def test_skill_loader_scan(self, tmp_path):
        """Test SkillLoader scanning."""
        from deep_code.extensions.skills.loader import SkillLoader

        # Create skill directory structure
        skills_dir = tmp_path / ".deepcode" / "skills"
        skills_dir.mkdir(parents=True)

        skill1 = skills_dir / "skill1"
        skill1.mkdir()
        (skill1 / "SKILL.md").write_text("---\nname: skill1\n---\n", encoding="utf-8")

        loader = SkillLoader(project_root=tmp_path, include_user_skills=False)
        count = loader.scan()

        assert count == 1
        assert "skill1" in loader


class TestSkillParser:
    """Tests for SKILL.md parsing (SKILL-002)."""

    def test_parse_yaml_frontmatter(self):
        """Test parsing YAML frontmatter."""
        from deep_code.extensions.skills.parser import parse_yaml_frontmatter

        content = """name: pdf
description: Extract text from PDFs
allowed-tools: Read, Grep, Bash
model: opus
color: orange"""

        result = parse_yaml_frontmatter(content)

        assert result["name"] == "pdf"
        assert result["description"] == "Extract text from PDFs"
        assert result["model"] == "opus"
        assert result["color"] == "orange"

    def test_parse_yaml_list(self):
        """Test parsing YAML list."""
        from deep_code.extensions.skills.parser import parse_yaml_frontmatter

        content = """name: test
allowed-tools:
  - Read
  - Grep
  - Bash"""

        result = parse_yaml_frontmatter(content)

        assert result["name"] == "test"
        assert result["allowed-tools"] == ["Read", "Grep", "Bash"]

    def test_parse_skill_file(self):
        """Test parsing complete SKILL.md file."""
        from deep_code.extensions.skills.parser import parse_skill_file

        content = """---
name: pdf
description: PDF processing skill
---

# PDF Processing

Use this skill to extract text from PDFs.
"""

        frontmatter, body = parse_skill_file(content)

        assert frontmatter["name"] == "pdf"
        assert "PDF Processing" in body

    def test_parse_skill_definition(self):
        """Test parsing into SkillDefinition."""
        from deep_code.extensions.skills.parser import parse_skill_definition

        content = """---
name: pdf
description: Extract and analyze text from PDF documents
allowed-tools: Read, Grep, Glob, Bash
model: opus
color: orange
---

# PDF Processing Skill

Use the extract_text.py script to extract text from PDFs.
"""

        skill = parse_skill_definition(content)

        assert skill.name == "pdf"
        assert "Extract and analyze" in skill.description
        assert skill.allowed_tools == ["Read", "Grep", "Glob", "Bash"]
        assert skill.model == "opus"
        assert skill.color == "orange"
        assert "extract_text.py" in skill.body

    def test_skill_definition_tool_check(self):
        """Test SkillDefinition tool checking."""
        from deep_code.extensions.skills.parser import SkillDefinition

        skill = SkillDefinition(
            name="test",
            allowed_tools=["Read", "Grep"],
        )

        assert skill.is_tool_allowed("Read") is True
        assert skill.is_tool_allowed("Write") is False
        assert skill.has_tool_restrictions is True

    def test_skill_definition_no_restrictions(self):
        """Test SkillDefinition without tool restrictions."""
        from deep_code.extensions.skills.parser import SkillDefinition

        skill = SkillDefinition(name="test")

        assert skill.is_tool_allowed("AnyTool") is True
        assert skill.has_tool_restrictions is False


class TestSkillRegistry:
    """Tests for skill registry (SKILL-003)."""

    def test_registry_initialization(self):
        """Test registry initialization."""
        from deep_code.extensions.skills.registry import SkillRegistry

        registry = SkillRegistry()

        assert registry.is_loaded is False
        assert len(registry) == 0

    def test_registry_load(self, tmp_path):
        """Test loading skills into registry."""
        from deep_code.extensions.skills.registry import SkillRegistry

        # Create skill
        skills_dir = tmp_path / ".deepcode" / "skills" / "test"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text(
            "---\nname: test\ndescription: Test skill\n---\nInstructions",
            encoding="utf-8"
        )

        registry = SkillRegistry(project_root=tmp_path, include_user_skills=False)
        count = registry.load()

        assert count == 1
        assert "test" in registry

    def test_registry_search(self, tmp_path):
        """Test searching skills."""
        from deep_code.extensions.skills.registry import SkillRegistry

        # Create skills
        skills_dir = tmp_path / ".deepcode" / "skills"
        skills_dir.mkdir(parents=True)

        pdf_skill = skills_dir / "pdf"
        pdf_skill.mkdir()
        (pdf_skill / "SKILL.md").write_text(
            "---\nname: pdf\ndescription: Extract text from PDF documents\n---\n",
            encoding="utf-8"
        )

        registry = SkillRegistry(project_root=tmp_path, include_user_skills=False)
        registry.load()

        results = registry.search("extract PDF text")

        assert len(results) > 0
        assert results[0].name == "pdf"

    def test_registry_format_available_skills(self, tmp_path):
        """Test formatting available skills as XML."""
        from deep_code.extensions.skills.registry import SkillRegistry

        # Create skill
        skills_dir = tmp_path / ".deepcode" / "skills" / "test"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text(
            "---\nname: test\ndescription: Test skill\n---\n",
            encoding="utf-8"
        )

        registry = SkillRegistry(project_root=tmp_path, include_user_skills=False)
        registry.load()

        xml = registry.format_available_skills()

        assert "<available_skills>" in xml
        assert "<name>test</name>" in xml


class TestSkillMatcher:
    """Tests for task matching (SKILL-004)."""

    def test_extract_task_keywords(self):
        """Test extracting keywords from task."""
        from deep_code.extensions.skills.matcher import extract_task_keywords

        keywords = extract_task_keywords("Please help me extract text from a PDF file")

        assert "extract" in keywords
        assert "text" in keywords
        assert "pdf" in keywords
        assert "file" in keywords
        # Stop words should be removed
        assert "please" not in keywords
        assert "from" not in keywords

    def test_matcher_find_best_match(self, tmp_path):
        """Test finding best matching skill."""
        from deep_code.extensions.skills.registry import SkillRegistry
        from deep_code.extensions.skills.matcher import SkillMatcher

        # Create skill
        skills_dir = tmp_path / ".deepcode" / "skills" / "pdf"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text(
            "---\nname: pdf\ndescription: Extract and analyze text from PDF documents\n---\n",
            encoding="utf-8"
        )

        registry = SkillRegistry(project_root=tmp_path, include_user_skills=False)
        registry.load()

        matcher = SkillMatcher(registry)
        result = matcher.find_best_match("I need to extract text from a PDF")

        assert result is not None
        assert result.skill.name == "pdf"
        assert result.score > 0

    def test_matcher_slash_command(self, tmp_path):
        """Test matching slash command."""
        from deep_code.extensions.skills.registry import SkillRegistry
        from deep_code.extensions.skills.matcher import SkillMatcher

        # Create skill
        skills_dir = tmp_path / ".deepcode" / "skills" / "commit"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text(
            "---\nname: commit\ndescription: Create git commits\n---\n",
            encoding="utf-8"
        )

        registry = SkillRegistry(project_root=tmp_path, include_user_skills=False)
        registry.load()

        matcher = SkillMatcher(registry)
        result = matcher.find_best_match("run /commit")

        assert result is not None
        assert result.skill.name == "commit"
        assert result.score > 0.5  # Should be a strong match

    def test_matcher_find_by_slash_command(self, tmp_path):
        """Test finding skill by slash command."""
        from deep_code.extensions.skills.registry import SkillRegistry
        from deep_code.extensions.skills.matcher import SkillMatcher

        # Create skill
        skills_dir = tmp_path / ".deepcode" / "skills" / "pdf"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text(
            "---\nname: pdf\ndescription: PDF processing\n---\n",
            encoding="utf-8"
        )

        registry = SkillRegistry(project_root=tmp_path, include_user_skills=False)
        registry.load()

        matcher = SkillMatcher(registry)

        # With slash
        skill = matcher.find_by_slash_command("/pdf")
        assert skill is not None
        assert skill.name == "pdf"

        # Without slash
        skill = matcher.find_by_slash_command("pdf")
        assert skill is not None
        assert skill.name == "pdf"


class TestSkillExecutor:
    """Tests for skill execution (SKILL-006, SKILL-007, SKILL-008)."""

    def test_executor_prepare_context(self, tmp_path):
        """Test preparing skill context."""
        from deep_code.extensions.skills.parser import SkillDefinition
        from deep_code.extensions.skills.loader import SkillLocation
        from deep_code.extensions.skills.executor import SkillExecutor

        # Create skill directory with auxiliary file
        skill_dir = tmp_path / "pdf"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: pdf\n---\nInstructions", encoding="utf-8")
        (skill_dir / "extract.py").write_text("# Python script", encoding="utf-8")

        skill = SkillDefinition(name="pdf", body="Instructions")
        location = SkillLocation(path=skill_dir, scope="project", name="pdf")

        executor = SkillExecutor()
        context = executor.prepare_context(skill, location)

        assert context.skill.name == "pdf"
        assert context.base_path == skill_dir
        assert len(context.auxiliary_files) == 1

    def test_executor_activate_deactivate(self):
        """Test activating and deactivating skills."""
        from deep_code.extensions.skills.parser import SkillDefinition
        from deep_code.extensions.skills.loader import SkillLocation
        from deep_code.extensions.skills.executor import SkillExecutor, SkillContext
        from pathlib import Path

        skill = SkillDefinition(name="test", body="Instructions")
        location = SkillLocation(path=Path("/tmp/test"), scope="project", name="test")
        context = SkillContext(skill=skill, location=location, base_path=Path("/tmp/test"))

        executor = SkillExecutor()

        # Activate
        result = executor.activate(context)
        assert executor.is_active is True
        assert "<skill" in result

        # Deactivate
        executor.deactivate()
        assert executor.is_active is False

    def test_executor_tool_restrictions(self):
        """Test tool restriction enforcement (SKILL-007)."""
        from deep_code.extensions.skills.parser import SkillDefinition
        from deep_code.extensions.skills.loader import SkillLocation
        from deep_code.extensions.skills.executor import SkillExecutor, SkillContext
        from pathlib import Path

        skill = SkillDefinition(
            name="test",
            allowed_tools=["Read", "Grep"],
        )
        location = SkillLocation(path=Path("/tmp/test"), scope="project", name="test")
        context = SkillContext(skill=skill, location=location, base_path=Path("/tmp/test"))

        executor = SkillExecutor()
        executor.activate(context)

        assert executor.is_tool_allowed("Read") is True
        assert executor.is_tool_allowed("Grep") is True
        assert executor.is_tool_allowed("Write") is False
        assert executor.is_tool_allowed("Bash") is False

    def test_executor_model_override(self):
        """Test model selection support (SKILL-008)."""
        from deep_code.extensions.skills.parser import SkillDefinition
        from deep_code.extensions.skills.loader import SkillLocation
        from deep_code.extensions.skills.executor import SkillExecutor, SkillContext
        from pathlib import Path

        skill = SkillDefinition(name="test", model="opus")
        location = SkillLocation(path=Path("/tmp/test"), scope="project", name="test")
        context = SkillContext(skill=skill, location=location, base_path=Path("/tmp/test"))

        executor = SkillExecutor()
        executor.activate(context)

        assert executor.get_model_override() == "opus"

    def test_context_format_for_injection(self):
        """Test formatting context for LLM injection."""
        from deep_code.extensions.skills.parser import SkillDefinition
        from deep_code.extensions.skills.loader import SkillLocation
        from deep_code.extensions.skills.executor import SkillContext
        from pathlib import Path

        skill = SkillDefinition(
            name="pdf",
            allowed_tools=["Read", "Bash"],
            body="Use extract_text.py to process PDFs.",
        )
        location = SkillLocation(path=Path("/tmp/pdf"), scope="project", name="pdf")
        context = SkillContext(
            skill=skill,
            location=location,
            base_path=Path("/tmp/pdf"),
        )

        formatted = context.format_for_injection()

        assert '<skill name="pdf">' in formatted
        assert "<instructions>" in formatted
        assert "extract_text.py" in formatted
        assert "<allowed_tools>" in formatted
        assert "Read" in formatted


class TestSkillTool:
    """Tests for Skill tool (SKILL-005)."""

    def test_skill_tool_properties(self, tmp_path):
        """Test SkillTool properties."""
        from deep_code.extensions.skills.registry import SkillRegistry
        from deep_code.core.tools.skill import SkillTool
        from deep_code.core.tools.base import ToolCategory

        registry = SkillRegistry(project_root=tmp_path, include_user_skills=False)
        tool = SkillTool(registry)

        assert tool.name == "Skill"
        assert tool.category == ToolCategory.AGENT
        assert tool.requires_permission is False

    def test_skill_tool_execute(self, tmp_path):
        """Test executing skill tool."""
        from deep_code.extensions.skills.registry import SkillRegistry
        from deep_code.core.tools.skill import SkillTool

        # Create skill
        skills_dir = tmp_path / ".deepcode" / "skills" / "pdf"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text(
            "---\nname: pdf\ndescription: PDF processing\n---\nUse this for PDFs.",
            encoding="utf-8"
        )

        registry = SkillRegistry(project_root=tmp_path, include_user_skills=False)
        registry.load()

        tool = SkillTool(registry)
        result = tool.execute({"skill": "pdf"})

        assert result.success is True
        assert "pdf" in result.output.lower()
        assert "activated" in result.output.lower()

    def test_skill_tool_execute_not_found(self, tmp_path):
        """Test executing skill tool with non-existent skill."""
        from deep_code.extensions.skills.registry import SkillRegistry
        from deep_code.core.tools.skill import SkillTool

        registry = SkillRegistry(project_root=tmp_path, include_user_skills=False)
        registry.load()

        tool = SkillTool(registry)
        result = tool.execute({"skill": "nonexistent"})

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_skill_tool_with_slash(self, tmp_path):
        """Test skill tool handles slash prefix."""
        from deep_code.extensions.skills.registry import SkillRegistry
        from deep_code.core.tools.skill import SkillTool

        # Create skill
        skills_dir = tmp_path / ".deepcode" / "skills" / "commit"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text(
            "---\nname: commit\ndescription: Git commits\n---\n",
            encoding="utf-8"
        )

        registry = SkillRegistry(project_root=tmp_path, include_user_skills=False)
        registry.load()

        tool = SkillTool(registry)
        result = tool.execute({"skill": "/commit"})

        assert result.success is True

    def test_skill_tool_json_schema(self, tmp_path):
        """Test skill tool JSON schema."""
        from deep_code.extensions.skills.registry import SkillRegistry
        from deep_code.core.tools.skill import SkillTool

        registry = SkillRegistry(project_root=tmp_path, include_user_skills=False)
        tool = SkillTool(registry)

        schema = tool.get_json_schema()

        assert schema["type"] == "function"
        assert schema["function"]["name"] == "Skill"
        assert "skill" in schema["function"]["parameters"]["properties"]


class TestSkillIntegration:
    """Integration tests for skills."""

    def test_full_workflow(self, tmp_path):
        """Test complete skill workflow."""
        from deep_code.extensions.skills import (
            SkillRegistry,
            SkillMatcher,
            SkillExecutor,
        )

        # Create skill
        skills_dir = tmp_path / ".deepcode" / "skills" / "pdf"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text("""---
name: pdf
description: Extract and analyze text from PDF documents
allowed-tools: Read, Grep, Glob, Bash
model: opus
---

# PDF Processing Skill

Use the extract_text.py script to extract text from PDFs.
""", encoding="utf-8")
        (skills_dir / "extract_text.py").write_text("# Script", encoding="utf-8")

        # Load registry
        registry = SkillRegistry(project_root=tmp_path, include_user_skills=False)
        registry.load()

        # Match task
        matcher = SkillMatcher(registry)
        match = matcher.find_best_match("I need to extract text from a PDF file")

        assert match is not None
        assert match.skill.name == "pdf"

        # Execute skill
        entry = registry.get_entry("pdf")
        executor = SkillExecutor()
        context = executor.prepare_context(entry.definition, entry.location)
        executor.activate(context)

        # Verify context
        assert executor.is_active
        assert executor.is_tool_allowed("Read")
        assert not executor.is_tool_allowed("Write")
        assert executor.get_model_override() == "opus"

        # Deactivate
        executor.deactivate()
        assert not executor.is_active

    def test_multiple_skills(self, tmp_path):
        """Test with multiple skills."""
        from deep_code.extensions.skills import SkillRegistry, SkillMatcher

        skills_dir = tmp_path / ".deepcode" / "skills"
        skills_dir.mkdir(parents=True)

        # Create multiple skills
        for name, desc in [
            ("pdf", "Extract text from PDF documents"),
            ("commit", "Create git commits with proper messages"),
            ("review", "Review code changes and provide feedback"),
        ]:
            skill_dir = skills_dir / name
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                f"---\nname: {name}\ndescription: {desc}\n---\n",
                encoding="utf-8"
            )

        registry = SkillRegistry(project_root=tmp_path, include_user_skills=False)
        registry.load()

        assert len(registry) == 3

        matcher = SkillMatcher(registry)

        # Test different queries
        pdf_match = matcher.find_best_match("extract text from PDF")
        assert pdf_match.skill.name == "pdf"

        commit_match = matcher.find_best_match("create a git commit")
        assert commit_match.skill.name == "commit"

        review_match = matcher.find_best_match("review my code changes")
        assert review_match.skill.name == "review"
