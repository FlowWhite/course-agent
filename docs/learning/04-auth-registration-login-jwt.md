# 第 4 篇：鉴权——注册、登录、JWT 与用户隔离

## 1. 鉴权解决什么问题

不同用户的agent是不同的，为了区分，我们需要引入鉴权机制。

首先我们要区分认证与授权的区别，认证能够区分用户的身份，做用户隔离，授权是为了区分用户的权限。在course-agent项目中，我们需要认证来区分不同的用户，授权来给不同的用户相应的权限。

## 2. 注册流程

注册请求体会先经过 `RegisterRequest` 的校验，然后进入 `register_api`。

```python
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
```

这一注册接口在auth.py中，前端发送的请求体会进入create_user_data，在auth_service中。

```python
def create_user_data(
    username: str,
    password: str,
) -> dict[str, Any]:
    """
    创建用户，并将密码转换为哈希后保存。
    """
    normalized_username = username.strip()

    if len(normalized_username) < 3:
        raise ValueError("用户名至少需要 3 个字符")

    if len(normalized_username) > 100:
        raise ValueError("用户名不能超过 100 个字符")

    if len(password) < 8:
        raise ValueError("密码至少需要 8 个字符")

    password_hash = password_hasher.hash(password)

    with get_postgres_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            try:
                cursor.execute(
                    """
                    INSERT INTO users (
                        username,
                        password_hash
                    )
                    VALUES (%s, %s)
                    RETURNING
                        id,
                        username,
                        is_active,
                        created_at
                    """,
                    (
                        normalized_username,
                        password_hash,
                    ),
                )

                row = cursor.fetchone()

            except psycopg.errors.UniqueViolation as exc:
                raise UserAlreadyExistsError(
                    "用户名已经存在"
                ) from exc

    return _public_user(row)
```

我们能看到这一部分对数据进行了规范，并且通过 `password_hash = password_hasher.hash(password)`，和数据库操作保存了数据库密码的哈希值，这样即使数据库内容泄露，也不会直接暴露用户的原始密码。最后还会返回 `return _public_user(row)` 返回给上层用户信息，如：

```python
return {
    "id": row["id"],
    "username": row["username"],
    "is_active": row["is_active"],
    "created_at": created_at.isoformat(),
}
```

如此一来，注册操作就完成了。

## 3. 登录验证流程

登录接口同样在auth.py中。

```python
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
```

客户端发送的请求体进入authenticate_user_data函数，在auth_service中。

```python
def authenticate_user_data(
    username: str,
    password: str,
) -> dict[str, Any] | None:
    """
    验证用户名和密码。

    验证成功返回用户信息；
    验证失败返回 None。
    """
    normalized_username = username.strip()

    with get_postgres_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    username,
                    password_hash,
                    is_active,
                    created_at
                FROM users
                WHERE username = %s
                """,
                (normalized_username,),
            )

            row = cursor.fetchone()

    if row is None:
        return None

    if not row["is_active"]:
        return None

    password_is_valid = password_hasher.verify(
        password,
        row["password_hash"],
    )

    if not password_is_valid:
        return None

    return _public_user(row)
```

仍然是先对信息进行标准化处理，然后通过数据库操作查询相应用户，并且验证密码和哈希，这个验证过程中对数据进行了多次判断，最重要的是：

```python
password_is_valid = password_hasher.verify(
    password,
    row["password_hash"],
)
```

这一部分使用verify函数进行了验证。

## 4. JWT是什么，如何生成

JWT是登录成功后发给客户端的一段令牌，它不仅表示这个用户已经通过了登录验证，还携带了其他的用户信息。让我们看看JWT是由什么创建的，在上面的登录函数中，我们可以看到：

```python
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
```

调用的create_access_token函数位于auth_security.py：

```python
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
```

登录时调用这一函数，会根据用户信息生成JWT，并写入用户 ID，用户名，签发时间，过期时间，正是函数写入payload的这四个变量。此外，JWT还会使用：

```text
JWT_SECRET_KEY
JWT_ALGORITHM
```

来生成签名，并返回成为access_token。JWT中的Payload只是编码，不是加密，所以不能放入密码等敏感信息。

## 5. 前端如何携带 JWT

登陆成功后，login函数返回JWT：

```python
return ToolResponse(
    success=True,
    data={
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    },
).model_dump(mode="json")
```

前端对其进行保存：

```javascript
accessToken.value = result.access_token
sessionStorage.setItem(
  "course-agent-access-token",
  result.access_token,
)
```

之后请求任务、课程等接口时，前端得以统一添加请求头：

```javascript
headers.set(
  "Authorization",
  `Bearer ${accessToken.value}`,
)
```

最终发送的 HTTP 请求类似：

```http
GET /api/v1/tasks
Authorization: Bearer eyJ...
```

## 6. 后端如何读取JWT

以files.py文件名中的upload_course_file_api函数为例：

```python
@router.post("/files", status_code=201)
async def upload_course_file_api(
    course_id: str = Form(...),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
) -> dict: ...
```

可以看到 `current_user: dict = Depends(get_current_user)`，这一句使用了依赖，在dependencies.py中：

```python
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login"
)

def get_current_user(
    token: str = Depends(oauth2_scheme),
) -> dict:
    """Resolve the authenticated user from an Authorization bearer token."""
    try:
        return decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=401,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
```

其中 `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")` 这一句，它的作用是从请求头中提取出token，比如前面的HTTP请求中的 `Authorization: Bearer eyJ`。

下面就会交给get_current_user函数，可以看到参数的传入就是使用了对oauth2_scheme的依赖，传入了token。里面执行了decode_access_token函数，这一函数就在之前的auth_security中。我们之前在这里使用用户信息生成access_token，现在要使用decode_access_token函数验证用户。

```python
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
```

可以看到这一函数大致是access_token的反向操作，先用jwt.decode解析并验证JWT生成payload，得出返回用户信息，最终通过两个函数的返回让upload_course_file_api函数中的current_user得到了相应的值。由此我们可知，这里的current_user不是客户端自己提供的，而是来自验证的JWT。

## 7. 认证和授权的区别

身份认证说明了你的身份，在项目中的实现：

```text
用户名和密码
  → JWT
  → get_current_user()
  → current_user
```

权限控制顾名思义，在项目中的实现：

```text
current_user["id"]
  → user_id
  → 数据库查询条件
```

所以即使用户 A 知道用户 B 的任务 ID，也不能直接查询用户 B 的任务。

## 8. 用户数据隔离

仅仅是在前端对用户数据进行隐藏是不够的，因为用户可以自己构造 HTTP 请求。真正的保护必须在后端：

```text
JWT验证
  ↓
取得 user_id
  ↓
SQL 强制限制 user_id
```

所以项目的隔离结构是：

```text
客户端
  → 不能决定 user_id

JWT
  → 后端确认 user_id

数据库查询
  → 强制使用 user_id
```

## 9. Token过期和退出登录

JWT中有过期时间 `exp`。当Token过期后，`decode_access_token`验证失败，后端会返回401，前端需要清除保存的Token并重新登录。

退出登录时，前端会清除：

```javascript
accessToken.value = ""
sessionStorage.removeItem("course-agent-access-token")
```

当前项目没有额外的服务端Token黑名单，所以已经签发的JWT在过期前仍然有效。

## 10. 一条完整请求链路

```text
1. 用户发送用户名和密码
2. 后端查询用户
3. 验证密码哈希
4. 创建 JWT
5. 前端保存 access_token
6. 前端请求任务接口
7. 请求携带 Authorization Header
8. get_current_user() 验证 JWT
9. 得到 user_id
10. 任务查询使用 user_id
11. 返回属于该用户的任务
```

可以表示为：

```text
POST /api/v1/auth/login
  ↓
JWT

GET /api/v1/tasks
  + Authorization: Bearer <JWT>
  ↓
get_current_user()
  ↓
user_id
  ↓
list_tasks_data(user_id=...)
  ↓
PostgreSQL
```
