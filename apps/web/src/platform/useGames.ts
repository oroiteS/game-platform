import { useEffect, useState } from "react";
import { getGames, type GameSummary } from "../api/client";

type GamesState = {
  games: GameSummary[];
  loading: boolean;
  error: string | null;
};

let cachedGames: GameSummary[] | null = null;
let inflightGamesRequest: Promise<GameSummary[]> | null = null;

function loadGames(): Promise<GameSummary[]> {
  if (cachedGames) {
    return Promise.resolve(cachedGames);
  }

  inflightGamesRequest ??= getGames()
    .then((games) => {
      cachedGames = games;
      return games;
    })
    .finally(() => {
      inflightGamesRequest = null;
    });

  return inflightGamesRequest;
}

export function useGames(): GamesState {
  const [state, setState] = useState<GamesState>(() => ({
    games: cachedGames ?? [],
    loading: !cachedGames,
    error: null,
  }));

  useEffect(() => {
    let stale = false;

    if (cachedGames) {
      setState({ games: cachedGames, loading: false, error: null });
      return () => {
        stale = true;
      };
    }

    setState((current) => ({ ...current, loading: true, error: null }));
    loadGames()
      .then((games) => {
        if (!stale) {
          setState({ games, loading: false, error: null });
        }
      })
      .catch((error: Error) => {
        if (!stale) {
          setState({ games: [], loading: false, error: error.message });
        }
      });

    return () => {
      stale = true;
    };
  }, []);

  return state;
}
