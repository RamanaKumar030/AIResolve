import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { api } from "@/lib/api"
import type { Feedback } from "@/types"

export function AdminFeedback() {
  const [feedbacks, setFeedbacks] = useState<Feedback[]>([])

  useEffect(() => {
    api.get<Feedback[]>("/admin/feedback").then(setFeedbacks)
  }, [])

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Feedback</h1>
      <div className="space-y-4">
        {feedbacks.map((fb) => (
          <Card key={fb.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">{fb.user_name}</CardTitle>
                <div className="flex items-center gap-2">
                  {fb.ticket && (
                    <Badge variant={fb.ticket.status === "approved" ? "success" : "secondary"}>
                      {fb.ticket.status}
                    </Badge>
                  )}
                  <span className="text-xs text-muted-foreground">
                    {new Date(fb.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground mb-2">Reason:</p>
              <p className="text-sm">{fb.reason}</p>
              {fb.ticket && (
                <div className="mt-3 pt-3 border-t">
                  <p className="text-sm font-medium">Category: {fb.ticket.category}</p>
                  <p className="text-sm font-medium">Priority: {fb.ticket.priority}</p>
                  <p className="text-sm">Root Cause: {fb.ticket.root_cause}</p>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
        {feedbacks.length === 0 && (
          <p className="text-muted-foreground text-center py-8">No feedback yet</p>
        )}
      </div>
    </div>
  )
}
