import os
from datetime import datetime, timedelta, timezone

import jwt


def create_access_token(
    user_id: int,
    username: str,
) -> str:
    """
    根据用户信息生成 JWT。
    """
    secret_key = os.environ["JWT_SECRET_KEY"]
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")
    expire_minutes = int(
        os.getenv("JWT_EXPIRE_MINUTES", "60")
    )

    now = datetime.now(timezone.utc)
    expire_at = now + timedelta(
        minutes=expire_minutes
    )

    payload = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": expire_at,
    }

    return jwt.encode(
        payload,
        secret_key,
        algorithm=algorithm,
    )
def decode_access_token(
    token: str,
) -> dict:
    """
    验证并解析 JWT。
    """
    secret_key = os.environ["JWT_SECRET_KEY"]
    algorithm = os.getenv("JWT_ALGORITHM", "HS256")

    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[algorithm],
        )

        subject = payload.get("sub")
        username = payload.get("username")

        if not subject or not username:
            raise ValueError("令牌缺少用户信息")

        return {
            "id": int(subject),
            "username": username,
        }

    except (
        jwt.ExpiredSignatureError,
        jwt.InvalidTokenError,
        TypeError,
        ValueError,
    ) as exc:
        raise ValueError(
            "无效或已过期的访问令牌"
        ) from exc