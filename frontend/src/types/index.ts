export interface SimulationStatus {
  simulated_date: string
  pipeline_last_run: string | null
  is_running: boolean
}

export interface TrendPoint {
  month: string
  avg_rating: number
  count: number
}

export interface BreakdownPoint {
  group_value: string
  count: number
  avg_rating?: number
}

export interface ReviewExample {
  date: string
  rating: number
  company_size: string
  topics: string[]
  sentiment: string
  summary: string
}

export type ChartData = TrendPoint[] | BreakdownPoint[] | ReviewExample[]

export interface ChartPayload {
  type: 'trend' | 'breakdown' | 'examples'
  group_by?: 'topic' | 'sentiment' | 'company_size' | 'topic_sentiment'
  title?: string
  data: ChartData
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  charts: ChartPayload[]
  timestamp: Date
}

export interface PmSection {
  prompt: string
  answer: string
  charts: ChartPayload[]
}

export interface Report {
  month: string
  content: string
  pm_sections: PmSection[]
}

export interface Task {
  id: string
  prompt: string
  target_date: string
  status: string
  result: string | null
  created_at: string
}

export interface ChartFilters {
  company_size?: string
  topic?: string
  sentiment?: string
  date_from?: string
  date_to?: string
}
