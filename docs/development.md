# 开发约定

## 环境原则

- 前端固定使用 pnpm + React + Vite + TypeScript。
- 后端默认使用 uv。
- 后端 Web 框架固定使用 Flask。
- 不使用 npm。
- 不使用 Next.js 或其他 SSR 前端框架。
- 不在没有确认的情况下下载或安装新环境。
- 项目代码运行、测试优先使用 uv。
- skills 或独立脚本可使用 Python 或 Python3，避免污染项目环境。

## 前端约定

前端主应用位于 `apps/web/`。

固定技术栈：

- pnpm
- React
- Vite
- TypeScript

前端产物应构建为静态文件，由 Caddy 或 Nginx 提供访问。

建议职责：

- 首页。
- 游戏选择。
- 房间号输入。
- 路由。
- 通用 WebSocket 客户端。
- 断线重连提示。
- 调用游戏前端入口。

游戏界面代码放在 `games/<game-id>/web/`。

除非项目规范被明确修改，不引入 Next.js、Nuxt、Remix 或其他 SSR 前端框架。

### 前端开发命令

首次进入前端目录后安装依赖：

```bash
cd apps/web && pnpm install
```

启动开发服务器：

```bash
cd apps/web && pnpm dev
```

构建验证：

```bash
cd apps/web && pnpm build
```

如果 pnpm 忽略了 esbuild 的 build scripts，Vite 构建可能失败。处理方式任选其一：

```bash
cd apps/web && pnpm approve-builds --all
cd apps/web && pnpm rebuild esbuild
```

或在 `apps/web/pnpm-workspace.yaml` 中设置：

```yaml
allowBuilds:
  esbuild: true
```

然后执行：

```bash
cd apps/web && pnpm rebuild esbuild
```

## 后端约定

后端主应用位于 `apps/api/`。

建议职责：

- 应用启动。
- 配置加载。
- HTTP 路由。
- WebSocket 路由。
- RoomManager。
- storage 层。
- Session 恢复。
- 游戏注册表。

后端固定使用 Flask，建议保持：

```text
apps/api/
  main.py
  config.py
  extensions.py
  app/
    __init__.py
    platform/
      routes/
      services/
```

实时连接优先使用 Flask-Sock。除非项目规范被明确修改，不引入 FastAPI、Django 或其他 Python Web 框架。

平台持久化通过 `RoomManager` 下方的 storage 层完成。业务规则留在 `RoomManager`，SQLite 读写留在 storage。新增持久化测试应使用 pytest `tmp_path` 创建临时 SQLite 文件。

后端关键配置：

- `SQLITE_DB_PATH`：SQLite 文件路径，默认指向 `apps/api/var/game-platform.sqlite3`。
- `ROOM_TTL_SECONDS`：房间最大保留时间。
- `EMPTY_ROOM_TTL_SECONDS`：所有玩家断线后的空房间保留时间。
- `DISCONNECTED_PLAYER_TTL_SECONDS`：预留配置，当前未接入玩家级断线清理逻辑；当前重连取决于房间仍存在且 `sessionToken` 校验通过。
- `ROOM_CLEANUP_ENABLED`：预留配置，当前没有后台调度器读取该配置自动执行清理。
- `ROOM_CLEANUP_INTERVAL_SECONDS`：预留配置，当前没有后台调度器读取该配置作为清理间隔。

当前可确定使用的清理入口是 `RoomManager.cleanup_expired_rooms(...)`。测试或维护脚本可以显式调用该方法验证 `ROOM_TTL_SECONDS` 和 `EMPTY_ROOM_TTL_SECONDS` 对房间删除的影响。

### 后端开发命令

启动后端：

```bash
cd apps/api && uv run python main.py
```

运行测试：

```bash
cd apps/api && uv run pytest -v
```

## 文档优先级

开发新功能前，先确认是否需要更新：

- `docs/architecture.md`
- `docs/add-new-game.md`
- `packages/game-contract/README.md`
- 对应游戏的 `README.md`

## 测试建议

新增游戏至少覆盖：

- 初始状态创建。
- 玩家加入。
- 玩家断线。
- 玩家重连。
- 玩家离开。
- 合法操作。
- 非法操作。
- 状态快照。

平台层至少覆盖：

- 6 位房间号校验。
- 创建房间。
- 加入房间。
- sessionToken 恢复。
- 房间 TTL 和空房间 TTL 清理。
- SQLite 持久化和重启恢复。
