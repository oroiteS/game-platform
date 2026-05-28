import { useEffect, useState } from "react";
import { GameCatalog } from "./platform/GameCatalog";
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

  const roomMatch = path.match(/^\/rooms\/([0-9]{6})$/);

  return (
    <>
      <GameCatalog />
      {roomMatch ? <RoomPage roomCode={roomMatch[1]} /> : <HomePage />}
    </>
  );
}
