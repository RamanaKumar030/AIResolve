import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { ThemeProvider } from "@/providers/theme-provider"
import { AuthProvider, useAuth } from "@/providers/auth-provider"
import { ErrorBoundary } from "@/components/error-boundary"
import { Sidebar } from "@/components/layout/sidebar"
import { LoginPage } from "@/pages/login"
import { RegisterPage } from "@/pages/register"
import { ChatPage } from "@/pages/chat-page"
import { AdminLayout } from "@/pages/admin/admin-layout"
import { AdminDashboard } from "@/pages/admin/dashboard"
import { AdminUsers } from "@/pages/admin/users"
import { AdminTickets } from "@/pages/admin/tickets"
import { AdminFeedback } from "@/pages/admin/feedback"
import { AdminKnowledgeBase } from "@/pages/admin/knowledge-base"
import { AdminAnalytics } from "@/pages/admin/analytics"

const queryClient = new QueryClient()

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="flex items-center justify-center min-h-screen">Loading...</div>
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="flex items-center justify-center min-h-screen">Loading...</div>
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== "admin") return <Navigate to="/chat" replace />
  return <>{children}</>
}

function AppLayout() {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <ChatPage />
    </div>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme="system" storageKey="airesolve-theme">
        <ErrorBoundary>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route
                path="/chat"
                element={
                  <ProtectedRoute>
                    <AppLayout />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/chat/:conversationId"
                element={
                  <ProtectedRoute>
                    <AppLayout />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin"
                element={
                  <AdminRoute>
                    <AdminLayout />
                  </AdminRoute>
                }
              >
                <Route index element={<AdminDashboard />} />
                <Route path="users" element={<AdminUsers />} />
                <Route path="tickets" element={<AdminTickets />} />
                <Route path="feedback" element={<AdminFeedback />} />
                <Route path="knowledge-base" element={<AdminKnowledgeBase />} />
                <Route path="analytics" element={<AdminAnalytics />} />
              </Route>
              <Route path="/" element={<Navigate to="/chat" replace />} />
              <Route path="*" element={<Navigate to="/chat" replace />} />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
        </ErrorBoundary>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

export default App
