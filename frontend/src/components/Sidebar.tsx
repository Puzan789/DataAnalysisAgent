import { MessageSquare, Plus, Trash2, Database, X, LayoutDashboard } from 'lucide-react'
import type { Thread } from '@/types'

export type Page = 'chat' | 'dashboard'

interface SidebarProps {
  threads: Thread[]
  activeThreadId: string | null
  activePage: Page
  isOpen: boolean
  onClose: () => void
  onNewChat: () => void
  onSelectThread: (id: string) => void
  onDeleteThread: (id: string) => void
  onChangePage: (page: Page) => void
}

export default function Sidebar({
  threads,
  activeThreadId,
  activePage,
  isOpen,
  onClose,
  onNewChat,
  onSelectThread,
  onDeleteThread,
  onChangePage,
}: SidebarProps) {
  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`
          fixed lg:static inset-y-0 left-0 z-50
          w-72 bg-surface-1 border-r border-zinc-800
          flex flex-col
          transition-transform duration-200 ease-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-zinc-800">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-brand flex items-center justify-center">
              <Database size={16} className="text-white" />
            </div>
            <span className="text-sm font-semibold tracking-tight">Data Agent</span>
          </div>
          <button
            onClick={onClose}
            className="lg:hidden p-1 rounded-md hover:bg-surface-2 text-zinc-400"
          >
            <X size={18} />
          </button>
        </div>

        {/* Navigation tabs */}
        <div className="p-3 flex gap-1.5">
          <button
            onClick={() => { onChangePage('chat'); onClose() }}
            className={`
              flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all
              ${activePage === 'chat'
                ? 'bg-brand-dim text-brand-light'
                : 'text-zinc-500 hover:bg-surface-2 hover:text-zinc-300'
              }
            `}
          >
            <MessageSquare size={14} />
            Chat
          </button>
          <button
            onClick={() => { onChangePage('dashboard'); onClose() }}
            className={`
              flex-1 flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-xs font-medium transition-all
              ${activePage === 'dashboard'
                ? 'bg-brand-dim text-brand-light'
                : 'text-zinc-500 hover:bg-surface-2 hover:text-zinc-300'
              }
            `}
          >
            <LayoutDashboard size={14} />
            Database
          </button>
        </div>

        {/* Chat section - only show in chat mode */}
        {activePage === 'chat' && (
          <>
            <div className="px-3 pb-2">
              <button
                onClick={() => {
                  onNewChat()
                  onClose()
                }}
                className="
                  w-full flex items-center gap-2 px-3 py-2.5
                  rounded-lg border border-dashed border-zinc-700
                  text-sm text-zinc-300
                  hover:border-brand hover:text-brand-light hover:bg-brand-dim
                  transition-all duration-150
                "
              >
                <Plus size={16} />
                New conversation
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-2 pb-3">
              {threads.length === 0 ? (
                <p className="text-xs text-zinc-600 text-center mt-8">No conversations yet</p>
              ) : (
                <div className="space-y-0.5">
                  {threads.map((thread) => {
                    const id = thread.thread_id || thread.id || ''
                    const isActive = activeThreadId === id
                    return (
                      <div
                        key={id}
                        onClick={() => {
                          onSelectThread(id)
                          onClose()
                        }}
                        className={`
                          group flex items-center gap-2.5 px-3 py-2 rounded-lg cursor-pointer
                          transition-colors duration-100
                          ${isActive
                            ? 'bg-brand-dim text-brand-light'
                            : 'text-zinc-400 hover:bg-surface-2 hover:text-zinc-200'
                          }
                        `}
                      >
                        <MessageSquare size={14} className="flex-shrink-0 opacity-60" />
                        <span className="flex-1 text-sm truncate">
                          {thread.title || thread.first_message || `Chat ${id.slice(0, 8)}`}
                        </span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            onDeleteThread(id)
                          }}
                          className="
                            opacity-0 group-hover:opacity-100
                            p-1 rounded hover:bg-red-500/20 hover:text-red-400
                            transition-all duration-100
                          "
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </>
        )}

        {/* Dashboard hint */}
        {activePage === 'dashboard' && (
          <div className="flex-1 flex items-center justify-center px-6">
            <p className="text-xs text-zinc-600 text-center leading-relaxed">
              Browse your database tables, schemas, columns, and data
            </p>
          </div>
        )}

        {/* Footer */}
        <div className="p-3 border-t border-zinc-800">
          <div className="flex items-center gap-2 px-2">
            <div className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="text-xs text-zinc-500">Connected</span>
          </div>
        </div>
      </aside>
    </>
  )
}
