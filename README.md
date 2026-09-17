# Handball Information Platform

手球信息与比赛分析平台。目前已完成 Epic 1、Epic 2，以及 Epic 3 的 US3.1 比赛视频上传。

用户可以通过赛事、比赛、球队、球员或场馆查找信息。主要页面的数据由 FastAPI 从 PostgreSQL 读取；具备权限的教练或分析师可以为指定比赛上传 MP4 录像。AI 事件识别、视频审核和自动剪辑仍属于后续开发范围。

## US2.1 本版改动

1. 完成 Vue 3 + TypeScript 前端与 FastAPI 后端分离，并通过 Vite 代理连接 `/api`。
2. 建立 PostgreSQL、SQLAlchemy 和 Alembic 数据层，实现赛事、球队、球员、场馆和比赛的数据持久化与迁移。
3. 实现基础数据的新增、列表、详情和编辑接口，并加入外键存在性、主客队差异及完赛比分完整性校验。
4. 将主要页面从前端静态数据切换为真实 API 数据，补充关联展示、错误状态和前后端自动化测试，并用 v1.0 需求文档替换旧版需求。

## US2.2 本版改动

1. 新增用户与服务端会话数据模型，使用 Alembic 管理数据库迁移。
2. 使用 `scrypt` 保存密码哈希，使用随机会话令牌和 HttpOnly Cookie 保持登录状态。
3. 新增登录、当前用户和退出接口，并要求登录后才能调用基础数据写接口。
4. 新增 Vue 登录页、会话恢复、退出和 401 重新登录引导，并补充前后端测试。

## US2.3 本版改动

1. 建立运动员、教练/分析师、赛事管理员和系统管理员四种角色，以及五类业务权限。
2. 后端对赛事基础数据写操作和用户管理操作实施权限检查，直接请求接口也无法绕过限制。
3. 新增系统管理员用户管理页面，可在网页中创建用户、选择角色、启停账号和授予额外权限。
4. 前端根据当前用户权限显示新增、编辑和用户管理入口，并补充角色权限迁移与自动化测试。

## US3.1 本版改动

1. 支持教练或分析师从比赛详情页选择并上传 MP4 比赛录像。
2. 单文件默认上限为 10 GiB，前后端同时校验扩展名、媒体类型、MP4 文件头和实际字节数。
3. FastAPI 采用流式读取并写入本地存储，避免把整场比赛录像一次性加载到内存。
4. 新增视频数据表，记录所属比赛、上传用户、原始文件名、文件大小、存储位置和 uploaded 状态。
5. 上传成功后，比赛详情页显示关联视频；刷新页面后仍从 PostgreSQL 读取该关联记录。

## US3.2 本版改动

1. 上传过程中实时显示浏览器已上传百分比。
2. 新增 queued、processing、completed 和 failed 四种后台处理状态及处理进度。
3. 后台任务检查文件存在性、MP4 容器和记录大小，并计算 SHA-256 完整性摘要。
4. 比赛详情页自动轮询仍在处理的视频，进入最终状态后停止轮询。
5. 处理失败时保存并展示可理解的中文原因，具备权限的用户可以重新提交处理任务。

## 需求文档

当前正式需求文档为 [Handball AI Project Requirements v1.0](docs/Handball_AI_Project_Requirements_v1.0.docx)。该文件用于替代此前的旧版需求文件。

## 已实现功能

- 赛事、比赛、球队、球员和场馆的列表与详情展示
- 赛事、球队、球员、场馆和比赛数据的新增与编辑
- 赛事、球队、球员、场馆和比赛之间的关联查询与跳转
- 比赛主客队、比分状态和外键关系校验
- 录像与 AI 分析的后续功能入口

## 技术栈

- 前端：Vue 3、TypeScript、Vue Router、Pinia、Vite、Vitest、ESLint、Prettier
- 后端：FastAPI、SQLAlchemy、Pydantic、Pytest
- 数据库：PostgreSQL、Alembic
- 本地环境：Docker Compose

## 核心数据模型

- `Competition`：赛事
- `Team`：球队
- `Player`：球员，通过 `team_id` 关联球队
- `Venue`：场馆
- `Match`：比赛，通过外键关联赛事、主队、客队和场馆
- `User`：注册用户，只保存密码哈希，不保存明文密码
- `AuthSession`：服务端会话，只保存随机会话令牌的摘要
- `UserPermission`：用户在角色默认权限之外获得的可配置权限
- `Video`：比赛录像元数据，通过 `match_id` 关联比赛，文件本体保存在可配置存储目录

所有实体均使用稳定 ID 建立关系，避免使用显示名称作为数据关联依据。

## 项目结构

```text
.
├── frontend/                 # Vue 3 + TypeScript 前端应用
├── backend/                  # FastAPI 后端、Alembic 迁移和测试
├── docs/                     # 正式需求文档
├── docker-compose.yml        # PostgreSQL 本地环境
└── README.md
```

## 本地运行

### 1. 配置环境变量并启动 PostgreSQL

```bash
cp .env.example .env
docker compose up -d
```

### 2. 启动后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m app.scripts.create_user --email admin@example.com --name "系统管理员"
python -m uvicorn app.main:app --reload --port 8000
```

这条命令只用于创建第一个系统管理员，终端会要求输入并确认密码。之后可以登录网页，在“用户管理”页面创建其他账号，不需要每次使用终端。

健康检查：`http://127.0.0.1:8000/api/health`

API 文档：`http://127.0.0.1:8000/docs`

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

## 项目检查

```bash
cd frontend
npm run type-check
npm run test:unit -- --run
npx eslint .
npm run build

cd ../backend
source .venv/bin/activate
python -m pytest -q
```

当前检查结果：

```text
ESLint                         Passed
TypeScript type-check          Passed
Frontend unit tests            24 passed
Backend tests                  25 passed
Production build               Passed
```

## 开发路线

### Epic 1 Handball Information Platform

- [x] 赛事信息
- [x] 比赛列表与详情
- [x] 球队列表与详情
- [x] 球员列表与详情
- [x] 场馆列表与详情
- [x] 比赛组合筛选
- [x] 信息对象关联跳转
- [x] 录像和 AI 分析状态入口
- [x] Vue 页面 TypeScript 统一
- [x] 基础自动化测试

### Epic 2 Platform Backend Data Persistence and Accounts

- [x] US2.1 基础业务数据后端化与持久化
- [x] US2.2 登录平台并保持会话
- [x] US2.3 用户角色和权限

### Epic 3 Match Video Management

- [x] US3.1 MP4 视频上传
- [x] US3.1 视频与比赛记录关联
- [x] US3.2 上传进度和错误状态
- [x] US3.2 视频处理状态管理

### Epic 4 Event Review and Video Clips

- [ ] 人工新增、删除和调整事件
- [ ] 事件筛选和视频跳转
- [ ] 生成与导出事件片段

### Epic 5 AI Match Event Detection

- [ ] 自动检测进球事件
- [ ] 保存事件时间戳
- [ ] 保存 AI 置信度和检测来源
- [ ] 从事件跳转到对应视频时间

### Epic 6 Player Analysis and Personal Highlights

- [ ] 比赛事件与球员关联
- [ ] 球员单场统计
- [ ] 从统计指标查看对应视频
- [ ] 自动生成个人集锦

### Epic 7 to Epic 9 LLM RAG and Agent

- [ ] AI 赛后报告
- [ ] RAG 手球知识库
- [ ] 比赛分析 Agent

### Epic 10 Engineering Delivery

- [ ] 自动化测试、容器化、安全、日志和可观察性

## 当前范围说明

当前版本已经支持在比赛详情页上传 MP4 录像并持久保存其关联记录。

断点续传、对象存储分片、视频处理和 AI 分析仍属于后续 US 与 Epic，将在后续开发中逐步实现。

## License

本项目目前用于手球信息管理与智能比赛分析功能的开发和验证。正式开源许可证将在后续版本中补充。
