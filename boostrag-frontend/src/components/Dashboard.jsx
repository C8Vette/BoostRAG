import {
  Gauge,
  Wrench,
  CircleDot,
  Thermometer,
  Disc3,
  Cpu,
  BadgeCheck,
} from "lucide-react";
import { Panel, PanelHeader, Sparkline } from "./primitives";
import { SourceBackedAnswers } from "./AnswerPanel";

const categories = [
  { label: "Overview", icon: Gauge, active: true },
  { label: "Engine", icon: Wrench },
  { label: "Intake & Exhaust", icon: CircleDot },
  { label: "Cooling", icon: Thermometer },
  { label: "Suspension", icon: Disc3 },
  { label: "Wheels & Tires", icon: CircleDot },
  { label: "Braking", icon: BadgeCheck },
  { label: "Electronics", icon: Cpu },
];

const trending = [
  ["Stage 2 Tuning", "+96% this week"],
  ["Downpipes", "+72% this week"],
  ["Intake Systems", "+58% this week"],
  ["Cooling Upgrades", "+47% this week"],
  ["Wheel & Tire Fitment", "+33% this week"],
];

export function Dashboard({ answer, sources, origin, error }) {
  return (
    <section className="relative z-10 mx-auto grid max-w-[1580px] gap-6 px-5 pt-3 pb-2 lg:grid-cols-[215px_1fr_390px] lg:px-10">
      <CategoryPanel />
      <SourceBackedAnswers
        answer={answer}
        sources={sources}
        origin={origin}
        error={error}
      />
      <TrendingPanel />
    </section>
  );
}

export function CategoryPanel() {
  return (
    <Panel className="p-2">
      {categories.map(({ label, icon: Icon, active }) => (
        <button
          key={label}
          className={`relative flex w-full items-center gap-3 border-b border-zinc-800/90 px-3 py-[10px] text-left text-[12px] font-black uppercase transition ${
            active
              ? "bg-zinc-900/70 text-zinc-100"
              : "text-zinc-400 hover:bg-zinc-900/40 hover:text-white"
          }`}
        >
          {active && (
            <span className="absolute left-0 top-0 h-full w-[3px] bg-red-600 shadow-[0_0_12px_rgba(220,38,38,.9)]" />
          )}
          <Icon size={18} className={active ? "text-red-600" : "text-zinc-500"} />
          {label}
        </button>
      ))}
    </Panel>
  );
}

export function TrendingPanel() {
  return (
    <Panel className="p-4">
      <PanelHeader title="Trending Topics" />

      <div className="space-y-2">
        {trending.map(([topic, stat], index) => (
          <div
            key={topic}
            className="grid grid-cols-[32px_1fr_auto] items-center gap-3 border border-zinc-800 bg-black/40 p-2"
          >
            <div className="grid h-8 w-8 place-items-center border border-yellow-500/70 bg-zinc-950 font-black text-yellow-400">
              {index + 1}
            </div>

            <div>
              <p className="text-[13px] font-black leading-4 text-zinc-100">
                {topic}
              </p>
              <p className="text-[11px] font-black text-green-500">{stat}</p>
            </div>

            <Sparkline />
          </div>
        ))}
      </div>
    </Panel>
  );
}
