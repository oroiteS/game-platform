# 轻量部署建议

目标服务器内存约 4G，因此优先单体轻量部署。

## 推荐形态

```text
Caddy 或 Nginx
  -> 前端静态文件
  -> /api 转发到 Python 后端
  -> /ws 转发到 Python 后端

Python 后端
  -> 单进程
  -> 内存房间状态
  -> SQLite 恢复信息
```

## 早期避免

早期不建议引入：

- 多个后端 worker。
- Redis。
- PostgreSQL。
- Celery。
- 消息队列。
- Docker Compose 多容器部署。
- 服务拆分。
- SSR 前端服务。

## 后端进程

本项目后端固定使用 Flask：

```bash
uv run python main.py
```

具体命令以项目实际依赖和入口为准。

## 扩展顺序

当单进程内存房间不够用时，按这个顺序扩展：

1. 优化房间过期和清理策略。
2. 引入 Redis 保存房间状态和连接映射。
3. 后端改为多 worker。
4. 引入 PostgreSQL 保存长期用户、战绩和排行榜。
5. 再考虑水平扩展。
