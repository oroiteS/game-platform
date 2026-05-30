import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { RoomSummary } from "../api/client";
import type { RoomSession } from "./sessionStore";

export type RoomSnapshot = {
  room: RoomSummary;
  game: unknown;
};

export type SocketStatus = "idle" | "connecting" | "open" | "closed";

type ServerMessage =
  | {
      type: "room_snapshot";
      room: RoomSummary;
      game: unknown;
    }
  | {
      type: "error";
      code?: string;
      message?: string;
    };

const HEARTBEAT_INTERVAL_MS = 10_000;
const HEARTBEAT_MESSAGE = JSON.stringify({ type: "heartbeat" });

function roomSocketUrl(roomCode: string, session: RoomSession): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const query = new URLSearchParams({
    playerId: session.playerId,
    sessionToken: session.sessionToken,
  });
  const base = import.meta.env.BASE_URL;
  return `${protocol}//${window.location.host}${base}ws/rooms/${encodeURIComponent(
    roomCode,
  )}?${query.toString()}`;
}

export function useRoomSocket(roomCode: string | null, session: RoomSession | null) {
  const socketRef = useRef<WebSocket | null>(null);
  const [status, setStatus] = useState<SocketStatus>("idle");
  const [snapshot, setSnapshot] = useState<RoomSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!roomCode || !session) {
      setStatus("idle");
      setSnapshot(null);
      return;
    }

    setStatus("connecting");
    setError(null);
    const socket = new WebSocket(roomSocketUrl(roomCode, session));
    socketRef.current = socket;
    const isCurrentSocket = () => socketRef.current === socket;
    let heartbeatIntervalId: ReturnType<typeof window.setInterval> | null = null;

    const clearHeartbeat = () => {
      if (heartbeatIntervalId === null) {
        return;
      }
      window.clearInterval(heartbeatIntervalId);
      heartbeatIntervalId = null;
    };

    const sendHeartbeat = () => {
      if (!isCurrentSocket() || socket.readyState !== WebSocket.OPEN) {
        return;
      }
      socket.send(HEARTBEAT_MESSAGE);
    };

    socket.addEventListener("open", () => {
      if (!isCurrentSocket()) {
        return;
      }
      setStatus("open");
      clearHeartbeat();
      heartbeatIntervalId = window.setInterval(sendHeartbeat, HEARTBEAT_INTERVAL_MS);
    });

    socket.addEventListener("message", (event) => {
      if (!isCurrentSocket()) {
        return;
      }
      try {
        const message = JSON.parse(event.data) as ServerMessage;
        if (message.type === "room_snapshot") {
          setSnapshot({ room: message.room, game: message.game });
          return;
        }
        if (message.type === "error") {
          setError(message.message ?? message.code ?? "WebSocket error");
        }
      } catch {
        setError("收到无法解析的服务器消息");
      }
    });

    socket.addEventListener("error", () => {
      clearHeartbeat();
      if (!isCurrentSocket()) {
        return;
      }
      setError("WebSocket 连接异常");
    });

    socket.addEventListener("close", () => {
      clearHeartbeat();
      if (!isCurrentSocket()) {
        return;
      }
      setStatus("closed");
    });

    return () => {
      clearHeartbeat();
      if (isCurrentSocket()) {
        socketRef.current = null;
      }
      socket.close();
    };
  }, [roomCode, session]);

  const sendGameAction = useCallback((action: { type: string; payload?: unknown }) => {
    const socket = socketRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      setError("连接尚未就绪");
      return false;
    }

    socket.send(JSON.stringify({ type: "game_action", action }));
    return true;
  }, []);

  return useMemo(
    () => ({ status, snapshot, error, sendGameAction }),
    [status, snapshot, error, sendGameAction],
  );
}
