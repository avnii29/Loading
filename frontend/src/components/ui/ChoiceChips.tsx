import type { ReactNode } from "react";

export type ChipTone = "coral" | "mango" | "leaf" | "sky" | "berry" | "flame" | "sand";

type Option<T extends string> = {
  value: T;
  label: string;
  icon?: ReactNode;
  hint?: string;
  tone?: ChipTone;
};

type Props<T extends string> = {
  label: string;
  options: Option<T>[];
  value: T | null | undefined;
  onChange: (value: T) => void;
  columns?: 2 | 3 | 4 | 7;
  required?: boolean;
};

export function ChoiceChips<T extends string>({
  label,
  options,
  value,
  onChange,
  columns = 2,
  required,
}: Props<T>) {
  return (
    <fieldset className={`choice-fieldset cols-${columns}`}>
      <legend>
        {label}
        {required ? <span className="req"> *</span> : null}
      </legend>
      <div className="choice-grid" role="radiogroup" aria-label={label}>
        {options.map((option) => {
          const selected = value === option.value;
          const tone = option.tone || "coral";
          return (
            <button
              key={option.value}
              type="button"
              role="radio"
              aria-checked={selected}
              className={`choice-chip tone-${tone}${selected ? " is-selected" : ""}`}
              onClick={() => onChange(option.value)}
            >
              {option.icon ? (
                <span className="choice-icon-badge" aria-hidden>
                  {option.icon}
                </span>
              ) : null}
              <span className="choice-copy">
                <span className="choice-label">{option.label}</span>
                {option.hint ? <small>{option.hint}</small> : null}
              </span>
            </button>
          );
        })}
      </div>
    </fieldset>
  );
}

type YesNoProps = {
  title: string;
  icon?: ReactNode;
  accent?: ChipTone;
  value: boolean | undefined;
  onChange: (value: boolean) => void;
};

export function YesNoTile({ title, icon, accent = "leaf", value, onChange }: YesNoProps) {
  const answered = typeof value === "boolean";
  return (
    <div
      className={`yesno-tile tone-${accent}${value === true ? " is-yes" : ""}${value === false ? " is-no" : ""}${answered ? " is-answered" : ""}`}
    >
      <div className="yesno-head">
        {icon ? (
          <span className="yesno-icon" aria-hidden>
            {icon}
          </span>
        ) : null}
        <strong>{title}</strong>
      </div>
      <div className="yesno-actions">
        <button
          type="button"
          className={`yn-btn yn-yes${value === true ? " is-selected" : ""}`}
          aria-pressed={value === true}
          onClick={() => onChange(true)}
        >
          Yes
        </button>
        <button
          type="button"
          className={`yn-btn yn-no${value === false ? " is-selected" : ""}`}
          aria-pressed={value === false}
          onClick={() => onChange(false)}
        >
          No
        </button>
      </div>
    </div>
  );
}
