import { useEffect, useMemo, useState } from "react";

interface Props {
  pageCount: number;
  onChange: (ranges: [number, number][] | null) => void;
  placeholder?: string;
}

interface Parsed {
  ranges: [number, number][];
  error: string | null;
}

function parseRanges(raw: string, pageCount: number): Parsed {
  const text = raw.trim();
  if (!text) return { ranges: [], error: null };
  const parts = text.split(",").map((s) => s.trim()).filter(Boolean);
  const out: [number, number][] = [];
  for (const p of parts) {
    const m = /^(\d+)(?:\s*-\s*(\d+))?$/.exec(p);
    if (!m) return { ranges: [], error: `Invalid segment: "${p}"` };
    const a = Number(m[1]);
    const b = m[2] !== undefined ? Number(m[2]) : a;
    if (a < 1 || b < 1 || b < a) return { ranges: [], error: `Invalid range: "${p}"` };
    if (a > pageCount || b > pageCount) {
      return { ranges: [], error: `Range "${p}" exceeds page count ${pageCount}` };
    }
    out.push([a, b]);
  }
  if (out.length === 0) return { ranges: [], error: "Enter at least one range" };
  return { ranges: out, error: null };
}

export function RangeInput({ pageCount, onChange, placeholder }: Props) {
  const [raw, setRaw] = useState("");
  const parsed = useMemo(() => parseRanges(raw, pageCount), [raw, pageCount]);

  useEffect(() => {
    onChange(parsed.error ? null : parsed.ranges);
  }, [parsed, onChange]);

  return (
    <div>
      <input
        type="text"
        value={raw}
        onChange={(e) => setRaw(e.target.value)}
        placeholder={placeholder ?? "e.g. 1-3, 5, 7-12"}
        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none"
      />
      {parsed.error && (
        <p className="mt-1 text-xs text-red-600">{parsed.error}</p>
      )}
      {!parsed.error && parsed.ranges.length > 0 && (
        <p className="mt-1 text-xs text-slate-500">
          {parsed.ranges.length} range{parsed.ranges.length === 1 ? "" : "s"}
        </p>
      )}
    </div>
  );
}
