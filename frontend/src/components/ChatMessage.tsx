import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Bot, User } from 'lucide-react'
import type { Message } from '@/types'

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

export default function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-3 animate-slide-up ${isUser ? 'flex-row-reverse' : ''}`}>
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
      <div
        className={`
          max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed
          ${isUser
            ? 'bg-blue-600 text-white rounded-br-md'
            : 'bg-surface-2 border border-zinc-800 text-zinc-200 rounded-bl-md'
          }
        `}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : message.content ? (
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
      </div>
    </div>
  )
}
