import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";

export function Page({ children, wide = false }: { children: ReactNode; wide?: boolean }) {
  return (
    <div className={`mx-auto flex w-full flex-col gap-10 px-6 py-12 ${wide ? "max-w-5xl" : "max-w-3xl"}`}>
      {children}
    </div>
  );
}

export function PageHeader({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <header className="flex flex-col gap-2">
      <h1 className="font-serif text-3xl tracking-tight text-neutral-950">{title}</h1>
      {children && <p className="max-w-2xl text-sm leading-relaxed text-neutral-600">{children}</p>}
    </header>
  );
}

export function Button({
  children,
  variant = "primary",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "ghost" }) {
  const styles = {
    primary: "border-neutral-950 bg-neutral-950 text-white hover:bg-neutral-800",
    secondary: "border-neutral-300 bg-white text-neutral-950 hover:border-neutral-950",
    ghost: "border-transparent bg-transparent text-neutral-600 hover:text-neutral-950",
  }[variant];
  return (
    <button
      {...props}
      className={`shrink-0 border px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${styles} ${props.className ?? ""}`}
    >
      {children}
    </button>
  );
}

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-950 placeholder:text-neutral-400 ${props.className ?? ""}`}
    />
  );
}

export function TextArea(props: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      rows={2}
      {...props}
      className={`w-full resize-none border-0 bg-transparent px-3 py-2 text-sm text-neutral-950 placeholder:text-neutral-400 focus:outline-none ${props.className ?? ""}`}
    />
  );
}

export function Select(props: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={`w-full border border-neutral-300 bg-white px-3 py-2 text-sm text-neutral-950 ${props.className ?? ""}`}
    />
  );
}

export function ErrorText({ error }: { error?: string | null }) {
  if (!error) return null;
  return (
    <p role="alert" className="border border-neutral-950 px-3 py-2 text-sm text-neutral-950">
      {error}
    </p>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="text-sm leading-relaxed text-neutral-500">{children}</p>;
}

export function Label({ children }: { children: ReactNode }) {
  return <span className="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">{children}</span>;
}

export function Progress({ value }: { value: number }) {
  const pct = Math.max(0, Math.min(100, Math.round(value * 100)));
  return (
    <div className="flex items-center gap-3">
      <div className="h-1 flex-1 bg-neutral-200">
        <div className="h-1 bg-neutral-950 transition-[width]" style={{ width: `${pct}%` }} />
      </div>
      <span className="w-8 text-right text-[11px] tabular-nums text-neutral-500">{pct}%</span>
    </div>
  );
}
