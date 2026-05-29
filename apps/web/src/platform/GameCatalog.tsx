import { useEffect, useId, useRef, useState, type RefObject } from "react";
import { Button } from "../components/ui/Button";
import { FieldError } from "../components/ui/FieldError";
import { StatusBadge } from "../components/ui/StatusBadge";
import { getGame, type GameDetail } from "../api/client";
import { useGames } from "./useGames";

function GameDetailPanel({
  game,
  loading,
  error,
  titleId,
  closeButtonRef,
  onClose,
}: {
  game: GameDetail | null;
  loading: boolean;
  error: string | null;
  titleId: string;
  closeButtonRef: RefObject<HTMLButtonElement | null>;
  onClose: () => void;
}) {
  return (
    <section className="game-detail-modal">
      <div className="modal-heading">
        <div>
          <p className="eyebrow">Rules</p>
          <h2 id={titleId}>{game?.name ?? "游戏规则"}</h2>
        </div>
        <Button ref={closeButtonRef} type="button" variant="ghost" onClick={onClose}>
          关闭
        </Button>
      </div>

      {loading ? <p className="state-text" aria-live="polite">正在读取游戏详情…</p> : null}
      {error ? <FieldError message={error} /> : null}

      {!loading && !error && game ? (
        <div className="game-detail-body">
          <p className="eyebrow">{game.id}</p>
          <p className="game-detail-summary">{game.summary}</p>
          <dl>
            <div>
              <dt>人数</dt>
              <dd>
                {game.minPlayers}-{game.maxPlayers}
              </dd>
            </div>
          </dl>
          <div className="rules-text" dangerouslySetInnerHTML={{ __html: game.rules }} />
        </div>
      ) : null}
    </section>
  );
}

type GameCatalogProps = {
  gameId?: string;
};

export function GameCatalog({ gameId }: GameCatalogProps) {
  const panelId = useId();
  const detailTitleId = useId();
  const [open, setOpen] = useState(false);
  const [selectedGameId, setSelectedGameId] = useState<string | null>(null);
  const [selectedGame, setSelectedGame] = useState<GameDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement | null>(null);
  const panelRef = useRef<HTMLElement | null>(null);
  const detailDialogRef = useRef<HTMLDivElement | null>(null);
  const detailCloseButtonRef = useRef<HTMLButtonElement | null>(null);
  const detailTriggerRef = useRef<HTMLButtonElement | null>(null);
  const restoreFocusRef = useRef(false);
  const detailRequestIdRef = useRef(0);
  const [search, setSearch] = useState("");
  const { games, loading: gamesLoading, error: gamesError } = useGames();

  const closeGameDetail = () => {
    detailRequestIdRef.current += 1;
    setSelectedGameId(null);
    setSelectedGame(null);
    setDetailError(null);
    setDetailLoading(false);
    window.requestAnimationFrame(() => detailTriggerRef.current?.focus());
  };

  const toggleGameDetail = (gameId: string, trigger: HTMLButtonElement) => {
    detailTriggerRef.current = trigger;
    if (selectedGameId === gameId) {
      closeGameDetail();
      return;
    }
    setSelectedGameId(gameId);
  };

  const closeCatalog = () => {
    if (selectedGameId) {
      closeGameDetail();
    }
    restoreFocusRef.current = true;
    setOpen(false);
  };

  useEffect(() => {
    if (!open) {
      if (restoreFocusRef.current) {
        triggerRef.current?.focus();
        restoreFocusRef.current = false;
      }
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        if (selectedGameId) {
          closeGameDetail();
        } else {
          closeCatalog();
        }
        return;
      }

      if (event.key !== "Tab") {
        return;
      }

      const activeTrap = selectedGameId ? detailDialogRef.current : panelRef.current;
      const focusableElements = activeTrap?.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );
      if (!focusableElements || focusableElements.length === 0) {
        return;
      }

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      if (event.shiftKey && document.activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
      } else if (!event.shiftKey && document.activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    window.requestAnimationFrame(() => {
      if (selectedGameId) {
        detailCloseButtonRef.current?.focus();
      } else {
        closeButtonRef.current?.focus();
      }
    });

    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, selectedGameId]);

  useEffect(() => {
    if (!selectedGameId) {
      setSelectedGame(null);
      setDetailError(null);
      setDetailLoading(false);
      return;
    }

    const requestId = detailRequestIdRef.current + 1;
    detailRequestIdRef.current = requestId;
    setDetailLoading(true);
    setDetailError(null);
    setSelectedGame(null);

    getGame(selectedGameId)
      .then((nextGame) => {
        if (detailRequestIdRef.current === requestId) {
          setSelectedGame(nextGame);
        }
      })
      .catch((nextError: Error) => {
        if (detailRequestIdRef.current === requestId) {
          setSelectedGame(null);
          setDetailError(nextError.message);
        }
      })
      .finally(() => {
        if (detailRequestIdRef.current === requestId) {
          setDetailLoading(false);
        }
      });
  }, [selectedGameId]);

  useEffect(() => {
    if (open && gameId) {
      setSelectedGameId(gameId);
      setSearch("");
    }
  }, [open, gameId]);

  const filteredGames = games.filter((g) =>
    g.name.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="game-catalog">
      <Button
        className="catalog-trigger"
        type="button"
        variant="secondary"
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-controls={panelId}
        ref={triggerRef}
        onClick={() => setOpen((current) => !current)}
      >
        游戏目录
      </Button>

      {open ? (
        <aside
          className="catalog-panel"
          id={panelId}
          role="dialog"
          aria-label="游戏目录"
          ref={panelRef}
        >
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Catalog</p>
              <h2>游戏目录</h2>
            </div>
            <Button
              ref={closeButtonRef}
              type="button"
              variant="ghost"
              onClick={closeCatalog}
            >
              关闭
            </Button>
          </div>

          <div className="catalog-search">
            <input
              type="search"
              className="catalog-search-input"
              placeholder="搜索游戏..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              aria-label="搜索游戏"
            />
          </div>

          {gamesLoading ? <p className="state-text" aria-live="polite">正在读取游戏列表…</p> : null}
          {gamesError ? <FieldError message={gamesError} /> : null}
          {!gamesLoading && !gamesError && games.length === 0 ? (
            <p className="state-text">暂无游戏</p>
          ) : null}

          {!gamesLoading && !gamesError && games.length > 0 && filteredGames.length === 0 ? (
            <p className="state-text">未找到匹配的游戏</p>
          ) : null}

          <div className="catalog-list" aria-label="游戏列表">
            {filteredGames.map((game) => (
              <button
                className={game.id === selectedGameId ? "catalog-item is-selected" : "catalog-item"}
                key={game.id}
                type="button"
                aria-pressed={game.id === selectedGameId}
                onClick={(event) => toggleGameDetail(game.id, event.currentTarget)}
              >
                <strong>{game.name}</strong>
                <span>{game.summary}</span>
                <StatusBadge tone="neutral">
                  {game.minPlayers}-{game.maxPlayers} 人
                </StatusBadge>
              </button>
            ))}
          </div>
        </aside>
      ) : null}

      {open && selectedGameId ? (
        <div
          className="modal-backdrop"
          role="presentation"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closeGameDetail();
            }
          }}
        >
          <div
            className="modal-dialog"
            ref={detailDialogRef}
            role="dialog"
            aria-modal="true"
            aria-labelledby={detailTitleId}
          >
            <GameDetailPanel
              game={selectedGame}
              loading={detailLoading}
              error={detailError}
              titleId={detailTitleId}
              closeButtonRef={detailCloseButtonRef}
              onClose={closeGameDetail}
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}
