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
  -> SQLite 持久化房间、玩家、session token hash 和游戏状态
  -> 进程内 WebSocket 连接管理
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

后端需要一个可写 SQLite 文件路径，默认配置为 `SQLITE_DB_PATH`。生产部署时应把该路径放到持久化磁盘目录，并确保后端进程有读写权限。SQLite 文件应纳入备份策略。

默认应用配置会把 SQLite 文件放在 `apps/api/var/game-platform.sqlite3`。部署时可以把 `SQLITE_DB_PATH` 指向挂载盘、数据盘或其他会随发布保留的目录。

SQLite 不替代跨进程实时同步。没有跨进程 WebSocket 广播前，仍推荐单后端进程。

## 扩展顺序

当单进程 SQLite 房间存储和进程内连接管理不够用时，按这个顺序扩展：

1. 优化房间过期和清理策略。
2. 引入 Redis 保存房间状态和连接映射。
3. 后端改为多 worker。
4. 引入 PostgreSQL 保存长期用户、战绩和排行榜。
5. 再考虑水平扩展。
