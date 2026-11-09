import { useState } from "react";
import { NavLink } from "react-router-dom";

const LINKS = [
  { to: "/search", label: "Library" },
  { to: "/chat", label: "Questions" },
  { to: "/integrity", label: "Integrity" },
  { to: "/graph", label: "Graph" },
  { to: "/research", label: "Research" },
  { to: "/eval", label: "Evaluation" },
];

export function NavBar() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-20 border-b border-neutral-200 bg-white/90 backdrop-blur">
      <nav
        aria-label="Main navigation"
        className="mx-auto flex max-w-5xl items-center px-6 py-3"
      >
        <NavLink
          to="/"
          end
          className="flex items-center gap-2 font-serif text-xl font-semibold tracking-tight text-[#163e32]"
          onClick={() => setOpen(false)}
        >
          <span
            aria-hidden
            className="grid h-7 w-7 place-items-center rounded-md bg-[#234e39] font-serif text-sm text-white"
          >
            p.
          </span>{" "}
          PaperMind
        </NavLink>

        <div className="ml-10 hidden items-center gap-1 md:flex">
          {LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `border-b-2 px-3 py-1.5 text-sm transition-colors ${
                  isActive
                    ? "border-neutral-950 font-medium text-neutral-950"
                    : "border-transparent text-neutral-500 hover:border-neutral-300 hover:text-neutral-900"
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </div>

        <button
          type="button"
          className="ml-auto border border-neutral-300 px-2 py-1 text-xs text-neutral-700 md:hidden"
          onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          aria-label="Toggle navigation"
        >
          {open ? "Close" : "Menu"}
        </button>
      </nav>

      {open && (
        <div className="flex flex-col border-t border-neutral-200 px-6 py-3 md:hidden">
          {LINKS.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `py-2 text-sm ${isActive ? "font-medium text-neutral-950" : "text-neutral-600"}`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </div>
      )}
    </header>
  );
}
