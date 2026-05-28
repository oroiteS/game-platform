import { useEffect, useState } from "react";
import { getRoom, joinRoom, type RoomSummary } from "../api/client";
import { LobbyDemo } from "../games/lobby-demo/LobbyDemo";
import { getRoomSession, saveRoomSession, type RoomSession } from "../platform/sessionStore";
import { useRoomSocket } from "../platform/useRoomSocket";

type RoomPageProps = {
  roomCode: string;
};

export function RoomPage({ roomCode }: RoomPageProps) {
  const [session, setSession] = useState<RoomSession | null>(() => getRoomSession(roomCode));
  const [nickname, setNickname] = useState("");
  const [room, setRoom] = useState<RoomSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const { status, snapshot, error, sendGameAction } = useRoomSocket(roomCode, session);

  const visibleRoom = snapshot?.room ?? room;

  useEffect(() => {
    setSession(getRoomSession(roomCode));
    setRoom(null);
    setFormError(null);
    getRoom(roomCode)
      .then(setRoom)
      .catch((nextError: Error) => setFormError(nextError.message));
  }, [roomCode]);

  const handleJoin = async () => {
    if (!nickname.trim()) {
      setFormError("请填写昵称");
      return;
    }

    setLoading(true);
    setFormError(null);
    try {
      const response = await joinRoom(roomCode, nickname.trim());
      const nextSession = {
        gameId: response.room.gameId,
        playerId: response.player.playerId,
        sessionToken: response.sessionToken,
        nickname: response.player.nickname,
      };
      saveRoomSession(roomCode, nextSession);
      setSession(nextSession);
      setRoom(response.room);
    } catch (nextError) {
      setFormError((nextError as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="app-shell room-shell">
      <section className="room-header">
        <div>
          <p className="eyebrow">Room</p>
          <h1>{roomCode}</h1>
        </div>
        <a className="ghost-link" href="#/">
          返回首页
        </a>
      </section>

      {!session ? (
        <section className="work-panel join-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Join</p>
              <h2>加入此房间</h2>
            </div>
          </div>
          <label>
            昵称
            <input
              value={nickname}
              onChange={(event) => setNickname(event.target.value)}
              maxLength={24}
              placeholder="输入昵称"
            />
          </label>
          <button type="button" className="primary-button" disabled={loading} onClick={handleJoin}>
            加入
          </button>
          {formError ? (
            <p className="error-text" role="alert">
              {formError}
            </p>
          ) : null}
        </section>
      ) : (
        <section className="room-grid">
          <div className="work-panel">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Status</p>
                <h2>房间状态</h2>
              </div>
              <span className={`connection-badge ${status}`}>{status}</span>
            </div>

            <dl className="room-facts">
              <div>
                <dt>游戏</dt>
                <dd>{visibleRoom?.gameId ?? session.gameId}</dd>
              </div>
              <div>
                <dt>容量</dt>
                <dd>{visibleRoom ? `${visibleRoom.players.length}/${visibleRoom.capacity}` : "-"}</dd>
              </div>
              <div>
                <dt>状态</dt>
                <dd>{visibleRoom?.status ?? "-"}</dd>
              </div>
            </dl>

            <div className="player-list">
              {(visibleRoom?.players ?? []).map((player) => (
                <div className="player-row" key={player.playerId}>
                  <span>{player.nickname}</span>
                  <span className={player.connected ? "online-text" : "offline-text"}>
                    {player.connected ? "online" : "offline"}
                  </span>
                </div>
              ))}
            </div>

            {error ? (
              <p className="error-text" role="alert">
                {error}
              </p>
            ) : null}
            {formError ? (
              <p className="error-text" role="alert">
                {formError}
              </p>
            ) : null}
          </div>

          {visibleRoom ? (
            <LobbyDemo
              room={visibleRoom}
              gameState={snapshot?.game}
              onAction={sendGameAction}
            />
          ) : null}
        </section>
      )}
    </main>
  );
}
