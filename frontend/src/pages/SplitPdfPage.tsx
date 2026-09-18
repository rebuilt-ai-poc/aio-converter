import { useState } from "react";

import { splitPdf, type SplitMode } from "../api/converter";
import { PdfToolLayout, usePdfDoc } from "../components/PdfToolLayout";
import { RangeInput } from "../components/RangeInput";

type SplitKind = "every_page" | "every_n" | "ranges";

interface ControlsProps {
  kind: SplitKind;
  setKind: (k: SplitKind) => void;
  n: number;
  setN: (n: number) => void;
  ranges: [number, number][] | null;
  setRanges: (r: [number, number][] | null) => void;
}

function SplitControls({ kind, setKind, n, setN, ranges, setRanges }: ControlsProps) {
  const { pageCount } = usePdfDoc();

  return (
    <div className="space-y-4">
      <div className="text-sm text-slate-600">
        This PDF has <b>{pageCount}</b> pages. How should we split it?
      </div>
      <div className="space-y-2 text-sm">
        <label className="flex items-center gap-2">
          <input
            type="radio"
            checked={kind === "every_page"}
            onChange={() => setKind("every_page")}
          />
          <span>One file per page</span>
        </label>
        <label className="flex items-center gap-2">
          <input
            type="radio"
            checked={kind === "every_n"}
            onChange={() => setKind("every_n")}
          />
          <span>Every</span>
          <input
            type="number"
            min={1}
            max={Math.max(1, pageCount)}
            value={n}
            onChange={(e) => setN(Math.max(1, Number(e.target.value) || 1))}
            disabled={kind !== "every_n"}
            className="w-16 rounded border border-slate-300 px-2 py-1 text-sm disabled:bg-slate-100"
          />
          <span>pages</span>
        </label>
        <label className="flex items-start gap-2">
          <input
            type="radio"
            checked={kind === "ranges"}
            onChange={() => setKind("ranges")}
            className="mt-2"
          />
          <div className="flex-1">
            <div>Custom ranges</div>
            {kind === "ranges" && (
              <div className="mt-2">
                <RangeInput pageCount={pageCount} onChange={setRanges} />
              </div>
            )}
          </div>
        </label>
      </div>
      {kind === "ranges" && ranges === null && (
        <p className="text-xs text-slate-500">Enter a valid range list to enable Split.</p>
      )}
    </div>
  );
}

export default function SplitPdfPage() {
  const [kind, setKind] = useState<SplitKind>("every_page");
  const [n, setN] = useState<number>(2);
  const [ranges, setRanges] = useState<[number, number][] | null>(null);

  const canSubmit =
    kind === "every_page" ||
    (kind === "every_n" && n >= 1) ||
    (kind === "ranges" && ranges !== null && ranges.length > 0);

  function buildMode(): SplitMode {
    if (kind === "every_page") return { type: "every_page" };
    if (kind === "every_n") return { type: "every_n", n };
    return { type: "ranges", ranges: ranges ?? [] };
  }

  return (
    <PdfToolLayout
      title="Split PDF"
      description="Split a PDF into multiple files — every page, every N pages, or custom ranges. Download the result as a ZIP."
      capabilityKey="pdf:split"
      submitLabel="Split PDF"
      canSubmit={canSubmit}
      onSubmit={(file) => splitPdf(file, buildMode())}
    >
      <SplitControls
        kind={kind}
        setKind={setKind}
        n={n}
        setN={setN}
        ranges={ranges}
        setRanges={setRanges}
      />
    </PdfToolLayout>
  );
}
