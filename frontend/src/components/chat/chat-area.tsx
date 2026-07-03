import { useEffect, useRef } from "react"
import { motion } from "framer-motion"
import { Loader2 } from "lucide-react"
import { ChatMessage } from "./chat-message"
import type { Message } from "@/types"

interface ChatAreaProps {
  messages: Message[]
  streaming: boolean
  streamContent: string
}

export function ChatArea({ messages, streaming, streamContent }: ChatAreaProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, streamContent])

  if (messages.length === 0 && !streaming) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center max-w-md"
        >
          <h2 className="text-2xl font-bold mb-2">Welcome to AIResolve</h2>
          <p className="text-muted-foreground">
            Ask any question and get instant AI-powered answers. Your conversations
            will be saved and used to improve future responses.
          </p>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto px-4">
      <div className="max-w-4xl mx-auto">
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg}
            showActions={msg.role === "assistant" && !streaming} />
        ))}

        {streaming && streamContent && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex gap-3 py-4"
          >
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
              <Loader2 className="h-4 w-4 animate-spin" />
            </div>
            <div className="rounded-2xl px-4 py-2.5 bg-muted border">
              <div className="prose dark:prose-invert max-w-none">
                <p>{streamContent}</p>
              </div>
            </div>
          </motion.div>
        )}

        {streaming && !streamContent && (
          <div className="flex gap-3 py-4">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
              <Loader2 className="h-4 w-4 animate-spin" />
            </div>
            <div className="flex items-center gap-1 rounded-2xl px-4 py-2.5 bg-muted border">
              <span className="h-2 w-2 rounded-full bg-foreground/30 animate-bounce" />
              <span className="h-2 w-2 rounded-full bg-foreground/30 animate-bounce delay-100" />
              <span className="h-2 w-2 rounded-full bg-foreground/30 animate-bounce delay-200" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  )
}
