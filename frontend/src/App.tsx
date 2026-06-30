import { useState, useCallback, useRef, useEffect } from 'react'
import { DashboardLayout } from '@/components/layout/DashboardLayout'
import { SimulationBar } from '@/components/simulation/SimulationBar'
import { ChatPanel } from '@/components/chat/ChatPanel'
import { ReportPanel } from '@/components/report/ReportPanel'
import { ReportsDrawer } from '@/components/reports/ReportsDrawer'
import { EmailModal } from '@/components/report/EmailModal'
import { Button } from '@/components/ui/button'
import { FileText } from 'lucide-react'
import { useSimulation } from '@/hooks/useSimulation'
import { useChat } from '@/hooks/useChat'
import { useReport } from '@/hooks/useChartData'
import type { Report } from '@/types'

const params = new URLSearchParams(window.location.search)
const IS_VIEWER = params.get('mode') === 'viewer'
const VIEWER_MONTH = params.get('month') ?? undefined

export default function App() {
  useEffect(() => {
    const handleBeforePrint = () => {
      // Recharts ResizeObserver doesn't fire during print layout —
      // dispatching resize forces it to re-measure with print dimensions.
      window.dispatchEvent(new Event('resize'))
      // Second dispatch after a tick, for charts that render lazily
      requestAnimationFrame(() => window.dispatchEvent(new Event('resize')))
    }
    window.addEventListener('beforeprint', handleBeforePrint)
    return () => window.removeEventListener('beforeprint', handleBeforePrint)
  }, [])

  const [drawerOpen, setDrawerOpen] = useState(false)
  const [emailModalOpen, setEmailModalOpen] = useState(false)
  const [viewingMonth, setViewingMonth] = useState<string | undefined>(VIEWER_MONTH)

  const { report, loading: reportLoading, error: reportError, reload: reloadReport, clear: clearReport } = useReport(viewingMonth)

  // Ref breaks the circular dependency:
  // handleAdvanceComplete → clearChat (from useChat)
  // useSimulation(handleAdvanceComplete) → simulatedDate → useChat
  const clearChatRef = useRef<() => void>(() => {})

  const handleAdvanceComplete = useCallback(() => {
    reloadReport()
    clearChatRef.current()
  }, [reloadReport])

  const { status, advancing, advance, reset } = useSimulation(handleAdvanceComplete)

  const simulatedDate = status?.simulated_date ?? null

  const { messages, loading: chatLoading, send, clear: clearChat } = useChat(simulatedDate)
  clearChatRef.current = clearChat

  const handleReportUpdated = useCallback((updated: Report) => {
    void updated
    reloadReport()
  }, [reloadReport])

  const isRunning = advancing || (status?.is_running ?? false)

  return (
    <>
      <DashboardLayout
        topBar={
          !IS_VIEWER ? (
            <SimulationBar
              simulatedDate={simulatedDate}
              isRunning={isRunning}
              onNextMonth={advance}
              onReportsClick={() => setDrawerOpen(true)}
              onReset={async () => { clearReport(); await reset(); setViewingMonth(undefined) }}
              isViewer={IS_VIEWER}
            />
          ) : (
            <div className="flex items-center justify-between h-14 px-6 border-b border-border bg-background">
              <span className="text-sm font-semibold text-foreground">Review Radar — Rapor Görüntüleyici</span>
              <Button variant="ghost" size="sm" className="h-7 text-xs gap-1.5" onClick={() => setDrawerOpen(true)}>
                <FileText className="w-3.5 h-3.5" />
                Raporlar
              </Button>
            </div>
          )
        }
        leftPanel={
          <ReportPanel
            report={report}
            loading={reportLoading}
            error={reportError}
            onSendEmail={!IS_VIEWER ? () => setEmailModalOpen(true) : undefined}
          />
        }
        rightPanel={
          <ChatPanel
            messages={messages}
            loading={chatLoading}
            onSend={send}
            isViewer={IS_VIEWER}
            simulatedDate={simulatedDate}
            onReportUpdated={handleReportUpdated}
          />
        }
      />

      <ReportsDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onSelectMonth={(m) => { setViewingMonth(m); setDrawerOpen(false) }}
      />

      {report && (
        <EmailModal
          open={emailModalOpen}
          onClose={() => setEmailModalOpen(false)}
          month={report.month.toString()}
        />
      )}
    </>
  )
}
