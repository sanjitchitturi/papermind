import { NavLink } from "react-router-dom";

const LINKS = [
  { to: "/", label: "Search" },
  { to: "/chat", label: "Chat" },
  { to: "/integrity", label: "Citation Integrity" },
  { to: "/graph", label: "Knowledge Graph" },
  { to: "/research", label: "Research Mode" },
  { to: "/eval", label: "Eval Dashboard" },
];

export function NavBar() {
  return (
    <nav className="flex items-center gap-1 border-b border-gray-800 bg-gray-950 px-4 py-3">
      <span className="mr-6 text-lg font-bold text-gray-100">PaperMind</span>
      {LINKS.map((link) => (
        <NavLink
          key={link.to}
          to={link.to}
          className={({ isActive }) =>
            `rounded px-3 py-1.5 text-sm ${isActive ? "bg-gray-800 text-white" : "text-gray-400 hover:text-gray-200"}`
          }
        >
          {link.label}
        </NavLink>
      ))}
    </nav>
  );
}
