import { Outlet, Link, useLocation } from "react-router-dom"
import { cn } from "@/lib/utils"
import {
  LayoutDashboard,
  Users,
  MessageSquare,
  Ticket,
  ThumbsUp,
  BookOpen,
  BarChart3,
  ArrowLeft,
} from "lucide-react"
import { Button } from "@/components/ui/button"

const navItems = [
  { href: "/admin", icon: LayoutDashboard, label: "Dashboard", exact: true },
  { href: "/admin/users", icon: Users, label: "Users" },
  { href: "/admin/tickets", icon: Ticket, label: "Tickets" },
  { href: "/admin/feedback", icon: ThumbsUp, label: "Feedback" },
  { href: "/admin/knowledge-base", icon: BookOpen, label: "Knowledge Base" },
  { href: "/admin/analytics", icon: BarChart3, label: "Analytics" },
]

export function AdminLayout() {
  const location = useLocation()

  return (
    <div className="flex h-screen">
      <aside className="w-56 border-r bg-card flex flex-col">
        <div className="p-4 border-b">
          <Link to="/chat" className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground mb-3">
            <ArrowLeft className="h-4 w-4" />
            Back to Chat
          </Link>
          <h2 className="font-semibold">Admin Panel</h2>
        </div>
        <nav className="flex-1 p-2 space-y-1">
          {navItems.map((item) => {
            const isActive = item.exact
              ? location.pathname === item.href
              : location.pathname.startsWith(item.href)
            return (
              <Link
                key={item.href}
                to={item.href}
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "hover:bg-accent"
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </Link>
            )
          })}
        </nav>
      </aside>
      <main className="flex-1 overflow-y-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}
