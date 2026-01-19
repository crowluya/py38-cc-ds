---
title: Zettelkasten Method
created: 2024-01-19T12:00:00
modified: 2024-01-19T12:00:00
tags: [knowledge-management, methodology, productivity]
---

# Zettelkasten Method

The Zettelkasten (German for "slipbox") is a personal knowledge management system developed by sociologist Niklas Luhmann.

## Core Principles

### 1. Atomic Notes
Each note should contain a single idea or concept. This makes notes:
- Easier to link
- More reusable
- Simpler to understand

### 2. Linking
Create web-like connections between notes:
- **Direct links**: References to related concepts
- **Implicit links**: Notes that contribute to ideas
- **Structure notes**: Overviews of multiple concepts

### 3. Own Your Words
Don't just copy information. Rephrase ideas in your own words to:
- Enhance understanding
- Aid memory retention
- Build unique connections

## Implementation with PK

Use PK to implement a digital Zettelkasten:

```bash
# Create atomic notes
pk new "Atomic Design Principle"
pk new "Component-Driven Development"

# Link them together
pk edit "Atomic Design Principle"
# Add: See also [[Component-Driven Development]]
```

## Benefits

- **Serendipity**: Discover unexpected connections
- **Productivity**: Write faster by reusing notes
- **Learning**: Build knowledge through connections
- **Creativity**: Combine ideas in novel ways

## Related Concepts

- [[Getting Started with PK]] - PK implementation
- [[Note-taking Best Practices]] - Practical tips
- [[Progressive Summarization]] - Processing information

## Resources

- "How to Take Smart Notes" by Sönke Ahrens
- Luhmann's Communication Theory of Society
- Digital tools like Obsidian, Roam Research, and PK
