import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { getSystemCapabilities } from "../api/converter";
import type { ApiError, SystemInfo } from "../types";
import { DropZone } from "./DropZone";
import { loadPdf, type PDFDocumentProxy } from "../lib/pdfjs";

interface PdfDocState {
  file: File;
  pdfDoc: PDFDocumentProxy;
  pageCount: number;
}

const PdfDocContext = createContext<PdfDocState | null>(null);

export function usePdfDoc(): PdfDocState {
  const ctx = useContext(PdfDocContext);
  if (!ctx) throw new Error("usePdfDoc must be used inside PdfToolLayout children");
  return ctx;
}

interface ToolResult {
  url: string;
  name: string;
  size: number;
}

interface Props {
  title: string;
  description: string;
  /** Accept-string for DropZone. Defaults to "application/pdf,.pdf". */
  accept?: string;
  /** Capability key in /api/system.conversions (e.g. "pdf:split"). */
  capabilityKey: string;
  /** Label on the primary submit button. */
  submitLabel: string;
  /** Whether the primary submit is currently valid. */
  canSubmit: boolean;
  /** Async submit handler — must return a { blob, filename } shape. */
  onSubmit: (file: File) => Promise<{ blob: Blob; filename: string }>;
  /** Tool-specific controls (has access to usePdfDoc()). */
  children: React.ReactNode;
}

function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function PdfToolLayout({
  title,
  description,
  accept = "application/pdf,.pdf",
  capabilityKey,
  submitLabel,
  canSubmit,
  onSubmit,
  children,
}: Props) {
  const [system, setSystem] = useState<SystemInfo | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [pdfDoc, setPdfDoc] = useState<PDFDocumentProxy | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<ApiError | null>(null);
  const [result, setResult] = useState<ToolResult | null>(null);

  useEffect(() => {
    document.title = `${title} — Universal Converter`;
  }, [title]);

  useEffect(() => {
    getSystemCapabilities()
      .then(setSystem)
      .catch(() => setSystem(null));
  }, []);

  // Load pdf.js document whenever `file` changes.
  useEffect(() => {
    if (!file) {
      setPdfDoc(null);
      setLoadError(null);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
    loadPdf(file)
      .then((doc) => {
        if (cancelled) {
          doc.destroy();
          return;
        }
        setPdfDoc(doc);
        setLoading(false);
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        setLoadError(e instanceof Error ? e.message : "Failed to open PDF");
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [file]);

  // Cleanup pdfDoc on unmount / change.
  useEffect(() => {
    return () => {
      pdfDoc?.destroy();
    };
  }, [pdfDoc]);

  // Cleanup result blob URLs.
  useEffect(() => {
    return () => {
      if (result) URL.revokeObjectURL(result.url);
    };
  }, [result]);

  const capabilityAvailable = useMemo(() => {
    if (!system) return true;
    const v = system.conversions[capabilityKey];
    return v !== false;
  }, [system, capabilityKey]);

  const docState: PdfDocState | null = useMemo(
    () => (file && pdfDoc ? { file, pdfDoc, pageCount: pdfDoc.numPages } : null),
    [file, pdfDoc],
  );

  const reset = useCallback(() => {
    if (result) URL.revokeObjectURL(result.url);
    setFile(null);
    setPdfDoc(null);
    setLoadError(null);
    setSubmitError(null);
    setResult(null);
  }, [result]);

  async function handleSubmit() {
    if (!file || !canSubmit) return;
    setSubmitting(true);
    setSubmitError(null);
    setResult(null);
    try {
      const { blob, filename } = await onSubmit(file);
      const url = URL.createObjectURL(blob);
      setResult({ url, name: filename, size: blob.size });
    } catch (e) {
      setSubmitError(e as ApiError);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <header className="mb-6">
        <h1 className="text-3xl font-semibold text-slate-900">{title}</h1>
        <p className="mt-1 text-sm text-slate-500">{description}</p>
      </header>

      {!capabilityAvailable && (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          This tool requires PyMuPDF, which is not installed on this system.
        </div>
      )}

      {!file && (
        <DropZone onFiles={(fs) => setFile(fs[0] ?? null)} accept={accept} />
      )}

      {file && (
        <div className="rounded-2xl border bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div className="min-w-0">
              <div className="text-xs uppercase tracking-wide text-slate-400">
                File
              </div>
              <div className="truncate text-lg font-medium text-slate-800">
                {file.name}
              </div>
              <div className="text-xs text-slate-500">
                {humanSize(file.size)}
                {docState ? ` · ${docState.pageCount} pages` : ""}
              </div>
            </div>
            <button
              onClick={reset}
              className="rounded px-3 py-1.5 text-sm text-slate-500 hover:bg-slate-100"
            >
              Clear
            </button>
          </div>

          {loading && (
            <div className="rounded-lg bg-slate-50 px-4 py-3 text-sm text-slate-500">
              Loading PDF…
            </div>
          )}

          {loadError && (
            <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <div className="font-medium">Could not open PDF</div>
              <div className="mt-0.5">{loadError}</div>
            </div>
          )}

          {docState && !result && (
            <>
              <PdfDocContext.Provider value={docState}>
                <div className="mt-2">{children}</div>
              </PdfDocContext.Provider>

              <div className="mt-6 flex items-center gap-3">
                <button
                  onClick={handleSubmit}
                  disabled={
                    submitting || !canSubmit || !capabilityAvailable
                  }
                  className="rounded-lg bg-indigo-600 px-5 py-2 font-medium text-white shadow-sm hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
                >
                  {submitting ? "Working…" : submitLabel}
                </button>
                {submitting && (
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200">
                    <div className="h-full w-1/3 animate-pulse bg-indigo-400" />
                  </div>
                )}
              </div>
            </>
          )}

          {submitError && (
            <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <div className="font-medium">Operation failed</div>
              <div className="mt-0.5">{submitError.message}</div>
            </div>
          )}

          {result && (
            <div className="mt-6 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-4">
              <div className="text-sm font-medium text-emerald-900">
                ✓ Done
              </div>
              <div className="mt-2 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate font-medium text-slate-800">
                    {result.name}
                  </div>
                  <div className="text-xs text-slate-500">
                    {humanSize(result.size)}
                  </div>
                </div>
                <a
                  href={result.url}
                  download={result.name}
                  className="rounded-lg bg-emerald-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-emerald-700"
                >
                  Download
                </a>
              </div>
              <button
                onClick={reset}
                className="mt-3 text-sm text-emerald-700 underline underline-offset-2 hover:text-emerald-900"
              >
                Start over
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
