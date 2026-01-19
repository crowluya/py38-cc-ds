use crate::types::KnowledgeGraph;
use anyhow::Result;

/// Export knowledge graph to Graphviz DOT format
pub fn to_dot(graph: &KnowledgeGraph) -> Result<String> {
    let mut dot = String::from("digraph KnowledgeGraph {\n");
    dot.push_str("    node [shape=box, style=rounded];\n");
    dot.push_str("    rankdir=LR;\n\n");

    // Add nodes
    for (id, note) in &graph.notes {
        let escaped_title = escape_dot_string(&note.title);
        dot.push_str(&format!("    \"{}\" [label=\"{}\"];\n", id, escaped_title));
    }

    dot.push_str("\n");

    // Add edges
    let mut added_edges = std::collections::HashSet::new();
    for (from_id, to_list) in &graph.forward_links {
        for to_id in to_list {
            // Avoid duplicate edges
            let edge = (from_id.clone(), to_id.clone());
            if added_edges.insert(edge) {
                dot.push_str(&format!("    \"{}\" -> \"{}\";\n", from_id, to_id));
            }
        }
    }

    dot.push_str("}\n");
    Ok(dot)
}

/// Escape special characters for DOT format
fn escape_dot_string(s: &str) -> String {
    s.replace('"', r#"\""#)
        .replace('\\', r#"\\"#)
        .replace('\n', r"\n")
        .replace('\t', r"\t")
}

/// Export knowledge graph to JSON format
pub fn to_json(graph: &KnowledgeGraph) -> Result<String> {
    serde_json::to_string_pretty(graph).map_err(anyhow::Error::from)
}

/// Export knowledge graph to a custom JSON format optimized for visualization
pub fn to_visualization_json(graph: &KnowledgeGraph) -> Result<String> {
    let nodes: Vec<NodeData> = graph
        .notes
        .iter()
        .map(|(id, note)| NodeData {
            id: id.clone(),
            title: note.title.clone(),
            tags: note.tags.clone(),
            created_at: note.created_at.to_rfc3339(),
            modified_at: note.modified_at.to_rfc3339(),
        })
        .collect();

    let edges: Vec<EdgeData> = graph
        .forward_links
        .iter()
        .flat_map(|(from, to_list)| {
            to_list.iter().map(move |to| EdgeData {
                from: from.clone(),
                to: to.clone(),
            })
        })
        .collect();

    let vis_data = VisualizationData { nodes, edges };
    serde_json::to_string_pretty(&vis_data).map_err(anyhow::Error::from)
}

#[derive(Debug, serde::Serialize)]
struct NodeData {
    id: String,
    title: String,
    tags: Vec<String>,
    created_at: String,
    modified_at: String,
}

#[derive(Debug, serde::Serialize)]
struct EdgeData {
    from: String,
    to: String,
}

#[derive(Debug, serde::Serialize)]
struct VisualizationData {
    nodes: Vec<NodeData>,
    edges: Vec<EdgeData>,
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{KnowledgeGraph, Note};
    use chrono::Utc;

    #[test]
    fn test_to_dot_basic() {
        let mut graph = KnowledgeGraph::new();
        let note1 = Note::new("Note One".to_string(), "Content".to_string());
        let note2 = Note::new("Note Two".to_string(), "Links to [[note-one]]".to_string());
        graph.add_note(note1);
        graph.add_note(note2);
        graph.rebuild_links();

        let dot = to_dot(&graph).unwrap();
        assert!(dot.contains("digraph KnowledgeGraph"));
        assert!(dot.contains("note-one"));
        assert!(dot.contains("note-two"));
    }

    #[test]
    fn test_to_json() {
        let mut graph = KnowledgeGraph::new();
        let note = Note::new("Test".to_string(), "Content".to_string());
        graph.add_note(note);

        let json = to_json(&graph).unwrap();
        assert!(json.contains("\"notes\""));
        assert!(json.contains("\"forward_links\""));
    }

    #[test]
    fn test_escape_dot_string() {
        assert_eq!(escape_dot_string("hello"), "hello");
        assert_eq!(escape_dot_string("say \"hello\""), r#"say \"hello\""#);
        assert_eq!(escape_dot_string("line1\nline2"), r#"line1\nline2"#);
    }
}
