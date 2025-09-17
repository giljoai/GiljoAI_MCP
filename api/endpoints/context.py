"""
Context and vision management API endpoints
"""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel


router = APIRouter()


class ContextIndexResponse(BaseModel):
    product_id: str
    index: dict[str, Any]
    document_count: int
    total_sections: int


class VisionResponse(BaseModel):
    part: int
    total_parts: int
    content: str
    tokens: int


@router.get("/index", response_model=ContextIndexResponse)
async def get_context_index(product_id: Optional[str] = Query(None, description="Product ID")):
    """Get the context index for intelligent querying"""
    try:
        from giljo_mcp.tools.context import get_context_index

        result = await get_context_index(product_id=product_id)

        if not result.get("success"):
            raise HTTPException(status_code=404, detail="Context index not found")

        index = result.get("index", {})
        return ContextIndexResponse(
            product_id=product_id or "default",
            index=index,
            document_count=len(index.get("documents", [])),
            total_sections=sum(len(doc.get("sections", [])) for doc in index.get("documents", [])),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vision", response_model=VisionResponse)
async def get_vision(
    part: int = Query(1, description="Part number to retrieve"),
    max_tokens: int = Query(20000, description="Maximum tokens per part"),
):
    """Get the vision document (chunked if large)"""
    try:
        from giljo_mcp.tools.context import get_vision

        result = await get_vision(part=part, max_tokens=max_tokens)

        if not result.get("success"):
            raise HTTPException(status_code=404, detail="Vision document not found")

        return VisionResponse(
            part=part,
            total_parts=result.get("total_parts", 1),
            content=result.get("content", ""),
            tokens=result.get("tokens", 0),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vision/index", response_model=dict[str, Any])
async def get_vision_index():
    """Get the vision document index"""
    try:
        from giljo_mcp.tools.context import get_vision_index

        result = await get_vision_index()

        if not result.get("success"):
            raise HTTPException(status_code=404, detail="Vision index not found")

        return result.get("index", {})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings", response_model=dict[str, Any])
async def get_product_settings(product_id: Optional[str] = Query(None, description="Product ID")):
    """Get all product settings for analysis"""
    try:
        from giljo_mcp.tools.context import get_product_settings

        result = await get_product_settings(product_id=product_id)

        if not result.get("success"):
            raise HTTPException(status_code=404, detail="Product settings not found")

        return result.get("settings", {})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
