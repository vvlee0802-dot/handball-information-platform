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

US3.2 已实现：

- 上传进度由前端 XMLHttpRequest 实时反馈
- queued、processing、completed、failed 后台处理状态
- 文件存在性、MP4 容器、记录大小和 SHA-256 完整性检查
- `POST /api/videos/{video_id}/retry` 失败任务重试接口
- 处理失败原因、处理进度、尝试次数和时间戳持久化

当前后台任务运行在 FastAPI 进程内，适合本地 MVP。生产环境应迁移到独立任务队列，避免应用重启导致排队任务丢失。

US5.2 本地进球检测原型已实现：

- 根据最终比分校验人工进球标注是否完整
- 生成时间隔离的进球/非进球训练与验证集
- 使用预训练 VideoMAE 提取特征，训练二分类头
- 每 5 秒滑动扫描整场视频，生成带置信度的待审核候选事件
- 完整标注比赛自动进入评估模式，计算命中、漏检、误报、Precision、Recall、F1 和时间偏差
- 评估模式不重复创建 AI 事件；非评估模式重跑会替换旧的未确认草稿
- `analysis_predictions` 保留每条命中、误报和漏检明细，误报经人工确认后才会进入下一版困难负样本
- 误报审核已形成 48 个 V2 困难负样本，另有 11 个不可靠片段被排除
- V1/V2 模型产物分目录保存，并可在同一特征缓存和验证集上执行公平比较
- 当前本地候选模型为 `goal-detector-v2`；可通过 `GOAL_MODEL_DIR` 回退到 V1
- 训练和整场推理统一使用保持比例的居中裁剪，避免黑边造成特征分布偏移
- V2 整场评估达到 49 命中、57 误报、16 漏报，Precision 46.2%、Recall 75.4%、F1 57.3%

AI 依赖是可选的：普通 API 开发只安装 `requirements.txt`，本地训练和推理再安装 `requirements-ml.txt`。数据集保存在 `backend/datasets`，模型产物保存在 `backend/model_artifacts`，两者均不提交到 Git。

应用迁移并创建首个本地用户：

```bash
cd backend
source .venv/bin/activate
python -m alembic upgrade head
python -m app.scripts.create_user --email admin@example.com --name "系统管理员"
```

命令行用于引导创建首个系统管理员。登录前端后，可在“用户管理”页面创建并配置其他账号。
