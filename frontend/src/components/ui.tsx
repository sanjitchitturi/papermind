import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";

export function Page({ children, wide = false }: { children: ReactNode; wide?: boolean }) {
  return <div className={`mx-auto flex flex-col gap-10 px-6 py-12 ${wide ? "max-w-5xl" : "max-w-3xl"}`}>{children}</div>;
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
      className={`shrink-0 border px-4 py-2 text-sm font-medium disabled:opacity-40 ${styles} ${props.className ?? ""}`}
    />
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

export function ErrorText({ error }: { error?: string | null }) {
  if (!error) return null;
  return <p className="border border-neutral-950 px-3 py-2 text-sm text-neutral-950">{error}</p>;
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="text-sm text-neutral-500">{children}</p>;
}

export function Label({ children }: { children: ReactNode }) {
  return <span className="text-[10px] font-semibold uppercase tracking-wider text-neutral-500">{children}</span>;
}
