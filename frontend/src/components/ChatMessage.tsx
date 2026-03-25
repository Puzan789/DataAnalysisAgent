import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Bot, User, Copy, Check, Pencil, ChevronDown, ChevronRight, Database, Brain, Route, Zap, BarChart3 } from 'lucide-react'
import type { Message, Step, ChartResult } from '@/types'
import VegaChart from './VegaChart'

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-zinc-500 animate-pulse-dot"
          style={{ animationDelay: `${i * 0.16}s` }}
        />
      ))}
    </div>
  )
}

const stepIcons: Record<string, typeof Brain> = {
  routing: Route,
  routed: Route,
  sql_agent: Database,
  general_agent: Brain,
  sql_generated: Database,
  sql_executed: Zap,
  sql_error: Zap,
  validating: Brain,
  generating: Brain,
}

function StepIndicator({ step }: { step: Step }) {
  const [expanded, setExpanded] = useState(false)
  const Icon = stepIcons[step.type] || Brain
  const hasDetail = !!step.detail

  return (
    <div className="flex flex-col">
      <button
        onClick={() => hasDetail && setExpanded(!expanded)}
        className={`flex items-center gap-2 text-xs text-zinc-400 py-0.5 ${hasDetail ? 'cursor-pointer hover:text-zinc-300' : 'cursor-default'}`}
      >
        {hasDetail ? (
          expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />
        ) : (
          <span className="w-[10px]" />
        )}
        <Icon size={12} className="text-brand-light flex-shrink-0" />
        <span>{step.label}</span>
      </button>
      {expanded && step.detail && (
        <pre className="ml-[34px] mt-1 mb-1 text-[11px] text-emerald-400 bg-surface border border-zinc-800 rounded-md px-3 py-2 overflow-x-auto font-mono whitespace-pre-wrap">
          {step.detail}
        </pre>
      )}
    </div>
  )
}

function StepsPanel({ steps }: { steps: Step[] }) {
  const [collapsed, setCollapsed] = useState(false)

  if (steps.length === 0) return null

  return (
    <div className="mb-2 border border-zinc-800 rounded-lg bg-surface/50 overflow-hidden">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center gap-2 w-full px-3 py-1.5 text-xs text-zinc-500 hover:text-zinc-400 transition-colors"
      >
        {collapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
        <span className="font-medium">{steps.length} step{steps.length > 1 ? 's' : ''}</span>
      </button>
      {!collapsed && (
        <div className="px-3 pb-2 space-y-0.5">
          {steps.map((step, i) => (
            <StepIndicator key={i} step={step} />
          ))}
        </div>
      )}
    </div>
  )
}

interface ChatMessageProps {
  message: Message
  onEdit?: (messageId: string, content: string) => void
  isStreaming?: boolean
  chartResult?: ChartResult
  onGenerateChart?: (messageId: string) => void
  onCloseChart?: (messageId: string) => void
}

export default function ChatMessage({ message, onEdit, isStreaming, chartResult, onGenerateChart, onCloseChart }: ChatMessageProps) {
  const isUser = message.role === 'user'
  const [copied, setCopied] = useState(false)
  const [editing, setEditing] = useState(false)
  const [editText, setEditText] = useState(message.content)

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleEditSubmit = () => {
    if (editText.trim() && editText !== message.content) {
      onEdit?.(message.id, editText.trim())
    }
    setEditing(false)
  }

  const handleEditKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleEditSubmit()
    }
    if (e.key === 'Escape') {
      setEditing(false)
      setEditText(message.content)
    }
  }

  return (
    <div className={`group flex gap-3 animate-slide-up ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className={`
          w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5
          ${isUser ? 'bg-blue-600' : 'bg-brand'}
        `}
      >
        {isUser ? <User size={15} className="text-white" /> : <Bot size={15} className="text-white" />}
      </div>

      {/* Content */}
      <div className="max-w-[75%] flex flex-col">
        <div
          className={`
            rounded-2xl px-4 py-3 text-sm leading-relaxed
            ${isUser
              ? 'bg-blue-600 text-white rounded-br-md'
              : 'bg-surface-2 border border-zinc-800 text-zinc-200 rounded-bl-md'
            }
          `}
        >
          {isUser ? (
            editing ? (
              <div className="flex flex-col gap-2">
                <textarea
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  onKeyDown={handleEditKeyDown}
                  className="bg-blue-700/50 text-white rounded-lg px-3 py-2 text-sm resize-none outline-none border border-blue-400/30 focus:border-blue-400/60 min-h-[60px]"
                  rows={2}
                  autoFocus
                />
                <div className="flex gap-2 justify-end">
                  <button
                    onClick={() => { setEditing(false); setEditText(message.content) }}
                    className="text-xs text-blue-200/70 hover:text-white px-2 py-1"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleEditSubmit}
                    className="text-xs bg-white/20 hover:bg-white/30 text-white rounded px-3 py-1"
                  >
                    Send
                  </button>
                </div>
              </div>
            ) : (
              <p className="whitespace-pre-wrap">{message.content}</p>
            )
          ) : (
            <>
              {message.steps && message.steps.length > 0 && (
                <StepsPanel steps={message.steps} />
              )}
              {message.content ? (
                <div className="prose prose-invert prose-sm max-w-none
                  prose-p:my-1.5 prose-p:leading-relaxed
                  prose-headings:text-zinc-100 prose-headings:font-semibold prose-headings:mt-3 prose-headings:mb-1.5
                  prose-h4:text-[15px]
                  prose-strong:text-brand-light prose-strong:font-semibold
                  prose-code:text-emerald-400 prose-code:bg-surface prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded prose-code:text-xs prose-code:font-mono
                  prose-pre:bg-surface prose-pre:border prose-pre:border-zinc-800 prose-pre:rounded-lg prose-pre:my-2
                  prose-ul:my-1.5 prose-ol:my-1.5 prose-li:my-0.5
                  prose-table:my-2
                  prose-th:bg-surface prose-th:px-3 prose-th:py-2 prose-th:text-xs prose-th:font-medium prose-th:text-zinc-400 prose-th:uppercase prose-th:tracking-wider
                  prose-td:px-3 prose-td:py-2 prose-td:border-zinc-800
                  prose-a:text-brand-light prose-a:no-underline hover:prose-a:underline
                ">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                </div>
              ) : (
                <TypingIndicator />
              )}
              {/* Chart rendering */}
              {chartResult && (
                <VegaChart result={chartResult} onClose={() => onCloseChart?.(message.id)} />
              )}
            </>
          )}
        </div>

        {/* Chart generate button - always visible when chart data available */}
        {!editing && !isStreaming && message.content && !isUser && message.chartData && onGenerateChart && !chartResult && (
          <div className="flex mt-2">
            <button
              onClick={() => onGenerateChart(message.id)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand/10 border border-brand/30 text-brand-light hover:bg-brand/20 hover:border-brand/50 transition-colors text-xs font-medium"
              title="Generate chart"
            >
              <BarChart3 size={14} />
              <span>Generate Chart</span>
            </button>
          </div>
        )}

        {/* Action buttons */}
        {!editing && !isStreaming && message.content && (
          <div className={`flex gap-1 mt-1 opacity-0 group-hover:opacity-100 transition-opacity ${isUser ? 'justify-end' : 'justify-start'}`}>
            <button
              onClick={handleCopy}
              className="p-1 rounded hover:bg-zinc-800 text-zinc-500 hover:text-zinc-300 transition-colors"
              title="Copy message"
            >
              {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
            </button>
            {isUser && onEdit && (
              <button
                onClick={() => setEditing(true)}
                className="p-1 rounded hover:bg-zinc-800 text-zinc-500 hover:text-zinc-300 transition-colors"
                title="Edit message"
              >
                <Pencil size={14} />
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
