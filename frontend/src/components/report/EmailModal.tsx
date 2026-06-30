import { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Checkbox } from '@/components/ui/checkbox'
import { Button } from '@/components/ui/button'
import { Send, Loader2, Check } from 'lucide-react'
import { sendReportEmail } from '@/services/api'

const RECIPIENTS = [
  { id: 'pm', email: 'merenr.oglu@gmail.com', label: 'PM (Eren Reyhanlioglu)' },
  { id: 'emp1', email: 'mehmeterenreyhanlioglu@gmail.com', label: 'Çalışan 1' },
  { id: 'emp2', email: 'erenm158@gmail.com', label: 'Çalışan 2' },
]

interface Props {
  open: boolean
  onClose: () => void
  month: string
}

export function EmailModal({ open, onClose, month }: Props) {
  const [selected, setSelected] = useState<Set<string>>(new Set(['pm']))
  const [status, setStatus] = useState<'idle' | 'loading' | 'done' | 'error'>('idle')

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleSend = async () => {
    const selected_recipients = RECIPIENTS.filter((r) => selected.has(r.id))
    const recipients = selected_recipients.map((r) => r.email)
    if (!recipients.length) return
    const pm_email = RECIPIENTS.find((r) => r.id === 'pm')?.email
    setStatus('loading')
    try {
      await sendReportEmail(month, recipients, pm_email)
      setStatus('done')
      setTimeout(() => { setStatus('idle'); onClose() }, 1500)
    } catch {
      setStatus('error')
      setTimeout(() => setStatus('idle'), 2000)
    }
  }

  const monthLabel = new Date(month).toLocaleDateString('tr-TR', { month: 'long', year: 'numeric' })

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) onClose() }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-sm font-semibold">Email Gönder</DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            {monthLabel} raporunu seçili kişilere gönder
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-3 py-3">
          {RECIPIENTS.map((r) => (
            <label
              key={r.id}
              className="flex items-center gap-3 cursor-pointer rounded-lg border border-border px-4 py-3 hover:bg-accent/30 transition-colors"
            >
              <Checkbox
                checked={selected.has(r.id)}
                onCheckedChange={() => toggle(r.id)}
              />
              <div>
                <p className="text-sm font-medium text-foreground">{r.label}</p>
                <p className="text-xs text-muted-foreground">{r.email}</p>
              </div>
            </label>
          ))}
        </div>

        <DialogFooter className="gap-2">
          <Button variant="ghost" size="sm" className="text-xs" onClick={onClose}>İptal</Button>
          <Button
            size="sm"
            className="text-xs gap-1.5 bg-blue-600 hover:bg-blue-700"
            disabled={!selected.size || status === 'loading' || status === 'done'}
            onClick={handleSend}
          >
            {status === 'loading' && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            {status === 'done' && <Check className="w-3.5 h-3.5" />}
            {status === 'idle' && <Send className="w-3.5 h-3.5" />}
            {status === 'done' ? 'Gönderildi!' : status === 'error' ? 'Hata!' : 'Gönder'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
