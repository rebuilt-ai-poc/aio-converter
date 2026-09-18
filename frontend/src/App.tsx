import { useEffect, useMemo, useState } from "react";

import { convertFile, getSystemCapabilities, mergePdfs } from "./api/converter";
import { DropZone } from "./components/DropZone";
import { MergeList } from "./components/MergeList";
import { OptionsPanel } from "./components/OptionsPanel";
import type { ApiError, SourceFormat, Status, SystemInfo, TargetFormat } from "./types";

const EXT_TO_SOURCE: Record<string, SourceFormat> = {
  pdf: "pdf",
  txt: "txt",
  md: "md",
  markdown: "md",
  docx: "docx",
  png: "png",
  svg: "svg",
};

const TARGETS_BY_SOURCE: Record<SourceFormat, TargetFormat[]> = {
  pdf: ["docx", "txt", "md"],
  txt: ["pdf"],
  md: ["pdf"],
  docx: ["pdf"],
  png: ["jpg"],
  svg: ["jpg"],
};

const TARGET_LABEL: Record<TargetFormat, string> = {
  pdf: "PDF",
  txt: "Text",
  md: "Markdown",
  docx: "Word (DOCX)",
  jpg: "JPEG",
};

function detectSource(file: File): SourceFormat | null {
  const ext = file.name.split(".").pop()?.toLowerCase() ?? "";
  return EXT_TO_SOURCE[ext] ?? null;
}

function pairKey(source: SourceFormat, target: TargetFormat): string {
  return `${source}->${target}`;
}

function humanSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

const DEP_LABEL: Record<string, string> = {
  pandoc: "Pandoc",
  typst: "Typst",
  libreoffice: "LibreOffice",
  resvg: "resvg",
  pymupdf4llm: "PyMuPDF4LLM",
  python_docx: "python-docx",
};

function missingDependencyFor(
  source: SourceFormat,
  target: TargetFormat,
  system: SystemInfo | null,
): string | null {
  if (!system) return null;
  const e = system.engines;
  const need = (ok: boolean, label: string) => (ok ? null : label);
  switch (`${source}->${target}`) {
    case "md->pdf":
      return need(e.pandoc, "Pandoc") ?? need(e.typst, "Typst");
    case "docx->pdf":
      return need(e.libreoffice, "LibreOffice");
    case "svg->jpg":
      return need(e.resvg, "resvg");
    case "pdf->md":
      return need(e.pymupdf4llm, "PyMuPDF4LLM");
    case "pdf->docx":
      return need(e.python_docx, "python-docx");
  }
  return null;
}

export default function App() {
  const [system, setSystem] = useState<SystemInfo | null>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [target, setTarget] = useState<TargetFormat | null>(null);
  const [options, setOptions] = useState<Record<string, unknown>>({});
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<ApiError | null>(null);
  const [result, setResult] = useState<{ url: string; name: string; size: number } | null>(null);

  useEffect(() => {
    getSystemCapabilities()
      .then(setSystem)
      .catch((e: ApiError) => setError(e));
  }, []);

  // Cleanup blob URLs.
  useEffect(() => {
    return () => {
      if (result) URL.revokeObjectURL(result.url);
    };
  }, [result]);

  const source: SourceFormat | null = useMemo(() => {
    if (files.length === 0) return null;
    const first = detectSource(files[0]);
    if (!first) return null;
    // Multi-file only allowed when they're all PDFs (for the merge flow).
    if (files.length > 1 && !files.every((f) => detectSource(f) === "pdf")) return null;
    return first;
  }, [files]);

  const isMerge = files.length > 1 && source === "pdf";
  const targets: TargetFormat[] = source ? TARGETS_BY_SOURCE[source] ?? [] : [];

  // Reset target selection when the file set changes.
  useEffect(() => {
    setResult(null);
    setError(null);
    if (source == null) {
      setTarget(null);
      return;
    }
    if (isMerge) {
      setTarget("pdf");
      return;
    }
    setTarget((prev) => (prev && targets.includes(prev) ? prev : (targets[0] ?? null)));
    setOptions({});
  }, [source, isMerge]); // eslint-disable-line react-hooks/exhaustive-deps

  const missingDep = useMemo(
    () => (source && target ? missingDependencyFor(source, target, system) : null),
    [source, target, system],
  );

  const availability = useMemo(() => system?.conversions ?? {}, [system]);
  const disabledPair =
    source && target && !isMerge
      ? availability[pairKey(source, target)] === false
      : false;

  async function handleConvert() {
    if (!source) return;
    setError(null);
    setResult(null);
    setStatus("converting");
    try {
      if (isMerge) {
        const { blob, filename } = await mergePdfs(files);
        const url = URL.createObjectURL(blob);
        setResult({ url, name: filename, size: blob.size });
      } else if (target) {
        const { blob, filename } = await convertFile(files[0], target, options);
        const url = URL.createObjectURL(blob);
        setResult({ url, name: filename, size: blob.size });
      }
      setStatus("success");
    } catch (e) {
      setError(e as ApiError);
      setStatus("error");
    }
  }

  function reset() {
    if (result) URL.revokeObjectURL(result.url);
    setFiles([]);
    setTarget(null);
    setOptions({});
    setStatus("idle");
    setError(null);
    setResult(null);
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <header className="mb-8">
        <h1 className="text-3xl font-semibold text-slate-900">Universal Converter</h1>
        <p className="mt-1 text-sm text-slate-500">
          Local, private, no uploads to any server. PDF · DOCX · TXT · Markdown · PNG · SVG.
        </p>
      </header>

      {files.length === 0 && (
        <DropZone
          onFiles={(fs) => setFiles(fs)}
          accept=".pdf,.txt,.md,.markdown,.docx,.png,.svg"
          multiple
        />
      )}

      {files.length > 0 && (
        <div className="rounded-2xl border bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <div className="text-xs uppercase tracking-wide text-slate-400">Detected</div>
              <div className="text-lg font-medium text-slate-800">
                {source ? source.toUpperCase() : "Mixed / unsupported"}
                {isMerge ? ` × ${files.length}` : ""}
              </div>
            </div>
            <button
              onClick={reset}
              className="rounded px-3 py-1.5 text-sm text-slate-500 hover:bg-slate-100"
            >
              Clear
            </button>
          </div>

          {!isMerge && files[0] && (
            <div className="mb-4 flex items-center gap-3 rounded-xl bg-slate-50 px-4 py-3">
              <span className="flex-1 truncate font-medium text-slate-800">{files[0].name}</span>
              <span className="text-xs text-slate-500">{humanSize(files[0].size)}</span>
            </div>
          )}

          {isMerge && (
            <MergeList
              files={files}
              onReorder={setFiles}
              onRemove={(i) => setFiles(files.filter((_, j) => j !== i))}
            />
          )}

          {source && !isMerge && targets.length > 0 && (
            <div className="mt-6">
              <div className="text-xs uppercase tracking-wide text-slate-400">Convert to</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {targets.map((t) => {
                  const missing = missingDependencyFor(source, t, system);
                  const unavailable = availability[pairKey(source, t)] === false;
                  return (
                    <button
                      key={t}
                      onClick={() => setTarget(t)}
                      disabled={unavailable}
                      className={
                        "rounded-full px-4 py-1.5 text-sm transition-colors " +
                        (target === t
                          ? "bg-indigo-600 text-white"
                          : "bg-slate-100 text-slate-700 hover:bg-slate-200") +
                        (unavailable ? " cursor-not-allowed opacity-50" : "")
                      }
                      title={missing ? `${missing} not installed` : undefined}
                    >
                      {TARGET_LABEL[t]}
                    </button>
                  );
                })}
              </div>
              {disabledPair && missingDep && (
                <p className="mt-3 text-sm text-amber-700">
                  {TARGET_LABEL[target!]} conversion requires <b>{missingDep}</b>, which is not
                  installed on this system.
                </p>
              )}
            </div>
          )}

          {source && target && !isMerge && (
            <div className="mt-6 rounded-xl border bg-slate-50 p-4">
              <OptionsPanel
                source={source}
                target={target}
                options={options}
                onChange={setOptions}
              />
            </div>
          )}

          <div className="mt-6 flex items-center gap-3">
            <button
              onClick={handleConvert}
              disabled={
                status === "converting" ||
                !source ||
                (!isMerge && !target) ||
                (!!disabledPair && !isMerge)
              }
              className="rounded-lg bg-indigo-600 px-5 py-2 font-medium text-white shadow-sm hover:bg-indigo-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {status === "converting"
                ? "Converting…"
                : isMerge
                ? "Merge PDFs"
                : "Convert"}
            </button>
            {status === "converting" && (
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200">
                <div className="h-full w-1/3 animate-pulse bg-indigo-400" />
              </div>
            )}
          </div>

          {error && (
            <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <div className="font-medium">Conversion failed</div>
              <div className="mt-0.5">{error.message}</div>
            </div>
          )}

          {result && status === "success" && (
            <div className="mt-6 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-4">
              <div className="text-sm font-medium text-emerald-900">✓ Conversion complete</div>
              <div className="mt-2 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate font-medium text-slate-800">{result.name}</div>
                  <div className="text-xs text-slate-500">{humanSize(result.size)}</div>
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
                Convert another
              </button>
            </div>
          )}
        </div>
      )}

      {system && (
        <footer className="mt-8 text-center text-xs text-slate-400">
          Engines available:{" "}
          {Object.entries(system.engines)
            .filter(([, ok]) => ok)
            .map(([k]) => DEP_LABEL[k] ?? k)
            .join(" · ") || "none"}
        </footer>
      )}
    </div>
  );
}
