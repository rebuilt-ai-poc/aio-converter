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
