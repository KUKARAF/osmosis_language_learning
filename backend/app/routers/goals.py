from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import GoalCreate, GoalResponse
from app.services import goal_service

router = APIRouter()


@router.get("")
async def list_goals(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GoalResponse]:
    goals = await goal_service.get_goals(db, user.id)
    return [_goal_response(g) for g in goals]


@router.post("")
async def create_goal(
    body: GoalCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GoalResponse:
    language = body.language or user.target_language or "unknown"
    goal = await goal_service.create_goal(
        db, user_id=user.id, title=body.title,
        language=language, media_type=body.media_type,
    )
    return _goal_response(goal)


@router.get("/{goal_id}")
async def get_goal(
    goal_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GoalResponse:
    goal = await goal_service.get_goal(db, goal_id)
    if goal is None or goal.user_id != user.id:
        raise HTTPException(status_code=404, detail="Goal not found")
    return _goal_response(goal)


def _goal_response(g) -> GoalResponse:
    return GoalResponse(
        id=g.id, title=g.title, media_type=g.media_type, language=g.language,
        status=g.status, total_words=g.total_words, known_words=g.known_words,
        created_at=g.created_at, completed_at=g.completed_at,
    )
