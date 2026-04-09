'use client'

import { useEffect, useRef, useState } from 'react'
import type { ChatMessage } from '@/lib/types/coach'
import { Button } from '../ui/button'

interface Props {
  messages: ChatMessage[]
  isStreaming: boolean
  onSend: (text: string) => void
  onAbort: () => void
}

export function ChatInterface({ messages, isStreaming, onSend, onAbort }: Props) {
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    if (!input.trim() || isStreaming) return
    onSend(input.trim())
    setInput('')
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto space-y-4 p-4 min-h-0">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-[#8b949e] text-sm">
            Ask me anything about your health and longevity.
          </div>
        )}
        {messages.map(msg => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-[#1f6feb] text-white rounded-br-sm'
                  : 'bg-[#21262d] text-[#e6edf3] rounded-bl-sm'
              }`}
            >
              {msg.content || <span className="opacity-40 animate-pulse">●●●</span>}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-[#30363d] p-4 flex gap-3">
        <input
          className="flex-1 bg-[#0d1117] border border-[#30363d] rounded-lg px-4 py-2.5 text-sm text-[#e6edf3] placeholder-[#484f58] focus:outline-none focus:border-[#58a6ff]"
          placeholder="Ask about your health..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
          disabled={isStreaming}
        />
        {isStreaming
          ? <Button variant="secondary" onClick={onAbort} size="md">Stop</Button>
          : <Button onClick={handleSend} disabled={!input.trim()} size="md">Send</Button>
        }
      </div>
    </div>
  )
}
