import { useEffect, useRef } from 'react'
import embed from 'vega-embed'
import type { ChartResult } from '@/types'
import { Loader2, AlertCircle, X } from 'lucide-react'

interface VegaChartProps {
  result: ChartResult
  onClose: () => void
}

export default function VegaChart({ result, onClose }: VegaChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (result.status === 'finished' && result.chart_schema && containerRef.current) {
      embed(containerRef.current, result.chart_schema as any, {
        actions: { export: true, source: false, compiled: false, editor: false },
        theme: 'dark',
        renderer: 'svg',
      }).catch((err) => console.error('Vega embed error:', err))
    }
  }, [result])

  if (result.status === 'generating' || result.status === 'fetching') {
    return (
      <div className="mt-3 border border-zinc-800 rounded-lg bg-surface/50 p-4">
        <div className="flex items-center gap-2 text-sm text-zinc-400">
          <Loader2 size={16} className="animate-spin" />
          <span>{result.status === 'fetching' ? 'Fetching data...' : 'Generating chart...'}</span>
        </div>
      </div>
    )
  }

  if (result.status === 'failed') {
    return (
      <div className="mt-3 border border-red-900/50 rounded-lg bg-red-950/20 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm text-red-400">
            <AlertCircle size={16} />
            <span>{result.error || 'Chart generation failed'}</span>
          </div>
          <button onClick={onClose} className="p-1 text-zinc-500 hover:text-zinc-300">
            <X size={14} />
          </button>
        </div>
        {result.reasoning && (
          <p className="mt-2 text-xs text-zinc-500">{result.reasoning}</p>
        )}
      </div>
    )
  }

  if (result.status === 'finished') {
    return (
      <div className="mt-3 border border-zinc-800 rounded-lg bg-surface/50 overflow-hidden">
        <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-800">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-zinc-400">
              {result.chart_type?.replace('_', ' ')} chart
            </span>
            {result.reasoning && (
              <span className="text-xs text-zinc-600">— {result.reasoning}</span>
            )}
          </div>
          <button onClick={onClose} className="p-1 text-zinc-500 hover:text-zinc-300">
            <X size={14} />
          </button>
        </div>
        <div ref={containerRef} className="p-3 [&_.vega-embed]:w-full [&_svg]:w-full" />
      </div>
    )
  }

  return null
}
