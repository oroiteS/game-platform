export const gameConfig = {
  id: "fake-person",
  name: "伪人游戏",
  summary: "谁是伪人？玩家秘密获取身份，主持人猜测每个人的真实身份。",
  rules: `
    <div style="display:grid;gap:16px;">
      <div>
        <p class="eyebrow" style="margin:0 0 8px;">角色</p>
        <p><strong style="color:var(--color-primary-strong);">1 名主持人</strong> — 不参与身份分配，负责抽题和猜测</p>
        <p><strong style="color:var(--color-accent);">其余玩家</strong> — 秘密选择「人类」或「伪人」</p>
      </div>
      <div>
        <p class="eyebrow" style="margin:0 0 8px;">流程</p>
        <ol style="margin:0;padding-left:1.2em;display:grid;gap:6px;">
          <li>所有玩家<strong>准备</strong>，其中一人成为<strong>主持人</strong></li>
          <li>每位玩家秘密选择<strong>人类</strong>或<strong>伪人</strong>身份</li>
          <li>伪人自动获得一个<strong style="color:var(--color-accent);">关键词</strong></li>
          <li>主持人抽取问题，玩家<strong>线下口头</strong>轮流回答</li>
          <li style="color:var(--color-accent);font-weight:700;">伪人必须将关键词自然融入回答</li>
          <li>主持人逐一猜测每个玩家的真实身份</li>
          <li>猜错立刻揭示真相；全部猜对则伪人获胜</li>
        </ol>
      </div>
    </div>
  `,
  minPlayers: 3,
  maxPlayers: 10,
  load: () => import("./web/GameApp"),
};
