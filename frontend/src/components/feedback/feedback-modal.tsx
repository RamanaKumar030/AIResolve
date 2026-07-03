import { useState } from "react"
import { AlertTriangle } from "lucide-react"
import { motion, AnimatePresence } from "framer-motion"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { api } from "@/lib/api"

interface FeedbackModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  messageId: string
}

export function FeedbackModal({ open, onOpenChange, messageId }: FeedbackModalProps) {
  const [reason, setReason] = useState("")
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState("")

  const handleSubmit = async () => {
    if (!reason.trim()) {
      setError("Please provide a reason for your feedback")
      return
    }

    setSubmitting(true)
    setError("")

    try {
      await api.post("/feedback/submit", {
        message_id: messageId,
        reason: reason.trim(),
      })
      setSubmitted(true)
      setTimeout(() => {
        onOpenChange(false)
        setSubmitted(false)
        setReason("")
      }, 2000)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit feedback")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <AnimatePresence mode="wait">
          {submitted ? (
            <motion.div
              key="success"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center py-8"
            >
              <div className="h-12 w-12 rounded-full bg-green-500/10 flex items-center justify-center mb-4">
                <AlertTriangle className="h-6 w-6 text-green-500" />
              </div>
              <p className="text-lg font-medium">Feedback Submitted</p>
              <p className="text-sm text-muted-foreground mt-1">
                Thank you for helping us improve!
              </p>
            </motion.div>
          ) : (
            <motion.div
              key="form"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <DialogHeader>
                <DialogTitle>Help Us Improve</DialogTitle>
                <DialogDescription>
                  We're sorry this answer wasn't helpful. Please tell us why so we can improve.
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4 py-4">
                <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400 text-sm">
                  <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                  <p>This feedback will be analyzed and used to improve future responses.</p>
                </div>

                <Textarea
                  placeholder="What was wrong with this answer? (e.g., incorrect information, unclear explanation, missing details...)"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  className="min-h-[120px] resize-none"
                />

                {error && (
                  <p className="text-sm text-destructive">{error}</p>
                )}

                <div className="flex justify-end gap-2">
                  <Button
                    variant="outline"
                    onClick={() => onOpenChange(false)}
                    disabled={submitting}
                  >
                    Cancel
                  </Button>
                  <Button onClick={handleSubmit} disabled={submitting}>
                    {submitting ? "Submitting..." : "Submit Feedback"}
                  </Button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </DialogContent>
    </Dialog>
  )
}
