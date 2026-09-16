# Handball Information Platform

手球信息与比赛分析平台。目前已完成 Epic 1 页面基线，以及 Epic 2 的 US2.1 业务数据接入。

用户可以通过赛事、比赛、球队、球员或场馆查找信息。主要页面的数据现由 FastAPI 从 PostgreSQL 读取，不再只依赖浏览器中的静态内容。录像上传、AI 事件识别、视频审核和自动剪辑仍属于后续开发范围。

## US2.1 本版改动

1. 完成 Vue 3 + TypeScript 前端与 FastAPI 后端分离，并通过 Vite 代理连接 `/api`。
2. 建立 PostgreSQL、SQLAlchemy 和 Alembic 数据层，实现赛事、球队、球员、场馆和比赛的数据持久化与迁移。
3. 实现基础数据的新增、列表、详情和编辑接口，并加入外键存在性、主客队差异及完赛比分完整性校验。
4. 将主要页面从前端静态数据切换为真实 API 数据，补充关联展示、错误状态和前后端自动化测试，并用 v1.0 需求文档替换旧版需求。

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
python -m uvicorn app.main:app --reload --port 8000
```

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
Frontend unit tests            15 passed
Backend tests                  12 passed
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

### Epic 2 Match Video Management

- [x] US2.1 基础业务数据后端化与持久化
- [ ] MP4 视频上传
- [ ] 视频与比赛记录关联
- [ ] 上传进度和错误状态
- [ ] 视频处理状态管理

### Epic 3 AI Match Event Detection

- [ ] 自动检测进球事件
- [ ] 保存事件时间戳
- [ ] 保存 AI 置信度和检测来源
- [ ] 从事件跳转到对应视频时间

### Epic 4 Event Review and Match Analysis

- [ ] 事件类型筛选
- [ ] 人工新增事件
- [ ] 删除误识别事件
- [ ] 调整事件时间点
- [ ] 事件统计

### Epic 5 Video Clip and Export

- [ ] 自动生成事件片段
- [ ] 单个片段导出
- [ ] 批量导出进球片段

### Epic 6 Player Analysis and Personal Highlights

- [ ] 比赛事件与球员关联
- [ ] 球员单场统计
- [ ] 从统计指标查看对应视频
- [ ] 自动生成个人集锦

## 当前范围说明

当前版本中的“上传录像”和“查看分析”页面用于建立完整的产品导航流程。

这些页面暂时只显示功能边界说明，不执行真实文件上传、视频处理或 AI 分析。对应能力将在 Epic 2 至 Epic 5 中逐步实现。

## License

本项目目前用于手球信息管理与智能比赛分析功能的开发和验证。正式开源许可证将在后续版本中补充。
