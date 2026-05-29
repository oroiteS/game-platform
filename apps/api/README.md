# API App

后端主服务目录。

建议技术栈：

- Python
- uv
- Flask
- Flask-Sock
- SQLite

职责：

- HTTP API。
- WebSocket API。
- RoomManager。
- 匿名玩家 session。
- 断线重连。
- 房间过期清理入口。
- 游戏后端模块注册。

早期推荐单进程运行。房间、玩家、session token hash 和游戏状态会保存到 SQLite；当前 WebSocket 连接仍保存在进程内。

关键配置：

- `SQLITE_DB_PATH`
- `ROOM_TTL_SECONDS`
- `EMPTY_ROOM_TTL_SECONDS`
- `PLAYER_ONLINE_TIMEOUT_SECONDS`：玩家心跳或动作超过该秒数未更新后，可被标记为断线；默认 30 秒。
- `DISCONNECTED_PLAYER_TTL_SECONDS`：预留，当前不删除单个断线玩家。
- `ROOM_CLEANUP_ENABLED`：预留，当前没有后台调度器自动执行清理。
- `ROOM_CLEANUP_INTERVAL_SECONDS`：预留，当前没有后台调度器读取该间隔。

当前房间清理入口是 `RoomManager.cleanup_expired_rooms(...)`，需要由测试、维护脚本或后续调度器显式调用。

启动：

```bash
cd apps/api && uv run python main.py
```

测试：

```bash
cd apps/api && uv run pytest -v
```

除非项目规范被明确修改，不使用 FastAPI、Django 或其他 Python Web 框架。
