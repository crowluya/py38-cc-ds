---
name: code-review
description: Review code for bugs, security issues, and best practices. Use when users ask for code review or PR review.
allowed-tools: Read, Grep, Glob
model: opus
color: blue
---

# Code Review Skill

Perform thorough code reviews focusing on:

## Review Checklist

1. **Bugs & Logic Errors**
   - Off-by-one errors
   - Null/undefined handling
   - Edge cases

2. **Security Issues**
   - SQL injection
   - XSS vulnerabilities
   - Hardcoded secrets

3. **Best Practices**
   - Code readability
   - DRY principle
   - Error handling

4. **Performance**
   - N+1 queries
   - Unnecessary loops
   - Memory leaks

## Output Format

Provide feedback in this format:

```
[SEVERITY] file:line - Description
  Suggestion: How to fix
```

Severity levels: CRITICAL, WARNING, INFO
