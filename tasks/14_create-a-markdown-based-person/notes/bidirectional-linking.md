---
title: Bidirectional Linking
created: 2024-01-19T12:00:00
modified: 2024-01-19T12:00:00
tags: [features, linking, knowledge-graph]
---

# Bidirectional Linking

Bidirectional linking is a core feature of PK that enables automatic tracking of note connections.

## How It Works

When Note A links to Note B:
- Note A has an **outgoing link** to Note B
- Note B automatically shows a **backlink** from Note A

This creates a web of knowledge that grows organically.

## Creating Links

Use wiki-style syntax `[[Note Title]]`:

```markdown
# My Current Note

This concept is related to [[Another Concept]] and
builds on [[Foundational Idea]].

You can also use aliases: [[Another Concept|custom display text]]
```

## Viewing Connections

### Show outgoing links
```bash
pk show "My Current Note"
# Displays the note with link count
```

### Show backlinks
```bash
pk backlinks "My Current Note"
# Lists all notes that link here
```

### Check link health
```bash
pk check-links
# Reports broken links and orphan notes
```

## Benefits

### 1. Context
See how ideas connect and build on each other.

### 2. Discovery
Find related notes you might have forgotten.

### 3. Validation
Orphan notes may need better integration.

### 4. Navigation
Jump between related concepts easily.

## Best Practices

1. **Link liberally**: When you reference another concept, link it
2. **Use descriptive titles**: Makes links more meaningful
3. **Review backlinks**: See how others use your notes
4. **Fix broken links**: Run `pk check-links` regularly

## Link Types

### Conceptual Links
`[[Related Concept]]` - Shows thematic connection

### Hierarchical Links
`[[Parent Concept]]` - Shows broader category

### Sequential Links
`[[Previous Step]]` → [[Current Step]] → [[Next Step]]

## Related Features

- [[Full-Text Search]] - Find connections by searching
- [[Tag Management]] - Organize related notes
- [[Getting Started with PK]] - Learn PK basics
