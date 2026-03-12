from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import BalanceResponse
from app.services import billing_service

router = APIRouter()


@router.get("/balance")
async def get_balance(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BalanceResponse:
    balance = await billing_service.get_balance(db, user.id)
    return BalanceResponse(balance=balance)


@router.get("/packs")
async def get_packs():
    return {"status": 501, "message": "Not implemented yet"}


@router.post("/purchase")
async def purchase():
    return {"status": 501, "message": "Not implemented yet"}


@router.get("/history")
async def get_history():
    return {"status": 501, "message": "Not implemented yet"}
