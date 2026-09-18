import * as pdfjsLib from "pdfjs-dist";
import type { PDFDocumentProxy } from "pdfjs-dist";

// Worker URL resolved by Vite. pdfjs-dist v4 ships an ESM worker.
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  "pdfjs-dist/build/pdf.worker.mjs",
  import.meta.url,
).toString();

export async function loadPdf(file: File): Promise<PDFDocumentProxy> {
  const buf = await file.arrayBuffer();
  // pdf.js keeps a reference to the array — copy to a fresh Uint8Array so the
  // underlying ArrayBuffer isn't reused/detached elsewhere.
  const data = new Uint8Array(buf);
  const task = pdfjsLib.getDocument({ data });
  return task.promise;
}

export type { PDFDocumentProxy };
