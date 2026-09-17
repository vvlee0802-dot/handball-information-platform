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

US2.3 已实现：

- 运动员、教练/分析师、赛事管理员和系统管理员角色
- 角色默认权限与用户额外权限
- 基础数据写接口和用户管理接口的后端权限检查
- `GET /api/admin/users`
- `POST /api/admin/users`
- `PATCH /api/admin/users/{user_id}`
- 停用账号时撤销该用户现有会话

US3.1 已实现：

- `videos` 数据表及 Alembic 迁移
- `GET /api/videos/upload-policy`
- `GET /api/matches/{match_id}/videos`
- `PUT /api/matches/{match_id}/videos`
- MP4 扩展名、媒体类型、文件头和大小的后端校验
- 默认 10 GiB 上限和流式本地文件写入
- 比赛视频上传权限检查及 uploaded 状态持久化

视频文件默认保存在 `backend/uploads`，该目录不提交到 Git。可以通过根目录 `.env` 调整：

```bash
VIDEO_UPLOAD_MAX_BYTES=10737418240
VIDEO_UPLOAD_DIR=backend/uploads
```

应用迁移并创建首个本地用户：

```bash
cd backend
source .venv/bin/activate
python -m alembic upgrade head
python -m app.scripts.create_user --email admin@example.com --name "系统管理员"
```

命令行用于引导创建首个系统管理员。登录前端后，可在“用户管理”页面创建并配置其他账号。
