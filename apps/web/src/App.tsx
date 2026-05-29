import { useEffect, useState } from "react";
import { ThemeToggle } from "./components/ThemeToggle";
import { GameCatalog } from "./platform/GameCatalog";
import { getRoomSession } from "./platform/sessionStore";
import { HomePage } from "./pages/HomePage";
import { RoomPage } from "./pages/RoomPage";

function readHashPath(): string {
  const hash = window.location.hash.replace(/^#/, "");
  return hash.startsWith("/") ? hash : "/";
}

export function App() {
  const [path, setPath] = useState(readHashPath);

  useEffect(() => {
    const handleHashChange = () => setPath(readHashPath());
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  const [currentGameId, setCurrentGameId] = useState<string>();

  useEffect(() => {
    const roomMatch = path.match(/^\/rooms\/([0-9]{6})$/);
    if (roomMatch) {
      const session = getRoomSession(roomMatch[1]);
      setCurrentGameId(session?.gameId);
    } else {
      setCurrentGameId(undefined);
    }
  }, [path]);

  const roomMatch = path.match(/^\/rooms\/([0-9]{6})$/);

  return (
    <>
      <a className="skip-link" href="#main-content">
        跳到主要内容
      </a>
      <div className="site-actions" role="group" aria-label="平台工具">
        <ThemeToggle />
        <GameCatalog gameId={currentGameId} />
      </div>
      {roomMatch ? <RoomPage roomCode={roomMatch[1]} /> : <HomePage />}
    </>
  );
}
