import { NavLink, Route, Routes } from "react-router-dom";

import HomePage from "./pages/HomePage";
import SplitPdfPage from "./pages/SplitPdfPage";
import DeletePagesPage from "./pages/DeletePagesPage";
import ExtractPagesPage from "./pages/ExtractPagesPage";
import ReorderPagesPage from "./pages/ReorderPagesPage";

const NAV_ITEMS: { to: string; label: string }[] = [
  { to: "/", label: "Convert" },
  { to: "/split-pdf", label: "Split PDF" },
  { to: "/delete-pdf-pages", label: "Delete Pages" },
  { to: "/extract-pdf-pages", label: "Extract Pages" },
  { to: "/reorder-pdf-pages", label: "Reorder Pages" },
];

export default function App() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <nav className="mb-8 flex flex-wrap gap-2 border-b border-slate-200 pb-4">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              "rounded-full px-3 py-1.5 text-sm transition-colors " +
              (isActive
                ? "bg-slate-900 text-white"
                : "text-slate-600 hover:bg-slate-100")
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>

      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/split-pdf" element={<SplitPdfPage />} />
        <Route path="/delete-pdf-pages" element={<DeletePagesPage />} />
        <Route path="/extract-pdf-pages" element={<ExtractPagesPage />} />
        <Route path="/reorder-pdf-pages" element={<ReorderPagesPage />} />
      </Routes>
    </div>
  );
}
