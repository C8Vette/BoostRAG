import { Gauge, Zap, ShieldCheck } from "lucide-react";
import { CornerMarks } from "./primitives";

export function Hero() {
  return (
    <section className="relative w-full">
      <div className="relative h-[555px] overflow-hidden border-b border-zinc-800/80 bg-black md:h-[525px] lg:h-[595px]">
        {/* Full-width hero image */}
        <img
          src="/assets/hero-car.png"
          alt="Dark BMW M340i in red-lit garage"
          className="absolute inset-0 h-full w-full object-cover object-[54%_18%] opacity-100 brightness-[1.65] contrast-[1.08] saturate-[1.08]"
        />

        {/* Overlays - softened only, no layout changes */}
        <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(0,0,0,0.82)_0%,rgba(0,0,0,0.62)_30%,rgba(0,0,0,0.22)_58%,rgba(0,0,0,0.10)_100%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(0,0,0,0.02)_0%,rgba(0,0,0,0.06)_68%,rgba(0,0,0,0.58)_100%)]" />
        <div className="absolute left-0 top-0 h-full w-[48%] bg-[radial-gradient(circle_at_36%_36%,rgba(127,29,29,0.18),transparent_48%)]" />

        {/* Left rail visual gutter */}
        <div className="absolute left-0 top-0 hidden h-full w-[86px] border-r border-zinc-900/80 bg-black/20 xl:block" />

        {/* Inner content - unchanged */}
        <div className="relative z-10 mx-auto flex h-full max-w-[1780px] items-start px-7 pt-[78px] lg:px-24 xl:pl-[110px]">
          <div className="max-w-[720px]">
            <div className="mb-3 flex items-center gap-5">
              <p className="text-[17px] font-black italic uppercase tracking-wide text-yellow-400 drop-shadow-[0_0_8px_rgba(250,204,21,.25)]">
                Research smart. Build fast. Drive hard.
              </p>

              <div className="hidden h-[10px] w-28 bg-[repeating-linear-gradient(110deg,#dc2626_0_4px,transparent_4px_8px)] lg:block" />
            </div>

            <h1 className="select-none text-[62px] font-black italic uppercase leading-[0.86] tracking-[-0.06em] sm:text-[82px] lg:text-[96px] xl:text-[104px]">
              <span className="block text-zinc-100 drop-shadow-[0_4px_0_rgba(255,255,255,.08)]">
                THE M340i
              </span>
              <span className="block text-red-600 drop-shadow-[0_0_30px_rgba(220,38,38,.35)]">
                PERFORMANCE
              </span>
              <span className="block text-red-600 drop-shadow-[0_0_30px_rgba(220,38,38,.25)]">
                ADVANTAGE
              </span>
            </h1>

            <p className="mt-5 max-w-[560px] text-[17px] font-medium leading-7 text-zinc-300">
              BoostRAG delivers source-backed answers, real-world insights,
              and parts intelligence for serious enthusiasts.
            </p>

            <div className="mt-7 grid max-w-[600px] grid-cols-1 gap-3 sm:grid-cols-3">
              <HeroMiniCard
                icon={<Gauge size={34} />}
                title="Precise Answers"
                text="Backed by trusted sources & data"
              />
              <HeroMiniCard
                icon={<Zap size={34} />}
                title="Real-World Insights"
                text="Community tested. Proven results."
              />
              <HeroMiniCard
                icon={<ShieldCheck size={34} />}
                title="Build Confidently"
                text="The right parts. The right way."
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function HeroMiniCard({ icon, title, text }) {
  return (
    <div className="relative min-h-[72px] border border-zinc-700/70 bg-black/55 px-4 py-3 backdrop-blur-sm">
      <CornerMarks />
      <div className="flex items-center gap-3">
        <div className="text-red-600">{icon}</div>
        <div>
          <h3 className="text-[11px] font-black uppercase text-zinc-100">
            {title}
          </h3>
          <p className="mt-1 text-[11px] font-semibold leading-4 text-zinc-400">
            {text}
          </p>
        </div>
      </div>
    </div>
  );
}
