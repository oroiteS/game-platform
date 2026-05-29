export const gameConfig = {
  id: "fake-person",
  name: "伪人游戏",
  summary: "谁是伪人？玩家秘密获取身份，主持人猜测每个人的真实身份。",
  rules: (
    "1 名主持人（不参与），其余玩家秘密选择「人类」或「伪人」身份。"
    + "伪人随机获得一个关键词。主持人抽取问题后，玩家线下轮流回答"
    + "（伪人必须将关键词融入回答）。主持人逐一猜测每个玩家是人是伪人，"
    + "猜错即揭示真相。"
  ),
  minPlayers: 3,
  maxPlayers: 10,
  load: () => import("./web/GameApp"),
};
