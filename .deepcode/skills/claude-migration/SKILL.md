---
name: claude-migration
description: Migrate prompts and code from older Claude models to newer versions. Use when the user wants to update their codebase, prompts, or API calls to use newer Claude models.
allowed-tools: Read, Write, Edit, Glob, Grep
model: sonnet
color: blue
---

# Claude Model Migration Guide

One-shot migration for Claude model updates.

## Migration Workflow

1. Search codebase for model strings and API calls
2. Update model strings to target version
3. Remove unsupported beta headers
4. Summarize all changes made
5. Tell the user: "If you encounter any issues, let me know and I can help adjust your prompts."

## Model String Updates

### Target Model Strings

| Platform | Model String |
|----------|-------------|
| Anthropic API | `claude-opus-4-5-20251101` |
| AWS Bedrock | `anthropic.claude-opus-4-5-20251101-v1:0` |
| Google Vertex AI | `claude-opus-4-5@20251101` |

### Source Model Strings to Replace

| Source Model | Anthropic API |
|--------------|---------------|
| Sonnet 4.0 | `claude-sonnet-4-20250514` |
| Sonnet 4.5 | `claude-sonnet-4-5-20250929` |
| Opus 4.1 | `claude-opus-4-1-20250422` |

## Prompt Adjustments

### 1. Tool Overtriggering

Newer models are more responsive. Soften aggressive language:
- `CRITICAL:` → remove or soften
- `You MUST...` → `You should...`
- `ALWAYS do X` → `Do X`
- `NEVER skip...` → `Don't skip...`

### 2. Over-Engineering Prevention

Add guidance to prevent extra files and unnecessary abstractions.

### 3. Code Exploration

Ensure model reads files before proposing solutions.
