export type ThemePreference = "system" | "light" | "dark";
export type ResolvedTheme = "light" | "dark";

export const THEME_STORAGE_KEY = "game-platform.theme:v1";

const LIGHT_THEME_COLOR = "#f4f1e8";
const DARK_THEME_COLOR = "#111820";

type Listener = () => void;

const listeners = new Set<Listener>();

let mediaQuery: MediaQueryList | null = null;
let cachedPreference: ThemePreference = readStoredTheme();

function isThemePreference(value: string | null): value is ThemePreference {
  return value === "system" || value === "light" || value === "dark";
}

function readStoredTheme(): ThemePreference {
  if (typeof window === "undefined") {
    return "system";
  }

  try {
    const storedTheme = window.localStorage.getItem(THEME_STORAGE_KEY);
    return isThemePreference(storedTheme) ? storedTheme : "system";
  } catch {
    return "system";
  }
}

function getMediaQuery(): MediaQueryList | null {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return null;
  }

  mediaQuery ??= window.matchMedia("(prefers-color-scheme: dark)");
  return mediaQuery;
}

export function resolveTheme(preference: ThemePreference): ResolvedTheme {
  if (preference === "dark" || preference === "light") {
    return preference;
  }

  return getMediaQuery()?.matches ? "dark" : "light";
}

export function getThemePreference(): ThemePreference {
  return cachedPreference;
}

function syncMetaThemeColor(resolvedTheme: ResolvedTheme): void {
  const meta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]');
  if (meta) {
    meta.content = resolvedTheme === "dark" ? DARK_THEME_COLOR : LIGHT_THEME_COLOR;
  }
}

export function applyTheme(preference: ThemePreference): ResolvedTheme {
  const resolvedTheme = resolveTheme(preference);

  if (typeof document !== "undefined") {
    document.documentElement.dataset.theme = resolvedTheme;
    document.documentElement.style.colorScheme = resolvedTheme;
    syncMetaThemeColor(resolvedTheme);
  }

  return resolvedTheme;
}

function notifyListeners(): void {
  applyTheme(cachedPreference);
  listeners.forEach((listener) => listener());
}

export function setThemePreference(preference: ThemePreference): void {
  cachedPreference = preference;

  try {
    if (preference === "system") {
      window.localStorage.removeItem(THEME_STORAGE_KEY);
    } else {
      window.localStorage.setItem(THEME_STORAGE_KEY, preference);
    }
  } catch {
    // Theme still updates for the current document if storage is blocked.
  }

  notifyListeners();
}

export function subscribeTheme(listener: Listener): () => void {
  listeners.add(listener);
  applyTheme(cachedPreference);

  return () => {
    listeners.delete(listener);
  };
}

function handleSystemThemeChange(): void {
  if (cachedPreference === "system") {
    notifyListeners();
  }
}

const systemQuery = getMediaQuery();
systemQuery?.addEventListener("change", handleSystemThemeChange);

if (typeof window !== "undefined") {
  window.addEventListener("storage", (event) => {
    if (event.key !== THEME_STORAGE_KEY) {
      return;
    }
    cachedPreference = isThemePreference(event.newValue) ? event.newValue : "system";
    notifyListeners();
  });
}

applyTheme(cachedPreference);
