import { useState } from "react";
import { NavLink } from "react-router-dom";

const LINKS = [
  { to: "/search", label: "Library" },
  { to: "/chat", label: "Chat" },
  { to: "/integrity", label: "Integrity" },
  { to: "/graph", label: "Graph" },
  { to: "/research", label: "Research" },
  { to: "/eval", label: "Eval" },
];

export function NavBar() {
  const [open, setOpen] = useState(false);

  return (
    <header className="sticky top-0 z-20 border-b border-neutral-200 bg-white/90 backdrop-blur">
      <nav className="mx-auto flex max-w-5xl items-center px-6 py-3">
        <NavLink
          to="/"
          end
          className="font-serif text-xl font-semibold tracking-tight text-neutral-950"
          onClick={() => setOpen(false)}
        >
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

        <a
          href="https://github.com/sanjitchitturi/papermind"
          className="ml-auto hidden text-xs text-neutral-500 hover:text-neutral-950 md:block"
        >
          Source
        </a>

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
          <a
            href="https://github.com/sanjitchitturi/papermind"
            className="py-2 text-sm text-neutral-600"
          >
            Source on GitHub
          </a>
        </div>
      )}
    </header>
  );
}
