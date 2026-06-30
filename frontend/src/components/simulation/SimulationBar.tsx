import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Calendar, ChevronRight, Loader2, Radar, BookOpen, RotateCcw } from 'lucide-react'

interface SimulationBarProps {
  simulatedDate: string | null
  isRunning: boolean
  onNextMonth: () => void
  onReportsClick: () => void
  onReset: () => void
  isViewer?: boolean
}

export function SimulationBar({
  simulatedDate,
  isRunning,
  onNextMonth,
  onReportsClick,
  onReset,
  isViewer = false,
}: SimulationBarProps) {
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    if (!isRunning) { setProgress(0); return }
    setProgress(10)
    const interval = setInterval(() => {
      setProgress((p) => (p >= 90 ? 90 : p + 2))
    }, 800)
    return () => clearInterval(interval)
  }, [isRunning])

  useEffect(() => {
    if (!isRunning && progress > 0) {
      setProgress(100)
      const t = setTimeout(() => setProgress(0), 600)
      return () => clearTimeout(t)
    }
  }, [isRunning, progress])

  const formattedDate = simulatedDate
    ? new Date(simulatedDate + 'T12:00:00').toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' })
    : '—'

  const handleReset = () => {
    if (window.confirm('Tüm raporlar silinecek ve simülasyon başa dönecek. Review verileri korunur. Devam etmek istiyor musun?')) {
      onReset()
    }
  }

  return (
    <nav className="relative w-full bg-background border-b border-border no-print">
      <div className="flex items-center justify-between h-14 px-6">
        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-500/10 text-blue-400">
            <Radar className="w-4 h-4" />
          </div>
          <span className="text-sm font-semibold text-foreground tracking-tight">Review Radar</span>
        </div>

        {/* Simulated Date */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-muted/50 border border-border">
          <Calendar className="w-3.5 h-3.5 text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">{formattedDate}</span>
          {isRunning && (
            <span className="text-xs text-blue-400 animate-pulse ml-1">Pipeline çalışıyor…</span>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={onReportsClick} className="gap-1.5 text-xs h-8">
            <BookOpen className="w-3.5 h-3.5" />
            Raporlar
          </Button>
          {!isViewer && (
            <>
              <Button variant="outline" size="sm" onClick={handleReset} disabled={isRunning} className="gap-1.5 text-xs h-8 text-muted-foreground hover:text-destructive hover:border-destructive">
                <RotateCcw className="w-3.5 h-3.5" />
                Sıfırla
              </Button>
              <Button size="sm" onClick={onNextMonth} disabled={isRunning} className="gap-1.5 text-xs h-8 bg-blue-600 hover:bg-blue-700 text-white border-0">
                {isRunning ? (
                  <><Loader2 className="w-3.5 h-3.5 animate-spin" />Yükleniyor…</>
                ) : (
                  <>Sonraki Ay<ChevronRight className="w-3.5 h-3.5" /></>
                )}
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Progress bar */}
      {progress > 0 && (
        <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-muted overflow-hidden">
          <div
            className="h-full bg-blue-500 transition-all duration-700 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}
    </nav>
  )
}
