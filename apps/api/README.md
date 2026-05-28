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

早期推荐单进程运行，因为房间状态默认保存在内存中。

启动：

```bash
cd apps/api && uv run python main.py
```

测试：

```bash
cd apps/api && uv run pytest -v
```

除非项目规范被明确修改，不使用 FastAPI、Django 或其他 Python Web 框架。
