import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Float, Index, Integer, Text, ForeignKey
from sqlalchemy.orm import DeclarativeBase, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Text, primary_key=True, default=_uuid)
    oidc_sub = Column(Text, unique=True, nullable=False)
    name = Column(Text)
    known_languages = Column(Text, default="[]")  # JSON array
    target_language = Column(Text)
    daily_token_limit = Column(Integer, nullable=False, default=50000)
    tokens_used_today = Column(Integer, nullable=False, default=0)
    streak_days = Column(Integer, nullable=False, default=0)
    last_groomed_at = Column(Text)
    payment_path = Column(Text)  # "individual" | "commune" | NULL
    created_at = Column(Text, nullable=False, default=_utcnow)
    updated_at = Column(Text, nullable=False, default=_utcnow, onupdate=_utcnow)

    cats = relationship("Cat", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")

    __table_args__ = (Index("idx_users_oidc_sub", "oidc_sub"),)


class Cat(Base):
    __tablename__ = "cats"

    id = Column(Text, primary_key=True, default=_uuid)
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    language = Column(Text, nullable=False)
    name = Column(Text)
    state = Column(Text, nullable=False, default="happy")
    hospitalized_reason = Column(Text)
    created_at = Column(Text, nullable=False, default=_utcnow)

    user = relationship("User", back_populates="cats")
    conversations = relationship("Conversation", back_populates="cat")

    __table_args__ = (
        Index("idx_cats_user_lang", "user_id", "language", unique=True),
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Text, primary_key=True, default=_uuid)
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    cat_id = Column(Text, ForeignKey("cats.id"), nullable=False)
    title = Column(Text)
    summary = Column(Text)
    summary_through_msg_id = Column(Text)
    created_at = Column(Text, nullable=False, default=_utcnow)

    user = relationship("User", back_populates="conversations")
    cat = relationship("Cat", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", order_by="Message.created_at")

    __table_args__ = (Index("idx_conversations_user", "user_id"),)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Text, primary_key=True, default=_uuid)
    conversation_id = Column(Text, ForeignKey("conversations.id"), nullable=False)
    role = Column(Text, nullable=False)  # user | assistant | system | tool
    content = Column(Text)
    tool_calls = Column(Text)  # JSON array
    tool_call_id = Column(Text)
    token_count = Column(Integer)
    created_at = Column(Text, nullable=False, default=_utcnow)

    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index("idx_messages_conversation", "conversation_id", "created_at"),
    )


class SRSCard(Base):
    __tablename__ = "srs_cards"

    id = Column(Text, primary_key=True, default=_uuid)
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    card_type = Column(Text, nullable=False)  # vocabulary | grammar | phrase
    front = Column(Text, nullable=False)
    back = Column(Text, nullable=False)
    context_sentence = Column(Text)
    language = Column(Text, nullable=False)
    fsrs_stability = Column(Float)
    fsrs_difficulty = Column(Float)
    fsrs_due = Column(Text)
    fsrs_last_review = Column(Text)
    fsrs_reps = Column(Integer, nullable=False, default=0)
    fsrs_lapses = Column(Integer, nullable=False, default=0)
    fsrs_state = Column(Integer, nullable=False, default=0)
    source = Column(Text)  # chat | goal_import | manual
    created_at = Column(Text, nullable=False, default=_utcnow)

    reviews = relationship("SRSReviewLog", back_populates="card")
    goal_words = relationship("GoalWord", back_populates="card")

    __table_args__ = (
        Index("idx_srs_user_due", "user_id", "language", "fsrs_due"),
    )


class SRSReviewLog(Base):
    __tablename__ = "srs_review_logs"

    id = Column(Text, primary_key=True, default=_uuid)
    card_id = Column(Text, ForeignKey("srs_cards.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1-4
    source = Column(Text, nullable=False)  # chat_agentic | flashcard_manual
    scheduled_days = Column(Float)
    elapsed_days = Column(Float)
    review_at = Column(Text, nullable=False, default=_utcnow)

    card = relationship("SRSCard", back_populates="reviews")

    __table_args__ = (
        Index("idx_review_logs_card", "card_id", "review_at"),
    )


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Text, primary_key=True, default=_uuid)
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    title = Column(Text, nullable=False)
    media_type = Column(Text)  # movie | series | book | other
    language = Column(Text, nullable=False)
    status = Column(Text, nullable=False, default="active")
    total_words = Column(Integer)
    known_words = Column(Integer, default=0)
    srt_content = Column(Text)
    created_at = Column(Text, nullable=False, default=_utcnow)
    completed_at = Column(Text)

    goal_words = relationship("GoalWord", back_populates="goal")

    __table_args__ = (Index("idx_goals_user", "user_id", "status"),)


class GoalWord(Base):
    __tablename__ = "goal_words"

    goal_id = Column(Text, ForeignKey("goals.id"), primary_key=True)
    card_id = Column(Text, ForeignKey("srs_cards.id"), primary_key=True)
    added_at = Column(Text, nullable=False, default=_utcnow)

    goal = relationship("Goal", back_populates="goal_words")
    card = relationship("SRSCard", back_populates="goal_words")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Text, primary_key=True, default=_uuid)
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    type = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    body = Column(Text)
    read = Column(Integer, nullable=False, default=0)
    created_at = Column(Text, nullable=False, default=_utcnow)

    __table_args__ = (
        Index("idx_notifications_user", "user_id", "read", "created_at"),
    )


class Commune(Base):
    __tablename__ = "communes"

    id = Column(Text, primary_key=True, default=_uuid)
    name = Column(Text, nullable=False)
    invite_code = Column(Text, unique=True, nullable=False)
    premium = Column(Float, nullable=False, default=25.0)
    decay = Column(Float, nullable=False, default=0.88)
    created_at = Column(Text, nullable=False, default=_utcnow)


class CommuneMember(Base):
    __tablename__ = "commune_members"

    id = Column(Text, primary_key=True, default=_uuid)
    commune_id = Column(Text, ForeignKey("communes.id"), nullable=False)
    user_id = Column(Text, ForeignKey("users.id"), unique=True, nullable=False)
    role = Column(Text, nullable=False, default="member")
    joined_at = Column(Text, nullable=False, default=_utcnow)

    __table_args__ = (Index("idx_commune_members_commune", "commune_id"),)


class CommuneBilling(Base):
    __tablename__ = "commune_billing"

    id = Column(Text, primary_key=True, default=_uuid)
    commune_id = Column(Text, ForeignKey("communes.id"), nullable=False)
    billing_month = Column(Text, nullable=False)
    member_count = Column(Integer, nullable=False)
    total_llm_cost = Column(Float, nullable=False)
    price_per_user = Column(Float, nullable=False)
    total_revenue = Column(Float, nullable=False)
    created_at = Column(Text, nullable=False, default=_utcnow)

    __table_args__ = (
        Index("idx_commune_billing", "commune_id", "billing_month", unique=True),
    )


class TokenTransaction(Base):
    __tablename__ = "token_transactions"

    id = Column(Text, primary_key=True, default=_uuid)
    user_id = Column(Text, ForeignKey("users.id"), nullable=False)
    type = Column(Text, nullable=False)  # purchase | usage | bonus | vet_fee
    amount = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    description = Column(Text)
    stripe_payment_id = Column(Text)
    created_at = Column(Text, nullable=False, default=_utcnow)

    __table_args__ = (Index("idx_token_tx_user", "user_id", "created_at"),)
