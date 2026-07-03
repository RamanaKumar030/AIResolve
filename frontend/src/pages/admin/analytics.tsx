import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { api } from "@/lib/api"
import type { DashboardStats } from "@/types"

export function AdminAnalytics() {
  const [stats, setStats] = useState<DashboardStats | null>(null)

  useEffect(() => {
    api.get<DashboardStats>("/admin/dashboard").then(setStats)
  }, [])

  if (!stats) return <p>Loading...</p>

  const totalVotes = stats.total_tickets
  const approvalRate = stats.total_tickets > 0
    ? Math.round((stats.tickets_by_status?.approved || 0) / stats.total_tickets * 100)
    : 0

  const metrics = [
    { label: "Total Messages", value: stats.total_messages },
    { label: "Avg Messages per Conversation", value: stats.total_conversations > 0
      ? (stats.total_messages / stats.total_conversations).toFixed(1) : "0" },
    { label: "Ticket Approval Rate", value: `${approvalRate}%` },
    { label: "KB Utilization", value: stats.total_kb_entries > 0 ? `${stats.total_kb_entries} entries` : "No entries" },
  ]

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Analytics</h1>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {metrics.map((metric) => (
          <Card key={metric.label}>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {metric.label}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metric.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>System Overview</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div>
              <p className="text-sm text-muted-foreground mb-1">Users</p>
              <div className="flex items-center gap-2">
                <div
                  className="h-2 rounded-full bg-primary"
                  style={{
                    width: `${stats.total_users > 0
                      ? (stats.users_by_role?.student || 0) / stats.total_users * 100
                      : 0}%`,
                  }}
                />
                <span className="text-xs text-muted-foreground">
                  {stats.users_by_role?.student || 0} students / {stats.users_by_role?.admin || 0} admins
                </span>
              </div>
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-1">Tickets</p>
              <div className="flex items-center gap-2">
                <div
                  className="h-2 rounded-full bg-green-500"
                  style={{
                    width: `${stats.total_tickets > 0
                      ? (stats.tickets_by_status?.approved || 0) / stats.total_tickets * 100
                      : 0}%`,
                  }}
                />
                <span className="text-xs text-muted-foreground">
                  {stats.tickets_by_status?.approved || 0} approved / {stats.total_tickets} total
                </span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
