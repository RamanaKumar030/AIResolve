import { useEffect, useState, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { api } from "@/lib/api"
import type { Ticket, RecommendationReasoning } from "@/types"

const priorityColors: Record<string, "warning" | "destructive" | "secondary" | "default"> = {
  low: "secondary",
  medium: "warning",
  high: "destructive",
  critical: "destructive",
}

const statusColors: Record<string, "secondary" | "warning" | "success" | "destructive"> = {
  open: "secondary",
  in_review: "warning",
  approved: "success",
  rejected: "destructive",
}

const recommendationConfig: Record<string, { label: string; variant: "success" | "destructive" | "warning" }> = {
  recommend_approve: { label: "AI Recommends: Approve", variant: "success" },
  recommend_reject: { label: "AI Recommends: Reject", variant: "destructive" },
  recommend_review: { label: "AI Recommends: Review", variant: "warning" },
}

function parseReasoning(raw: string | null | undefined): RecommendationReasoning | null {
  if (!raw) return null
  try {
    return JSON.parse(raw) as RecommendationReasoning
  } catch {
    return null
  }
}

function RecommendationBadge({ ticket }: { ticket: Ticket }) {
  if (!ticket.recommendation) return null
  const config = recommendationConfig[ticket.recommendation]
  if (!config) return null

  return (
    <Badge variant={config.variant}>
      {config.label}
      {ticket.confidence_score != null && ` (${ticket.confidence_score}%)`}
    </Badge>
  )
}

function ReasoningDisplay({ reasoning }: { reasoning: RecommendationReasoning | null }) {
  if (!reasoning) return null
  const sections: [string, string][] = [
    ["Factual Accuracy", reasoning.factual_accuracy],
    ["Addresses Root Cause", reasoning.addresses_root_cause],
    ["Completeness", reasoning.completeness],
    ["Risk If Wrong", reasoning.risk_if_wrong],
  ]
  return (
    <div className="space-y-1.5">
      <Separator />
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">AI Reasoning Breakdown</p>
      {sections.map(([label, value]) =>
        value ? (
          <div key={label}>
            <p className="text-xs font-medium text-muted-foreground">{label}</p>
            <p className="text-xs whitespace-pre-wrap">{value}</p>
          </div>
        ) : null
      )}
    </div>
  )
}

export function AdminTickets() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [filter, setFilter] = useState("")
  const [autoClearEnabled, setAutoClearEnabled] = useState(false)
  const [loadingSetting, setLoadingSetting] = useState(true)

  const loadTickets = useCallback(async () => {
    const params = new URLSearchParams()
    if (filter) params.set("status", filter)
    const data = await api.get<Ticket[]>(`/admin/tickets?${params}`)
    setTickets(data)
  }, [filter])

  const loadAutoClearSetting = useCallback(async () => {
    try {
      const data = await api.get<{ key: string; value: string | null }>("/admin/settings/auto_clear_enabled")
      setAutoClearEnabled(data.value === "true")
    } catch {
      setAutoClearEnabled(false)
    } finally {
      setLoadingSetting(false)
    }
  }, [])

  useEffect(() => {
    loadTickets()
  }, [loadTickets])

  useEffect(() => {
    loadAutoClearSetting()
  }, [loadAutoClearSetting])

  const handleAutoClearToggle = async (enabled: boolean) => {
    setAutoClearEnabled(enabled)
    await api.put("/admin/settings/auto_clear_enabled", { value: enabled ? "true" : "false" })
  }

  const handleReview = async (ticketId: string, status: string) => {
    await api.post(`/admin/tickets/${ticketId}/review`, { status })
    loadTickets()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Tickets</h1>
        <div className="flex items-center gap-2">
          <Select value={filter} onValueChange={(v) => setFilter(v === "all" ? "" : v)}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="open">Open</SelectItem>
              <SelectItem value="in_review">In Review</SelectItem>
              <SelectItem value="approved">Approved</SelectItem>
              <SelectItem value="rejected">Rejected</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <Card>
        <CardContent className="flex items-center gap-4 py-4">
          <Switch
            id="auto-clear"
            checked={autoClearEnabled}
            onCheckedChange={handleAutoClearToggle}
            disabled={loadingSetting}
          />
          <div className="grid gap-0.5">
            <Label htmlFor="auto-clear" className="text-sm font-medium cursor-pointer">
              Auto Clear
            </Label>
            <p className="text-xs text-muted-foreground">
              AI automatically approves/rejects tickets it is highly confident about, without admin review.
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="space-y-4">
        {tickets.map((ticket) => {
          const reasoning = parseReasoning(ticket.recommendation_reasoning)
          return (
            <Card key={ticket.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 flex-wrap">
                    <CardTitle className="text-base">{ticket.category.replace("_", " ")}</CardTitle>
                    <Badge variant={priorityColors[ticket.priority] || "secondary"}>
                      {ticket.priority}
                    </Badge>
                    <Badge variant={statusColors[ticket.status] || "secondary"}>
                      {ticket.status.replace("_", " ")}
                    </Badge>
                    <RecommendationBadge ticket={ticket} />
                  </div>
                  <span className="text-xs text-muted-foreground whitespace-nowrap ml-2">
                    {new Date(ticket.created_at).toLocaleDateString()}
                  </span>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Sentiment</p>
                  <p className="text-sm">{ticket.sentiment}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Root Cause</p>
                  <p className="text-sm">{ticket.root_cause}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Suggested Answer</p>
                  <p className="text-sm whitespace-pre-wrap">{ticket.suggested_answer}</p>
                </div>
                {reasoning && (
                  <ReasoningDisplay reasoning={reasoning} />
                )}
                {ticket.status === "open" && (
                  <div className="flex gap-2 pt-2">
                    <Button size="sm" variant="outline" onClick={() => handleReview(ticket.id, "in_review")}>
                      Start Review
                    </Button>
                    <Button size="sm" className="bg-green-600" onClick={() => handleReview(ticket.id, "approved")}>
                      Approve
                    </Button>
                    <Button size="sm" variant="destructive" onClick={() => handleReview(ticket.id, "rejected")}>
                      Reject
                    </Button>
                  </div>
                )}
                {ticket.status === "in_review" && (
                  <div className="flex gap-2 pt-2">
                    <Button size="sm" className="bg-green-600" onClick={() => handleReview(ticket.id, "approved")}>
                      Approve
                    </Button>
                    <Button size="sm" variant="destructive" onClick={() => handleReview(ticket.id, "rejected")}>
                      Reject
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          )
        })}
        {tickets.length === 0 && (
          <p className="text-muted-foreground text-center py-8">No tickets found</p>
        )}
      </div>
    </div>
  )
}
