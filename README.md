# Ticket Desk

迷你工单台：本地 Web API，支持派工单、写备注、标记阻塞、标记完成。无登录、无前端。数据存 PostgreSQL。

## 技术栈

- **API**：Python FastAPI + SQLAlchemy + Uvicorn
- **数据库**：PostgreSQL 16
- **编排**：Docker Compose（`api` + `db`，可选 `test`）

## 前置要求

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)（含 Compose）
- 能拉取镜像（若访问 Docker Hub 超时，需配置国内镜像加速，见文末）

## 快速启动

```powershell
cd D:\Work\Ticket-Desk
copy .env.example .env
docker compose up -d --build
```

启动后 API 地址：`http://127.0.0.1:8000`

Swagger 文档：`http://127.0.0.1:8000/docs`

检查是否就绪：

```powershell
curl.exe http://127.0.0.1:8000/healthz
```

期望：

```json
{"ok":true,"db":"up"}
```

停止服务：

```powershell
docker compose down
```

清除数据卷（会删库）：

```powershell
docker compose down -v
```

## 环境变量

复制 `.env.example` 为 `.env` 后按需修改。**不要把 `.env` 提交进仓库。**

| 变量 | 说明 | 示例 |
|------|------|------|
| `POSTGRES_DB` | 数据库名 | `ticketdesk` |
| `POSTGRES_USER` | 数据库用户 | `ticket` |
| `POSTGRES_PASSWORD` | 数据库密码 | 自行设置 |

`api` 容器内的 `DATABASE_URL` 由 Compose 根据上述变量自动拼接，无需手写。

## 项目结构

```text
Ticket-Desk/
├── app/
│   ├── main.py          # 路由与业务
│   ├── db.py            # 数据库与模型
│   └── schemas.py       # 请求/响应模型
├── tests/
│   └── test_api.py      # 对接真实 API 的集成测试
├── compose.yaml
├── Dockerfile
├── requirements.txt
├── .env.example
└── .env                 # 本地配置（不入库）
```

## 接口一览

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/healthz` | 健康检查（含数据库） |
| `POST` | `/tickets` | 创建工单 |
| `GET` | `/tickets` | 列表（可筛选） |
| `GET` | `/tickets/{id}` | 工单详情 |
| `POST` | `/tickets/{id}/notes` | 添加备注 |
| `POST` | `/tickets/{id}/block` | 标记阻塞（幂等） |
| `POST` | `/tickets/{id}/done` | 标记完成 |

通用错误：

| HTTP | body |
|------|------|
| `400` | `{"error":"wrong_parameter"}` |
| `404` | `{"error":"ticket_not_found"}` |
| `409` | `{"error":"already_done"}` |
| `503` | `{"ok":false,"db":"down"}`（仅 `/healthz`） |

---

### `GET /healthz`

数据库正常：`200` + `{"ok":true,"db":"up"}`  
数据库异常：`503` + `{"ok":false,"db":"down"}`

```powershell
curl.exe http://127.0.0.1:8000/healthz
```

---

### `POST /tickets`

创建工单。`title` 必填（1～80 字），`assignee` 必填，`priority` 为 `low` / `medium` / `high`（默认 `medium`）。成功 `201`，`status` 为 `open`。

```powershell
curl.exe -X POST http://127.0.0.1:8000/tickets -H "Content-Type: application/json" -d "{\"title\":\"修登录页\",\"assignee\":\"intern\",\"priority\":\"high\"}"
```

示例响应：

```json
{
  "id": 1,
  "title": "修登录页",
  "assignee": "intern",
  "priority": "high",
  "status": "open",
  "created_at": "2026-08-20T05:55:00.000000Z",
  "notes": []
}
```

缺 `title`（应 `400`）：

```powershell
curl.exe -i -X POST http://127.0.0.1:8000/tickets -H "Content-Type: application/json" -d "{\"assignee\":\"intern\"}"
```

---

### `GET /tickets`

返回数组，按 `created_at` 新→旧。支持查询参数：

- `?status=open` / `?status=done` / `?status=blocked`
- `?assignee=intern`

```powershell
curl.exe "http://127.0.0.1:8000/tickets"
```

```powershell
curl.exe "http://127.0.0.1:8000/tickets?status=open"
```

```powershell
curl.exe "http://127.0.0.1:8000/tickets?status=blocked"
```

```powershell
curl.exe "http://127.0.0.1:8000/tickets?assignee=intern"
```

---

### `GET /tickets/{id}`

```powershell
curl.exe http://127.0.0.1:8000/tickets/1
```

不存在时 `404`：`{"error":"ticket_not_found"}`

---

### `POST /tickets/{id}/notes`

请求体只需 `body`（1～500 字）。成功 `201`，响应为完整备注对象（含服务端生成的 `id`、`ticket_id`、`created_at`）。

```powershell
curl.exe -X POST http://127.0.0.1:8000/tickets/1/notes -H "Content-Type: application/json" -d "{\"body\":\"复现了，准备改\"}"
```

示例响应：

```json
{
  "id": 1,
  "ticket_id": 1,
  "body": "复现了，准备改",
  "created_at": "2026-08-20T05:55:43.092997Z"
}
```

工单不存在（应 `404`）：

```powershell
curl.exe -i -X POST http://127.0.0.1:8000/tickets/999999/notes -H "Content-Type: application/json" -d "{\"body\":\"不会成功\"}"
```

---

### `POST /tickets/{id}/block`

将工单状态设为 `blocked`。无需请求体。已是 `blocked` 时再次调用仍返回 `200`（幂等）。不存在时 `404`。

```powershell
curl.exe -X POST http://127.0.0.1:8000/tickets/1/block
```

```powershell
curl.exe -i -X POST http://127.0.0.1:8000/tickets/999999/block
```

---

### `POST /tickets/{id}/done`

将工单状态设为 `done`。已完成再调一次返回 `409`：`{"error":"already_done"}`。

```powershell
curl.exe -X POST http://127.0.0.1:8000/tickets/1/done
```

```powershell
curl.exe -i -X POST http://127.0.0.1:8000/tickets/1/done
```

请把命令中的 `1` 换成实际工单 `id`。

---

## 自动测试

先确保 `api` / `db` 已启动，再跑 Compose 的 `test` 服务（对真实 API 发请求）：

```powershell
docker compose up -d --build
docker compose --profile test run --rm test
```

成功示例：

```text
.........                                                              [100%]
9 passed in 0.XXs
```

覆盖场景包括：创建工单、缺 title 返回 400、完成工单、完成不影响其它工单、重复完成 409、写备注 404、阻塞工单、重复阻塞幂等、阻塞不存在工单 404。  
每条用例结束后会删除**本次测试创建的工单**（备注随外键 CASCADE 一并清除），不整库清空，以免误删你手动造的数据。

更详细输出：

```powershell
docker compose --profile test run --rm test pytest -v /app/tests
```

## 推荐手动验收顺序

在 PowerShell 中逐条执行（每条单行，避免粘贴时只跑第一行）：

```powershell
curl.exe http://127.0.0.1:8000/healthz
curl.exe -X POST http://127.0.0.1:8000/tickets -H "Content-Type: application/json" -d "{\"title\":\"修登录页\",\"assignee\":\"intern\",\"priority\":\"high\"}"
curl.exe "http://127.0.0.1:8000/tickets"
curl.exe http://127.0.0.1:8000/tickets/1
curl.exe -X POST http://127.0.0.1:8000/tickets/1/notes -H "Content-Type: application/json" -d "{\"body\":\"复现了，准备改\"}"
curl.exe -X POST http://127.0.0.1:8000/tickets/1/block
curl.exe -X POST http://127.0.0.1:8000/tickets/1/done
curl.exe -i -X POST http://127.0.0.1:8000/tickets/1/done
```

Windows 请使用 `curl.exe`，不要用 PowerShell 里别名为 `Invoke-WebRequest` 的 `curl`。

## 常见问题

### 构建时拉不了 `python:3.12-slim` / 连接 `registry-1.docker.io` 超时

多为无法直连 Docker Hub。打开 **Docker Desktop → Settings → Docker Engine**，增加镜像加速后 Apply & restart，例如：

```json
{
  "registry-mirrors": [
    "https://docker.1ms.run",
    "https://docker.xuanyuan.me",
    "https://docker.m.daocloud.io"
  ]
}
```

然后再执行 `docker compose up -d --build`。

### `healthz` 一直失败

```powershell
docker compose ps
docker compose logs api
docker compose logs db
```

确认 `db` 为 healthy，`.env` 中账号密码与首次初始化一致（改密码后若沿用旧数据卷，可能连不上，需 `docker compose down -v` 后重建）。

### 端口被占用

API 默认绑定 `127.0.0.1:8000`。若冲突，修改 `compose.yaml` 中 `api.ports` 后再启动。
