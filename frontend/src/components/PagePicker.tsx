import { usePdfDoc } from "./PdfToolLayout";
import { PdfThumbnail } from "./PdfThumbnail";

interface Props {
  mode: "keep" | "remove";
  selected: number[]; // 1-indexed
  onChange: (pages: number[]) => void;
}

export function PagePicker({ mode, selected, onChange }: Props) {
  const { pdfDoc, pageCount } = usePdfDoc();
  const selectedSet = new Set(selected);

  function toggle(pageNumber: number) {
    if (selectedSet.has(pageNumber)) {
      onChange(selected.filter((p) => p !== pageNumber));
    } else {
      onChange([...selected, pageNumber].sort((a, b) => a - b));
    }
  }

  const caption = mode === "remove" ? "Click pages to remove" : "Click pages to keep";
  const chip = mode === "remove" ? "Remove" : "Keep";

  return (
    <div>
      <div className="mb-3 flex items-center justify-between text-sm">
        <span className="text-slate-600">{caption}</span>
        <span className="text-slate-500">
          {selected.length} of {pageCount} selected
        </span>
      </div>
      <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-5">
        {Array.from({ length: pageCount }, (_, i) => i + 1).map((n) => {
          const isSelected = selectedSet.has(n);
          const ring =
            mode === "remove"
              ? isSelected
                ? "ring-2 ring-red-500 bg-red-50"
                : "hover:ring-2 hover:ring-slate-300"
              : isSelected
              ? "ring-2 ring-emerald-500 bg-emerald-50"
              : "hover:ring-2 hover:ring-slate-300";
          return (
            <button
              key={n}
              type="button"
              onClick={() => toggle(n)}
              className={
                "relative flex flex-col items-center rounded-lg p-2 transition " + ring
              }
            >
              <PdfThumbnail pdfDoc={pdfDoc} pageNumber={n} />
              <span className="mt-1 text-xs text-slate-600">
                {n}
                {isSelected ? ` · ${chip}` : ""}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
