export type NodeUpdateEvent = { type: "node_update"; thread_id: string; data: Record<string, unknown> }
export type InterruptedEvent = { type: "interrupted"; status: "interrupted"; thread_id: string; interrupt: unknown }
export type CompletedEvent = {
  type: "completed"
  status: "completed"
  thread_id: string
  response?: string
  requires_external_research?: boolean
  knowledge_source?: string
  termination_reason?: string
  degraded?: boolean
  [key: string]: unknown
}
export type ErrorEvent = { type: "error"; status: "error"; thread_id: string; error: string; detail?: string }
export type LumenEvent = NodeUpdateEvent | InterruptedEvent | CompletedEvent | ErrorEvent

export type TurnStatus = "streaming" | "completed" | "interrupted" | "terminated" | "error" | "stopped"

export interface Turn {
  id: string
  query: string
  editedQuery?: string
  status: TurnStatus
  progressSteps: string[]
  response?: string
  knowledgeSource?: string
  requiresExternalResearch?: boolean
  degraded?: boolean
  terminationReason?: string
  interrupt?: unknown
  errorMessage?: string
}

export interface Session {
  id: string
  title: string
  createdAt: string
  updatedAt: string
}
