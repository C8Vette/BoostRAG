export function SideRail() {
  return (
    <aside className="pointer-events-none fixed left-0 top-[72px] z-20 hidden h-[560px] w-[86px] xl:block">
      <div className="absolute inset-0 border-r border-zinc-900/80 bg-black/18" />

      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rotate-[-90deg] whitespace-nowrap text-[11px] font-black uppercase tracking-[0.42em] text-zinc-500">
        RESEARCH · COMP · UPGRADE · B58
      </div>
    </aside>
  );
}
