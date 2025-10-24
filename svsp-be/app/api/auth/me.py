from fastapi import APIRouter, Request, HTTPException, status

router = APIRouter(
    prefix="/auth",
    tags=["Auth"])


@router.get("/me")
async def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Require login"
        )
    return {"user": user}
