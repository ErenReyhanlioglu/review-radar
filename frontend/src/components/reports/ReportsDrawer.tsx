import { useEffect, useState } from 'react'
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerDescription } from '@/components/ui/drawer'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Printer, FileText, Loader2 } from 'lucide-react'
import { listReports } from '@/services/api'
import type { Report } from '@/types'

interface Props {
  open: boolean
  onClose: () => void
  onSelectMonth: (month: string) => void
}

export function ReportsDrawer({ open, onClose, onSelectMonth }: Props) {
  const [reports, setReports] = useState<Report[]>([])
  const [loading, setLoading] = useState(false)
  const [printing, setPrinting] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    listReports().then(setReports).finally(() => setLoading(false))
  }, [open])

  const handlePrint = async (report: Report) => {
    setPrinting(report.month)
    const win = window.open('', '_blank')
    if (!win) return
    const monthLabel = new Date(report.month).toLocaleDateString('tr-TR', { month: 'long', year: 'numeric' })
    win.document.write(`
      <html>
        <head>
          <title>Review Radar — ${monthLabel}</title>
          <style>
            body { font-family: -apple-system, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 24px; color: #111; line-height: 1.6; }
            h1,h2,h3 { color: #111; } ul { padding-left: 1.2em; }
            @media print { body { margin: 0; } }
          </style>
        </head>
        <body>
          <h1>Review Radar — ${monthLabel} Raporu</h1>
          <hr/>
          <pre style="white-space:pre-wrap;font-family:inherit">${report.content}</pre>
          <script>window.onload = () => { window.print(); window.close(); }<\/script>
        </body>
      </html>
    `)
    win.document.close()
    setPrinting(null)
  }

  return (
    <Drawer open={open} onOpenChange={(v) => { if (!v) onClose() }}>
      <DrawerContent className="max-h-[80vh]">
        <DrawerHeader className="border-b border-border pb-3">
          <DrawerTitle className="text-sm font-semibold flex items-center gap-2">
            <FileText className="w-4 h-4" />
            Geçmiş Raporlar
          </DrawerTitle>
          <DrawerDescription className="text-xs">Ayları seçerek raporu görüntüle veya PDF olarak indir.</DrawerDescription>
        </DrawerHeader>

        <ScrollArea className="flex-1 px-4 py-3 max-h-[60vh]">
          {loading && (
            <div className="flex justify-center py-8">
              <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          )}
          {!loading && reports.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-8">Henüz rapor yok.</p>
          )}
          <div className="space-y-2">
            {reports.map((r) => {
              const label = new Date(r.month).toLocaleDateString('tr-TR', { month: 'long', year: 'numeric' })
              return (
                <div
                  key={r.month}
                  className="flex items-center justify-between rounded-lg border border-border bg-card px-4 py-3 hover:bg-accent/30 transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <FileText className="w-4 h-4 text-muted-foreground" />
                    <div>
                      <p className="text-sm font-medium text-foreground">{label}</p>
                      <p className="text-xs text-muted-foreground">{r.month}</p>
                    </div>
                    <Badge variant="secondary" className="text-xs">Mevcut</Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-7 text-xs"
                      onClick={() => { onSelectMonth(r.month); onClose() }}
                    >
                      Görüntüle
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-7 text-xs gap-1"
                      disabled={printing === r.month}
                      onClick={() => handlePrint(r)}
                    >
                      {printing === r.month
                        ? <Loader2 className="w-3 h-3 animate-spin" />
                        : <Printer className="w-3 h-3" />}
                      PDF
                    </Button>
                  </div>
                </div>
              )
            })}
          </div>
        </ScrollArea>
      </DrawerContent>
    </Drawer>
  )
}
