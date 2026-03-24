import { useState, useEffect, useRef } from 'react'
import { Menu } from 'lucide-react'
import Sidebar, { type Page } from '@/components/Sidebar'
import ChatMessage from '@/components/ChatMessage'
import ChatInput from '@/components/ChatInput'
import EmptyState from '@/components/EmptyState'
import Dashboard from '@/components/Dashboard'
import AuthForm from '@/components/AuthForm'
import { useChat } from '@/hooks/useChat'
import { useAuth } from '@/hooks/useAuth'

export default function App() {
  const auth = useAuth()
  const {
    threads,
    activeThreadId,
    messages,
    isStreaming,
    loadThreads,
    selectThread,
    newChat,
    deleteThread,
    sendMessage,
  } = useChat(auth.user?.id || null, auth.token || null)

  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [activePage, setActivePage] = useState<Page>('chat')
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (auth.user) {
      loadThreads()
    }
  }, [auth.user, loadThreads])

  useEffect(() => {
    const el = scrollRef.current
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
    }
  }, [messages])

  const handleSend = (query: string) => {
    if (!activeThreadId) newChat()
    sendMessage(query)
  }

  const handleSelectThread = (id: string) => {
    selectThread(id)
    setActivePage('chat')
  }

  const handleNewChat = () => {
    newChat()
    setActivePage('chat')
  }

  const headerTitle = activePage === 'dashboard'
    ? 'Database Explorer'
    : activeThreadId
      ? 'Conversation'
      : 'Data Agent'

  if (!auth.user) {
    return <AuthForm onLogin={auth.login} onSignup={auth.signup} />
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        threads={threads}
        activeThreadId={activeThreadId}
        activePage={activePage}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onNewChat={handleNewChat}
        onSelectThread={handleSelectThread}
        onDeleteThread={deleteThread}
        onChangePage={setActivePage}
      />

      <main className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="flex items-center justify-between px-4 py-3 border-b border-zinc-800 bg-surface-1/50 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-1.5 rounded-md hover:bg-surface-2 text-zinc-400"
            >
              <Menu size={18} />
            </button>
            <h1 className="text-sm font-medium text-zinc-300">{headerTitle}</h1>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-zinc-500">{auth.user.email}</span>
            <button
              onClick={auth.logout}
              className="text-xs text-zinc-400 hover:text-brand-light"
            >
              Logout
            </button>
          </div>
          {activePage === 'chat' && isStreaming && (
            <div className="flex items-center gap-2 text-xs text-brand-light">
              <div className="w-1.5 h-1.5 rounded-full bg-brand animate-pulse" />
              Generating...
            </div>
          )}
        </header>

        {/* Content */}
        {activePage === 'dashboard' ? (
          <Dashboard />
        ) : messages.length === 0 ? (
          <EmptyState onSend={handleSend} />
        ) : (
          <div ref={scrollRef} className="flex-1 overflow-y-auto">
            <div className="max-w-3xl mx-auto px-4 py-6 space-y-5">
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}
            </div>
          </div>
        )}

        {/* Input - only in chat mode */}
        {activePage === 'chat' && (
          <ChatInput onSend={handleSend} disabled={isStreaming} />
        )}
      </main>
    </div>
  )
}
