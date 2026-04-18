"use client";

interface Fixture {
  id: string;
  label: string;
}

const FIXTURES: Fixture[] = [
  { id: "01-high-risk-55m-smoker", label: "01 — High-risk 55M smoker (Grade B)" },
  { id: "02-borderline-55f-sdm", label: "02 — Borderline 55F SDM (Grade C)" },
  { id: "03-too-young-35m", label: "03 — Too young 35M (age exit)" },
  { id: "04-grade-i-78f", label: "04 — Grade I 78F (insufficient evidence)" },
  { id: "05-prior-mi-62m", label: "05 — Prior MI 62M (secondary prevention exit)" },
  { id: "cross-01-ascvd-62m", label: "X01 — ASCVD 62M (cross-domain, no preemption)" },
  { id: "cross-02-primary-55m", label: "X02 — Primary 55M (preemption: ACC/AHA > USPSTF)" },
  { id: "cross-03-ckd3b-65m", label: "X03 — CKD 3b 65M (modifier: KDIGO → ACC/AHA)" },
  { id: "cross-04-ckd3a-55m", label: "X04 — CKD 3a 55M (modifier: KDIGO → USPSTF + ACC/AHA)" },
];

interface FixturePickerProps {
  selected: string | null;
  onSelect: (fixtureId: string) => void;
  disabled?: boolean;
}

export default function FixturePicker({
  selected,
  onSelect,
  disabled,
}: FixturePickerProps) {
  return (
    <select
      data-testid="fixture-picker"
      className="bg-white border border-slate-300 rounded px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
      value={selected ?? ""}
      onChange={(e) => onSelect(e.target.value)}
      disabled={disabled}
    >
      <option value="" disabled>
        Select a fixture...
      </option>
      {FIXTURES.map((f) => (
        <option key={f.id} value={f.id}>
          {f.label}
        </option>
      ))}
    </select>
  );
}

export { FIXTURES };
