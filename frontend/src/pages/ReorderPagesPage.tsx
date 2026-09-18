import { useEffect, useState } from "react";

import { reorderPdfPages } from "../api/converter";
import { PdfToolLayout, usePdfDoc } from "../components/PdfToolLayout";
import { SortablePages } from "../components/SortablePages";

function Controls({
  order,
  setOrder,
}: {
  order: number[];
  setOrder: (o: number[]) => void;
}) {
  const { pageCount } = usePdfDoc();

  // Initialise / reset order when the loaded PDF changes.
  useEffect(() => {
    setOrder(Array.from({ length: pageCount }, (_, i) => i + 1));
  }, [pageCount, setOrder]);

  if (order.length !== pageCount) return null;
  return <SortablePages order={order} onChange={setOrder} />;
}

export default function ReorderPagesPage() {
  const [order, setOrder] = useState<number[]>([]);

  return (
    <PdfToolLayout
      title="Reorder PDF Pages"
      description="Drag thumbnails to change the order of pages, then save the reordered PDF."
      capabilityKey="pdf:reorder-pages"
      submitLabel="Save Reordered PDF"
      canSubmit={order.length > 0}
      onSubmit={(file) => reorderPdfPages(file, order)}
    >
      <Controls order={order} setOrder={setOrder} />
    </PdfToolLayout>
  );
}
