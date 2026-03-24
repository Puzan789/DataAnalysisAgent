import { useState, useRef, useEffect, type KeyboardEvent } from 'react'
import { Send } from 'lucide-react'

interface ChatInputProps {
  onSend: (message: string) => void
  disabled: boolean
}

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = `${Math.min(el.scrollHeight, 160)}px`
    }
  }, [value])

  const handleSend = () => {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue('')
  }

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="border-t border-zinc-800 bg-surface p-4">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-end gap-2 bg-surface-1 border border-zinc-800 rounded-xl p-1.5 focus-within:border-brand/50 transition-colors">
          <textarea
            ref={textareaRef}
            rows={1}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder="Ask about your data..."
            className="
              flex-1 bg-transparent text-sm text-zinc-100
              placeholder:text-zinc-600
              resize-none outline-none
              px-3 py-2
              max-h-40
              disabled:opacity-50
            "
          />
          <button
            onClick={handleSend}
            disabled={!value.trim() || disabled}
            className="
              p-2 rounded-lg bg-brand text-white
              hover:bg-brand-light
              disabled:opacity-30 disabled:cursor-not-allowed
              transition-all duration-150
              flex-shrink-0
            "
          >
            <Send size={16} />
          </button>
        </div>
        <p className="text-[11px] text-zinc-600 text-center mt-2">
          Responses are generated from your database via SQL queries
        </p>
      </div>
    </div>
  )
}
