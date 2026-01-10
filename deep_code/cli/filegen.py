from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional, Tuple


class FileType(str, Enum):
    python = "python"
    requirements = "requirements"
    json = "json"
    markdown = "markdown"
    text = "text"
    yaml = "yaml"


@dataclass
class ValidationResult:
    ok: bool
    error: str = ""


_REQUIREMENT_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_.-]*(\[[A-Za-z0-9_,.-]+\])?\s*(==|>=|<=|~=|!=|>|<)\s*[A-Za-z0-9_.+-]+\s*$"
)


def _strip_outer_code_fence(text: str) -> str:
    s = text.strip()
    if s.startswith("```"):
        # Remove first fence line
        first_nl = s.find("\n")
        if first_nl != -1:
            s = s[first_nl + 1 :]
        # Remove trailing fence
        last_fence = s.rfind("```")
        if last_fence != -1:
            s = s[:last_fence]
    return s.strip("\n")


def sanitize_content(file_type: FileType, raw: str) -> str:
    s = raw
    s = s.replace("\r\n", "\n")
    s = _strip_outer_code_fence(s)

    if file_type == FileType.requirements:
        lines = []
        for line in s.split("\n"):
            t = line.strip()
            if not t:
                continue
            if t.startswith("#"):
                continue
            if t.startswith("-") or t.startswith("*"):
                continue
            if "以下" in t or "requirements" in t.lower() and ":" in t:
                continue
            # Allow --index-url/--trusted-host/--extra-index-url
            if t.startswith("--"):
                lines.append(t)
                continue
            if _REQUIREMENT_RE.match(t):
                lines.append(t)
        return "\n".join(lines).strip() + "\n"

    if file_type == FileType.json:
        s2 = s.strip()
        # Try to extract first JSON object/array
        start = None
        for ch in ("{", "["):
            idx = s2.find(ch)
            if idx != -1:
                start = idx if start is None else min(start, idx)
        if start is not None:
            s2 = s2[start:]
        # Trim trailing text after last } or ]
        end_obj = s2.rfind("}")
        end_arr = s2.rfind("]")
        end = max(end_obj, end_arr)
        if end != -1:
            s2 = s2[: end + 1]
        return s2.strip() + "\n"

    # For other types, just ensure newline termination
    s = s.strip("\n") + "\n"
    return s


def validate_content(file_type: FileType, content: str) -> ValidationResult:
    if file_type == FileType.requirements:
        lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
        if not lines:
            return ValidationResult(False, "requirements.txt is empty")
        for ln in lines:
            if ln.startswith("--"):
                continue
            if not _REQUIREMENT_RE.match(ln):
                return ValidationResult(False, f"invalid requirement line: {ln}")
        return ValidationResult(True)

    if file_type == FileType.json:
        try:
            json.loads(content)
        except Exception as e:
            return ValidationResult(False, f"invalid json: {e}")
        return ValidationResult(True)

    if file_type == FileType.python:
        try:
            compile(content, "<generated>", "exec")
        except Exception as e:
            return ValidationResult(False, f"python syntax error: {e}")
        return ValidationResult(True)

    # Markdown/text/yaml: we only enforce non-empty
    if not content.strip():
        return ValidationResult(False, "content is empty")

    return ValidationResult(True)


def build_generation_prompt(file_type: FileType, target_path: str, instruction: str) -> str:
    ext = Path(target_path).suffix.lower()
    header = (
        "You are generating a single file for a software project.\n"
        "Strict output rules (must follow):\n"
        "- Output ONLY the file content.\n"
        "- Do NOT include explanations, prefaces, or summaries.\n"
        "- Do NOT wrap the whole output in Markdown code fences.\n"
        "- Ensure the output is valid for the requested file type.\n"
    )

    type_rules = {
        FileType.requirements: (
            "File type: requirements.txt\n"
            "- Output must be valid pip requirements format.\n"
            "- One requirement per line.\n"
            "- No prose lines.\n"
        ),
        FileType.python: (
            "File type: Python source\n"
            "- Output must be valid Python 3.8 code.\n"
            "- Include all necessary imports.\n"
        ),
        FileType.json: (
            "File type: JSON\n"
            "- Output must be a single valid JSON value (object or array).\n"
        ),
        FileType.markdown: (
            "File type: Markdown\n"
            "- Output must be Markdown content.\n"
            "- Do not add any leading prose like 'Here is ...'.\n"
        ),
        FileType.yaml: (
            "File type: YAML\n"
            "- Output must be valid YAML.\n"
        ),
        FileType.text: "File type: plain text\n",
    }[file_type]

    return (
        header
        + type_rules
        + f"Target path: {target_path} (extension: {ext})\n"
        + "Instruction:\n"
        + instruction.strip()
        + "\n"
    )


def generate_validated(
    generate_fn: Callable[[str], str],
    file_type: FileType,
    target_path: str,
    instruction: str,
    max_attempts: int = 3,
) -> Tuple[str, ValidationResult]:
    prompt = build_generation_prompt(file_type, target_path, instruction)

    last_result = ValidationResult(False, "not attempted")
    last_content = ""

    for attempt in range(1, max_attempts + 1):
        raw = generate_fn(prompt)
        content = sanitize_content(file_type, raw)
        result = validate_content(file_type, content)
        last_result = result
        last_content = content
        if result.ok:
            return content, result

        # Ask for a strict retry with the validator error
        prompt = (
            build_generation_prompt(file_type, target_path, instruction)
            + "\nThe previous output was invalid for the requested file type.\n"
            + f"Validation error: {result.error}\n"
            + "Regenerate and follow the strict output rules.\n"
        )

    return last_content, last_result


def safe_write_text(path: str, content: str, overwrite: bool) -> None:
    p = Path(path)
    if p.exists() and not overwrite:
        raise FileExistsError(str(p))
    p.parent.mkdir(parents=True, exist_ok=True)
    # Ensure consistent newlines
    normalized = content.replace("\r\n", "\n")
    if not normalized.endswith("\n"):
        normalized += "\n"
    p.write_text(normalized, encoding="utf-8")


def detect_file_type(path: str, explicit: Optional[str]) -> FileType:
    if explicit:
        return FileType(explicit)

    ext = Path(path).suffix.lower()
    if ext in (".py",):
        return FileType.python
    if ext in (".json",):
        return FileType.json
    if ext in (".md", ".markdown"):
        return FileType.markdown
    if ext in (".yml", ".yaml"):
        return FileType.yaml
    if Path(path).name.lower() in ("requirements.txt",):
        return FileType.requirements

    return FileType.text
