from pydantic import BaseModel


# --- Auth ---
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    id: str
    name: str | None = None
    known_languages: list[str] = []
    target_language: str | None = None
    streak_days: int = 0


# --- Chat ---
class MessageCreate(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str | None = None
    tool_calls: str | None = None
    tool_call_id: str | None = None
    token_count: int | None = None
    created_at: str


class ConversationCreate(BaseModel):
    pass


class ConversationResponse(BaseModel):
    id: str
    cat_id: str
    title: str | None = None
    created_at: str


# --- SRS ---
class CardResponse(BaseModel):
    id: str
    card_type: str
    front: str
    back: str
    context_sentence: str | None = None
    language: str
    fsrs_stability: float | None = None
    fsrs_difficulty: float | None = None
    fsrs_due: str | None = None
    fsrs_reps: int = 0
    fsrs_lapses: int = 0
    fsrs_state: int = 0
    source: str | None = None
    created_at: str


class ReviewRequest(BaseModel):
    rating: int  # 1-4


class ReviewResponse(BaseModel):
    card: CardResponse
    next_review: str | None = None
    scheduled_days: float | None = None


class StatsResponse(BaseModel):
    total_cards: int
    due_today: int
    reviews_today: int
    streak_days: int


# --- Cat ---
class CatResponse(BaseModel):
    id: str
    language: str
    name: str | None = None
    state: str
    hospitalized_reason: str | None = None
    created_at: str


class GroomResponse(BaseModel):
    cat: CatResponse
    message: str


# --- Goal ---
class GoalCreate(BaseModel):
    title: str
    media_type: str | None = None
    language: str | None = None


class GoalResponse(BaseModel):
    id: str
    title: str
    media_type: str | None = None
    language: str
    status: str
    total_words: int | None = None
    known_words: int | None = None
    created_at: str
    completed_at: str | None = None


# --- Notification ---
class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str
    body: str | None = None
    read: bool
    created_at: str


# --- User ---
class UserUpdate(BaseModel):
    name: str | None = None
    known_languages: list[str] | None = None
    target_language: str | None = None


class UserResponse(BaseModel):
    id: str
    name: str | None = None
    known_languages: list[str] = []
    target_language: str | None = None
    streak_days: int = 0
    payment_path: str | None = None
    created_at: str


# --- Billing (stubs) ---
class BalanceResponse(BaseModel):
    balance: int


class TransactionResponse(BaseModel):
    id: str
    type: str
    amount: int
    balance_after: int
    description: str | None = None
    created_at: str


# --- Commune (stubs) ---
class CommuneCreate(BaseModel):
    name: str


class CommuneResponse(BaseModel):
    id: str
    name: str
    invite_code: str
    premium: float
    decay: float
    created_at: str
