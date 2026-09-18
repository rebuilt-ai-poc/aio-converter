import type { SourceFormat, TargetFormat } from "../types";

interface Props {
  source: SourceFormat;
  target: TargetFormat;
  options: Record<string, unknown>;
  onChange: (options: Record<string, unknown>) => void;
}

export function OptionsPanel({ source, target, options, onChange }: Props) {
  const set = (key: string, value: unknown) => onChange({ ...options, [key]: value });

  // Image quality + background applies to png/svg -> jpg.
  if (target === "jpg") {
    return (
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="text-sm text-slate-600">Quality</span>
          <input
            type="range"
            min={60}
            max={100}
            value={(options.quality as number) ?? 90}
            onChange={(e) => set("quality", Number(e.target.value))}
            className="mt-1 w-full"
          />
          <span className="text-xs text-slate-500">{(options.quality as number) ?? 90}</span>
        </label>
        <label className="block">
          <span className="text-sm text-slate-600">Background</span>
          <select
            value={(options.background as string) ?? "white"}
            onChange={(e) => set("background", e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
          >
            <option value="white">White</option>
            <option value="black">Black</option>
          </select>
        </label>
      </div>
    );
  }

  if (source === "txt" && target === "pdf") {
    return (
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="text-sm text-slate-600">Page size</span>
          <select
            value={(options.page_size as string) ?? "a4"}
            onChange={(e) => set("page_size", e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
          >
            <option value="a4">A4</option>
            <option value="letter">Letter</option>
          </select>
        </label>
        <label className="block">
          <span className="text-sm text-slate-600">Orientation</span>
          <select
            value={(options.orientation as string) ?? "portrait"}
            onChange={(e) => set("orientation", e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
          >
            <option value="portrait">Portrait</option>
            <option value="landscape">Landscape</option>
          </select>
        </label>
        <label className="block">
          <span className="text-sm text-slate-600">Margins</span>
          <select
            value={(options.margins as string) ?? "normal"}
            onChange={(e) => set("margins", e.target.value)}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
          >
            <option value="normal">Normal</option>
            <option value="narrow">Narrow</option>
          </select>
        </label>
        <label className="block">
          <span className="text-sm text-slate-600">Font size</span>
          <input
            type="number"
            min={8}
            max={24}
            value={(options.font_size as number) ?? 11}
            onChange={(e) => set("font_size", Number(e.target.value))}
            className="mt-1 w-full rounded border border-slate-300 px-2 py-1"
          />
        </label>
      </div>
    );
  }

  if (source === "md" && target === "pdf") {
    return (
      <label className="block">
        <span className="text-sm text-slate-600">Page size</span>
        <select
          value={(options.page_size as string) ?? "a4"}
          onChange={(e) => set("page_size", e.target.value)}
          className="mt-1 w-full max-w-xs rounded border border-slate-300 px-2 py-1"
        >
          <option value="a4">A4</option>
          <option value="letter">Letter</option>
        </select>
      </label>
    );
  }

  return <div className="text-sm text-slate-500">No options for this conversion.</div>;
}
