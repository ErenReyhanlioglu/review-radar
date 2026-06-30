import { useEffect, useState, useCallback } from 'react'
import { MarkdownContent } from '@/components/ui/MarkdownContent'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Printer, Mail, FileText, Loader2 } from 'lucide-react'
import { ChartRenderer } from '@/components/charts/ChartRenderer'
import { getTrend, getTopics, getSentiment, getCompanySize, getTopicSentiment } from '@/services/api'
import type { Report, ChartPayload } from '@/types'

interface Props {
  report: Report | null
  loading: boolean
  error: string | null
  onSendEmail?: () => void
}

// ── Chart fetching ────────────────────────────────────────────────────────────

function useReportCharts(month: string | null) {
  const [charts, setCharts] = useState<ChartPayload[]>([])

  useEffect(() => {
    if (!month) { setCharts([]); return }

    const monthStart = month.slice(0, 7) + '-01'
    const year = parseInt(monthStart.slice(0, 4))
    const month0 = parseInt(monthStart.slice(5, 7)) - 1
    const monthEnd = new Date(Date.UTC(year, month0 + 1, 0)).toISOString().slice(0, 10)
    const trendFrom = new Date(Date.UTC(year, month0 - 5, 1)).toISOString().slice(0, 10)

    Promise.all([
      getTrend({ date_from: trendFrom, date_to: monthEnd }),
      getTopics({ date_from: monthStart, date_to: monthStart }),
      getSentiment({ date_from: monthStart, date_to: monthEnd }),
      getCompanySize({ date_from: monthStart, date_to: monthEnd }),
      getTopicSentiment({ date_from: monthStart, date_to: monthStart }),
    ]).then(([trend, topics, sentiment, companySize, topicSentiment]) => {
      const built: ChartPayload[] = []

      if (trend?.length) built.push({ type: 'trend', data: trend })

      if (topics?.length) {
        built.push({
          type: 'breakdown', group_by: 'topic',
          data: topics.map((t) => ({ group_value: t.topic, count: t.count })),
        })
      }

      if (sentiment?.length) {
        const grouped: Record<string, number> = {}
        for (const s of sentiment) grouped[s.sentiment] = (grouped[s.sentiment] ?? 0) + s.count
        built.push({
          type: 'breakdown', group_by: 'sentiment',
          data: Object.entries(grouped).map(([group_value, count]) => ({ group_value, count })),
        })
      }

      if (topicSentiment?.length) {
        built.push({
          type: 'breakdown', group_by: 'topic_sentiment',
          data: topicSentiment.map((s) => ({ group_value: s.sentiment, count: s.count })),
        })
      }

      if (companySize?.length) {
        built.push({
          type: 'breakdown', group_by: 'company_size',
          data: companySize.map((c) => ({ group_value: c.company_size, count: c.count })),
        })
      }

      setCharts(built)
    }).catch(() => setCharts([]))
  }, [month])

  return charts
}

// ── Section parsing ───────────────────────────────────────────────────────────

interface Section {
  heading: string
  body: string
  charts: ChartPayload[]
}

const CHART_TITLES: Record<string, string> = {
  trend: 'Aylık Puan Trendi',
  topic: 'Konu Dağılımı',
  topic_sentiment: 'Konu Duygu Dağılımı',
  sentiment: 'Sentiment Dağılımı',
  company_size: 'Segment Dağılımı',
}

function chartTitle(c: ChartPayload) {
  if (c.type === 'trend') return CHART_TITLES.trend
  return CHART_TITLES[c.group_by ?? ''] ?? ''
}

function assignCharts(markdown: string, charts: ChartPayload[]): Section[] {
  const lines = markdown.split('\n')
  const rawSections: string[][] = []
  let current: string[] = []

  for (const line of lines) {
    if (line.startsWith('## ') && current.length > 0) {
      rawSections.push(current)
      current = [line]
    } else {
      current.push(line)
    }
  }
  if (current.length > 0) rawSections.push(current)

  return rawSections.map((sectionLines) => {
    const heading = sectionLines[0] ?? ''
    const body = sectionLines.slice(1).join('\n').replace(/^\n+/, '')
    const lower = heading.toLowerCase()
    let sectionCharts: ChartPayload[] = []

    if (/^## metrik/i.test(lower)) {
      sectionCharts = charts.filter((c) => c.type === 'trend')
    } else if (/^## konu/i.test(lower)) {
      sectionCharts = charts.filter((c) => c.group_by === 'topic' || c.group_by === 'topic_sentiment')
    } else if (/^## sentiment/i.test(lower)) {
      sectionCharts = charts.filter((c) => c.group_by === 'sentiment')
    } else if (/^## segment/i.test(lower)) {
      sectionCharts = charts.filter((c) => c.group_by === 'company_size')
    }

    return { heading, body, charts: sectionCharts }
  })
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ReportPanel({ report, loading, error, onSendEmail }: Props) {
  const charts = useReportCharts(report?.month ?? null)

  const [printWidth, setPrintWidth] = useState<number | undefined>()

  // When printWidth is set, React re-renders charts at that exact px width
  // (no ResizeObserver involved), then we open the print dialog.
  useEffect(() => {
    if (printWidth === undefined) return
    const id = setTimeout(() => {
      const prev = document.title
      if (report) document.title = `Review-Radar-${report.month}`
      window.print()
      document.title = prev
      setPrintWidth(undefined)
    }, 100) // charts already rendered synchronously by React; 100ms = one paint
    return () => clearTimeout(id)
  }, [printWidth, report])

  const handlePrint = useCallback(() => setPrintWidth(680), [])

  if (loading) {
    return (
      <div className="flex flex-col h-full items-center justify-center gap-3 text-muted-foreground">
        <Loader2 className="w-6 h-6 animate-spin" />
        <p className="text-sm">Rapor yükleniyor…</p>
      </div>
    )
  }

  if (error || !report) {
    return (
      <div className="flex flex-col h-full items-center justify-center gap-2 text-muted-foreground px-8 text-center">
        <FileText className="w-8 h-8 opacity-30" />
        <p className="text-sm">Henüz bu aya ait rapor yok.</p>
        <p className="text-xs opacity-60">Simülasyonu ilerletince rapor burada görünecek.</p>
      </div>
    )
  }

  const monthLabel = new Date(report.month).toLocaleDateString('tr-TR', {
    month: 'long',
    year: 'numeric',
  })

  const sections = assignCharts(report.content, charts)
  const pmSections = report.pm_sections ?? []

  return (
    <div className="flex flex-col h-full bg-background report-content print:!h-auto print:!overflow-visible">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-border bg-card/50 no-print">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-muted-foreground" />
          <span className="text-sm font-semibold text-foreground">{monthLabel} Raporu</span>
          <Badge variant="secondary" className="text-xs">Güncel</Badge>
        </div>
        <div className="flex items-center gap-1.5">
          {onSendEmail && (
            <Button variant="ghost" size="sm" className="h-7 text-xs gap-1" onClick={onSendEmail}>
              <Mail className="w-3.5 h-3.5" />
              E-posta
            </Button>
          )}
          <Button variant="ghost" size="sm" className="h-7 text-xs gap-1" onClick={handlePrint}>
            <Printer className="w-3.5 h-3.5" />
            PDF
          </Button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-6 py-5 print:!overflow-visible print:!h-auto">
        {/* Auto-generated report sections */}
        {sections.map((section, i) => (
          <div key={i}>
            <MarkdownContent>{section.heading}</MarkdownContent>

            {section.charts.length > 0 && (
              <div className="mt-3 mb-4 space-y-4">
                {section.charts.map((chart, j) => (
                  <div key={j} className="rounded-lg border border-border bg-card p-4">
                    <p className="text-xs font-medium text-muted-foreground mb-3 uppercase tracking-wide">
                      {chartTitle(chart)}
                    </p>
                    <ChartRenderer chart={chart} printWidth={printWidth} />
                  </div>
                ))}
              </div>
            )}

            {section.body && <MarkdownContent>{section.body}</MarkdownContent>}
          </div>
        ))}

        {/* PM Özel Analizleri */}
        {pmSections.length > 0 && (
          <div className="mt-8 pt-6 border-t border-border">
            <h2 className="text-base font-semibold text-foreground mb-5">PM Özel Analizleri</h2>
            <div className="space-y-5">
              {pmSections.map((section, i) => (
                <div key={i} className="rounded-xl border border-border bg-card/50 overflow-hidden">
                  {section.prompt && (
                    <div className="px-4 py-2.5 border-b border-border/60 bg-muted/30">
                      <p className="text-xs text-muted-foreground font-medium">Soru</p>
                      <p className="text-sm text-foreground mt-0.5">{section.prompt}</p>
                    </div>
                  )}

                  <div className="px-4 py-3">
                    <MarkdownContent>{section.answer}</MarkdownContent>
                  </div>

                  {section.charts.length > 0 && (
                    <div className="px-4 pb-4 pt-1 border-t border-border/50 space-y-4">
                      {section.charts.map((chart, j) => (
                        <div key={j} className="rounded-lg border border-border bg-card p-4">
                          {chart.title && (
                            <p className="text-xs font-medium text-muted-foreground mb-3 uppercase tracking-wide">
                              {chart.title}
                            </p>
                          )}
                          <ChartRenderer chart={chart} printWidth={printWidth} />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
