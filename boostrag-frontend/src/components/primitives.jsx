export function Panel({ children, className = "" }) {
  return (
    <div
      className={`relative border border-zinc-700/70 bg-zinc-950/80 shadow-[0_0_24px_rgba(0,0,0,.45)] backdrop-blur ${className}`}
    >
      <CornerMarks />
      {children}
    </div>
  );
}

export function PanelHeader({ title }) {
  return (
    <div className="mb-4 flex items-center justify-between border-b border-zinc-800 pb-3">
      <h2 className="text-[20px] font-black italic uppercase tracking-wide text-yellow-400">
        {title}
      </h2>

      <button className="text-[12px] font-black uppercase text-zinc-400 transition hover:text-red-500">
        View All
      </button>
    </div>
  );
}

export function CornerMarks() {
  return (
    <>
      <span className="pointer-events-none absolute left-0 top-0 h-4 w-4 border-l border-t border-red-600/90" />
      <span className="pointer-events-none absolute bottom-0 right-0 h-4 w-4 border-b border-r border-red-600/90" />
    </>
  );
}

export function SmallDot() {
  return (
    <span className="grid h-4 w-4 place-items-center rounded-full border border-zinc-500 text-[8px] text-zinc-400">
      •
    </span>
  );
}

export function Sparkline() {
  return (
    <svg viewBox="0 0 100 28" className="h-8 w-24 text-red-500">
      <polyline
        points="0,20 10,18 18,10 28,22 38,6 47,14 55,12 63,21 73,16 84,18 92,9 100,13"
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
}
