import { useState, useCallback, useRef } from 'react'
import { requestChart, pollChart } from '@/lib/api'
import type { ChartData, ChartResult } from '@/types'

export function useChart(token: string | null) {
  const [chartResults, setChartResults] = useState<Record<string, ChartResult>>({})
  const pollingRef = useRef<Record<string, ReturnType<typeof setInterval>>>({})

  const generateChart = useCallback(
    async (messageId: string, chartData: ChartData) => {
      try {
        // Set initial loading state
        setChartResults((prev) => ({
          ...prev,
          [messageId]: { status: 'generating' },
        }))

        const queryId = await requestChart(
          chartData.query,
          chartData.sql,
          chartData.data as unknown as Record<string, unknown>,
          token,
        )

        // Poll for results every 1.5s
        const interval = setInterval(async () => {
          try {
            const result = await pollChart(queryId, token)
            setChartResults((prev) => ({ ...prev, [messageId]: result }))

            if (result.status === 'finished' || result.status === 'failed' || result.status === 'stopped') {
              clearInterval(interval)
              delete pollingRef.current[messageId]
            }
          } catch (err) {
            console.error('Chart poll error:', err)
            clearInterval(interval)
            delete pollingRef.current[messageId]
            setChartResults((prev) => ({
              ...prev,
              [messageId]: { status: 'failed', error: 'Polling failed' },
            }))
          }
        }, 1500)

        pollingRef.current[messageId] = interval
      } catch (err) {
        console.error('Chart request error:', err)
        setChartResults((prev) => ({
          ...prev,
          [messageId]: { status: 'failed', error: 'Request failed' },
        }))
      }
    },
    [token],
  )

  const clearChart = useCallback((messageId: string) => {
    if (pollingRef.current[messageId]) {
      clearInterval(pollingRef.current[messageId])
      delete pollingRef.current[messageId]
    }
    setChartResults((prev) => {
      const next = { ...prev }
      delete next[messageId]
      return next
    })
  }, [])

  return { chartResults, generateChart, clearChart }
}
