import { useState } from "react"
import ReactMarkdown from "react-markdown"
import { ThumbsUp, ThumbsDown, Copy, Check, User, Bot } from "lucide-react"
import { motion } from "framer-motion"
import { Button } from "@/components/ui/button"
import { FeedbackModal } from "@/components/feedback/feedback-modal"
import { api } from "@/lib/api"
import { cn } from "@/lib/utils"
import type { Message } from "@/types"

interface ChatMessageProps {
  message: Message
  showActions?: boolean
  onVoteUpdate?: (messageId: string, voteType: string | null) => void
}

export function ChatMessage({ message, showActions = true, onVoteUpdate }: ChatMessageProps) {
  const [copied, setCopied] = useState(false)
  const [feedbackOpen, setFeedbackOpen] = useState(false)
  const [voteState, setVoteState] = useState<string | null>(message.vote)

  const isUser = message.role === "user"

  const handleCopy = async () => {
    await navigator.clipboard.writeText(message.content)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleVote = async (voteType: "upvote" | "downvote") => {
    try {
      const result = await api.post<{ vote_type: string | null }>(
        `/feedback/vote/${message.id}`,
        { vote_type: voteType }
      )
      setVoteState(result.vote_type)
      onVoteUpdate?.(message.id, result.vote_type)

      if (voteType === "downvote" && result.vote_type === "downvote") {
        setFeedbackOpen(true)
      }
    } catch (err) {
      console.error("Vote failed", err)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={cn("flex gap-3 py-4", isUser && "flex-row-reverse")}
    >
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-primary text-primary-foreground" : "bg-muted"
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      <div className={cn("flex flex-col max-w-[80%]", isUser ? "items-end" : "items-start")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-muted border"
          )}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose dark:prose-invert max-w-none">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>

        {!isUser && showActions && (
          <div className="flex items-center gap-1 mt-1.5">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => handleVote("upvote")}
            >
              <ThumbsUp
                className={cn(
                  "h-3.5 w-3.5",
                  voteState === "upvote" && "fill-current text-primary"
                )}
              />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => handleVote("downvote")}
            >
              <ThumbsDown
                className={cn(
                  "h-3.5 w-3.5",
                  voteState === "downvote" && "fill-current text-destructive"
                )}
              />
            </Button>
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleCopy}>
              {copied ? (
                <Check className="h-3.5 w-3.5 text-green-500" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
            </Button>
          </div>
        )}
      </div>

      <FeedbackModal
        open={feedbackOpen}
        onOpenChange={setFeedbackOpen}
        messageId={message.id}
      />
    </motion.div>
  )
}
