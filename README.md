# Lightweight Game Platform

这是一个面向多人房间游戏的轻量级平台骨架。

目标是让平台能力和具体游戏解耦：平台负责首页、房间、实时连接、匿名身份恢复；每个游戏只实现自己的前端界面、游戏规则和后端事件处理。

## 设计原则

- 开发结构模块化，运行部署轻量化。
- 新增游戏优先在 `games/<game-id>/` 内完成。
- 平台代码只提供通用能力，不写具体游戏规则。
- 默认不做登录，使用匿名玩家身份和 `sessionToken` 支持快速恢复。
- 早期部署只需要一个前端静态站点和一个 Python 后端进程。

## 目录

```text
apps/
  web/                  React + Vite + TypeScript 前端主应用
  api/                  Python 后端主服务
packages/
  game-contract/        游戏模块契约说明和类型草案
  shared/               跨前后端共享的协议、常量、文档
  ui/                   可复用 UI 组件，按需使用
games/
  _template/            新增游戏模板
docs/
  architecture.md       架构说明
  add-new-game.md       新增游戏指南
  development.md        开发约定
  deployment.md         轻量部署建议
```

## 推荐技术

- 前端：pnpm + React + Vite + TypeScript
- 后端：Python + Flask，实时连接优先使用 Flask-Sock
- Python 包管理：uv
- 第一阶段存储：SQLite 持久化房间、玩家、session token hash 和游戏状态；WebSocket 连接仍在进程内管理
- 实时连接：WebSocket

## 本地启动

后端：

```bash
cd apps/api && uv run python main.py
```

前端：

```bash
cd apps/web && pnpm dev
```

验证命令：

```bash
cd apps/api && uv run pytest -v
cd apps/web && pnpm build
```

首页提供创建房间和进入房间两个主要流程。创建房间时，房主选择游戏并输入本局人数；平台会校验人数不超过平台硬上限和游戏人数上限。进入房间时只需要输入 6 位房间号；如果本地没有该房间的 session，房间页会要求填写昵称并调用加入接口，加入上限以房间创建时保存的本局人数为准。

右上角或页面角落的 Games 入口会显示游戏目录，可以查看每个游戏的简介、人数范围和规则详情。

## 新增游戏入口

先阅读：

1. `docs/add-new-game.md`
2. `docs/architecture.md`
3. `games/_template/README.md`
4. `packages/game-contract/README.md`
