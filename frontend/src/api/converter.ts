import type { ApiError, SystemInfo } from "../types";

async function throwOnError(res: Response): Promise<never> {
  let msg = `HTTP ${res.status}`;
  let code = "HTTP_ERROR";
  try {
    const body = await res.json();
    if (body?.error) {
      code = body.error.code ?? code;
      msg = body.error.message ?? msg;
    }
  } catch {
    // ignore
  }
  const e: ApiError = { code, message: msg };
  throw e;
}

export async function getSystemCapabilities(): Promise<SystemInfo> {
  const res = await fetch("/api/system");
  if (!res.ok) await throwOnError(res);
  return res.json();
}

export interface ConvertResult {
  blob: Blob;
  filename: string;
}

function parseFilename(disposition: string | null, fallback: string): string {
  if (!disposition) return fallback;
  // RFC 5987 attachment; filename="foo.pdf" or filename*=UTF-8''foo.pdf
  const m1 = /filename\*\s*=\s*[^']*''([^;]+)/i.exec(disposition);
  if (m1) return decodeURIComponent(m1[1]);
  const m2 = /filename\s*=\s*"?([^";]+)"?/i.exec(disposition);
  if (m2) return m2[1];
  return fallback;
}

export async function convertFile(
  file: File,
  outputFormat: string,
  options: Record<string, unknown> = {},
  fallbackName = "output",
): Promise<ConvertResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("output_format", outputFormat);
  if (Object.keys(options).length) form.append("options", JSON.stringify(options));

  const res = await fetch("/api/convert", { method: "POST", body: form });
  if (!res.ok) await throwOnError(res);
  const blob = await res.blob();
  const filename = parseFilename(res.headers.get("content-disposition"), fallbackName);
  return { blob, filename };
}

export async function mergePdfs(files: File[]): Promise<ConvertResult> {
  const form = new FormData();
  for (const f of files) form.append("files", f);
  const res = await fetch("/api/merge/pdf", { method: "POST", body: form });
  if (!res.ok) await throwOnError(res);
  const blob = await res.blob();
  const filename = parseFilename(res.headers.get("content-disposition"), "merged.pdf");
  return { blob, filename };
}

// ---------------------------------------------------------------------------
// PDF page operations
// ---------------------------------------------------------------------------
export type SplitMode =
  | { type: "every_page" }
  | { type: "every_n"; n: number }
  | { type: "ranges"; ranges: [number, number][] };

async function postPdfOp(
  path: string,
  file: File,
  options: Record<string, unknown> | undefined,
  fallbackName: string,
): Promise<ConvertResult> {
  const form = new FormData();
  form.append("file", file);
  if (options !== undefined) form.append("options", JSON.stringify(options));
  const res = await fetch(path, { method: "POST", body: form });
  if (!res.ok) await throwOnError(res);
  const blob = await res.blob();
  const filename = parseFilename(res.headers.get("content-disposition"), fallbackName);
  return { blob, filename };
}

export async function splitPdf(file: File, mode: SplitMode): Promise<ConvertResult> {
  const stem = file.name.replace(/\.pdf$/i, "");
  return postPdfOp("/api/pdf/split", file, { mode }, `${stem}-split.zip`);
}

export async function deletePdfPages(file: File, pages: number[]): Promise<ConvertResult> {
  const stem = file.name.replace(/\.pdf$/i, "");
  return postPdfOp("/api/pdf/delete-pages", file, { pages }, `${stem}-edited.pdf`);
}

export async function extractPdfPages(file: File, pages: number[]): Promise<ConvertResult> {
  const stem = file.name.replace(/\.pdf$/i, "");
  return postPdfOp("/api/pdf/extract-pages", file, { pages }, `${stem}-extracted.pdf`);
}

export async function reorderPdfPages(file: File, order: number[]): Promise<ConvertResult> {
  const stem = file.name.replace(/\.pdf$/i, "");
  return postPdfOp("/api/pdf/reorder-pages", file, { order }, `${stem}-reordered.pdf`);
}
