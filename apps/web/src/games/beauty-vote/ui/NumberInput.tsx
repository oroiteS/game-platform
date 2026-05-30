// ---------------------------------------------------------------------------
// NumberInput — range slider + number input with forbidden/inherited hints
// ---------------------------------------------------------------------------

type Props = {
  value: number;
  onChange: (n: number) => void;
  min?: number;
  max?: number;
  forbiddenNumber?: number | null;
  inheritedNumber?: number | null;
};

export function NumberInput({
  value,
  onChange,
  min = 0,
  max = 100,
  forbiddenNumber = null,
  inheritedNumber = null,
}: Props) {
  const isForbidden = forbiddenNumber !== null && value === forbiddenNumber;

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange(Number(e.target.value));
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const raw = e.target.value;
    // Allow empty input temporarily while typing
    if (raw === "") {
      onChange(min);
      return;
    }
    const n = Number(raw);
    if (isNaN(n)) return;
    onChange(Math.max(min, Math.min(max, n)));
  };

  return (
    <div className="text-field">
      <label className="text-field__label">你的数字</label>

      {/* Range slider */}
      <input
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={handleSliderChange}
        aria-label={`选择数字 ${value}`}
        style={{
          width: "100%",
          accentColor: isForbidden
            ? "var(--color-danger)"
            : "var(--color-primary)",
        }}
      />

      {/* Number input */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <input
          type="number"
          className="text-field__input"
          min={min}
          max={max}
          value={value}
          onChange={handleInputChange}
          aria-label="输入数字"
          style={{ width: 100 }}
        />
        <span
          style={{
            fontSize: "1.2rem",
            fontWeight: 700,
            color: isForbidden
              ? "var(--color-danger)"
              : "var(--color-text)",
          }}
        >
          {value}
        </span>
      </div>

      {/* Forbidden number hint */}
      {forbiddenNumber !== null && (
        <p
          className="text-field__help"
          style={{
            color: "var(--color-danger)",
            fontWeight: 600,
          }}
        >
          禁区数字：{forbiddenNumber}（选择将被扣3分）
        </p>
      )}

      {/* Inherited number hint */}
      {inheritedNumber !== null && (
        <p
          className="text-field__help"
          style={{
            color: "var(--color-primary)",
            fontWeight: 600,
          }}
        >
          继承数字：{inheritedNumber}（获胜+2分，失败固定-1分）
        </p>
      )}
    </div>
  );
}
