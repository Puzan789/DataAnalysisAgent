import { useState, useCallback, useRef } from 'react'
import { v4 as uuidv4 } from 'uuid'
import { streamChat, fetchThreads, fetchMessages, removeThread } from '@/lib/api'
import type { Message, Thread } from '@/types'

export function useChat(userId: string | null, token: string | null) {
  const [threads, setThreads] = useState<Thread[]>([])
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const abortRef = useRef(false)

  const loadThreads = useCallback(async () => {
    if (!userId) return
    try {
      const data = await fetchThreads(userId, token)
      setThreads(data)
    } catch {
      // no threads yet
    }
  }, [userId, token])

  const loadMessages = useCallback(async (threadId: string) => {
    if (!userId) return
    try {
      const data = await fetchMessages(threadId, userId, token)
      setMessages(
        data.map((m) => ({
          id: uuidv4(),
          role: m.role as 'user' | 'assistant',
          content: m.content || m.message || '',
          timestamp: new Date(),
        }))
      )
    } catch {
      setMessages([])
    }
  }, [userId, token])

  const selectThread = useCallback(
    (threadId: string) => {
      setActiveThreadId(threadId)
      loadMessages(threadId)
    },
    [loadMessages]
  )

  const newChat = useCallback(() => {
    const id = uuidv4()
    setActiveThreadId(id)
    setMessages([])
    return id
  }, [])

  const deleteThread = useCallback(
    async (threadId: string) => {
      if (!userId) return
      try {
        await removeThread(threadId, userId, token)
        setThreads((prev) => prev.filter((t) => (t.thread_id || t.id) !== threadId))
        if (activeThreadId === threadId) {
          setActiveThreadId(null)
          setMessages([])
        }
      } catch (err) {
        console.error('Delete failed:', err)
      }
    },
    [activeThreadId, userId, token]
  )

  const sendMessage = useCallback(
    async (query: string) => {
      if (!query.trim() || isStreaming || !userId) return

      let threadId = activeThreadId
      if (!threadId) {
        threadId = uuidv4()
        setActiveThreadId(threadId)
      }

      setIsStreaming(true)
      abortRef.current = false

      const userMsg: Message = {
        id: uuidv4(),
        role: 'user',
        content: query,
        timestamp: new Date(),
      }

      const assistantMsg: Message = {
        id: uuidv4(),
        role: 'assistant',
        content: '',
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, userMsg, assistantMsg])

      await streamChat(query, threadId, userId, {
        onToken: (token) => {
          if (abortRef.current) return
          setMessages((prev) => {
            const updated = [...prev]
            const last = updated[updated.length - 1]
            if (last?.role === 'assistant') {
              updated[updated.length - 1] = {
                ...last,
                content: last.content + token,
              }
            }
            return updated
          })
        },
        onIds: (ids) => {
          console.log('Retrieved IDs:', ids)
        },
        onDone: () => {
          setIsStreaming(false)
          loadThreads()
        },
        onError: (err) => {
          console.error('Stream error:', err)
          setMessages((prev) => {
            const updated = [...prev]
            const last = updated[updated.length - 1]
            if (last?.role === 'assistant' && !last.content) {
              updated[updated.length - 1] = {
                ...last,
                content: 'Something went wrong. Please try again.',
              }
            }
            return updated
          })
          setIsStreaming(false)
        },
      }, token)
    },
    [activeThreadId, isStreaming, loadThreads, token, userId]
  )

  return {
    threads,
    activeThreadId,
    messages,
    isStreaming,
    loadThreads,
    selectThread,
    newChat,
    deleteThread,
    sendMessage,
  }
}
