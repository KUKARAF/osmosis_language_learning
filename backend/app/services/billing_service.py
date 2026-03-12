"""Billing service — stub for MVP. All methods are no-ops in DEV_MODE."""

from app.config import settings


async def check_daily_limit(user) -> bool:
    """True if user can still chat today. Always True in DEV_MODE."""
    if settings.DEV_MODE:
        return True
    return user.tokens_used_today < user.daily_token_limit


async def deduct_tokens(db, user_id: str, amount: int, description: str = "") -> None:
    """Debit tokens. No-op in DEV_MODE."""
    if settings.DEV_MODE:
        return
    # TODO: implement token deduction + transaction log
    pass


async def get_balance(db, user_id: str) -> int:
    """Current token balance. Returns max int in DEV_MODE."""
    if settings.DEV_MODE:
        return 999999
    return 0
