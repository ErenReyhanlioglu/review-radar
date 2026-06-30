import type { ReactNode } from 'react'

interface Props {
  topBar: ReactNode
  leftPanel: ReactNode
  rightPanel: ReactNode
}

export function DashboardLayout({ topBar, leftPanel, rightPanel }: Props) {
  return (
    <div className="flex flex-col h-screen bg-background overflow-hidden print:block print:h-auto print:overflow-visible">
      <div className="print:hidden">{topBar}</div>
      <div className="flex flex-1 overflow-hidden print:block print:overflow-visible">
        <div className="w-1/2 border-r border-border overflow-hidden flex flex-col print:!w-full print:!border-0 print:!overflow-visible print:!h-auto">
          {leftPanel}
        </div>
        <div className="w-1/2 overflow-hidden flex flex-col print:hidden">
          {rightPanel}
        </div>
      </div>
    </div>
  )
}
