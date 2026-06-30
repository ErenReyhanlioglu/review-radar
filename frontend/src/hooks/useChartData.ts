import { useState, useEffect, useCallback } from 'react'
import { getLatestReport, getReport } from '@/services/api'
import type { Report } from '@/types'

export function useReport(month?: string) {
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async (targetMonth?: string) => {
    setLoading(true)
    setError(null)
    try {
      const data = targetMonth ? await getReport(targetMonth) : await getLatestReport()
      setReport(data)
    } catch {
      setError('Rapor bulunamadı.')
      setReport(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load(month) }, [load, month])

  const clear = useCallback(() => { setReport(null); setError(null) }, [])

  return { report, loading, error, reload: () => load(month), clear }
}
