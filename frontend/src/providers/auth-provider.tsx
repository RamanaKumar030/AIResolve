import { createContext, useContext, useEffect, useState } from "react"
import type { User } from "@/types"
import { supabase } from "@/lib/supabase"
import { api } from "@/lib/api"

interface AuthContextType {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const init = async () => {
      const token = localStorage.getItem("airesolve_token")
      if (token) {
        try {
          const userData = await api.get<User>("/auth/me")
          setUser(userData)
        } catch {
          localStorage.removeItem("airesolve_token")
        }
      }
      setLoading(false)
    }
    init()
  }, [])

  const login = async (email: string, password: string) => {
    const data = await api.post<{ access_token: string; user: User }>("/auth/login", {
      email,
      password,
    })
    localStorage.setItem("airesolve_token", data.access_token)
    setUser(data.user)
  }

  const register = async (email: string, password: string, fullName: string) => {
    const data = await api.post<{ access_token: string; user: User }>("/auth/register", {
      email,
      password,
      full_name: fullName,
    })
    localStorage.setItem("airesolve_token", data.access_token)
    setUser(data.user)
  }

  const logout = async () => {
    localStorage.removeItem("airesolve_token")
    await supabase.auth.signOut()
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
