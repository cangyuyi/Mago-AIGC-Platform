# API 设计规范

## 统一响应格式

```json
{
  "code": 0,
  "message": "ok",
  "data": { ... }
}
```

- `code = 0` 表示成功
- `code != 0` 表示错误，`message` 为错误描述
- HTTP状态码与code配合使用

## 分页格式

```
GET /api/v1/projects?page=1&page_size=20
```

响应:
```json
{
  "code": 0,
  "data": {
    "items": [...],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

## 认证

所有受保护接口需要Header:
```
Authorization: Bearer <access_token>
```

## 主要端点

### 认证
- POST /api/v1/auth/register
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh
- GET  /api/v1/auth/me

### 项目
- GET    /api/v1/projects
- POST   /api/v1/projects
- GET    /api/v1/projects/:id
- PUT    /api/v1/projects/:id
- DELETE /api/v1/projects/:id

### Agent (SSE流式)
- POST /api/v1/agent/run → text/event-stream

### 热点（后续实现）
- GET /api/v1/trends
- POST /api/v1/viral-videos/analyze

### 脚本/分镜/提示词（后续实现）
- CRUD /api/v1/scripts
- CRUD /api/v1/storyboards
- CRUD /api/v1/prompt-packages
