# AIResolve

AI-powered student support system with intelligent feedback analysis and RAG-based knowledge base.

## Architecture

```
AIResolve/
├── backend/          # FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── api/v1/   # API routes
│   │   ├── core/     # Config, security, logging
│   │   ├── db/models/  # SQLAlchemy models
│   │   ├── repositories/  # Data access layer
│   │   ├── schemas/   # Pydantic schemas
│   │   └── services/  # Business logic
│   └── main.py
├── frontend/         # React + Vite + TailwindCSS
│   └── src/
│       ├── components/  # UI components
│       ├── pages/       # Route pages
│       ├── providers/   # Context providers
│       └── hooks/       # Custom hooks
└── docker-compose.yml
```

## Features

- **AI Chat**: Real-time streaming responses with RAG context
- **Feedback System**: Upvote/downvote with mandatory feedback modal
- **AI Analysis**: OpenAI analyzes feedback, generates tickets with root cause analysis
- **Admin Dashboard**: Review tickets, manage users, curate knowledge base
- **RAG Knowledge Base**: Approved answers automatically improve future responses

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- Supabase account
- OpenAI API key

### Setup

1. Clone and install dependencies:

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

2. Configure environment:

```bash
cp .env.example .env
# Edit .env with your Supabase and OpenAI credentials
```

3. Run the application:

```bash
# Backend (terminal 1)
cd backend
uvicorn main:app --reload --port 8000

# Frontend (terminal 2)
cd frontend
npm run dev
```

### Docker

```bash
docker compose up --build
```

### Database

Tables are auto-created on first run. For vector search support, ensure the `pgvector` extension is enabled in your Supabase project:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

## API Endpoints

### Auth
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `GET /api/v1/auth/me` - Get current user

### Chat
- `POST /api/v1/chat/send` - Send message (streaming response)
- `GET /api/v1/chat/conversations` - List conversations
- `GET /api/v1/chat/conversations/:id` - Get conversation detail
- `DELETE /api/v1/chat/conversations/:id` - Delete conversation
- `GET /api/v1/chat/search?q=` - Search conversations

### Feedback
- `POST /api/v1/feedback/vote/:message_id` - Upvote/downvote
- `POST /api/v1/feedback/submit` - Submit feedback

### Admin
- `GET /api/v1/admin/dashboard` - Dashboard stats
- `GET /api/v1/admin/users` - List users
- `GET /api/v1/admin/tickets` - List tickets
- `POST /api/v1/admin/tickets/:id/review` - Review ticket
- `GET /api/v1/admin/feedback` - List feedback

### Knowledge Base
- `GET /api/v1/knowledge-base/entries` - List entries
- `GET /api/v1/knowledge-base/search?q=` - Search entries

## License

MIT
