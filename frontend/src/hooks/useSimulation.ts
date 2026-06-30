import { useState, useEffect, useCallback, useRef } from 'react'
import { getSimulationStatus, advanceSimulation, resetSimulation } from '@/services/api'
import type { SimulationStatus } from '@/types'

export function useSimulation(onAdvanceComplete?: () => void) {
  const [status, setStatus] = useState<SimulationStatus | null>(null)
  const [advancing, setAdvancing] = useState(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchStatus = useCallback(async () => {
    try {
      const s = await getSimulationStatus()
      setStatus(s)
      return s
    } catch {
      return null
    }
  }, [])

  useEffect(() => { fetchStatus() }, [fetchStatus])

  const stopPolling = useCallback(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
  }, [])

  const startPolling = useCallback(() => {
    stopPolling()
    pollRef.current = setInterval(async () => {
      const s = await fetchStatus()
      if (s && !s.is_running) {
        stopPolling()
        setAdvancing(false)
        onAdvanceComplete?.()
      }
    }, 3000)
  }, [fetchStatus, stopPolling, onAdvanceComplete])

  const advance = useCallback(async () => {
    if (advancing) return
    setAdvancing(true)
    try {
      await advanceSimulation()
      startPolling()
    } catch {
      setAdvancing(false)
    }
  }, [advancing, startPolling])

  const reset = useCallback(async () => {
    await resetSimulation()
    await fetchStatus()
  }, [fetchStatus])

  useEffect(() => () => stopPolling(), [stopPolling])

  return { status, advancing, advance, reset, refresh: fetchStatus }
}
