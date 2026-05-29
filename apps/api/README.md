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
- 房间过期清理。
- 游戏后端模块注册。

早期推荐单进程运行。房间、玩家、session token hash 和游戏状态会保存到 SQLite；当前 WebSocket 连接仍保存在进程内。

关键配置：

- `SQLITE_DB_PATH`
- `ROOM_TTL_SECONDS`
- `EMPTY_ROOM_TTL_SECONDS`
- `DISCONNECTED_PLAYER_TTL_SECONDS`
- `ROOM_CLEANUP_ENABLED`
- `ROOM_CLEANUP_INTERVAL_SECONDS`

启动：

```bash
cd apps/api && uv run python main.py
```

测试：

```bash
cd apps/api && uv run pytest -v
```

除非项目规范被明确修改，不使用 FastAPI、Django 或其他 Python Web 框架。
