import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { api } from "@/lib/api"
import type { UserAdmin } from "@/types"

export function AdminUsers() {
  const [users, setUsers] = useState<UserAdmin[]>([])
  const [search, setSearch] = useState("")
  const navigate = useNavigate()

  const loadUsers = async () => {
    const params = new URLSearchParams()
    if (search) params.set("search", search)
    const data = await api.get<UserAdmin[]>(`/admin/users?${params}`)
    setUsers(data)
  }

  useEffect(() => {
    loadUsers()
  }, [])

  const toggleActive = async (userId: string) => {
    await api.patch(`/admin/users/${userId}/toggle-active`)
    loadUsers()
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Users</h1>
        <Input
          placeholder="Search users..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs"
        />
      </div>
      <Card>
        <CardContent className="p-0">
          <table className="w-full">
            <thead>
              <tr className="border-b text-sm text-muted-foreground">
                <th className="text-left p-4 font-medium">Name</th>
                <th className="text-left p-4 font-medium">Email</th>
                <th className="text-left p-4 font-medium">Role</th>
                <th className="text-left p-4 font-medium">Status</th>
                <th className="text-left p-4 font-medium">Conversations</th>
                <th className="text-left p-4 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="border-b last:border-0">
                  <td className="p-4">{user.full_name}</td>
                  <td className="p-4 text-muted-foreground">{user.email}</td>
                  <td className="p-4">
                    <Badge variant={user.role === "admin" ? "default" : "secondary"}>
                      {user.role}
                    </Badge>
                  </td>
                  <td className="p-4">
                    <Badge variant={user.is_active ? "success" : "destructive"}>
                      {user.is_active ? "Active" : "Inactive"}
                    </Badge>
                  </td>
                  <td className="p-4">{user.conversation_count}</td>
                  <td className="p-4">
                    <Button variant="outline" size="sm" onClick={() => toggleActive(user.id)}>
                      {user.is_active ? "Deactivate" : "Activate"}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  )
}
