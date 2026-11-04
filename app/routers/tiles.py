from fastapi import APIRouter, HTTPException, Path, Response, status

from app.services.tiles import TileError, get_tile

router = APIRouter(tags=["tiles"])


@router.get("/tiles/{z}/{x}/{name}")
async def tile(
    z: int = Path(ge=0, le=19),
    x: int = Path(ge=0),
    name: str = Path(pattern=r"^\d+\.png$"),
):
    y = int(name.removesuffix(".png"))
    if x >= 2**z or y >= 2**z:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tile fuera de rango")
    try:
        content = await get_tile(z, x, y)
    except TileError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return Response(content, media_type="image/png", headers={"Cache-Control": "public, max-age=604800"})
