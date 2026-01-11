---
name: hookify-rules
description: Write hookify rules for Claude Code hooks. Use when the user asks to create a hookify rule, write a hook rule, configure hookify, or needs guidance on hookify rule syntax and patterns.
allowed-tools: Read, Write, Edit, Glob
model: sonnet
color: purple
---

# Writing Hookify Rules

## Overview

Hookify rules are markdown files with YAML frontmatter that define patterns to watch for and messages to show when those patterns match.

## Rule File Format

```markdown
---
name: rule-identifier
enabled: true
event: bash|file|stop|prompt|all
pattern: regex-pattern-here
---

Message to show when this rule triggers.
```

## Frontmatter Fields

- **name** (required): Unique identifier (kebab-case)
- **enabled** (required): Boolean to activate/deactivate
- **event** (required): Which hook event to trigger on
  - `bash`: Bash tool commands
  - `file`: Edit, Write tools
  - `stop`: When agent wants to stop
  - `prompt`: When user submits a prompt
  - `all`: All events
- **action** (optional): `warn` (default) or `block`
- **pattern**: Regex pattern to match

## Event Type Guide

### bash Events
```yaml
event: bash
pattern: sudo\s+|rm\s+-rf|chmod\s+777
```

### file Events
```yaml
event: file
pattern: console\.log\(|eval\(|innerHTML\s*=
```

### stop Events
```yaml
event: stop
pattern: .*
```

## Pattern Writing Tips

### Regex Basics
- `\s` - whitespace
- `\d` - digit
- `\w` - word character
- `.` - any character
- `+` - one or more
- `*` - zero or more
- `|` - OR

### Examples
```
rm\s+-rf         # Matches: rm -rf
console\.log\(   # Matches: console.log(
(eval|exec)\(    # Matches: eval( or exec(
```

## File Organization

- Location: `.claude/` directory
- Naming: `.claude/hookify.{name}.local.md`
- Add `.claude/*.local.md` to `.gitignore`
