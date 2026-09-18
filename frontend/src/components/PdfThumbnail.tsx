import { useEffect, useRef } from "react";
import type { PDFDocumentProxy } from "../lib/pdfjs";

interface Props {
  pdfDoc: PDFDocumentProxy;
  pageNumber: number; // 1-indexed
  width?: number;
}

export function PdfThumbnail({ pdfDoc, pageNumber, width = 150 }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    let cancelled = false;
    const canvas = canvasRef.current;
    if (!canvas) return;

    (async () => {
      const page = await pdfDoc.getPage(pageNumber);
      if (cancelled) return;
      const viewport = page.getViewport({ scale: 1 });
      const scale = width / viewport.width;
      const scaledViewport = page.getViewport({ scale });
      canvas.width = Math.floor(scaledViewport.width);
      canvas.height = Math.floor(scaledViewport.height);
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      await page.render({ canvasContext: ctx, viewport: scaledViewport }).promise;
    })().catch(() => {
      // Render errors on individual pages should not crash the tool.
    });

    return () => {
      cancelled = true;
    };
  }, [pdfDoc, pageNumber, width]);

  return (
    <canvas
      ref={canvasRef}
      className="block h-auto max-w-full rounded border border-slate-200 bg-white"
      style={{ width }}
    />
  );
}
