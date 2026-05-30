export const gameConfig = {
  id: "beauty-vote",
  name: "美人投票",
  summary: "规则不断变化的数字博弈——选择最接近目标值的数字，在被淘汰前活到最后。新规则随淘汰解锁，旧规则可能卷土重来。",
  rules: `
<div style="display:grid;gap:16px;">

<div>
  <p class="eyebrow" style="margin:0 0 8px;">基本玩法</p>
  <p>每回合秘密选择 <strong>0~100</strong> 整数。计算所有人数字平均值，目标值 T = 0.8 × 平均值。</p>
  <p>最接近 T 的玩家<strong>获胜不扣分</strong>；最远的 3 名扣 2 分；其余扣 1 分。</p>
  <p>初始 <strong>15 分</strong>，扣至 0 淘汰。最后存活者胜利。</p>
</div>

<div>
  <p class="eyebrow" style="margin:0 0 8px;">动态规则（核心机制）</p>
  <p>每淘汰 <strong>1~2 人</strong>（取决于存活人数），从 10 条隐藏规则中随机解锁一条。</p>
  <p>规则分三个域：<strong>独立域</strong>（永久叠加）、<strong>目标值域</strong>（互斥替换）、<strong>胜负替代域</strong>（互斥替换）。</p>
  <p style="color:var(--color-accent);font-weight:700;">被替换的规则回到池中，随时可能再次出现。</p>
</div>

<div>
  <p class="eyebrow" style="margin:0 0 8px;">特殊事件</p>
  <p>每回合 <strong>15%</strong> 概率触发：数字风暴（数字随机±5）、分数重置、匿名失效、双倍积分、幸运豁免。</p>
</div>

<div>
  <p class="eyebrow" style="margin:0 0 8px;">回合上限</p>
  <p>第 20 回合未结束时，全员分数减半，之后每回合 T=0。</p>
</div>

</div>`,
  minPlayers: 4,
  maxPlayers: 30,
  load: () => import("./web/GameApp"),
};
