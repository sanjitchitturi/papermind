export function Footer() {
  return (
    <footer className="mt-auto border-t border-neutral-200">
      <div className="mx-auto flex max-w-5xl flex-col gap-3 px-6 py-7 text-xs text-neutral-500 sm:flex-row sm:items-center sm:justify-between">
        <p>
          <span className="font-serif text-base text-[#163e32]">PaperMind</span>
          <span className="ml-3">A little clarity for your next idea.</span>
        </p>
        <div className="flex gap-5">
          <span>Local research workspace</span>
        </div>
      </div>
    </footer>
  );
}
