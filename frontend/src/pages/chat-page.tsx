import { useEffect } from "react"
import { useParams } from "react-router-dom"
import { ChatArea } from "@/components/chat/chat-area"
import { ChatInput } from "@/components/chat/chat-input"
import { useChatStore } from "@/hooks/use-chat-store"

export function ChatPage() {
  const { conversationId } = useParams()
  const {
    messages,
    streaming,
    streamContent,
    sendMessage,
    stopStreaming,
    setCurrentConversation,
    loadConversations,
  } = useChatStore()

  useEffect(() => {
    loadConversations()
  }, [])

  useEffect(() => {
    setCurrentConversation(conversationId || null)
  }, [conversationId])

  const handleSend = async (content: string) => {
    await sendMessage(content)
  }

  return (
    <div className="flex-1 flex flex-col h-screen">
      <ChatArea
        messages={messages}
        streaming={streaming}
        streamContent={streamContent}
      />
      <ChatInput onSend={handleSend} onStop={stopStreaming} loading={streaming} />
    </div>
  )
}
