import { useEffect, useState, type FormEvent } from "react";
import { Button } from "../components/ui/Button";
import { FieldError } from "../components/ui/FieldError";
import { Panel } from "../components/ui/Panel";
import { StatusBadge } from "../components/ui/StatusBadge";
import { TextField } from "../components/ui/TextField";
import { getRoom, joinRoom, type PlayerSummary, type RoomSummary } from "../api/client";
import { LobbyDemo } from "../games/lobby-demo/LobbyDemo";
import { FakePersonGame } from "../games/fake-person/FakePersonGame";
import { BeautyVoteGame } from "../games/beauty-vote/GameApp";
import { getRoomSession, saveRoomSession, type RoomSession } from "../platform/sessionStore";
import { useRoomSocket, type SocketStatus } from "../platform/useRoomSocket";

type RoomPageProps = {
  roomCode: string;
};

function connectionLabel(status: SocketStatus): string {
  if (status === "open") {
    return "已连接";
  }
  if (status === "connecting") {
    return "连接中";
  }
  if (status === "closed") {
    return "已断开";
  }
  return "未连接";
}

function connectionTone(status: SocketStatus): "neutral" | "success" | "warning" | "danger" {
  if (status === "open") {
    return "success";
  }
  if (status === "connecting") {
    return "warning";
  }
  if (status === "closed") {
    return "danger";
  }
  return "neutral";
}

function RoomHeader({ roomCode }: { roomCode: string }) {
  return (
    <section className="room-header">
      <div>
        <p className="eyebrow">Room</p>
        <h1>{roomCode}</h1>
      </div>
      <a className="ui-link-button" href="#/">
        返回首页
      </a>
    </section>
  );
}

function JoinRoomPanel({
  nickname,
  loading,
  roomError,
  formError,
  onNicknameChange,
  onSubmit,
}: {
  nickname: string;
  loading: boolean;
  roomError: string | null;
  formError: string | null;
  onNicknameChange: (nickname: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <Panel className="join-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Join</p>
          <h2>加入此房间</h2>
        </div>
      </div>
      {roomError ? <FieldError message={roomError} /> : null}
      <form className="form-stack" onSubmit={onSubmit} noValidate>
        <TextField
          id="room-nickname"
          name="nickname"
          label="昵称"
          value={nickname}
          onChange={(event) => onNicknameChange(event.target.value)}
          autoComplete="nickname"
          maxLength={24}
          placeholder="输入昵称…"
          error={formError}
        />
        <Button type="submit" disabled={loading}>
          {loading ? "加入中…" : "加入房间"}
        </Button>
      </form>
    </Panel>
  );
}

function RoomFacts({
  room,
  fallbackGameId,
}: {
  room: RoomSummary | null;
  fallbackGameId: string;
}) {
  return (
    <dl className="room-facts">
      <div>
        <dt>游戏</dt>
        <dd>{room?.gameId ?? fallbackGameId}</dd>
      </div>
      <div>
        <dt>容量</dt>
        <dd>{room ? `${room.players.length}/${room.capacity}` : "-"}</dd>
      </div>
      <div>
        <dt>状态</dt>
        <dd>{room?.status ?? "-"}</dd>
      </div>
    </dl>
  );
}

function PlayerList({ players }: { players: PlayerSummary[] }) {
  return (
    <section className="player-list" aria-labelledby="room-player-list-title">
      <h3 id="room-player-list-title">玩家列表</h3>
      {players.length === 0 ? <p className="state-text">暂无玩家</p> : null}
      {players.map((player) => (
        <div className="player-row" key={player.playerId}>
          <span>{player.nickname}</span>
          <StatusBadge tone={player.connected ? "success" : "neutral"}>
            {player.connected ? "在线" : "离线"}
          </StatusBadge>
        </div>
      ))}
    </section>
  );
}

function RoomStatusPanel({
  room,
  session,
  connectionStatus,
  socketError,
  roomError,
  roomLoading,
}: {
  room: RoomSummary | null;
  session: RoomSession;
  connectionStatus: SocketStatus;
  socketError: string | null;
  roomError: string | null;
  roomLoading: boolean;
}) {
  return (
    <Panel>
      <div className="section-heading">
        <div>
          <p className="eyebrow">Status</p>
          <h2>房间状态</h2>
        </div>
        <StatusBadge
          tone={connectionTone(connectionStatus)}
          aria-live="polite"
          aria-atomic="true"
        >
          {connectionLabel(connectionStatus)}
        </StatusBadge>
      </div>

      {roomLoading ? <p className="state-text" aria-live="polite">正在读取房间状态…</p> : null}
      <RoomFacts room={room} fallbackGameId={session.gameId} />
      <PlayerList players={room?.players ?? []} />

      {socketError ? <FieldError message={socketError} /> : null}
      {roomError ? <FieldError message={roomError} /> : null}
    </Panel>
  );
}

export function RoomPage({ roomCode }: RoomPageProps) {
  const [session, setSession] = useState<RoomSession | null>(() => getRoomSession(roomCode));
  const [nickname, setNickname] = useState("");
  const [room, setRoom] = useState<RoomSummary | null>(null);
  const [roomLoading, setRoomLoading] = useState(false);
  const [joining, setJoining] = useState(false);
  const [roomError, setRoomError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const { status, snapshot, error, sendGameAction } = useRoomSocket(roomCode, session);

  const visibleRoom = snapshot?.room ?? room;

  useEffect(() => {
    let stale = false;

    setSession(getRoomSession(roomCode));
    setRoom(null);
    setFormError(null);
    setRoomError(null);
    setRoomLoading(true);

    getRoom(roomCode)
      .then((nextRoom) => {
        if (!stale) {
          setRoom(nextRoom);
        }
      })
      .catch((nextError: Error) => {
        if (!stale) {
          setRoomError(nextError.message);
        }
      })
      .finally(() => {
        if (!stale) {
          setRoomLoading(false);
        }
      });

    return () => {
      stale = true;
    };
  }, [roomCode]);

  const handleJoin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!nickname.trim()) {
      setFormError("请填写昵称");
      return;
    }

    setJoining(true);
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
      setJoining(false);
    }
  };

  return (
    <main className="app-shell room-shell" id="main-content">
      <RoomHeader roomCode={roomCode} />

      {!session ? (
        <JoinRoomPanel
          nickname={nickname}
          loading={joining}
          roomError={roomError}
          formError={formError}
          onNicknameChange={setNickname}
          onSubmit={handleJoin}
        />
      ) : (
        <section className="room-grid">
          <RoomStatusPanel
            room={visibleRoom}
            session={session}
            connectionStatus={status}
            socketError={error}
            roomError={roomError}
            roomLoading={roomLoading}
          />

          {visibleRoom && session ? (
            visibleRoom.gameId === "fake-person" ? (
              <FakePersonGame room={visibleRoom} gameState={snapshot?.game} playerId={session.playerId} onAction={sendGameAction} />
            ) : visibleRoom.gameId === "beauty-vote" ? (
              <BeautyVoteGame room={visibleRoom} gameState={snapshot?.game} playerId={session.playerId} onAction={sendGameAction} />
            ) : (
              <LobbyDemo room={visibleRoom} gameState={snapshot?.game} onAction={sendGameAction} />
            )
          ) : (
            <Panel>
              <p className="state-text" aria-live="polite">等待房间快照…</p>
            </Panel>
          )}
        </section>
      )}
    </main>
  );
}
