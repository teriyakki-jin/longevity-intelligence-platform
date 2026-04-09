'use client'

import { useCoach } from '@/lib/hooks/use-coach'
import { ChatInterface } from '@/components/coach/chat-interface'

export default function CoachPage() {
  const { messages, isStreaming, error, send, abort } = useCoach()

  return (
    <div className="flex flex-col h-screen">
      <div className="px-6 py-4 border-b border-[#30363d]">
        <h2 className="text-xl font-bold text-[#e6edf3]">AI Health Coach</h2>
        <p className="text-[#8b949e] text-sm mt-0.5">
          Personalized health guidance. Not medical advice.
        </p>
      </div>
      {error && (
        <div className="mx-6 mt-4 bg-[#ff7b7222] border border-[#ff7b72] rounded-xl p-3 text-[#ff7b72] text-sm">{error}</div>
      )}
      <div className="flex-1 min-h-0">
        <ChatInterface messages={messages} isStreaming={isStreaming} onSend={send} onAbort={abort} />
      </div>
    </div>
  )
}
