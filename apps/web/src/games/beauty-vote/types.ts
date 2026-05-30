export type GamePhase = "lobby" | "submit" | "reveal" | "ended";

export interface RuleInfo {
  id: number;
  name: string;
  description: string;
}

export interface ActiveRules {
  independent: number[];
  target_value: number | null;
  win_loss_alt: number | null;
}

export interface SpecialEvent {
  type: "number_storm" | "score_reset" | "double_points" | "lucky_exemption";
  target_player: string | null;
}

export interface Calculation {
  method: string;
  label: string;
  detail: string;
}

export interface PlayerState {
  playerId: string;
  nickname: string;
  score: number;
  alive: boolean;
  lastNumber: number | null;
}

export interface MySubmission {
  number: number;
  use_leverage: boolean;
  reverse_number: number | null;
  betray_target: string | null;
}

export interface BeautyVoteState {
  phase: GamePhase;
  round: number;
  players: PlayerState[];
  readyPlayerIds: string[];
  capacity: number;
  currentT: number | null;
  lastT: number | null;
  forbiddenNumber: number | null;
  activeRules: ActiveRules;
  rulesDisplay: RuleInfo[] | null;
  specialEvent: SpecialEvent | null;
  winnerIds: string[];
  furthestIds: string[];
  ruleLog: Array<{ unlocked: number; replaced: number | null; message: string; round: number }>;
  roundLog: Record<string, unknown> | null;
  calculation: Calculation | null;
  hasHiddenRule: boolean;
  mySubmission: MySubmission | null;
  allSubmissions: Record<number, Record<string, number>> | null;
  totalEliminations: number;
}
