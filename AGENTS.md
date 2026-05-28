# AGENTS.md

## 语言规范

Always respond in Chinese-simplified.

## 项目目标

这是一个轻量级多人游戏平台。开发结构采用 Monorepo 和游戏模块化设计，但部署运行保持单体轻量。

优先阅读：

1. `README.md`
2. `docs/architecture.md`
3. `docs/add-new-game.md`
4. `docs/development.md`
5. `packages/game-contract/README.md`

## 技术约定

- 前端固定使用 pnpm + React + Vite + TypeScript。
- 不使用 npm。
- 不使用 Next.js 或其他 SSR 前端框架。
- 后端默认使用 uv。
- 后端 Web 框架固定使用 Flask。
- WebSocket 优先使用 Flask-Sock。
- 不在未确认的情况下下载或安装新环境。
- 项目代码运行、测试优先使用 uv。
- skills 或独立脚本可使用 Python 或 Python3，避免污染项目环境。

## 架构约定

- 平台能力放在 `apps/` 和 `packages/`。
- 具体游戏放在 `games/<game-id>/`。
- 新增游戏优先复制 `games/_template/`。
- 平台负责房间、连接、匿名身份、断线重连。
- 游戏模块只负责游戏规则、前端界面和游戏事件。
- 默认不做登录，使用匿名玩家 + `sessionToken` 恢复。
- 早期不引入 Redis、PostgreSQL、消息队列或多 worker。

## 后续开发原则

- 修改平台能力前，先确认是否会影响所有游戏。
- 修改游戏能力时，优先限制在对应 `games/<game-id>/` 目录。
- 如果发现两个以上游戏重复代码，再考虑抽到 `packages/`。
- 文档和契约变化要同步更新 `docs/` 和 `packages/game-contract/`。
