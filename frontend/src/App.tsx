import { Route, Routes } from "react-router-dom";
import { NavBar } from "./components/NavBar";
import { Home } from "./pages/Home";
import { Search } from "./pages/Search";
import { PaperChat } from "./pages/PaperChat";
import { CitationIntegrity } from "./pages/CitationIntegrity";
import { KnowledgeGraph } from "./pages/KnowledgeGraph";
import { ResearchMode } from "./pages/ResearchMode";
import { EvalDashboard } from "./pages/EvalDashboard";

export function App() {
  return (
    <div className="min-h-screen bg-white font-sans text-neutral-950">
      <NavBar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/search" element={<Search />} />
        <Route path="/chat" element={<PaperChat />} />
        <Route path="/integrity" element={<CitationIntegrity />} />
        <Route path="/graph" element={<KnowledgeGraph />} />
        <Route path="/research" element={<ResearchMode />} />
        <Route path="/eval" element={<EvalDashboard />} />
      </Routes>
    </div>
  );
}
