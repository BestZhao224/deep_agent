import { appendStreamEvent, parseSseDataLine } from '../lib/stream'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export async function fetchSessions() {
  const response = await fetch(`${API_BASE}/api/sessions`)
  if (!response.ok) throw new Error(`加载会话失败：${response.status}`)
  return response.json()
}

export async function fetchSession(threadId) {
  const response = await fetch(`${API_BASE}/api/sessions/${threadId}`)
  if (!response.ok) throw new Error(`加载会话失败：${response.status}`)
  return response.json()
}

export async function streamChat({ message, threadId, state, onEvent }) {
  const response = await fetch(`${API_BASE}/api/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, thread_id: threadId }),
  })
  if (!response.ok || !response.body) {
    throw new Error(`请求失败：${response.status}`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      const event = parseSseDataLine(line)
      if (!event) continue
      appendStreamEvent(state, event)
      onEvent?.(event)
    }
  }
}
