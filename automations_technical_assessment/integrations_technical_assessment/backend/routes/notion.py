from fastapi import APIRouter, HTTPException
from integrations.notion import get_items_notion

router = APIRouter()

@router.post("/integrations/notion/items")
async def fetch_notion_items(credentials: dict):
    try:
        items = await get_items_notion(credentials)
        return items
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
