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

Epic 8 RAG 知识库已实现：

- PDF、TXT 和 Markdown 文档上传、来源分块、失败重试与级联删除
- 百炼 Embedding 向量化、余弦相似度 Top-K 检索和 Qwen 依据内回答
- 文档、页码或章节、引用片段和相关度分数的可追溯返回
- 平台、球队和上传者三级可见范围，以及直接接口访问的权限隔离
- 固定问题集和版本化评测记录，包含 Recall@K、引用命中率、无依据回答率和逐题明细

Embedding 当前以 PostgreSQL JSON 字段保存，并由应用层计算余弦相似度，适合本地 MVP 数据量；扩大知识库后可无缝迁移到 pgvector 索引检索。

Epic 9 比赛分析 Agent 已实现：

- 使用比赛概况、已确认事件、球员官方统计和 RAG 知识检索工具回答自然语言问题
- 每轮回答保存模型状态、来源以及脱敏后的工具名称、参数、耗时、结果摘要和错误
- 同一会话保留比赛上下文和短期聊天历史；删除会话同步清理消息、运行记录与短期记忆
- 服务端按用户权限动态下发工具白名单，未授权或不存在的工具调用会被拒绝
- 修改比赛状态等写操作只生成待确认方案，确认时再次检查权限并记录独立审计日志
- 失败的 Agent 运行可在页面重试，工具错误或数据缺失时要求模型明确说明，禁止编造结果

应用迁移并创建首个本地用户：

```bash
cd backend
source .venv/bin/activate
python -m alembic upgrade head
python -m app.scripts.create_user --email admin@example.com --name "系统管理员"
```

命令行用于引导创建首个系统管理员。登录前端后，可在“用户管理”页面创建并配置其他账号。
