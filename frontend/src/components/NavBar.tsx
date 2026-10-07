import { NavLink } from "react-router-dom";

const LINKS = [
  { to: "/search", label: "Search" },
  { to: "/chat", label: "Chat" },
  { to: "/integrity", label: "Citation Integrity" },
  { to: "/graph", label: "Knowledge Graph" },
  { to: "/research", label: "Research Mode" },
  { to: "/eval", label: "Eval Dashboard" },
];

export function NavBar() {
  return (
    <nav className="flex items-center gap-1 border-b border-neutral-200 bg-white px-6 py-4">
      <NavLink to="/" end className="mr-10 font-serif text-xl font-semibold tracking-tight text-neutral-950">
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
