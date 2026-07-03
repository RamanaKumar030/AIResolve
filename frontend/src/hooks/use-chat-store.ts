import { create } from "zustand"
import type { Conversation, Message, StreamEvent } from "@/types"
import { api } from "@/lib/api"

interface ChatState {
  conversations: Conversation[]
  currentConversationId: string | null
  messages: Message[]
  streaming: boolean
  streamContent: string
  loading: boolean
  abortController: AbortController | null

  loadConversations: () => Promise<void>
  createConversation: () => Promise<string | null>
  setCurrentConversation: (id: string | null) => Promise<void>
  sendMessage: (content: string) => Promise<void>
  stopStreaming: () => void
  searchConversations: (query: string) => Promise<void>
  deleteConversation: (id: string) => Promise<void>
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: [],
  currentConversationId: null,
  messages: [],
  streaming: false,
  streamContent: "",
  loading: false,
  abortController: null,

  loadConversations: async () => {
    try {
      const convs = await api.get<Conversation[]>("/chat/conversations")
      set({ conversations: convs })
    } catch (err) {
      console.error("Failed to load conversations", err)
    }
  },

  createConversation: async () => {
    try {
      const conv = await api.post<Conversation>("/chat/conversations", {
        title: "New Conversation",
      })
      set((state) => ({
        conversations: [conv, ...state.conversations],
        currentConversationId: conv.id,
        messages: [],
      }))
      return conv.id
    } catch (err) {
      console.error("Failed to create conversation", err)
      return null
    }
  },

  setCurrentConversation: async (id: string | null) => {
    const { currentConversationId } = get()
    if (!id) {
      set({ currentConversationId: null, messages: [] })
      return
    }
    if (id === currentConversationId) return
    try {
      const detail = await api.get<{ id: string; messages: Message[] }>(
        `/chat/conversations/${id}`
      )
      set({
        currentConversationId: id,
        messages: detail.messages || [],
      })
    } catch (err) {
      console.error("Failed to load conversation", err)
    }
  },

  sendMessage: async (content: string) => {
    const { currentConversationId, messages } = get()

    const abortController = new AbortController()
    set({ abortController })

    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`,
      conversation_id: currentConversationId || "",
      role: "user",
      content,
      created_at: new Date().toISOString(),
      vote: null,
      feedback: null,
    }

    set((state) => ({
      messages: [...state.messages, tempUserMsg],
      streaming: true,
      streamContent: "",
    }))

    try {
      const response = await fetch(`/api/v1/chat/send`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("airesolve_token")}`,
        },
        body: JSON.stringify({
          conversation_id: currentConversationId,
          content,
        }),
        signal: abortController.signal,
      })

      if (!response.ok) throw new Error("Failed to send message")

      const reader = response.body?.getReader()
      if (!reader) throw new Error("No response stream")

      const decoder = new TextDecoder()
      let fullContent = ""
      let newConvId = currentConversationId || ""
      let newMsgId = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split("\n").filter(Boolean)

        for (const line of lines) {
          try {
            const event: StreamEvent = JSON.parse(line)
            if (event.type === "chunk" && event.content) {
              fullContent += event.content
              set({ streamContent: fullContent })
            } else if (event.type === "done") {
              newConvId = event.conversation_id || newConvId
              newMsgId = event.message_id || ""

              const assistantMsg: Message = {
                id: newMsgId,
                conversation_id: newConvId,
                role: "assistant",
                content: event.content || fullContent,
                created_at: new Date().toISOString(),
                vote: null,
                feedback: null,
              }

              set((state) => ({
                currentConversationId: newConvId,
                messages: [...state.messages, assistantMsg],
                streaming: false,
                streamContent: "",
              }))

              await get().loadConversations()
            } else if (event.type === "error") {
              throw new Error(event.error || "Stream error")
            }
          } catch (e) {
            console.error("Parse error:", e)
          }
        }
      }
    } catch (err) {
      console.error("Send message error:", err)
    } finally {
      set({ streaming: false, streamContent: "", abortController: null })
    }
  },

  stopStreaming: () => {
    const { abortController } = get()
    if (abortController) {
      abortController.abort()
      set({ abortController: null })
    }
  },

  searchConversations: async (query: string) => {
    if (!query.trim()) {
      await get().loadConversations()
      return
    }
    try {
      const convs = await api.get<Conversation[]>(
        `/chat/search?q=${encodeURIComponent(query)}`
      )
      set({ conversations: convs })
    } catch (err) {
      console.error("Search failed", err)
    }
  },

  deleteConversation: async (id: string) => {
    try {
      await api.delete(`/chat/conversations/${id}`)
      set((state) => ({
        conversations: state.conversations.filter((c) => c.id !== id),
        currentConversationId:
          state.currentConversationId === id ? null : state.currentConversationId,
        messages:
          state.currentConversationId === id ? [] : state.messages,
      }))
    } catch (err) {
      console.error("Delete failed", err)
    }
  },
}))
