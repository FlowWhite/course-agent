"""Authentication endpoints."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ...auth_security import create_access_token
from ...auth_service import (
    UserAlreadyExistsError,
    authenticate_user_data,
    create_user_data,
)
from ...models import ToolResponse
from ..schemas import LoginRequest, RegisterRequest


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login")
def login_api(request: LoginRequest) -> dict:
    """Validate user credentials and return an access token."""
    try:
        user = authenticate_user_data(
            username=request.username,
            password=request.password,
        )
        if user is None:
            return JSONResponse(
                status_code=401,
                content=ToolResponse(
                    success=False,
                    error="用户名或密码错误",
                ).model_dump(mode="json"),
            )

        access_token = create_access_token(
            user_id=user["id"],
            username=user["username"],
        )
        return ToolResponse(
            success=True,
            data={
                "access_token": access_token,
                "token_type": "bearer",
                "user": user,
            },
        ).model_dump(mode="json")
    except Exception:
        return JSONResponse(
            status_code=500,
            content=ToolResponse(
                success=False,
                error="登录处理失败",
            ).model_dump(mode="json"),
        )


@router.post("/register", status_code=201)
def register_api(request: RegisterRequest) -> dict:
    """Create a user account."""
    try:
        user = create_user_data(
            username=request.username,
            password=request.password,
        )
        return ToolResponse(
            success=True,
            data={"user": user, "message": "注册成功，请登录"},
        ).model_dump(mode="json")
    except UserAlreadyExistsError as exc:
        return JSONResponse(
            status_code=409,
            content=ToolResponse(
                success=False,
                error=str(exc),
            ).model_dump(mode="json"),
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content=ToolResponse(
                success=False,
                error=str(exc),
            ).model_dump(mode="json"),
        )
    except Exception:
        return JSONResponse(
            status_code=500,
            content=ToolResponse(
                success=False,
                error="注册处理失败",
            ).model_dump(mode="json"),
        )
