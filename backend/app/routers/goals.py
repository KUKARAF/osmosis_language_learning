from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.models import GoalWord
from app.schemas import (
    GoalCreate, GoalResponse,
    SubtitleResult, SubtitleImportRequest, SubtitleImportResponse,
)
from osmosis_media.providers.subdl import SubDLProvider
from app.config import settings
from app.services import goal_service, goal_import_service
from app import plugins
from sqlalchemy import delete

router = APIRouter()


@router.get("")
async def list_goals(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[GoalResponse]:
    goals = await goal_service.get_goals(db, user.id)
    return [_goal_response(g) for g in goals]


@router.get("/media-types")
async def media_types() -> list[str]:
    return plugins.goal_media_types()


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


@router.delete("/{goal_id}", status_code=204)
async def delete_goal(
    goal_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    goal = await goal_service.get_goal(db, goal_id)
    if goal is None or goal.user_id != user.id:
        raise HTTPException(status_code=404, detail="Goal not found")
    await db.execute(delete(GoalWord).where(GoalWord.goal_id == goal_id))
    await db.delete(goal)
    await db.commit()
    return Response(status_code=204)


@router.get("/{goal_id}/subtitles")
async def search_subtitles(
    goal_id: str,
    season: int | None = Query(default=None),
    episode: int | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[SubtitleResult]:
    goal = await goal_service.get_goal(db, goal_id)
    if goal is None or goal.user_id != user.id:
        raise HTTPException(status_code=404, detail="Goal not found")
    if not settings.SUBDL_API_KEY:
        raise HTTPException(status_code=503, detail="SUBDL_API_KEY not configured")
    provider = SubDLProvider(api_key=settings.SUBDL_API_KEY)
    from app.services.goal_import_service import _clean_title
    results = await provider.search(
        title=_clean_title(goal.title), language=goal.language,
        season=season, episode=episode,
    )
    return [SubtitleResult(name=r.name, url=r.url, lang=r.lang) for r in results]


@router.post("/{goal_id}/subtitles")
async def import_subtitles(
    goal_id: str,
    body: SubtitleImportRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubtitleImportResponse:
    goal = await goal_service.get_goal(db, goal_id)
    if goal is None or goal.user_id != user.id:
        raise HTTPException(status_code=404, detail="Goal not found")
    try:
        from osmosis_media.providers.base import SubtitleResult as SRResult
        provider = SubDLProvider(api_key=settings.SUBDL_API_KEY)
        srt = await provider.download(SRResult(name="", url=body.subdl_url, lang=""))
        result = await goal_import_service.import_from_srt(
            db, goal, srt_content=srt, source_url=body.subdl_url,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return SubtitleImportResponse(**result)


class AutoImportRequest(BaseModel):
    season: int | None = None
    episode: int | None = None


@router.post("/{goal_id}/auto-import")
async def auto_import(
    goal_id: str,
    body: AutoImportRequest | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubtitleImportResponse:
    goal = await goal_service.get_goal(db, goal_id)
    if goal is None or goal.user_id != user.id:
        raise HTTPException(status_code=404, detail="Goal not found")
    try:
        result = await goal_import_service.auto_import(
            db, goal,
            season=body.season if body else None,
            episode=body.episode if body else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return SubtitleImportResponse(**result)


def _goal_response(g) -> GoalResponse:
    actions = plugins.goal_actions_for(g.media_type or "")
    return GoalResponse(
        id=g.id, title=g.title, media_type=g.media_type, language=g.language,
        status=g.status, total_words=g.total_words, known_words=g.known_words,
        actions=actions,
        created_at=g.created_at, completed_at=g.completed_at,
    )
