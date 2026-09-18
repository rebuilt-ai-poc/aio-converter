export type SourceFormat = "pdf" | "txt" | "md" | "docx" | "png" | "svg";
export type TargetFormat = "pdf" | "txt" | "md" | "docx" | "jpg";

export interface SystemInfo {
  engines: {
    pymupdf: boolean;
    pymupdf4llm: boolean;
    python_docx: boolean;
    reportlab: boolean;
    pillow: boolean;
    pandoc: boolean;
    typst: boolean;
    libreoffice: boolean;
    resvg: boolean;
  };
  conversions: Record<string, boolean>;
  limits: {
    max_file_mb: number;
    max_merge_files: number;
    max_merge_total_mb: number;
  };
}

export interface ApiError {
  code: string;
  message: string;
}

export type Status = "idle" | "converting" | "success" | "error";
