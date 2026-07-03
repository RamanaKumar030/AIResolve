import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { api } from "@/lib/api"
import type { KnowledgeBaseEntry } from "@/types"

export function AdminKnowledgeBase() {
  const [entries, setEntries] = useState<KnowledgeBaseEntry[]>([])
  const [searchQuery, setSearchQuery] = useState("")
  const [searchResults, setSearchResults] = useState<KnowledgeBaseEntry[]>([])

  useEffect(() => {
    api.get<KnowledgeBaseEntry[]>("/knowledge-base/entries").then(setEntries)
  }, [])

  const handleSearch = async (q: string) => {
    setSearchQuery(q)
    if (!q.trim()) {
      setSearchResults([])
      return
    }
    try {
      const results = await api.get<KnowledgeBaseEntry[]>(
        `/knowledge-base/search?q=${encodeURIComponent(q)}`
      )
      setSearchResults(results)
    } catch {
      setSearchResults([])
    }
  }

  const displayEntries = searchQuery ? searchResults : entries

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Knowledge Base</h1>
        <Input
          placeholder="Search knowledge base..."
          value={searchQuery}
          onChange={(e) => handleSearch(e.target.value)}
          className="max-w-xs"
        />
      </div>

      <div className="space-y-4">
        {displayEntries.map((entry) => (
          <Card key={entry.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">{entry.question}</CardTitle>
                <Badge variant={entry.is_active ? "success" : "secondary"}>
                  {entry.is_active ? "Active" : "Inactive"}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm whitespace-pre-wrap">{entry.answer}</p>
              <p className="text-xs text-muted-foreground mt-2">
                Added {new Date(entry.created_at).toLocaleDateString()}
              </p>
            </CardContent>
          </Card>
        ))}
        {displayEntries.length === 0 && (
          <p className="text-muted-foreground text-center py-8">
            {searchQuery ? "No matching entries found" : "No knowledge base entries yet"}
          </p>
        )}
      </div>
    </div>
  )
}
