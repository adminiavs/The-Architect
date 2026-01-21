# Metadata Directory

This directory contains JSON schemas and structured data that augment the markdown documentation with:

- Concept relationships and dependencies
- Navigation maps and learning paths
- Verification status tracking
- Document metadata and cross-references

---

## Files

### `concept_graph.json`
**Purpose:** Maps all concepts, their relationships, and dependencies

**Structure:**
```json
{
  "concepts": [
    {
      "id": "concept_identifier",
      "name": "Human-readable name",
      "category": "axiom|geometry|mechanism|prediction|constant",
      "level": 0-6,
      "definition": "Clear definition",
      "primary_document": "path/to/document.md",
      "depends_on": ["prerequisite_concepts"],
      "required_by": ["dependent_concepts"],
      "tags": ["searchable", "tags"]
    }
  ],
  "relationships": [
    {
      "from": "concept_a",
      "to": "concept_b",
      "type": "derives|projects_to|enables|implements",
      "mechanism": "How they relate"
    }
  ]
}
```

**Usage:**
- Automated dependency checking
- Concept graph visualization
- Prerequisite validation
- Learning path generation

---

## Future Expansions

Additional metadata files to be added:

### `document_registry.json`
- Full document metadata
- Prerequisites and reading order
- Difficulty levels
- Estimated reading times

### `verification.json`
- All model predictions
- Experimental status
- Accuracy measurements
- References to sources

### `navigation.json`
- Predefined learning paths
- Quick-start guides
- Difficulty progression maps

### `transcript_index.json`
- Categorized transcript listing
- Topic tags
- Related formal documents
- Summary descriptions

---

## Validation

To maintain consistency between markdown content and JSON metadata:

1. **Manual review:** Check that referenced documents exist
2. **Automated validation:** Use scripts to verify:
   - All document paths are valid
   - All concept dependencies exist
   - No circular dependencies
   - All tags are from controlled vocabulary

---

## Design Philosophy

**Hybrid Approach:**
- Content remains in human-readable markdown
- Structure captured in machine-readable JSON
- Best of both worlds: readability + computability

**Principles:**
1. JSON augments, never replaces markdown
2. Markdown files are the source of truth for content
3. JSON provides structural and relational metadata
4. Tools use both layers for enhanced functionality

---

**Status:** Initial version (2026-01-21)  
**Maintainer:** The Architect  
**Schema Version:** 1.0
