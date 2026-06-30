import axios from 'axios'
import type { SimulationStatus, ChartPayload, Report, Task, ChartFilters } from '@/types'

const api = axios.create({
  baseURL: 'http://localhost:8001',
  headers: { 'Content-Type': 'application/json' },
})

// ── Simulation ────────────────────────────────────────────────────────────────

export const getSimulationStatus = () =>
  api.get<SimulationStatus>('/simulation/status').then((r) => r.data)

export const advanceSimulation = () =>
  api.post<{ status: string; simulated_date: string }>('/simulation/advance').then((r) => r.data)

export const resetSimulation = () =>
  api.post<{ status: string; simulated_date: string }>('/simulation/reset').then((r) => r.data)

// ── Charts ────────────────────────────────────────────────────────────────────

export const getTrend = (filters?: ChartFilters) =>
  api.get<{ data: { month: string; avg_rating: number; count: number }[] }>('/charts/trend', { params: filters }).then((r) => r.data.data)

export const getTopics = (filters?: ChartFilters) =>
  api.get<{ data: { topic: string; count: number }[] }>('/charts/topics', { params: filters }).then((r) => r.data.data)

export const getSentiment = (filters?: ChartFilters) =>
  api.get<{ data: { month: string; sentiment: string; count: number }[] }>('/charts/sentiment', { params: filters }).then((r) => r.data.data)

export const getCompanySize = (filters?: ChartFilters) =>
  api.get<{ data: { company_size: string; count: number }[] }>('/charts/company-size', { params: filters }).then((r) => r.data.data)

export const getTopicSentiment = (filters?: Pick<ChartFilters, 'date_from' | 'date_to'>) =>
  api.get<{ data: { sentiment: string; count: number }[] }>('/charts/topic-sentiment', { params: filters }).then((r) => r.data.data)

// ── Chat ──────────────────────────────────────────────────────────────────────

export const sendChatMessage = (message: string, simulated_date?: string | null) =>
  api.post<{ answer: string; chart_data: ChartPayload[] }>('/chat', { message, simulated_date }).then((r) => r.data)

// ── Tasks ─────────────────────────────────────────────────────────────────────

export const createTask = (prompt: string, target_date: string) =>
  api.post<Task>('/tasks', { prompt, target_date }).then((r) => r.data)

export const listTasks = () =>
  api.get<Task[]>('/tasks').then((r) => r.data)

// ── Reports ───────────────────────────────────────────────────────────────────

export const listReports = () =>
  api.get<Report[]>('/reports').then((r) => r.data)

export const getLatestReport = () =>
  api.get<Report>('/reports/latest').then((r) => r.data)

export const getReport = (month: string) =>
  api.get<Report>(`/reports/${month}`).then((r) => r.data)

export const appendToReport = (
  month: string,
  body: { prompt: string; answer: string; chart_data: ChartPayload[] }
) => api.post<Report>(`/reports/${month}/append`, body).then((r) => r.data)

export const sendReportEmail = (month: string, recipients: string[], pm_email?: string) =>
  api.post<{ success: boolean }>(`/reports/${month}/send`, { recipients, pm_email }).then((r) => r.data)
