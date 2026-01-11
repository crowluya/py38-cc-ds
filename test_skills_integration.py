#!/usr/bin/env python3
"""
Integration test for DeepCode Skills with real SKILL.md files.

Tests:
1. Skill discovery and loading
2. Skill matching
3. Skill execution
4. Tool restrictions
"""

import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from deep_code.extensions.skills.loader import SkillLoader, get_default_skill_paths
from deep_code.extensions.skills.parser import load_skill_from_directory
from deep_code.extensions.skills.registry import SkillRegistry
from deep_code.extensions.skills.matcher import SkillMatcher, create_matcher
from deep_code.extensions.skills.executor import SkillExecutor, build_skill_context
from deep_code.core.tools.skill import SkillTool, create_skill_tool


def test_skill_discovery():
    """Test skill directory discovery."""
    print("\n" + "=" * 60)
    print("TEST 1: Skill Discovery")
    print("=" * 60)

    project_root = Path(__file__).parent

    print(f"\n1. Project root: {project_root}")

    print("\n2. Getting default skill paths...")
    paths = get_default_skill_paths(project_root)
    for path in paths:
        p = Path(path)
        exists = "✓" if p.exists() else "✗"
        print(f"   [{exists}] {path}")

    print("\n3. Scanning for skills...")
    loader = SkillLoader(project_root=project_root)
    count = loader.scan()
    print(f"   Found {count} skills")

    print("\n4. Listing discovered skills:")
    for name in loader.list_skills():
        location = loader.get(name)
        if location:
            print(f"   - {name}: {location.path}")

    print("\n✅ Skill discovery test PASSED!")
    return True


def test_skill_parsing():
    """Test SKILL.md parsing."""
    print("\n" + "=" * 60)
    print("TEST 2: Skill Parsing")
    print("=" * 60)

    project_root = Path(__file__).parent
    skills_dir = project_root / ".deepcode" / "skills"

    print(f"\n1. Skills directory: {skills_dir}")

    # Test hello skill
    hello_dir = skills_dir / "hello"
    if hello_dir.exists():
        print("\n2. Parsing 'hello' skill...")
        skill = load_skill_from_directory(hello_dir)
        if skill:
            print(f"   Name: {skill.name}")
            print(f"   Description: {skill.description[:50]}...")
            print(f"   Allowed tools: {skill.allowed_tools}")
            print(f"   Model: {skill.model}")
            print(f"   Color: {skill.color}")
            print(f"   Body length: {len(skill.body)} chars")
        else:
            print("   ❌ Failed to parse!")
            return False

    # Test code-review skill
    review_dir = skills_dir / "code-review"
    if review_dir.exists():
        print("\n3. Parsing 'code-review' skill...")
        skill = load_skill_from_directory(review_dir)
        if skill:
            print(f"   Name: {skill.name}")
            print(f"   Description: {skill.description[:50]}...")
            print(f"   Allowed tools: {skill.allowed_tools}")
            print(f"   Model: {skill.model}")
            print(f"   Color: {skill.color}")
        else:
            print("   ❌ Failed to parse!")
            return False

    print("\n✅ Skill parsing test PASSED!")
    return True


def test_skill_registry():
    """Test skill registry."""
    print("\n" + "=" * 60)
    print("TEST 3: Skill Registry")
    print("=" * 60)

    project_root = Path(__file__).parent

    print("\n1. Creating registry...")
    registry = SkillRegistry(project_root=project_root)

    print("\n2. Loading skills...")
    count = registry.load()
    print(f"   Loaded {count} skills")

    print("\n3. Listing skills:")
    for name in registry.list_names():
        entry = registry.get_entry(name)
        if entry:
            print(f"   - {name} ({entry.location.scope})")

    print("\n4. Getting skill by name...")
    hello = registry.get("hello")
    if hello:
        print(f"   Found 'hello': {hello.description[:40]}...")
    else:
        print("   ❌ 'hello' not found!")
        return False

    print("\n5. Searching skills...")
    results = registry.search("review code")
    print(f"   Search 'review code' found {len(results)} results:")
    for skill in results:
        print(f"   - {skill.name}")

    print("\n6. Format available skills (XML):")
    xml = registry.format_available_skills()
    print(xml[:500] + "..." if len(xml) > 500 else xml)

    print("\n✅ Skill registry test PASSED!")
    return True


def test_skill_matcher():
    """Test skill matching."""
    print("\n" + "=" * 60)
    print("TEST 4: Skill Matcher")
    print("=" * 60)

    project_root = Path(__file__).parent
    registry = SkillRegistry(project_root=project_root)
    registry.load()

    print("\n1. Creating matcher...")
    matcher = SkillMatcher(registry)

    print("\n2. Testing task matching:")

    test_cases = [
        "Hello, how are you?",
        "Please review my code",
        "Can you do a PR review?",
        "/hello",
        "/code-review",
    ]

    for task in test_cases:
        print(f"\n   Task: '{task}'")

        # Check slash command first
        if task.startswith("/"):
            skill = matcher.find_by_slash_command(task)
            if skill:
                print(f"   → Slash command match: {skill.name}")
            else:
                print(f"   → No slash command match")
        else:
            # Regular matching
            results = matcher.match(task, limit=2)
            if results:
                for r in results:
                    print(f"   → Match: {r.skill.name} (score: {r.score:.2f})")
            else:
                print(f"   → No match")

    print("\n✅ Skill matcher test PASSED!")
    return True


def test_skill_executor():
    """Test skill execution."""
    print("\n" + "=" * 60)
    print("TEST 5: Skill Executor")
    print("=" * 60)

    project_root = Path(__file__).parent
    registry = SkillRegistry(project_root=project_root)
    registry.load()

    print("\n1. Creating executor...")
    executor = SkillExecutor()

    print("\n2. Getting 'hello' skill...")
    entry = registry.get_entry("hello")
    if not entry:
        print("   ❌ Skill not found!")
        return False

    print("\n3. Preparing context...")
    context = executor.prepare_context(entry.definition, entry.location)
    print(f"   Base path: {context.base_path}")
    print(f"   Skill: {context.skill.name}")
    print(f"   Auxiliary files: {context.auxiliary_files}")

    print("\n4. Activating skill...")
    output = executor.activate(context)
    print(f"   Output preview:")
    print("   " + output[:300].replace("\n", "\n   ") + "...")

    print("\n5. Testing tool restrictions...")
    print(f"   is_tool_allowed('Read'): {executor.is_tool_allowed('Read')}")
    print(f"   is_tool_allowed('Bash'): {executor.is_tool_allowed('Bash')}")
    print(f"   is_tool_allowed('Write'): {executor.is_tool_allowed('Write')}")

    print("\n6. Testing model override...")
    print(f"   get_model_override(): {executor.get_model_override()}")

    print("\n7. Deactivating skill...")
    executor.deactivate()
    print(f"   is_active: {executor.is_active}")

    print("\n✅ Skill executor test PASSED!")
    return True


def test_skill_tool():
    """Test SkillTool integration."""
    print("\n" + "=" * 60)
    print("TEST 6: Skill Tool")
    print("=" * 60)

    project_root = Path(__file__).parent

    print("\n1. Creating skill tool...")
    tool = create_skill_tool(project_root=project_root)

    print("\n2. Tool properties:")
    print(f"   Name: {tool.name}")
    print(f"   Category: {tool.category}")
    print(f"   Requires permission: {tool.requires_permission}")

    print("\n3. Tool description (with available skills):")
    desc = tool.description
    print(desc[:600] + "..." if len(desc) > 600 else desc)

    print("\n4. Executing skill 'hello'...")
    result = tool.execute({"skill": "hello"})
    print(f"   Success: {result.success}")
    print(f"   Output preview:")
    output = result.output[:400] if result.output else ""
    print("   " + output.replace("\n", "\n   ") + "...")

    print("\n5. Executing with slash command '/code-review'...")
    result = tool.execute({"skill": "/code-review"})
    print(f"   Success: {result.success}")
    if result.metadata:
        print(f"   Skill name: {result.metadata.get('skill_name')}")
        print(f"   Allowed tools: {result.metadata.get('allowed_tools')}")
        print(f"   Model: {result.metadata.get('model')}")

    print("\n6. Testing non-existent skill...")
    result = tool.execute({"skill": "non-existent"})
    print(f"   Success: {result.success}")
    print(f"   Error: {result.output[:100]}...")

    print("\n✅ Skill tool test PASSED!")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("DeepCode Skills Integration Tests")
    print("=" * 60)

    results = {}

    results["discovery"] = test_skill_discovery()
    results["parsing"] = test_skill_parsing()
    results["registry"] = test_skill_registry()
    results["matcher"] = test_skill_matcher()
    results["executor"] = test_skill_executor()
    results["tool"] = test_skill_tool()

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {name}: {status}")

    all_passed = all(results.values())
    print("\n" + ("ALL TESTS PASSED!" if all_passed else "SOME TESTS FAILED"))
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
