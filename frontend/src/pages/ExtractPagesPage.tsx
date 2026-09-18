import { useState } from "react";

import { extractPdfPages } from "../api/converter";
import { PagePicker } from "../components/PagePicker";
import { PdfToolLayout } from "../components/PdfToolLayout";

export default function ExtractPagesPage() {
  const [selected, setSelected] = useState<number[]>([]);

  return (
    <PdfToolLayout
      title="Extract PDF Pages"
      description="Pull selected pages out of a PDF into a new document. Click pages to include them, in the order you want them to appear."
      capabilityKey="pdf:extract-pages"
      submitLabel="Extract Selected Pages"
      canSubmit={selected.length > 0}
      onSubmit={(file) => extractPdfPages(file, selected)}
    >
      <PagePicker mode="keep" selected={selected} onChange={setSelected} />
    </PdfToolLayout>
  );
}
