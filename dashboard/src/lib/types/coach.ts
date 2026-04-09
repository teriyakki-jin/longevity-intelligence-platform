export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

export interface ChatRequest {
  message: string
  conversation_history: Array<{ role: string; content: string }>
  health_context: string | null
  stream: boolean
}

export type SSEEvent =
  | { type: 'text'; content: string }
  | { type: 'done' }
  | { type: 'error'; content: string }
