# Backend

该目录包含 Epic 2 的 FastAPI 后端。

当前包含：

- HTTP API 和请求验证
- 业务逻辑服务
- 数据库连接与数据模型
- 自动化测试

US2.1 已实现赛事、球队、球员、场馆和比赛的 PostgreSQL 持久化、CRUD API、关联校验与 Alembic 迁移。

US2.2 已实现：

- `users` 和 `auth_sessions` 数据表
- `scrypt` 密码哈希与安全随机会话令牌
- HttpOnly Cookie 会话保持
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`
- 基础数据写接口的登录保护

应用迁移并创建首个本地用户：

```bash
cd backend
source .venv/bin/activate
python -m alembic upgrade head
python -m app.scripts.create_user --email coach@example.com --name "王教练"
```

用户角色和细粒度权限属于 US2.3；当前 US2.2 只区分“未登录”和“已登录”。
