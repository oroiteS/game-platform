import { useEffect, useRef, useState } from "react";
import { getGame, getGames, type GameDetail, type GameSummary } from "../api/client";

export function GameCatalog() {
  const [open, setOpen] = useState(false);
  const [games, setGames] = useState<GameSummary[]>([]);
  const [selectedGame, setSelectedGame] = useState<GameDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const detailRequestIdRef = useRef(0);

  useEffect(() => {
    if (!open || games.length > 0) {
      return;
    }

    setLoading(true);
    setError(null);
    getGames()
      .then(setGames)
      .catch((nextError: Error) => setError(nextError.message))
      .finally(() => setLoading(false));
  }, [games.length, open]);

  const selectGame = (gameId: string) => {
    const requestId = detailRequestIdRef.current + 1;
    detailRequestIdRef.current = requestId;
    setLoading(true);
    setError(null);
    getGame(gameId)
      .then((nextGame) => {
        if (detailRequestIdRef.current === requestId) {
          setSelectedGame(nextGame);
        }
      })
      .catch((nextError: Error) => {
        if (detailRequestIdRef.current === requestId) {
          setError(nextError.message);
        }
      })
      .finally(() => {
        if (detailRequestIdRef.current === requestId) {
          setLoading(false);
        }
      });
  };

  return (
    <div className="game-catalog">
      <button
        className="catalog-trigger"
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        Games
      </button>

      {open ? (
        <aside className="catalog-panel" aria-label="游戏目录">
          <div className="panel-heading">
            <h2>Games</h2>
            <button type="button" className="ghost-button" onClick={() => setOpen(false)}>
              Close
            </button>
          </div>

          {loading ? <p className="muted">加载中...</p> : null}
          {error ? (
            <p className="error-text" role="alert">
              {error}
            </p>
          ) : null}

          <div className="catalog-list">
            {games.map((game) => (
              <button key={game.id} type="button" onClick={() => selectGame(game.id)}>
                <strong>{game.name}</strong>
                <span>{game.minPlayers}-{game.maxPlayers} 人</span>
              </button>
            ))}
          </div>

          {selectedGame ? (
            <div className="game-detail">
              <p className="eyebrow">{selectedGame.id}</p>
              <h3>{selectedGame.name}</h3>
              <p>{selectedGame.summary}</p>
              <dl>
                <div>
                  <dt>人数</dt>
                  <dd>{selectedGame.minPlayers}-{selectedGame.maxPlayers}</dd>
                </div>
              </dl>
              <p className="rules-text">{selectedGame.rules}</p>
            </div>
          ) : null}
        </aside>
      ) : null}
    </div>
  );
}
