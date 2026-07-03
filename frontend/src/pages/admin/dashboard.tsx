import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import { Users, MessageSquare, Ticket, BookOpen } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { api } from "@/lib/api"
import type { DashboardStats } from "@/types"

export function AdminDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)

  useEffect(() => {
    api.get<DashboardStats>("/admin/dashboard").then(setStats)
  }, [])

  if (!stats) return <p>Loading...</p>

  const cards = [
    { title: "Users", value: stats.total_users, icon: Users, color: "text-blue-500" },
    { title: "Conversations", value: stats.total_conversations, icon: MessageSquare, color: "text-green-500" },
    { title: "Tickets", value: stats.total_tickets, icon: Ticket, color: "text-orange-500" },
    { title: "KB Entries", value: stats.total_kb_entries, icon: BookOpen, color: "text-purple-500" },
  ]

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {cards.map((card, i) => (
          <motion.div
            key={card.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
          >
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">{card.title}</CardTitle>
                <card.icon className={`h-4 w-4 ${card.color}`} />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{card.value}</div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Tickets by Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Object.entries(stats.tickets_by_status).map(([status, count]) => (
                <div key={status} className="flex items-center justify-between">
                  <span className="text-sm capitalize">{status.replace("_", " ")}</span>
                  <span className="font-medium">{count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Users by Role</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Object.entries(stats.users_by_role).map(([role, count]) => (
                <div key={role} className="flex items-center justify-between">
                  <span className="text-sm capitalize">{role}</span>
                  <span className="font-medium">{count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {stats.recent_activity.map((activity) => (
                <div key={activity.id} className="flex items-center justify-between text-sm">
                  <span>
                    <span className="font-medium">{activity.user_name}</span>
                    {" "}{activity.action.replace("_", " ")}{" "}
                    <span className="text-muted-foreground">{activity.resource}</span>
                  </span>
                  <span className="text-muted-foreground text-xs">
                    {new Date(activity.created_at).toLocaleDateString()}
                  </span>
                </div>
              ))}
              {stats.recent_activity.length === 0 && (
                <p className="text-muted-foreground text-sm">No recent activity</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
