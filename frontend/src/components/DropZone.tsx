import { useCallback, useRef, useState } from "react";

interface Props {
  onFiles: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
}

export function DropZone({ onFiles, accept, multiple }: Props) {
  const [hover, setHover] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handle = useCallback(
    (files: FileList | null) => {
      if (!files || files.length === 0) return;
      onFiles(Array.from(files));
    },
    [onFiles],
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setHover(true);
      }}
      onDragLeave={() => setHover(false)}
      onDrop={(e) => {
        e.preventDefault();
        setHover(false);
        handle(e.dataTransfer.files);
      }}
      onClick={() => inputRef.current?.click()}
      className={
        "flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-16 text-center transition-colors " +
        (hover
          ? "border-indigo-400 bg-indigo-50"
          : "border-slate-300 bg-white hover:border-slate-400")
      }
    >
      <div className="text-4xl">📄</div>
      <div className="mt-4 text-lg font-medium text-slate-700">
        Drop {multiple ? "files" : "a file"} here
      </div>
      <div className="mt-1 text-sm text-slate-500">or click to choose</div>
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        accept={accept}
        multiple={multiple}
        onChange={(e) => handle(e.target.files)}
      />
    </div>
  );
}
