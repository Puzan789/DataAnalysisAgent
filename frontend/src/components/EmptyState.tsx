import { Database, Sparkles } from 'lucide-react'
import { SUGGESTIONS } from '@/lib/constants'

interface EmptyStateProps {
  onSend: (query: string) => void
}

export default function EmptyState({ onSend }: EmptyStateProps) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center px-6 pb-10">
      {/* Logo */}
      <div className="relative mb-6">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-brand to-blue-600 flex items-center justify-center shadow-lg shadow-brand/20">
          <Database size={28} className="text-white" />
        </div>
        <div className="absolute -top-1 -right-1 w-6 h-6 rounded-full bg-surface-1 border-2 border-surface flex items-center justify-center">
          <Sparkles size={12} className="text-brand-light" />
        </div>
      </div>

      <h2 className="text-xl font-semibold text-zinc-100 mb-2">Data Agent</h2>
      <p className="text-sm text-zinc-500 max-w-md text-center mb-8 leading-relaxed">
        Ask questions about your data in natural language.
        I'll generate SQL queries and return insights from your database.
      </p>

      {/* Suggestion grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-lg">
        {SUGGESTIONS.map((s) => (
          <button
            key={s.text}
            onClick={() => onSend(s.text)}
            className="
              group flex items-center gap-3 px-4 py-3
              bg-surface-1 border border-zinc-800 rounded-xl
              text-left text-sm text-zinc-400
              hover:border-brand/40 hover:bg-brand-dim hover:text-zinc-200
              transition-all duration-150
            "
          >
            <span className="text-lg">{s.icon}</span>
            <span>{s.text}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
