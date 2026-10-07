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
  return (
    <nav className="sticky top-0 z-20 flex items-center gap-1 border-b border-neutral-200 bg-white/95 px-6 py-3 backdrop-blur">
      <NavLink to="/" end className="mr-8 font-serif text-xl font-semibold tracking-tight text-neutral-950">
        PaperMind
      </NavLink>
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
    </nav>
  );
}
