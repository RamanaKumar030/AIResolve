import { useState, useRef, useEffect } from "react"
import { Send, Loader2, Square } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"

interface ChatInputProps {
  onSend: (message: string) => Promise<void>
  onStop?: () => void
  loading: boolean
}

export function ChatInput({ onSend, onStop, loading }: ChatInputProps) {
  const [input, setInput] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 200) + "px"
    }
  }, [input])

  const handleSend = async () => {
    const trimmed = input.trim()
    if (!trimmed || loading) return
    setInput("")
    await onSend(trimmed)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="border-t bg-background p-4">
      <div className="max-w-4xl mx-auto flex gap-2 items-end">
        <Textarea
          ref={textareaRef}
          placeholder="Ask a question..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          className="min-h-[44px] max-h-[200px] resize-none"
          rows={1}
          disabled={loading}
        />
        {loading && onStop ? (
          <Button
            onClick={onStop}
            size="icon"
            variant="destructive"
            className="h-[44px] w-[44px] shrink-0"
          >
            <Square className="h-4 w-4" />
          </Button>
        ) : (
          <Button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            size="icon"
            className="h-[44px] w-[44px] shrink-0"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        )}
      </div>
    </div>
  )
}
