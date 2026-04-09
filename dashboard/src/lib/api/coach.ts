import { API_BASE_URL } from '../constants'
import type { ChatRequest, SSEEvent } from '../types/coach'

export async function streamCoachChat(
  request: ChatRequest,
  onToken: (text: string) => void,
  onDone: () => void,
  onError: (err: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/coach/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  })

  if (!res.ok || !res.body) {
    onError(`Server error: ${res.status}`)
    return
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''

    for (const part of parts) {
      const line = part.trim()
      if (!line.startsWith('data: ')) continue
      try {
        const event = JSON.parse(line.slice(6)) as SSEEvent
        if (event.type === 'text') onToken(event.content)
        else if (event.type === 'done') { onDone(); return }
        else if (event.type === 'error') { onError(event.content); return }
      } catch {
        // skip malformed events
      }
    }
  }

  onDone()
}
