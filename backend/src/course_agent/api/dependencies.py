"""Shared FastAPI dependencies."""

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from ..auth_security import decode_access_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Resolve the authenticated user from an Authorization bearer token."""
    try:
        return decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
