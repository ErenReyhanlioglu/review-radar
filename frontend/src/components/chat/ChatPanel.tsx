import { useRef, useEffect, useState, type KeyboardEvent } from 'react'
import { Send } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ChatMessageBubble } from './ChatMessage'
import { appendToReport } from '@/services/api'
import type { ChatMessage, Report } from '@/types'

interface Props {
  messages: ChatMessage[]
  loading: boolean
  onSend: (text: string) => void
  isViewer?: boolean
  simulatedDate: string | null
  onReportUpdated?: (report: Report) => void
}

export function ChatPanel({ messages, loading, onSend, isViewer, simulatedDate, onReportUpdated }: Props) {
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight
  }, [messages, loading])

  const handleSend = () => {
    if (!input.trim() || loading) return
    onSend(input.trim())
    setInput('')
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  // Last generated report = sim_date - 1 month
  const getReportMonth = (): string | null => {
    if (!simulatedDate) return null
    const [sy, sm] = simulatedDate.split('-').map(Number)
    const y = sm === 1 ? sy - 1 : sy
    const m = sm === 1 ? 12 : sm - 1
    return `${y}-${String(m).padStart(2, '0')}-01`
  }

  const getUserPromptBefore = (assistantIdx: number): string => {
    for (let i = assistantIdx - 1; i >= 0; i--) {
      if (messages[i].role === 'user') return messages[i].content
    }
    return ''
  }

  const reportMonth = getReportMonth()

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-border bg-card/50">
        <div>
          <h2 className="text-sm font-semibold text-foreground">AI Asistan</h2>
          <p className="text-xs text-muted-foreground">Review verilerine dayalı analiz</p>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
          <span className="text-xs text-muted-foreground">Aktif</span>
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-32 text-center">
            <p className="text-sm text-muted-foreground">Apollo.io review verilerine soru sor.</p>
            <p className="text-xs text-muted-foreground/60 mt-1">Örn: "En çok hangi konu şikayet alıyor?"</p>
          </div>
        )}

        {messages.map((msg, idx) => {
          const isAssistant = msg.role === 'assistant'

          return (
            <ChatMessageBubble
              key={msg.id}
              message={msg}
              isViewer={isViewer}
              onAddToReport={isAssistant && reportMonth && !isViewer ? async () => {
                const updated = await appendToReport(reportMonth, {
                  prompt: getUserPromptBefore(idx),
                  answer: msg.content,
                  chart_data: msg.charts,
                })
                onReportUpdated?.(updated)
              } : undefined}
            />
          )
        })}

        {loading && (
          <ChatMessageBubble
            message={{ id: 'loading', role: 'assistant', content: '', charts: [], timestamp: new Date() }}
            isLoading
          />
        )}
      </div>

      {/* Input */}
      <div className="px-5 py-4 border-t border-border bg-card/50">
        <div className="flex items-end gap-2.5">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Apollo.io verileri hakkında soru sor…"
            className="min-h-[42px] max-h-[120px] resize-none bg-background text-sm"
            rows={1}
            disabled={loading}
          />
          <Button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            size="icon"
            className="h-[42px] w-[42px] shrink-0 bg-blue-600 hover:bg-blue-700"
          >
            <Send className="h-3.5 w-3.5" />
          </Button>
        </div>
        <p className="text-xs text-muted-foreground/50 mt-1.5">Enter gönder · Shift+Enter yeni satır</p>
      </div>
    </div>
  )
}
