import { MarkdownContent } from '@/components/ui/MarkdownContent'
import { ChartRenderer } from '@/components/charts/ChartRenderer'
import { AddToReportButton } from './AddToReportButton'
import type { ChatMessage as ChatMessageType } from '@/types'

const TypingIndicator = () => (
  <div className="flex items-center gap-1 px-1 py-1">
    <div className="w-1.5 h-1.5 bg-muted-foreground/50 rounded-full animate-bounce [animation-delay:-0.3s]" />
    <div className="w-1.5 h-1.5 bg-muted-foreground/50 rounded-full animate-bounce [animation-delay:-0.15s]" />
    <div className="w-1.5 h-1.5 bg-muted-foreground/50 rounded-full animate-bounce" />
  </div>
)

interface Props {
  message: ChatMessageType
  isLoading?: boolean
  isViewer?: boolean
  onAddToReport?: () => Promise<void>
}

export function ChatMessageBubble({ message, isLoading, isViewer, onAddToReport }: Props) {
  if (message.role === 'user') {
    return (
      <div className="flex justify-end mb-3">
        <div className="max-w-[72%] px-3.5 py-2 rounded-2xl bg-blue-600 text-white text-sm leading-relaxed">
          {message.content}
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start mb-3">
      <div className="max-w-[85%] min-w-0 rounded-xl bg-card border border-border shadow-sm overflow-hidden">
        <div className="px-4 py-3 min-w-0">
          {isLoading ? (
            <TypingIndicator />
          ) : (
            <MarkdownContent>{message.content}</MarkdownContent>
          )}
        </div>

        {message.charts.length > 0 && !isLoading && (
          <div className="px-4 pb-4 pt-2 border-t border-border/50 space-y-4">
            {message.charts.map((chart, i) => (
              <div key={i}>
                {chart.title && (
                  <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wide">
                    {chart.title}
                  </p>
                )}
                <ChartRenderer chart={chart} compact />
              </div>
            ))}
          </div>
        )}

        {!isLoading && !isViewer && onAddToReport && (
          <div className="px-4 pb-3">
            <AddToReportButton onAddToReport={onAddToReport} />
          </div>
        )}
      </div>
    </div>
  )
}
