export function Footer() {
  return (
    <footer className="mt-auto border-t border-neutral-200">
      <div className="mx-auto flex max-w-5xl flex-col gap-3 px-6 py-8 text-xs text-neutral-500 sm:flex-row sm:items-center sm:justify-between">
        <p>
          PaperMind. Read the papers. MIT License.
        </p>
        <div className="flex flex-wrap gap-4">
          <a href="https://github.com/sanjitchitturi/papermind" className="hover:text-neutral-950">
            GitHub
          </a>
          <a href="https://thepapermind.vercel.app" className="hover:text-neutral-950">
            Live
          </a>
          <a href="https://papermind-api-laof.onrender.com/docs" className="hover:text-neutral-950">
            API docs
          </a>
          <a href="https://papermind-api-laof.onrender.com/health" className="hover:text-neutral-950">
            Health
          </a>
        </div>
      </div>
    </footer>
  );
}
