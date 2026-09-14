# Handball Information Platform

手球信息与比赛分析平台。

项目目前聚焦于 Epic 1：建立赛事、比赛、球队、球员和场馆之间完整的信息查询与关联流程，并为后续比赛录像上传、AI 事件识别、视频审核和自动剪辑提供统一入口。

## 当前版本

当前版本已完成 Handball Information Platform 的核心前端功能。

主要用户可以通过赛事、球队、球员或场馆找到目标比赛，查看比赛基础信息，并从比赛详情进入后续录像上传或比赛分析流程。

> 当前仓库完成的是 Epic 1。录像上传、AI 进球识别、事件审核和视频剪辑仍属于后续开发阶段。

## 已实现功能

### 赛事

- 赛事列表
- 赛事详情
- 展示赛季、赛事级别和赛事状态
- 查看赛事下的全部比赛
- 从赛事详情进入比赛筛选结果

### 比赛

- 比赛列表
- 比赛详情
- 显示双方球队、日期、时间、比分、阶段和状态
- 显示所属赛事和比赛场馆
- 显示录像状态和 AI 分析状态
- 根据状态显示上传录像、重新上传、打开录像或查看分析入口

### 比赛筛选

比赛列表支持以下筛选条件：

- 关键词
- 赛事
- 球队
- 场馆
- 比赛日期
- 比赛阶段
- 比赛状态

支持多个条件组合筛选，以及一键清除全部筛选条件。

### 球队

- 球队列表
- 球队详情
- 展示球队基础资料
- 展示球队阵容
- 查看球队参与的比赛
- 从球队阵容进入球员详情

### 球员

- 球员列表
- 按球员名称、位置和所属球队筛选
- 球员详情
- 展示号码、位置、出生日期和所属球队
- 从球员详情进入球队详情

### 场馆

- 场馆列表
- 场馆详情
- 展示场馆地址、城市和容量
- 查看在该场馆举办的比赛
- 从场馆详情进入比赛筛选结果

### 信息关联

当前已打通以下信息关系：

```text
赛事 → 比赛
球队 → 球员
球队 → 比赛
球员 → 球队
场馆 → 比赛
比赛 → 赛事
比赛 → 球队
比赛 → 场馆
比赛 → 录像及分析入口
```

## 技术栈

- Vue 3
- TypeScript
- Vue Router
- Pinia
- Vite
- Vitest
- ESLint
- Prettier

## 数据模型

项目目前包含以下核心领域模型：

- `Competition`
- `Match`
- `Team`
- `Player`
- `Venue`
- `MatchFilters`
- `VideoStatus`
- `AnalysisStatus`

所有实体均使用稳定 ID 建立关系，避免使用显示名称作为数据关联依据。

当前阶段使用 TypeScript 模拟数据验证产品流程。后续接入后端 API 时，可以保持现有页面和类型结构不变，只替换数据访问层。

## 项目结构

```text
src/
├── assets/                 # 全局样式
├── components/             # 公共组件
│   ├── AppHeader.vue
│   ├── MatchTable.vue
│   └── NotFoundPanel.vue
├── data/
│   ├── handball.ts         # Epic 1 模拟数据和查询函数
│   └── __tests__/          # 数据关系与筛选测试
├── router/
│   └── index.ts            # 页面路由
├── types/
│   └── domain.ts           # TypeScript 领域模型
├── views/
│   ├── HomeView.vue
│   ├── CompetitionsView.vue
│   ├── CompetitionDetail.vue
│   ├── MatchesView.vue
│   ├── MatchGameDetail.vue
│   ├── TeamsView.vue
│   ├── TeamDetail.vue
│   ├── PlayersView.vue
│   ├── PlayerDetail.vue
│   ├── VenuesView.vue
│   ├── VenueDetail.vue
│   └── FeatureBoundaryView.vue
├── App.vue
└── main.ts
```

## 本地运行

### 环境要求

- Node.js `20.19+` 或 `22.12+`
- npm

### 安装依赖

```bash
npm install
```

### 启动开发服务器

```bash
npm run dev
```

启动后，根据终端显示的地址在浏览器中打开项目。默认地址通常为：

```text
http://localhost:5173
```

## 项目检查

### TypeScript 类型检查

```bash
npm run type-check
```

### 运行单元测试

```bash
npm run test:unit -- --run
```

### ESLint 检查

```bash
npx eslint .
```

### 生产环境构建

```bash
npm run build
```

### 本地预览生产构建

```bash
npm run preview
```

## 测试覆盖

当前自动化测试覆盖：

- 空筛选条件返回全部比赛
- 球队作为主队或客队时均可正确筛选
- 赛事、场馆、阶段、状态和日期组合筛选
- 关键词匹配赛事、球队、场馆和比赛阶段
- 比赛与赛事、球队、场馆的关系完整性
- 球员与球队的关系完整性
- 每项赛事至少关联一场比赛

当前检查结果：

```text
ESLint                         Passed
TypeScript type-check          Passed
Unit tests                     7 passed
Production build               Passed
Desktop browser QA             Passed
390px responsive QA            Passed
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
