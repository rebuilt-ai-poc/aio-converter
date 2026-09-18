import {
  DndContext,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  rectSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";

import { usePdfDoc } from "./PdfToolLayout";
import { PdfThumbnail } from "./PdfThumbnail";

interface Props {
  order: number[]; // 1-indexed permutation
  onChange: (order: number[]) => void;
}

export function SortablePages({ order, onChange }: Props) {
  const { pdfDoc } = usePdfDoc();
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
  );

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const from = order.indexOf(Number(active.id));
    const to = order.indexOf(Number(over.id));
    if (from < 0 || to < 0) return;
    onChange(arrayMove(order, from, to));
  }

  return (
    <div>
      <div className="mb-3 text-sm text-slate-600">
        Drag pages to reorder ({order.length} pages)
      </div>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext items={order} strategy={rectSortingStrategy}>
          <div className="grid grid-cols-3 gap-3 sm:grid-cols-4 md:grid-cols-5">
            {order.map((pageNumber, position) => (
              <SortablePage
                key={pageNumber}
                id={pageNumber}
                position={position + 1}
                originalPage={pageNumber}
                pdfDoc={pdfDoc}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>
    </div>
  );
}

interface SortablePageProps {
  id: number;
  position: number;
  originalPage: number;
  pdfDoc: ReturnType<typeof usePdfDoc>["pdfDoc"];
}

function SortablePage({ id, position, originalPage, pdfDoc }: SortablePageProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id });

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="flex cursor-grab flex-col items-center rounded-lg p-2 ring-1 ring-slate-200 hover:ring-slate-400 active:cursor-grabbing"
    >
      <PdfThumbnail pdfDoc={pdfDoc} pageNumber={originalPage} />
      <span className="mt-1 text-xs text-slate-600">
        {position}
        <span className="text-slate-400"> (was {originalPage})</span>
      </span>
    </div>
  );
}
