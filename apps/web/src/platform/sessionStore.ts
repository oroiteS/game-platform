const STORAGE_KEY = "game-platform.sessions";

export type RoomSession = {
  gameId: string;
  playerId: string;
  sessionToken: string;
  nickname: string;
};

type StoredSessions = Record<string, RoomSession>;

function readSessions(): StoredSessions {
  if (typeof window === "undefined") {
    return {};
  }

  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return {};
  }

  try {
    const parsed = JSON.parse(raw) as StoredSessions;
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function writeSessions(sessions: StoredSessions): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
}

export function getRoomSession(roomCode: string): RoomSession | null {
  return readSessions()[roomCode] ?? null;
}

export function saveRoomSession(roomCode: string, session: RoomSession): void {
  const sessions = readSessions();
  sessions[roomCode] = session;
  writeSessions(sessions);
}

export function clearRoomSession(roomCode: string): void {
  const sessions = readSessions();
  delete sessions[roomCode];
  writeSessions(sessions);
}
