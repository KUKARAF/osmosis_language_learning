# Architecture

Reference architecture for osmosis. Covers file structure, data model, services, API, LLM tooling, and frontend.

## 1. Project file structure

```
osmosis/
├── idea.md
├── soul.md
├── commune_payment.md
├── todo.md
├── architecture.md              # this file
├── docker-compose.yaml          # prod
├── dev.docker-compose.yaml      # dev
├── .env                         # secrets (not committed)
├── .env.example                 # template
├── .github/
│   └── workflows/
│       └── build.yaml           # build → push to GHCR
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app, lifespan, mount static
│   │   ├── config.py            # pydantic-settings, reads .env
│   │   ├── database.py          # SQLite connection, async engine
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── schemas.py           # pydantic request/response schemas
│   │   ├── dependencies.py      # FastAPI Depends helpers (get_db, get_current_user)
│   │   ├── auth.py              # OIDC PKCE helpers, token validation
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── chat.py
│   │   │   ├── cats.py
│   │   │   ├── srs.py
│   │   │   ├── goals.py
│   │   │   ├── notifications.py
│   │   │   ├── billing.py
│   │   │   ├── communes.py
│   │   │   └── users.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── auth_service.py
│   │   │   ├── llm_service.py
│   │   │   ├── chat_service.py
│   │   │   ├── srs_service.py
│   │   │   ├── cat_service.py
│   │   │   ├── goal_service.py
│   │   │   ├── billing_service.py
│   │   │   ├── commune_service.py
│   │   │   └── notification_service.py
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── executor.py      # ToolExecutor — dispatches tool_calls to services
│   │   │   └── definitions.py   # OpenAI function calling JSON schemas
│   │   └── templates/
│   │       ├── system.jinja     # main system prompt
│   │       ├── onboarding.jinja # first interaction prompt
│   │       └── review.jinja     # SRS review session prompt
│   └── tests/
│       ├── conftest.py
│       ├── test_chat.py
│       ├── test_srs.py
│       └── test_tools.py
├── frontend/
│   ├── index.html               # SPA shell
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   ├── app.js               # entry point, router
│   │   ├── api.js               # fetch wrappers for /api/*
│   │   ├── chat.js              # chat UI, SSE streaming
│   │   ├── srs.js               # flashcard review UI
│   │   ├── goals.js             # goals page
│   │   ├── settings.js          # user settings page
│   │   ├── notifications.js     # notification bell/panel
│   │   ├── auth.js              # OIDC PKCE flow
│   │   └── cat.js               # cat state display, grooming button
│   └── assets/
│       └── placeholder-cat.svg
└── mobile/                      # future — Rust APK
    └── README.md
```

## 2. Data model

All tables live in a single SQLite database. Column types use SQLite affinity (TEXT, INTEGER, REAL). Timestamps are ISO-8601 TEXT stored in UTC.

### users

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | TEXT | PK | UUID4 |
| oidc_sub | TEXT | UNIQUE NOT NULL | subject from authentik |
| name | TEXT | | display name, set agentically |
| known_languages | TEXT | | JSON array, e.g. `["en","pl"]` |
| target_language | TEXT | | ISO 639-1 code |
| daily_token_limit | INTEGER | NOT NULL DEFAULT 50000 | hidden from user |
| tokens_used_today | INTEGER | NOT NULL DEFAULT 0 | reset daily by cron |
| streak_days | INTEGER | NOT NULL DEFAULT 0 | |
| last_groomed_at | TEXT | | ISO-8601 or NULL |
| payment_path | TEXT | | `"individual"` or `"commune"` or NULL |
| created_at | TEXT | NOT NULL | |
| updated_at | TEXT | NOT NULL | |

Index: `idx_users_oidc_sub ON users(oidc_sub)`

### cats

One cat per user per target language.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | TEXT | PK | UUID4 |
| user_id | TEXT | FK → users.id, NOT NULL | |
| language | TEXT | NOT NULL | target language this cat teaches |
| name | TEXT | | cat name, can be set by user |
| state | TEXT | NOT NULL DEFAULT 'happy' | `happy`, `hangry`, `hospitalized` |
| hospitalized_reason | TEXT | | flavor text for hospitalization |
| created_at | TEXT | NOT NULL | |

Index: `idx_cats_user_lang ON cats(user_id, language)` UNIQUE

### conversations

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | TEXT | PK | UUID4 |
| user_id | TEXT | FK → users.id, NOT NULL | |
| cat_id | TEXT | FK → cats.id, NOT NULL | |
| title | TEXT | | auto-generated summary |
| created_at | TEXT | NOT NULL | |

Index: `idx_conversations_user ON conversations(user_id)`

### messages

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | TEXT | PK | UUID4 |
| conversation_id | TEXT | FK → conversations.id, NOT NULL | |
| role | TEXT | NOT NULL | `user`, `assistant`, `system`, `tool` |
| content | TEXT | | message body (NULL for pure tool_call messages) |
| tool_calls | TEXT | | JSON array of tool_call objects from LLM |
| tool_call_id | TEXT | | for role=tool responses |
| token_count | INTEGER | | total tokens (prompt+completion) for this exchange |
| created_at | TEXT | NOT NULL | |

Index: `idx_messages_conversation ON messages(conversation_id, created_at)`

### srs_cards

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | TEXT | PK | UUID4 |
| user_id | TEXT | FK → users.id, NOT NULL | |
| card_type | TEXT | NOT NULL | `vocabulary`, `grammar`, `phrase` |
| front | TEXT | NOT NULL | word/form in target language |
| back | TEXT | NOT NULL | translation/explanation in known language |
| context_sentence | TEXT | | example sentence |
| language | TEXT | NOT NULL | target language |
| fsrs_stability | REAL | | py-fsrs state |
| fsrs_difficulty | REAL | | py-fsrs state |
| fsrs_due | TEXT | | next review date ISO-8601 |
| fsrs_last_review | TEXT | | last review date |
| fsrs_reps | INTEGER | NOT NULL DEFAULT 0 | |
| fsrs_lapses | INTEGER | NOT NULL DEFAULT 0 | |
| fsrs_state | INTEGER | NOT NULL DEFAULT 0 | py-fsrs card state enum |
| source | TEXT | | `chat`, `goal_import`, `manual` |
| created_at | TEXT | NOT NULL | |

Index: `idx_srs_user_due ON srs_cards(user_id, language, fsrs_due)`

### srs_review_logs

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | TEXT | PK | UUID4 |
| card_id | TEXT | FK → srs_cards.id, NOT NULL | |
| rating | INTEGER | NOT NULL | 1=Again, 2=Hard, 3=Good, 4=Easy |
| source | TEXT | NOT NULL | `chat_agentic`, `flashcard_manual` |
| scheduled_days | REAL | | days until next review |
| elapsed_days | REAL | | days since last review |
| review_at | TEXT | NOT NULL | ISO-8601 |

Index: `idx_review_logs_card ON srs_review_logs(card_id, review_at)`

### goals

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | TEXT | PK | UUID4 |
| user_id | TEXT | FK → users.id, NOT NULL | |
| title | TEXT | NOT NULL | e.g. "Watch Sorda in Spanish" |
| media_type | TEXT | | `movie`, `series`, `book`, `other` |
| language | TEXT | NOT NULL | target language |
| status | TEXT | NOT NULL DEFAULT 'active' | `active`, `ready`, `completed` |
| total_words | INTEGER | | total unique words in imported content |
| known_words | INTEGER | DEFAULT 0 | words user has mastered |
| srt_content | TEXT | | raw subtitle text |
| created_at | TEXT | NOT NULL | |
| completed_at | TEXT | | |

Index: `idx_goals_user ON goals(user_id, status)`

### notifications

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | TEXT | PK | UUID4 |
| user_id | TEXT | FK → users.id, NOT NULL | |
| type | TEXT | NOT NULL | `goal_ready`, `streak_warning`, `commune_update`, `hospitalized` |
| title | TEXT | NOT NULL | |
| body | TEXT | | |
| read | INTEGER | NOT NULL DEFAULT 0 | boolean |
| created_at | TEXT | NOT NULL | |

Index: `idx_notifications_user ON notifications(user_id, read, created_at)`

### communes

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | TEXT | PK | UUID4 |
| name | TEXT | NOT NULL | |
| invite_code | TEXT | UNIQUE NOT NULL | short random code |
| premium | REAL | NOT NULL DEFAULT 25.0 | PLN — starting markup |
| decay | REAL | NOT NULL DEFAULT 0.88 | decay factor per member |
| created_at | TEXT | NOT NULL | |

### commune_members

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | TEXT | PK | UUID4 |
| commune_id | TEXT | FK → communes.id, NOT NULL | |
| user_id | TEXT | FK → users.id, UNIQUE NOT NULL | one commune per user |
| role | TEXT | NOT NULL DEFAULT 'member' | `founder`, `member` |
| joined_at | TEXT | NOT NULL | |

Index: `idx_commune_members_commune ON commune_members(commune_id)`

### commune_billing

Monthly billing snapshots.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | TEXT | PK | UUID4 |
| commune_id | TEXT | FK → communes.id, NOT NULL | |
| billing_month | TEXT | NOT NULL | `YYYY-MM` |
| member_count | INTEGER | NOT NULL | |
| total_llm_cost | REAL | NOT NULL | actual LLM spend in PLN |
| price_per_user | REAL | NOT NULL | computed price |
| total_revenue | REAL | NOT NULL | |
| created_at | TEXT | NOT NULL | |

Index: `idx_commune_billing ON commune_billing(commune_id, billing_month)` UNIQUE

### token_transactions

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | TEXT | PK | UUID4 |
| user_id | TEXT | FK → users.id, NOT NULL | |
| type | TEXT | NOT NULL | `purchase`, `usage`, `bonus`, `vet_fee` |
| amount | INTEGER | NOT NULL | positive = credit, negative = debit |
| balance_after | INTEGER | NOT NULL | running balance |
| description | TEXT | | e.g. "Can of tuna (5000 tokens)" |
| stripe_payment_id | TEXT | | for purchases |
| created_at | TEXT | NOT NULL | |

Index: `idx_token_tx_user ON token_transactions(user_id, created_at)`

## 3. Key services

### AuthService (`services/auth_service.py`)

```python
class AuthService:
    async def validate_oidc_token(self, token: str) -> dict:
        """Validate JWT from authentik, return claims."""

    async def get_or_create_user(self, oidc_claims: dict) -> User:
        """Find user by oidc_sub or create a new one."""
```

### LLMService (`services/llm_service.py`)

```python
class LLMService:
    async def chat_completion_stream(
        self,
        messages: list[dict],
        tools: list[dict],
        provider: str = "openrouter",  # or "groq"
    ) -> AsyncIterator[dict]:
        """
        Call OpenRouter/Groq chat completions API with streaming.
        Yields SSE-compatible chunks including tool_calls.
        Uses OpenAI-compatible API format for both providers.
        """

    def select_provider(self, context: str) -> str:
        """Pick openrouter vs groq based on latency needs."""

    def count_tokens(self, messages: list[dict]) -> int:
        """Estimate token usage for rate limiting."""
```

### ChatService (`services/chat_service.py`)

```python
class ChatService:
    async def handle_message(
        self, user: User, conversation_id: str, user_message: str
    ) -> AsyncIterator[str]:
        """
        Full chat turn:
        1. Load conversation history from DB
        2. Build messages array with system prompt (jinja-rendered)
        3. Call LLMService.chat_completion_stream with tool definitions
        4. If response contains tool_calls → ToolExecutor.execute → append tool results → re-call LLM
        5. Stream final text response as SSE events
        6. Persist all messages (user, assistant, tool) to DB
        7. Update user.tokens_used_today
        """

    async def build_system_prompt(self, user: User, cat: Cat) -> str:
        """Render system.jinja with user/cat context."""

    async def get_or_create_conversation(self, user: User) -> Conversation:
        """Get active conversation or create new one."""
```

### ToolExecutor (`tools/executor.py`)

```python
class ToolExecutor:
    """
    Receives tool_call objects from the LLM response,
    dispatches to the appropriate service method locally,
    returns tool results to feed back into the LLM.
    """

    def __init__(self, services: dict):
        self.registry: dict[str, Callable] = {
            "update_user_profile": self._update_user_profile,
            "rate_word": self._rate_word,
            "create_vocabulary_card": self._create_vocabulary_card,
            "search_media": self._search_media,
            "create_goal": self._create_goal,
        }

    async def execute(self, tool_calls: list[dict], user: User) -> list[dict]:
        """
        For each tool_call:
        1. Parse function name and arguments
        2. Look up handler in registry
        3. Execute handler with parsed args
        4. Return list of {tool_call_id, role: "tool", content: result_json}
        """

    async def _update_user_profile(self, user: User, **kwargs) -> dict:
        """Update user.name, known_languages, target_language, etc."""

    async def _rate_word(self, user: User, word: str, rating: int, context: str) -> dict:
        """Find or create SRS card, apply py-fsrs rating."""

    async def _create_vocabulary_card(self, user: User, front: str, back: str, **kwargs) -> dict:
        """Create a new SRS card from chat context."""

    async def _search_media(self, user: User, query: str, media_type: str) -> dict:
        """Search for movies/series, return results for goal creation."""

    async def _create_goal(self, user: User, title: str, media_type: str, **kwargs) -> dict:
        """Create a goal and optionally import SRT content."""
```

### SRSService (`services/srs_service.py`)

```python
class SRSService:
    async def get_due_cards(self, user_id: str, language: str, limit: int = 20) -> list[SRSCard]:
        """Get cards due for review, ordered by fsrs_due."""

    async def review_card(self, card_id: str, rating: int, source: str) -> SRSCard:
        """
        Apply py-fsrs rating to card:
        1. Load card from DB
        2. Build fsrs.Card from stored state
        3. Call fsrs.repeat() with the rating
        4. Update card with new scheduling state
        5. Log review in srs_review_logs
        6. Return updated card
        """

    async def find_or_create_card(
        self, user_id: str, word: str, language: str, back: str, **kwargs
    ) -> SRSCard:
        """Find existing card by front+language or create new one."""

    async def import_srt_words(self, user_id: str, goal_id: str, srt_text: str) -> int:
        """Parse SRT, extract unique words, create cards. Return count."""
```

### CatService (`services/cat_service.py`)

```python
class CatService:
    async def get_active_cat(self, user: User) -> Cat:
        """Get cat for user's current target_language. Create if needed."""

    async def groom(self, cat: Cat) -> Cat:
        """Groom the cat. Update state, reset streak timer."""

    async def update_state(self, cat: Cat) -> Cat:
        """
        Check last_groomed_at:
        - < 24h: happy
        - 24-72h: hangry
        - > 72h: hospitalized (generate reason)
        """

    async def hospitalize(self, cat: Cat) -> Cat:
        """Set hospitalized state with a random gruesome scenario."""

    async def heal(self, cat: Cat, user: User) -> Cat:
        """Heal hospitalized cat. Deduct vet fee tokens if on individual plan."""
```

### GoalService (`services/goal_service.py`)

```python
class GoalService:
    async def create_goal(self, user_id: str, title: str, media_type: str, language: str) -> Goal:
        """Create a new goal."""

    async def check_readiness(self, goal: Goal, user_id: str) -> float:
        """Calculate % of goal's words the user knows. Return 0.0-1.0."""

    async def mark_ready(self, goal_id: str) -> Goal:
        """Mark goal as ready, send notification."""
```

### BillingService (`services/billing_service.py`)

```python
class BillingService:
    async def purchase_tokens(self, user_id: str, pack: str) -> TokenTransaction:
        """Process Stripe payment, credit tokens."""

    async def deduct_tokens(self, user_id: str, amount: int, description: str) -> TokenTransaction:
        """Debit tokens for usage. Returns None if insufficient balance."""

    async def get_balance(self, user_id: str) -> int:
        """Current token balance."""

    async def check_daily_limit(self, user: User) -> bool:
        """True if user can still chat today."""
```

### CommuneService (`services/commune_service.py`)

```python
class CommuneService:
    async def create_commune(self, founder_id: str, name: str) -> Commune:
        """Create commune, add founder as first member."""

    async def join_commune(self, user_id: str, invite_code: str) -> CommuneMember:
        """Join a commune via invite code."""

    async def calculate_price(self, commune: Commune) -> float:
        """
        price_per_user = max(1.0, avg_llm_cost + premium * decay^(n-1))
        Uses rolling 3-month average for avg_llm_cost.
        """

    async def generate_monthly_billing(self, commune_id: str) -> CommuneBilling:
        """Create billing snapshot for the current month."""

    async def check_commune_budget(self, commune: Commune) -> bool:
        """True if commune hasn't exceeded spend ceiling."""
```

### NotificationService (`services/notification_service.py`)

```python
class NotificationService:
    async def create(self, user_id: str, type: str, title: str, body: str = "") -> Notification:
        """Create a notification."""

    async def get_unread(self, user_id: str) -> list[Notification]:
        """Get unread notifications for user."""

    async def mark_read(self, notification_id: str) -> None:
        """Mark single notification as read."""

    async def mark_all_read(self, user_id: str) -> None:
        """Mark all notifications as read."""
```

## 4. API endpoints

All endpoints are under `/api`. Authentication required unless noted.

### Auth — `/api/auth`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/auth/login` | Redirect to authentik OIDC authorize endpoint |
| GET | `/api/auth/callback` | OIDC callback, exchange code for tokens, set session |
| POST | `/api/auth/logout` | Clear session |
| GET | `/api/auth/me` | Return current user info |

### Chat — `/api/chat`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/chat/conversations` | List user's conversations |
| POST | `/api/chat/conversations` | Create new conversation |
| GET | `/api/chat/conversations/{id}/messages` | Get message history |
| POST | `/api/chat/conversations/{id}/messages` | Send message, returns SSE stream |

The `POST .../messages` endpoint returns `Content-Type: text/event-stream`. Events:

```
event: token
data: {"content": "Priv"}

event: token
data: {"content": "et,"}

event: tool_call
data: {"name": "rate_word", "arguments": {"word": "kot", "rating": 4, "context": "used correctly"}}

event: tool_result
data: {"name": "rate_word", "result": {"card_id": "...", "next_review": "2025-06-15"}}

event: token
data: {"content": " you used 'kot' perfectly!"}

event: done
data: {"message_id": "...", "tokens_used": 342}
```

### Cats — `/api/cats`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/cats` | List user's cats (all languages) |
| GET | `/api/cats/active` | Get active cat for current target language |
| POST | `/api/cats/active/groom` | Groom the active cat |
| POST | `/api/cats/active/heal` | Heal hospitalized cat (costs tokens) |

### SRS — `/api/srs`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/srs/cards` | List user's cards (with filters: language, due, card_type) |
| GET | `/api/srs/cards/due` | Get cards due for review |
| POST | `/api/srs/cards/{id}/review` | Submit manual flashcard review `{rating: 1-4}` |
| GET | `/api/srs/stats` | Review stats (cards learned, streak, etc.) |

### Goals — `/api/goals`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/goals` | List user's goals |
| POST | `/api/goals` | Create goal |
| GET | `/api/goals/{id}` | Goal detail with readiness % |
| POST | `/api/goals/{id}/import-srt` | Upload SRT file, import words as cards |

### Notifications — `/api/notifications`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/notifications` | Get notifications (unread first) |
| POST | `/api/notifications/{id}/read` | Mark as read |
| POST | `/api/notifications/read-all` | Mark all as read |

### Billing — `/api/billing`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/billing/balance` | Current token balance |
| GET | `/api/billing/packs` | Available token packs with prices |
| POST | `/api/billing/purchase` | Purchase token pack (Stripe checkout) |
| GET | `/api/billing/history` | Transaction history |

### Communes — `/api/communes`
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/communes` | Create commune |
| GET | `/api/communes/mine` | Get user's commune |
| POST | `/api/communes/join` | Join via invite code |
| GET | `/api/communes/{id}/members` | List members |
| GET | `/api/communes/{id}/pricing` | Current price calculation |
| GET | `/api/communes/{id}/billing` | Billing history |

### Users — `/api/users`
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/users/me` | Full user profile |
| PATCH | `/api/users/me` | Update profile (name, target_language, etc.) |
| GET | `/api/users/me/cats` | Alias for `/api/cats` |

## 5. LLM tool definitions

These are the OpenAI function calling schemas passed to the LLM in the `tools` parameter. The LLM returns `tool_calls` in its response; our `ToolExecutor` executes them locally.

### update_user_profile

```json
{
  "type": "function",
  "function": {
    "name": "update_user_profile",
    "description": "Update the user's profile information. Use this when you learn new things about the user during conversation, such as their name, languages they speak, or the language they want to learn.",
    "parameters": {
      "type": "object",
      "properties": {
        "name": {
          "type": "string",
          "description": "The user's display name"
        },
        "known_languages": {
          "type": "array",
          "items": {"type": "string"},
          "description": "ISO 639-1 codes of languages the user already speaks, e.g. ['en', 'pl']"
        },
        "target_language": {
          "type": "string",
          "description": "ISO 639-1 code of the language the user wants to learn, e.g. 'ru'"
        }
      },
      "additionalProperties": false
    }
  }
}
```

### rate_word

```json
{
  "type": "function",
  "function": {
    "name": "rate_word",
    "description": "Rate a word or grammar form the user just used in conversation. Call this whenever the user attempts to use a word or form in the target language. Rating guide: 4=Easy (used correctly without hesitation), 3=Good (minor error, right idea), 2=Hard (significant error, needed correction), 1=Again (completely wrong, needs re-learning).",
    "parameters": {
      "type": "object",
      "properties": {
        "word": {
          "type": "string",
          "description": "The word or grammar form being rated, in its dictionary/base form"
        },
        "rating": {
          "type": "integer",
          "enum": [1, 2, 3, 4],
          "description": "py-fsrs rating: 1=Again, 2=Hard, 3=Good, 4=Easy"
        },
        "context": {
          "type": "string",
          "description": "Brief note on how the user used the word, e.g. 'used correctly in a sentence' or 'confused accusative with genitive'"
        }
      },
      "required": ["word", "rating", "context"],
      "additionalProperties": false
    }
  }
}
```

### create_vocabulary_card

```json
{
  "type": "function",
  "function": {
    "name": "create_vocabulary_card",
    "description": "Create a new vocabulary or grammar flashcard. Use this when introducing a new word or concept to the user that they haven't encountered before.",
    "parameters": {
      "type": "object",
      "properties": {
        "front": {
          "type": "string",
          "description": "The word or phrase in the target language"
        },
        "back": {
          "type": "string",
          "description": "Translation or explanation in the user's known language"
        },
        "card_type": {
          "type": "string",
          "enum": ["vocabulary", "grammar", "phrase"],
          "description": "Type of card"
        },
        "context_sentence": {
          "type": "string",
          "description": "An example sentence using the word in the target language"
        }
      },
      "required": ["front", "back", "card_type"],
      "additionalProperties": false
    }
  }
}
```

### search_media

```json
{
  "type": "function",
  "function": {
    "name": "search_media",
    "description": "Search for movies, series, or other media content. Use this when the user mentions wanting to watch or consume something in their target language.",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {
          "type": "string",
          "description": "Search query, e.g. 'Sorda Spanish movie'"
        },
        "media_type": {
          "type": "string",
          "enum": ["movie", "series", "book", "other"],
          "description": "Type of media to search for"
        }
      },
      "required": ["query", "media_type"],
      "additionalProperties": false
    }
  }
}
```

### create_goal

```json
{
  "type": "function",
  "function": {
    "name": "create_goal",
    "description": "Create a language learning goal for the user. Use this when the user expresses a goal like wanting to watch a movie or read a book in the target language.",
    "parameters": {
      "type": "object",
      "properties": {
        "title": {
          "type": "string",
          "description": "Goal title, e.g. 'Watch Sorda in Spanish'"
        },
        "media_type": {
          "type": "string",
          "enum": ["movie", "series", "book", "other"],
          "description": "Type of media associated with the goal"
        }
      },
      "required": ["title"],
      "additionalProperties": false
    }
  }
}
```

## 6. Frontend structure

Single-page app using vanilla JS. No framework. All pages rendered client-side with DOM manipulation.

### Pages (hash-based routing)

| Route | Page | Description |
|-------|------|-------------|
| `#/` | Chat | Main chat interface (default) |
| `#/review` | Flashcards | SRS review session |
| `#/goals` | Goals | Goal list with readiness progress bars |
| `#/settings` | Settings | Profile, language selection, cat switching |

### Key JS modules

**`auth.js`** — OIDC PKCE flow
- `startLogin()` — redirect to authentik with code_challenge
- `handleCallback()` — exchange code for tokens, store in sessionStorage
- `getAccessToken()` — return current token, refresh if needed
- `logout()` — clear tokens, redirect

**`chat.js`** — Chat UI and SSE streaming
- `sendMessage(text)` — POST to API, open SSE stream
- `handleSSE(eventSource)` — process token/tool_call/tool_result/done events
- `renderMessage(msg)` — append message bubble to DOM
- `renderToolAction(toolCall)` — show inline UI for tool actions (e.g. "cat is writing in notebook")
- `renderInlineCard(card)` — render inline flashcard element in chat

**`srs.js`** — Flashcard review
- `loadDueCards()` — fetch due cards from API
- `showCard(card)` — render card front
- `flipCard()` — reveal back
- `submitRating(cardId, rating)` — POST review to API
- `askCatAboutCard(card)` — send card to chat for cat explanation

**`cat.js`** — Cat state display
- `loadCatState()` — fetch active cat
- `renderCat(cat)` — update cat visual (placeholder/emoji based on state)
- `groomCat()` — POST groom, update UI
- `renderGroomButton()` — daily grooming button

**`api.js`** — Fetch wrapper
- `apiFetch(path, options)` — adds auth header, handles 401 refresh, base URL

## 7. Chat streaming flow

End-to-end sequence for a single chat message:

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Frontend │     │  FastAPI      │     │  LLMService   │     │ OpenRouter/  │
│ (chat.js)│     │  ChatRouter   │     │               │     │ Groq API     │
└────┬─────┘     └──────┬───────┘     └──────┬────────┘     └──────┬───────┘
     │                  │                    │                     │
     │ POST /api/chat/  │                    │                     │
     │ conversations/   │                    │                     │
     │ {id}/messages    │                    │                     │
     │ {content: "..."}│                    │                     │
     │────────────────>│                    │                     │
     │                  │                    │                     │
     │  SSE stream open │                    │                     │
     │<─ ─ ─ ─ ─ ─ ─ ─ │                    │                     │
     │                  │                    │                     │
     │                  │ 1. Load history    │                     │
     │                  │ 2. Render system   │                     │
     │                  │    prompt (jinja)  │                     │
     │                  │ 3. Build messages  │                     │
     │                  │    array + tools   │                     │
     │                  │                    │                     │
     │                  │ chat_completion    │                     │
     │                  │ _stream(messages,  │                     │
     │                  │  tools, provider)  │                     │
     │                  │──────────────────>│                     │
     │                  │                    │ POST /v1/chat/      │
     │                  │                    │ completions         │
     │                  │                    │ (stream=true)       │
     │                  │                    │────────────────────>│
     │                  │                    │                     │
     │                  │                    │ SSE chunks          │
     │                  │                    │<─ ─ ─ ─ ─ ─ ─ ─ ─ ─│
     │                  │                    │                     │
     ╔══════════════════╪════════════════════╪═══════════════════╗ │
     ║ IF response contains tool_calls:      │                   ║ │
     ║                  │                    │                   ║ │
     ║ event: tool_call │ accumulate         │                   ║ │
     ║<─ ─ ─ ─ ─ ─ ─ ─ │ tool_call chunks   │                   ║ │
     ║                  │                    │                   ║ │
     ║                  │ ToolExecutor       │                   ║ │
     ║                  │ .execute(          │                   ║ │
     ║                  │   tool_calls,      │                   ║ │
     ║                  │   user)            │                   ║ │
     ║                  │──┐                 │                   ║ │
     ║                  │  │ local service   │                   ║ │
     ║                  │  │ method calls    │                   ║ │
     ║                  │  │ (SRS, profile,  │                   ║ │
     ║                  │  │  goals, etc.)   │                   ║ │
     ║                  │<─┘                 │                   ║ │
     ║                  │                    │                   ║ │
     ║ event:tool_result│                    │                   ║ │
     ║<─ ─ ─ ─ ─ ─ ─ ─ │                    │                   ║ │
     ║                  │                    │                   ║ │
     ║                  │ 2nd LLM call with  │                   ║ │
     ║                  │ tool results       │                   ║ │
     ║                  │──────────────────>│                   ║ │
     ║                  │                    │────────────────────>│
     ║                  │                    │<─ ─ ─ ─ ─ ─ ─ ─ ─ ─│
     ╚══════════════════╪════════════════════╪═══════════════════╝ │
     │                  │                    │                     │
     │ event: token     │ stream final       │                     │
     │ event: token     │ text response      │                     │
     │ event: token     │                    │                     │
     │<─ ─ ─ ─ ─ ─ ─ ─ │                    │                     │
     │                  │                    │                     │
     │ event: done      │ persist all msgs   │                     │
     │ {message_id,     │ update token count │                     │
     │  tokens_used}    │                    │                     │
     │<─ ─ ─ ─ ─ ─ ─ ─ │                    │                     │
     │                  │                    │                     │
```

### Loop behavior

The tool_call → execute → re-call loop can repeat multiple times in a single turn. For example, the LLM might:
1. Call `rate_word` for a word the user used
2. Call `create_vocabulary_card` for a new word it's introducing
3. Generate the final text response incorporating both results

Each iteration appends tool results to the messages array and re-calls the LLM until it produces a text-only response (no more tool_calls).

## 8. SRS-LLM bridge

How agentic SRS ratings flow through the system:

```
User says "Вчера я иду в магазин" (incorrect past tense)
          │
          ▼
    ┌─────────────┐
    │   LLM sees   │  System prompt instructs LLM to rate words
    │   the error   │  agentically during conversation
    └──────┬──────┘
           │
           ▼ LLM response includes:
    ┌──────────────────────────────────────────────────┐
    │ {                                                 │
    │   "tool_calls": [{                                │
    │     "id": "call_abc123",                          │
    │     "type": "function",                           │
    │     "function": {                                 │
    │       "name": "rate_word",                        │
    │       "arguments": "{                             │
    │         \"word\": \"идти\",                       │
    │         \"rating\": 2,                            │
    │         \"context\": \"used present tense идy     │
    │           instead of past tense ходил\"           │
    │       }"                                          │
    │     }                                             │
    │   }]                                              │
    │ }                                                 │
    └──────────────────┬───────────────────────────────┘
                       │
                       ▼
              ┌────────────────┐
              │  ToolExecutor   │  Parses tool_call, routes to handler
              │  .execute()     │
              └───────┬────────┘
                      │
                      ▼
              ┌────────────────┐
              │  SRSService     │
              │  .find_or_     │  1. Find card for "идти" (or create)
              │   create_card() │
              │  .review_card() │  2. Build fsrs.Card from stored state
              └───────┬────────┘
                      │
                      ▼
              ┌────────────────┐
              │   py-fsrs       │  3. fsrs.repeat(card, rating=Hard)
              │   .repeat()     │     → new scheduling state
              └───────┬────────┘
                      │
                      ▼
              ┌────────────────┐
              │   SQLite DB     │  4. UPDATE srs_cards SET
              │                 │     fsrs_stability, fsrs_difficulty,
              │                 │     fsrs_due, fsrs_reps, fsrs_lapses
              │                 │  5. INSERT INTO srs_review_logs
              └───────┬────────┘
                      │
                      ▼
              ┌────────────────┐
              │  Tool result    │  Return to ToolExecutor:
              │  → back to LLM  │  {"card_id": "...", "word": "идти",
              │                 │   "next_review": "2025-06-10",
              │                 │   "status": "reviewed"}
              └───────┬────────┘
                      │
                      ▼
              ┌────────────────┐
              │  LLM generates  │  "Ты *ходил* в магазин вчера?
              │  final response │   Что купил? 📝 *scribbles in
              │  with correction│   notebook*"
              └────────────────┘
```

### Manual flashcard reviews

When the user reviews cards in the flashcard UI (`#/review`), the flow is simpler:

```
Frontend (srs.js)
  → POST /api/srs/cards/{id}/review {rating: 3}
    → SRSService.review_card(card_id, rating=3, source="flashcard_manual")
      → py-fsrs.repeat()
      → UPDATE srs_cards, INSERT srs_review_logs
    → return updated card with next review date
```

Both paths (agentic chat and manual flashcard) converge at `SRSService.review_card()`, ensuring consistent SRS scheduling regardless of how the review happens.
