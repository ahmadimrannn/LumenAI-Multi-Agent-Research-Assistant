export const NODE_LABELS: Record<string, string> = {
  query_classifier: "Understanding your question",
  direct_knowledge_agent: "Checking existing knowledge",
  human_approval: "Waiting for your approval",
  researcher: "Searching sources",
  supervisor: "Reviewing search results",
  source_critic: "Checking source quality",
  evidence_extractor: "Extracting evidence",
  conflicts_analyst: "Looking for conflicts",
  report_writer: "Writing the report",
}

export function nodeLabel(node: string): string {
  return NODE_LABELS[node] ?? node.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase())
}
