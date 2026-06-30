import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, PieChart, Pie, Cell, Legend,
} from 'recharts'
import type { ChartPayload, TrendPoint, BreakdownPoint, ReviewExample } from '@/types'
import { Badge } from '@/components/ui/badge'

const COLORS = ['#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4', '#ec4899', '#84cc16', '#f97316', '#6366f1']

const SENTIMENT_COLORS: Record<string, string> = {
  pozitif: '#22c55e',
  negatif: '#ef4444',
  nötr: '#f59e0b',
}

interface Props {
  chart: ChartPayload
  compact?: boolean
  printWidth?: number
}

export function ChartRenderer({ chart, compact = false, printWidth }: Props) {
  const w = printWidth ?? '100%'
  const height = compact ? 160 : 200

  if (chart.type === 'trend') {
    const data = chart.data as TrendPoint[]
    return (
      <ResponsiveContainer width={w} height={200}>
        <LineChart data={data} margin={{ top: 4, right: 8, bottom: 4, left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#9ca3af' }} tickFormatter={(v: string) => v.slice(0, 7)} />
          <YAxis domain={[0, 5]} tick={{ fontSize: 11, fill: '#9ca3af' }} />
          <Tooltip
            contentStyle={{ background: '#1c1c1e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: '#e5e7eb' }}
            formatter={(v) => [typeof v === 'number' ? v.toFixed(2) : String(v ?? ''), 'Ort. Puan']}
          />
          <Line type="monotone" dataKey="avg_rating" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3, fill: '#3b82f6' }} />
        </LineChart>
      </ResponsiveContainer>
    )
  }

  if (chart.type === 'breakdown') {
    const data = chart.data as BreakdownPoint[]

    if (chart.group_by === 'sentiment' || chart.group_by === 'topic_sentiment') {
      return (
        <ResponsiveContainer width={w} height={200}>
          <PieChart>
            <Pie
              data={data}
              dataKey="count"
              nameKey="group_value"
              cx="50%"
              cy="50%"
              outerRadius={70}
              label={({ name, percent }) => `${name ?? ''} ${((percent ?? 0) * 100).toFixed(0)}%`}
              labelLine={false}
            >
              {data.map((d, i) => <Cell key={i} fill={SENTIMENT_COLORS[d.group_value] ?? COLORS[i % COLORS.length]} />)}
            </Pie>
            <Legend wrapperStyle={{ fontSize: 11, color: '#9ca3af' }} />
            <Tooltip contentStyle={{ background: '#1c1c1e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }} />
          </PieChart>
        </ResponsiveContainer>
      )
    }

    return (
      <ResponsiveContainer width={w} height={height}>
        <BarChart data={data} margin={{ top: 4, right: 8, bottom: 40, left: -20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
          <XAxis dataKey="group_value" tick={{ fontSize: 10, fill: '#9ca3af' }} angle={-30} textAnchor="end" interval={0} />
          <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} />
          <Tooltip
            contentStyle={{ background: '#1c1c1e', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: '#e5e7eb' }}
            itemStyle={{ color: '#e5e7eb' }}
          />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {data.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    )
  }

  if (chart.type === 'examples') {
    const data = chart.data as ReviewExample[]
    return (
      <div className="flex flex-col gap-2 max-h-64 overflow-y-auto pr-1">
        {data.map((r, i) => (
          <div key={i} className="rounded-lg border border-border bg-card p-3 text-sm">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-muted-foreground text-xs">{r.date}</span>
              <span className="text-yellow-400 font-medium">{'★'.repeat(Math.round(r.rating))}</span>
              <Badge variant="outline" className="text-xs py-0">{r.sentiment}</Badge>
            </div>
            <p className="text-foreground/90 leading-relaxed">{r.summary}</p>
            <div className="flex flex-wrap gap-1 mt-1">
              {r.topics.map((t) => (
                <Badge key={t} variant="secondary" className="text-xs py-0">{t}</Badge>
              ))}
            </div>
          </div>
        ))}
      </div>
    )
  }

  return null
}
