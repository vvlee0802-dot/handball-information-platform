# 手球数据平台部署与恢复手册

本文说明如何把项目部署到一台安装了 Docker Engine 和 Docker Compose 的 Linux 服务器，并完成健康检查、监控、备份和恢复演练。生产环境使用 Caddy 自动申请和续期 HTTPS 证书，前端 Nginx 只在 Docker 网络中访问后端，PostgreSQL、Redis、Prometheus 和 Alertmanager 不直接暴露到公网。

## 1 服务器与域名准备

1. 准备一台可运行 Docker 的 Linux 服务器，并在防火墙中只开放 TCP 22、80 和 443。
2. 将域名 A 或 AAAA 记录指向服务器公网地址。Caddy 必须能从公网完成证书验证。
3. 克隆仓库并进入项目根目录。
4. 复制生产环境模板：

```bash
cp .env.production.example .env.production
```

编辑 `.env.production`，至少替换 `APP_DOMAIN` 和 `POSTGRES_PASSWORD`。AI 功能启用时再填写百炼兼容接口、模型和密钥。不得把 `.env.production` 提交到 Git。

## 2 首次部署

```bash
ENV_FILE=.env.production ./scripts/deploy.sh
```

部署脚本会检查 Compose 配置、构建镜像、启动 PostgreSQL、Redis、FastAPI、RQ Worker、前端和 Caddy，并通过公开 HTTPS 地址执行健康检查。部署完成后创建首个管理员：

```bash
APP_ENV_FILE=.env.production docker compose --env-file .env.production \
  exec backend python -m app.scripts.create_user \
  --email admin@example.com --name "系统管理员"
```

如需导入可安全删除的演示数据：

```bash
APP_ENV_FILE=.env.production docker compose --env-file .env.production \
  exec backend python -m app.scripts.seed_demo
```

## 3 监控与告警

启动监控 profile：

```bash
APP_ENV_FILE=.env.production docker compose --env-file .env.production \
  --profile monitoring up -d prometheus alertmanager blackbox
```

Prometheus 和 Alertmanager 默认只监听服务器回环地址，分别使用端口 9090 和 9093。通过 SSH 隧道访问，避免把内部指标公开到互联网：

```bash
ssh -L 9090:127.0.0.1:9090 -L 9093:127.0.0.1:9093 user@server
```

Prometheus 展示 API 请求量、状态码、延迟、数据库和 Redis 可用性、RQ 队列深度、Worker 数量，以及视频分析、集锦、AI 报告、知识文档和 Agent 运行状态。告警规则覆盖服务不可用、依赖故障、5xx 比例、慢请求、队列积压、Worker 缺失和失败任务。Alertmanager 默认在本地 UI 汇总告警；正式值班时应在 `ops/alertmanager/alertmanager.yml` 中增加团队使用的邮件或 Webhook receiver。

## 4 备份

```bash
ENV_FILE=.env.production ./scripts/backup.sh
```

每次备份会在 `backups/<UTC 时间>/` 中生成 PostgreSQL 自定义格式备份、媒体目录压缩包、SHA-256 校验文件和清单。应把整个时间目录复制到服务器之外的加密存储，并按组织要求设置保留周期。

## 5 无损恢复演练

恢复演练始终写入独立的 `handball_restore_check` 数据库，不覆盖生产数据库：

```bash
ENV_FILE=.env.production ./scripts/restore-check.sh \
  backups/<UTC 时间>/database.dump
```

脚本验证数据库表数量和 Alembic 版本，结果写入 `backups/restore-reports/`，随后删除演练数据库。设置 `KEEP_RESTORE_DB=1` 可以暂时保留演练数据库做进一步核查。脚本会拒绝把恢复目标设置成生产数据库或 `postgres`。

## 6 发布验收与回滚

发布前在开发或测试机执行：

```bash
./scripts/release-check.sh
```

该脚本验证 Compose、构建前后端镜像、启动所有核心服务，并检查前端、API 和 Worker。生产发布后再次运行 `scripts/smoke-test.sh`，同时在 Prometheus 中确认服务探针和依赖指标均为 1。

回滚时切回上一条已验证的 Git 提交，再运行部署脚本。数据库结构发生变化前必须先备份；不得对生产数据执行 `git reset`、删除 Docker volume 或直接运行恢复演练数据库之外的覆盖操作。
