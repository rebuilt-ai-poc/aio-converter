interface Props {
  files: File[];
  onReorder: (files: File[]) => void;
  onRemove: (index: number) => void;
}

export function MergeList({ files, onReorder, onRemove }: Props) {
  const move = (from: number, to: number) => {
    if (to < 0 || to >= files.length) return;
    const next = files.slice();
    const [item] = next.splice(from, 1);
    next.splice(to, 0, item);
    onReorder(next);
  };

  return (
    <ol className="mt-4 divide-y rounded-xl border bg-white">
      {files.map((f, i) => (
        <li key={`${f.name}-${i}`} className="flex items-center gap-3 px-4 py-3">
          <span className="w-6 text-right text-sm text-slate-500">{i + 1}.</span>
          <span className="flex-1 truncate font-medium text-slate-800">{f.name}</span>
          <span className="text-xs text-slate-500">{(f.size / 1024).toFixed(1)} KB</span>
          <button
            onClick={() => move(i, i - 1)}
            className="rounded px-2 py-1 text-slate-500 hover:bg-slate-100 disabled:opacity-30"
            disabled={i === 0}
            aria-label="Move up"
          >
            ↑
          </button>
          <button
            onClick={() => move(i, i + 1)}
            className="rounded px-2 py-1 text-slate-500 hover:bg-slate-100 disabled:opacity-30"
            disabled={i === files.length - 1}
            aria-label="Move down"
          >
            ↓
          </button>
          <button
            onClick={() => onRemove(i)}
            className="rounded px-2 py-1 text-slate-500 hover:bg-red-50 hover:text-red-600"
            aria-label="Remove"
          >
            ×
          </button>
        </li>
      ))}
    </ol>
  );
}
