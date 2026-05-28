import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import {
  applyTheme,
  getThemePreference,
  resolveTheme,
  setThemePreference,
  subscribeTheme,
  type ResolvedTheme,
  type ThemePreference,
} from "./themeStore";

type ThemeContextValue = {
  preference: ThemePreference;
  resolvedTheme: ResolvedTheme;
  setPreference: (preference: ThemePreference) => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

function subscribeThemePreference(onStoreChange: () => void): () => void {
  return subscribeTheme(onStoreChange);
}

type ThemeSnapshot = `${ThemePreference}:${ResolvedTheme}`;

function makeThemeSnapshot(preference: ThemePreference): ThemeSnapshot {
  return `${preference}:${resolveTheme(preference)}`;
}

function getThemeSnapshot(): ThemeSnapshot {
  return makeThemeSnapshot(getThemePreference());
}

function getServerThemeSnapshot(): ThemeSnapshot {
  return "system:light";
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const snapshot = useSyncExternalStore<ThemeSnapshot>(
    subscribeThemePreference,
    getThemeSnapshot,
    getServerThemeSnapshot,
  );
  const [preference, resolvedTheme] = snapshot.split(":") as [ThemePreference, ResolvedTheme];

  useEffect(() => {
    applyTheme(preference);
  }, [preference]);

  const value = useMemo(
    () => ({
      preference,
      resolvedTheme,
      setPreference: setThemePreference,
    }),
    [preference, resolvedTheme],
  );

  return <ThemeContext value={value}>{children}</ThemeContext>;
}

export function useTheme(): ThemeContextValue {
  const value = useContext(ThemeContext);
  if (!value) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return value;
}
