from fastapi import APIRouter

router = APIRouter()


@router.post("")
async def create_commune():
    return {"status": 501, "message": "Not implemented yet"}


@router.get("/mine")
async def get_my_commune():
    return {"status": 501, "message": "Not implemented yet"}


@router.post("/join")
async def join_commune():
    return {"status": 501, "message": "Not implemented yet"}


@router.get("/{commune_id}/members")
async def list_members(commune_id: str):
    return {"status": 501, "message": "Not implemented yet"}


@router.get("/{commune_id}/pricing")
async def get_pricing(commune_id: str):
    return {"status": 501, "message": "Not implemented yet"}


@router.get("/{commune_id}/billing")
async def get_billing(commune_id: str):
    return {"status": 501, "message": "Not implemented yet"}
