export const gameConfig = {
  id: "template-game",
  name: "模板游戏",
  minPlayers: 1,
  maxPlayers: 4,
  load: () => import("./web/GameApp"),
};

