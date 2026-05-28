import { useTheme } from "../platform/ThemeProvider";
import type { ThemePreference } from "../platform/themeStore";

const OPTIONS: Array<{ value: ThemePreference; label: string }> = [
  { value: "system", label: "系统" },
  { value: "light", label: "白天" },
  { value: "dark", label: "暗黑" },
];

export function ThemeToggle() {
  const { preference, setPreference } = useTheme();

  return (
    <div className="theme-toggle" role="group" aria-label="界面主题">
      {OPTIONS.map((option) => (
        <button
          className="theme-toggle__button"
          type="button"
          aria-pressed={preference === option.value}
          key={option.value}
          onClick={() => setPreference(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
