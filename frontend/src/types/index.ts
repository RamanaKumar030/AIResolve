export interface User {
  id: string
  email: string
  full_name: string
  avatar_url: string | null
  role: "student" | "admin"
  is_active: boolean
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface Conversation {
  id: string
  title: string
  is_archived: boolean
  created_at: string
  updated_at: string
  message_count: number
}

export interface Message {
  id: string
  conversation_id: string
  role: "user" | "assistant"
  content: string
  created_at: string
  vote: "upvote" | "downvote" | null
  feedback: string | null
}

export interface ConversationDetail {
  id: string
  title: string
  is_archived: boolean
  created_at: string
  updated_at: string
  messages: Message[]
}

export interface Ticket {
  id: string
  feedback_id: string
  category: string
  priority: string
  sentiment: string
  root_cause: string
  suggested_answer: string
  status: string
  reviewed_by: string | null
  reviewed_at: string | null
  recommendation: string | null
  recommendation_reasoning: string | null
  confidence_score: number | null
  conflicts_with_existing_kb: boolean | null
  created_at: string
  updated_at: string
}

export interface RecommendationReasoning {
  factual_accuracy: string
  addresses_root_cause: string
  completeness: string
  risk_if_wrong: string
  summary: string
}

export interface Feedback {
  id: string
  message_id: string
  user_id: string
  user_name: string
  reason: string
  ticket_id: string | null
  created_at: string
  ticket: Ticket | null
}

export interface KnowledgeBaseEntry {
  id: string
  question: string
  answer: string
  source_ticket_id: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface DashboardStats {
  total_users: number
  total_conversations: number
  total_messages: number
  total_tickets: number
  total_kb_entries: number
  tickets_by_status: Record<string, number>
  users_by_role: Record<string, number>
  recent_activity: ActivityItem[]
}

export interface ActivityItem {
  id: string
  user_name: string
  action: string
  resource: string
  created_at: string
}

export interface UserAdmin {
  id: string
  email: string
  full_name: string
  role: string
  is_active: boolean
  created_at: string
  conversation_count: number
  feedback_count: number
}

export interface StreamEvent {
  type: "chunk" | "done" | "error"
  content?: string
  conversation_id?: string
  message_id?: string
  error?: string
}
