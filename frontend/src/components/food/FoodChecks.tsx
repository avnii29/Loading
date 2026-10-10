import { useId, useRef, useState } from "react";

function InfoTip({ text }: { text: string }) {
  const [phase, setPhase] = useState<"closed" | "open" | "fading">("closed");
  const id = useId();
  const timer = useRef(0);

  function show() {
    window.clearTimeout(timer.current);
    setPhase("open");
  }

  function hide() {
    setPhase((current) => (current === "closed" ? "closed" : "fading"));
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setPhase("closed"), 700);
  }

  return (
    <span className="info-wrap" onMouseEnter={show} onMouseLeave={hide} onFocus={show} onBlur={hide}>
      <button
        type="button"
        className="info-dot"
        aria-expanded={phase === "open"}
        aria-controls={id}
        aria-label="More about this question"
        onClick={show}
      >
        i
      </button>
      {phase !== "closed" ? (
        <span id={id} role="note" className={`info-pop${phase === "fading" ? " is-fading" : ""}`}>
          {text}
        </span>
      ) : null}
    </span>
  );
}

type Row = {
  key: string;
  label: string;
  help?: string;
  options: { value: string; label: string }[];
};

const DONOR_COOKED: Row[] = [
  { key: "freshly_prepared", label: "Freshly prepared?", help: "Select Yes if the food was freshly cooked or prepared. This alone does not guarantee safety.", options: [
    { value: "YES", label: "Yes" },
    { value: "NO", label: "No" },
  ]},
  { key: "stored_safely", label: "Stored safely?", help: "Was the food kept at an appropriate temperature after preparation? Select Not sure if you cannot confirm.", options: [
    { value: "YES", label: "Yes" },
    { value: "NO", label: "No" },
    { value: "NOT_SURE", label: "Not sure" },
  ]},
  { key: "covered", label: "Covered?", help: "Was the food protected from dust, insects, and other contamination?", options: [
    { value: "YES", label: "Yes" },
    { value: "NO", label: "No" },
  ]},
  { key: "time_since_cooking", label: "Time since cooking", help: "Choose how long it has been since cooking finished. Perishable cooked food generally should not remain at room temperature for over 2 hours, or 1 hour above 32°C.", options: [
    { value: "UNDER_2H", label: "Under 2h" },
    { value: "TWO_TO_FOUR", label: "2–4h" },
    { value: "OVER_4H", label: "Over 4h" },
    { value: "NOT_SURE", label: "Not sure" },
  ]},
  { key: "packaging", label: "Packed or unpacked?", help: "Tell us whether the food is already in a suitable container. Unpacked food may need appropriate food-safe packaging before transport.", options: [
    { value: "PACKED", label: "Packed" },
    { value: "UNPACKED", label: "Unpacked" },
  ]},
];

const DONOR_DRY: Row[] = [
  { key: "stored_safely", label: "Stored safely?", help: "Was the food kept at an appropriate temperature after preparation? Select Not sure if you cannot confirm.", options: [
    { value: "YES", label: "Yes" },
    { value: "NO", label: "No" },
    { value: "NOT_SURE", label: "Not sure" },
  ]},
  { key: "covered", label: "Covered?", help: "Was the food protected from dust, insects, and other contamination?", options: [
    { value: "YES", label: "Yes" },
    { value: "NO", label: "No" },
  ]},
  { key: "packaging", label: "Packed or unpacked?", help: "Tell us whether the food is already in a suitable container. Unpacked food may need appropriate food-safe packaging before transport.", options: [
    { value: "PACKED", label: "Packed" },
    { value: "UNPACKED", label: "Unpacked" },
  ]},
];

const PICKUP: Row[] = [
  { key: "seal_intact", label: "Seal intact?", help: "Check whether the container or seal is intact. Choose N/A if there is no seal to check.", options: [
    { value: "YES", label: "Yes" },
    { value: "NO", label: "No" },
    { value: "NA", label: "N/A" },
  ]},
  { key: "looks_normal", label: "Looks normal?", help: "Look for unusual discoloration, visible mould, leakage, or signs of contamination. Do not taste the food.", options: [
    { value: "YES", label: "Yes" },
    { value: "NO", label: "No" },
    { value: "NOT_SURE", label: "Not sure" },
  ]},
  { key: "unusual_smell", label: "Unusual smell?", help: "If an unusual or sour smell is noticed without opening sealed packaging, flag the food for review. Never taste food to check freshness.", options: [
    { value: "NO", label: "No" },
    { value: "YES", label: "Yes" },
    { value: "NOT_CHECKED", label: "Not checked" },
  ]},
  { key: "temperature", label: "Temperature", help: "Record the observable condition: hot, cold, or room temperature. Choose Unknown if you cannot tell. Touch alone cannot confirm a safe temperature.", options: [
    { value: "HOT", label: "Hot" },
    { value: "COLD", label: "Cold" },
    { value: "ROOM_TEMP", label: "Room temp" },
    { value: "UNKNOWN", label: "Unknown" },
  ]},
  { key: "spillage", label: "Spillage?", help: "Check for leaking containers, spilled food, or damaged packaging. Flag any contamination concern before transport.", options: [
    { value: "NO", label: "No" },
    { value: "YES", label: "Yes" },
  ]},
];

const INTAKE: Row[] = [
  { key: "packaging_intact", label: "Packaging intact?", help: "Check whether containers are closed, undamaged, and free from leakage or visible contamination.", options: [
    { value: "YES", label: "Yes" },
    { value: "NO", label: "No" },
    { value: "NA", label: "N/A" },
  ]},
  { key: "looks_normal", label: "Looks normal?", help: "Check for visible mould, unusual colour changes, leakage, or other signs of spoilage. Normal appearance does not guarantee safety.", options: [
    { value: "YES", label: "Yes" },
    { value: "NO", label: "No" },
    { value: "NOT_SURE", label: "Not sure" },
  ]},
  { key: "temperature", label: "Temperature", help: "Record the observed condition. If food safety depends on a specific temperature, use a suitable food thermometer and follow the applicable safety requirements.", options: [
    { value: "HOT", label: "Hot" },
    { value: "COLD", label: "Cold" },
    { value: "ROOM_TEMP", label: "Room temp" },
    { value: "UNKNOWN", label: "Unknown" },
  ]},
  { key: "quantity_received", label: "Quantity received", help: "Compare the amount received with the donor's declared quantity. Select Partial or Mismatch if it differs.", options: [
    { value: "FULL", label: "Full" },
    { value: "PARTIAL", label: "Partial" },
    { value: "MISMATCH", label: "Mismatch" },
  ]},
  { key: "accepted", label: "Accept / Hold / Reject", help: "Accept if requirements are met. Hold if safety or quantity needs clarification. Reject if the donation is unsuitable. Record a reason when holding or rejecting.", options: [
    { value: "ACCEPT", label: "Accept" },
    { value: "HOLD", label: "Hold" },
    { value: "REJECT", label: "Reject" },
  ]},
];

export function rowsFor(role: "donor" | "pickup" | "intake", handling?: string) {
  if (role === "pickup") return PICKUP;
  if (role === "intake") return INTAKE;
  return handling === "DRY_RATIONS" ? DONOR_DRY : DONOR_COOKED;
}

export function FoodChecks({
  role,
  handling,
  value,
  onChange,
}: {
  role: "donor" | "pickup" | "intake";
  handling?: string;
  value: Record<string, string>;
  onChange: (next: Record<string, string>) => void;
}) {
  const rows = rowsFor(role, handling);
  const answered = rows.filter((row) => value[row.key]).length;
  return (
    <section className="food-checks">
      <div className="food-checks-head">
        <h3>Food checks</h3>
        <span>
          {answered} of {rows.length}
        </span>
      </div>
      {rows.map((row) => (
        <div key={row.key} className="food-check-row">
          <p>
            {row.label}
            {row.help ? <InfoTip text={row.help} /> : null}
          </p>
          <div className="food-check-options" role="radiogroup" aria-label={row.label}>
            {row.options.map((option) => (
              <button
                key={option.value}
                type="button"
                className={`choice-chip compact${value[row.key] === option.value ? " is-selected" : ""}`}
                aria-checked={value[row.key] === option.value}
                role="radio"
                onClick={() => onChange({ ...value, [row.key]: option.value })}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}
