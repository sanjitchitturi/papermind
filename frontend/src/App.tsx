import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { NavBar } from "./components/NavBar";
import { StatusBar } from "./components/StatusBar";
import { Home } from "./pages/Home";

const Search = lazy(() => import("./pages/Search").then((m) => ({ default: m.Search })));
const PaperChat = lazy(() => import("./pages/PaperChat").then((m) => ({ default: m.PaperChat })));
const CitationIntegrity = lazy(() => import("./pages/CitationIntegrity").then((m) => ({ default: m.CitationIntegrity })));
const KnowledgeGraph = lazy(() => import("./pages/KnowledgeGraph").then((m) => ({ default: m.KnowledgeGraph })));
const ResearchMode = lazy(() => import("./pages/ResearchMode").then((m) => ({ default: m.ResearchMode })));
const EvalDashboard = lazy(() => import("./pages/EvalDashboard").then((m) => ({ default: m.EvalDashboard })));

function Fallback() {
  return <p className="px-6 py-12 text-sm text-neutral-500">Loading...</p>;
}

export function App() {
  return (
    <div className="min-h-screen bg-white font-sans text-neutral-950">
      <NavBar />
      <StatusBar />
      <Suspense fallback={<Fallback />}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/search" element={<Search />} />
          <Route path="/chat" element={<PaperChat />} />
          <Route path="/integrity" element={<CitationIntegrity />} />
          <Route path="/graph" element={<KnowledgeGraph />} />
          <Route path="/research" element={<ResearchMode />} />
          <Route path="/eval" element={<EvalDashboard />} />
        </Routes>
      </Suspense>
    </div>
  );
}
