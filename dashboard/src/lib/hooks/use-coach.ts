'use client'

import { useState, useCallback, useRef } from 'react'
import { streamCoachChat } from '../api/coach'
import type { ChatMessage } from '../types/coach'

export function useCoach(healthContext: string | null = null) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const send = useCallback(async (text: string) => {
    if (!text.trim() || isStreaming) return

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text.trim(),
      timestamp: Date.now(),
    }

    const assistantId = crypto.randomUUID()
    const assistantMsg: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: Date.now(),
    }

    setMessages(prev => [...prev, userMsg, assistantMsg])
    setIsStreaming(true)
    setError(null)

    abortRef.current = new AbortController()

    const history = messages.map(m => ({ role: m.role, content: m.content }))

    await streamCoachChat(
      { message: text.trim(), conversation_history: history, health_context: healthContext, stream: true },
      (token) => {
        setMessages(prev =>
          prev.map(m => m.id === assistantId ? { ...m, content: m.content + token } : m)
        )
      },
      () => setIsStreaming(false),
      (err) => { setError(err); setIsStreaming(false) },
      abortRef.current.signal,
    )
  }, [messages, isStreaming, healthContext])

  const abort = useCallback(() => {
    abortRef.current?.abort()
    setIsStreaming(false)
  }, [])

  const clear = useCallback(() => {
    setMessages([])
    setError(null)
  }, [])

  return { messages, isStreaming, error, send, abort, clear }
}
