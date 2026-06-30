import { useState, useCallback } from 'react'
import { sendChatMessage } from '@/services/api'
import type { ChatMessage, ChartPayload } from '@/types'

function makeId() { return Math.random().toString(36).slice(2) }

export function useChat(simulatedDate?: string | null) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)

  const send = useCallback(async (text: string) => {
    const userMsg: ChatMessage = {
      id: makeId(), role: 'user', content: text, charts: [], timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMsg])
    setLoading(true)

    try {
      const res = await sendChatMessage(text, simulatedDate)
      const assistantMsg: ChatMessage = {
        id: makeId(),
        role: 'assistant',
        content: res.answer,
        charts: res.chart_data as ChartPayload[],
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, assistantMsg])
      return assistantMsg
    } catch {
      const errMsg: ChatMessage = {
        id: makeId(), role: 'assistant',
        content: 'Bir hata oluştu, lütfen tekrar deneyin.',
        charts: [], timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errMsg])
      return errMsg
    } finally {
      setLoading(false)
    }
  }, [simulatedDate])

  const clear = useCallback(() => setMessages([]), [])

  return { messages, loading, send, clear }
}
