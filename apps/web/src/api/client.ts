export type GameSummary = {
  id: string;
  name: string;
  summary: string;
  minPlayers: number;
  maxPlayers: number;
};

export type GameDetail = GameSummary & {
  rules: string;
};

export type PlayerSummary = {
  playerId: string;
  nickname: string;
  connected: boolean;
};

export type RoomSummary = {
  roomCode: string;
  gameId: string;
  status: string;
  capacity: number;
  players: PlayerSummary[];
};

export type JoinResponse = {
  room: RoomSummary;
  player: PlayerSummary;
  sessionToken: string;
};

type ApiErrorBody = {
  error?: {
    code?: string;
    message?: string;
  };
};

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let message = `请求失败 (${response.status})`;
    try {
      const body = (await response.json()) as ApiErrorBody;
      message = body.error?.message ?? body.error?.code ?? message;
    } catch {
      // Keep the generic HTTP status message.
    }
    throw new Error(message);
  }

  return (await response.json()) as T;
}

export async function getGames(): Promise<GameSummary[]> {
  const payload = await requestJson<{ games: GameSummary[] }>("/api/games");
  return payload.games;
}

export async function getGame(gameId: string): Promise<GameDetail> {
  const payload = await requestJson<{ game: GameDetail }>(
    `/api/games/${encodeURIComponent(gameId)}`,
  );
  return payload.game;
}

export async function createRoom(
  gameId: string,
  nickname: string,
  capacity: number,
): Promise<JoinResponse> {
  return requestJson<JoinResponse>("/api/rooms", {
    method: "POST",
    body: JSON.stringify({ gameId, nickname, capacity }),
  });
}

export async function joinRoom(roomCode: string, nickname: string): Promise<JoinResponse> {
  return requestJson<JoinResponse>(`/api/rooms/${encodeURIComponent(roomCode)}/join`, {
    method: "POST",
    body: JSON.stringify({ nickname }),
  });
}

export async function getRoom(roomCode: string): Promise<RoomSummary> {
  const payload = await requestJson<{ room: RoomSummary }>(
    `/api/rooms/${encodeURIComponent(roomCode)}`,
  );
  return payload.room;
}
