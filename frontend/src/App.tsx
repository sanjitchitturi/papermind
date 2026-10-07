import { lazy, Suspense } from "react";
import { Route, Routes } from "react-router-dom";
import { Footer } from "./components/Footer";
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
  return (
    <div className="mx-auto max-w-3xl px-6 py-16">
      <div className="h-3 w-40 bg-neutral-200" />
      <div className="mt-6 h-3 w-full bg-neutral-100" />
      <div className="mt-2 h-3 w-5/6 bg-neutral-100" />
    </div>
  );
}

function NotFound() {
  return (
    <div className="mx-auto max-w-3xl px-6 py-24">
      <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-neutral-500">404</p>
      <h1 className="mt-3 font-serif text-3xl">That page is not in the library.</h1>
      <a href="/" className="mt-6 inline-block text-sm underline">
        Back to PaperMind
      </a>
    </div>
  );
}

export function App() {
  return (
    <div className="flex min-h-screen flex-col bg-white font-sans text-neutral-950">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:bg-white focus:px-3 focus:py-2 focus:text-sm"
      >
        Skip to content
      </a>
      <NavBar />
      <StatusBar />
      <main id="main" className="flex-1">
        <Suspense fallback={<Fallback />}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/search" element={<Search />} />
            <Route path="/chat" element={<PaperChat />} />
            <Route path="/integrity" element={<CitationIntegrity />} />
            <Route path="/graph" element={<KnowledgeGraph />} />
            <Route path="/research" element={<ResearchMode />} />
            <Route path="/eval" element={<EvalDashboard />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </main>
      <Footer />
    </div>
  );
}
