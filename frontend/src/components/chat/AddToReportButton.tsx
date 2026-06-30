import { useState } from 'react'
import { BookmarkPlus, Check, Loader2 } from 'lucide-react'

interface Props {
  onAddToReport: () => Promise<void>
}

export function AddToReportButton({ onAddToReport }: Props) {
  const [state, setState] = useState<'idle' | 'loading' | 'done'>('idle')

  const handle = async () => {
    setState('loading')
    await onAddToReport()
    setState('done')
    setTimeout(() => setState('idle'), 2000)
  }

  return (
    <div className="flex items-center gap-1 mt-2">
      <button
        disabled={state !== 'idle'}
        onClick={handle}
        className="inline-flex items-center gap-1.5 h-7 px-2.5 text-xs rounded-md border border-blue-500/30 text-blue-400 bg-transparent hover:bg-blue-500/10 hover:text-blue-300 disabled:opacity-50 disabled:pointer-events-none transition-colors"
      >
        {state === 'loading' && <Loader2 className="w-3 h-3 animate-spin" />}
        {state === 'done' && <Check className="w-3 h-3" />}
        {state === 'idle' && <BookmarkPlus className="w-3 h-3" />}
        {state === 'done' ? 'Eklendi' : 'Rapora Ekle'}
      </button>
    </div>
  )
}
