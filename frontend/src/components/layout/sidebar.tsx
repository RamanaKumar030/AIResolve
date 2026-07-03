import { useState } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { motion, AnimatePresence } from "framer-motion"
import {
  MessageSquare,
  Search,
  Plus,
  Settings,
  LogOut,
  PanelLeftClose,
  PanelLeft,
  GraduationCap,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useAuth } from "@/providers/auth-provider"
import { useChatStore } from "@/hooks/use-chat-store"
import { cn } from "@/lib/utils"

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const {
    conversations,
    setCurrentConversation,
    createConversation,
    searchConversations,
  } = useChatStore()

  const filteredConvs = searchQuery
    ? conversations.filter((c) =>
        c.title.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : conversations

  const handleNewChat = async () => {
    const id = await createConversation()
    if (id) navigate(`/chat/${id}`)
  }

  return (
    <motion.aside
      animate={{ width: collapsed ? 60 : 280 }}
      className="h-screen border-r bg-card flex flex-col overflow-hidden relative"
    >
      <div className="flex items-center justify-between p-3 border-b">
        {!collapsed && (
          <Link to="/" className="flex items-center gap-2 font-semibold">
            <GraduationCap className="h-5 w-5 text-primary" />
            <span>AIResolve</span>
          </Link>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? (
            <PanelLeft className="h-4 w-4" />
          ) : (
            <PanelLeftClose className="h-4 w-4" />
          )}
        </Button>
      </div>

      {!collapsed && (
        <>
          <div className="p-3">
            <Button onClick={handleNewChat} className="w-full gap-2">
              <Plus className="h-4 w-4" />
              New Chat
            </Button>
          </div>

          <div className="px-3 pb-2">
            <div className="relative">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search conversations..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value)
                  searchConversations(e.target.value)
                }}
                className="pl-8 h-9"
              />
            </div>
          </div>

          <nav className="flex-1 overflow-y-auto px-2">
            <AnimatePresence>
              {filteredConvs.map((conv) => (
                <motion.div
                  key={conv.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                >
                  <Button
                    variant="ghost"
                    className={cn(
                      "w-full justify-start text-left mb-1 truncate",
                      location.pathname === `/chat/${conv.id}` &&
                        "bg-accent"
                    )}
                    onClick={() => {
                      setCurrentConversation(conv.id)
                      navigate(`/chat/${conv.id}`)
                    }}
                  >
                    <MessageSquare className="h-4 w-4 mr-2 shrink-0" />
                    <span className="truncate">{conv.title}</span>
                  </Button>
                </motion.div>
              ))}
            </AnimatePresence>
          </nav>
        </>
      )}

      <div className={cn("border-t p-3", collapsed && "flex flex-col items-center gap-2")}>
        {!collapsed && (
          <div className="flex items-center gap-2 mb-2 px-1">
            <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-sm font-medium">
              {user?.full_name?.charAt(0)?.toUpperCase() || "?"}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{user?.full_name}</p>
              <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
            </div>
          </div>
        )}
        {user?.role === "admin" && (
          <Button
            variant="ghost"
            size={collapsed ? "icon" : "sm"}
            className="w-full justify-start mb-1"
            onClick={() => navigate("/admin")}
          >
            <Settings className="h-4 w-4" />
            {!collapsed && <span className="ml-2">Admin</span>}
          </Button>
        )}
        <Button
          variant="ghost"
          size={collapsed ? "icon" : "sm"}
          className="w-full justify-start text-destructive"
          onClick={logout}
        >
          <LogOut className="h-4 w-4" />
          {!collapsed && <span className="ml-2">Logout</span>}
        </Button>
      </div>
    </motion.aside>
  )
}
