import { useState } from "react";

import { deletePdfPages } from "../api/converter";
import { PagePicker } from "../components/PagePicker";
import { PdfToolLayout, usePdfDoc } from "../components/PdfToolLayout";

function Controls({
  selected,
  setSelected,
}: {
  selected: number[];
  setSelected: (p: number[]) => void;
}) {
  const { pageCount } = usePdfDoc();
  const wouldDeleteAll = selected.length === pageCount && pageCount > 0;
  return (
    <div>
      <PagePicker mode="remove" selected={selected} onChange={setSelected} />
      {wouldDeleteAll && (
        <p className="mt-3 text-xs text-red-600">
          You have selected every page. Deselect at least one to keep.
        </p>
      )}
    </div>
  );
}

export default function DeletePagesPage() {
  const [selected, setSelected] = useState<number[]>([]);
  // We rely on the layout's usePdfDoc for pageCount inside Controls, but for
  // the outer canSubmit we only know selection here. The backend still
  // enforces "not every page"; the inline warning above nudges users.
  const canSubmit = selected.length > 0;

  return (
    <PdfToolLayout
      title="Delete PDF Pages"
      description="Remove specific pages from a PDF. Preview thumbnails, click pages to remove, and download the edited PDF."
      capabilityKey="pdf:delete-pages"
      submitLabel="Delete Selected Pages"
      canSubmit={canSubmit}
      onSubmit={(file) => deletePdfPages(file, selected)}
    >
      <Controls selected={selected} setSelected={setSelected} />
    </PdfToolLayout>
  );
}
