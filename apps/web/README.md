# Web App

前端主应用目录。

固定技术栈：

- pnpm
- React
- Vite
- TypeScript

职责：

- 首页。
- 游戏选择。
- 6 位房间号输入。
- 通用路由。
- 通用 WebSocket 客户端。
- 匿名 session 保存和恢复。
- 加载 `games/<game-id>/web/` 中的游戏入口。

安装依赖：

```bash
cd apps/web && pnpm install
```

启动：

```bash
cd apps/web && pnpm dev
```

构建：

```bash
cd apps/web && pnpm build
```

本项目不使用 npm，不使用 Next.js 或其他 SSR 前端框架。
