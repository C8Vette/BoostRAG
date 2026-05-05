import { useState } from "react";
import ReactMarkdown from "react-markdown";

import {
  Search,
  Settings,
  Zap,
  ShieldCheck,
  Gauge,
  Wrench,
  Snowflake,
  Disc3,
  Cpu,
  CircleDot,
  Thermometer,
  BadgeCheck,
  Flag,
  TrendingUp,
  ChevronRight,
} from "lucide-react";

const navItems = ["Home", "Performance Areas", "Parts Library", "Guides", "About"];

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

const examples = [
  "Best intake for B58 reliability?",
  "Catted vs catless downpipe gains?",
  'Will 19" wheels affect ride quality?',
  "Best cooling upgrades for Stage 2?",
];

const answerCards = [
  {
    tag: "INTAKE",
    title: "High Flow Intakes: Do They Actually Add Power?",
    copy: "Testing shows gains of 8–15 whp on the B58 with quality intakes.",
    sources: 12,
    image: "/assets/intake-card.png",
  },
  {
    tag: "EXHAUST",
    title: "Catted vs Catless Downpipes on the B58",
    copy: "Catted retains low-end torque and keeps CEL at bay.",
    sources: 18,
    image: "/assets/downpipe-card.png",
  },
  {
    tag: "COOLING",
    title: "Upgraded Intercoolers: Worth It?",
    copy: "Lower IATs equal consistent power, especially in hot climates.",
    sources: 14,
    image: "/assets/intercooler-card.png",
  },
];

const trending = [
  ["Stage 2 Tuning", "+96% this week"],
  ["Downpipes", "+72% this week"],
  ["Intake Systems", "+58% this week"],
  ["Cooling Upgrades", "+47% this week"],
  ["Wheel & Tire Fitment", "+33% this week"],
];

function App() {
  const [query, setQuery] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  async function askBoostRAG(question = query) {
    const cleanedQuery = question.trim();

    if (!cleanedQuery) {
      setError("Please enter a question first.");
      return;
    }

    setIsLoading(true);
    setError("");
    setAnswer("");
    setSources([]);

    try {
      const response = await fetch("http://127.0.0.1:8000/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          query: cleanedQuery,
          top_k: 2,
        }),
      });

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      const data = await response.json();

      setAnswer(data.answer);
      setSources(data.sources || []);
      setQuery(cleanedQuery);
    } catch (err) {
      setError(
        "Something went wrong while asking BoostRAG. Make sure the FastAPI backend is running."
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="min-h-screen overflow-x-hidden bg-black text-zinc-100">
      <div className="fixed inset-0 bg-black" />

      <div className="fixed inset-0 opacity-[0.12] bg-[radial-gradient(circle_at_75%_8%,rgba(220,38,38,0.5),transparent_24%),radial-gradient(circle_at_28%_22%,rgba(127,29,29,0.28),transparent_20%),linear-gradient(180deg,#030303_0%,#050505_45%,#000_100%)]" />

      <div className="fixed inset-0 opacity-[0.055] [background-image:linear-gradient(rgba(255,255,255,.45)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.45)_1px,transparent_1px)] [background-size:52px_52px]" />

      <div className="relative z-10">
        <Header />

        <SideRail />

        <Hero />

        <SearchBand
          query={query}
          setQuery={setQuery}
          askBoostRAG={askBoostRAG}
          isLoading={isLoading}
        />

        <Dashboard answer={answer} sources={sources} error={error} />

        <FooterStrip />
      </div>
    </main>
  );
}

function Header() {
  return (
    <header className="relative z-30 h-[72px] border-b border-zinc-800/80 bg-black/90 backdrop-blur">
      <div className="mx-auto flex h-full max-w-[1780px] items-center justify-between px-5 lg:px-8">
        <div className="flex items-center gap-6">
          <div className="hidden h-10 w-10 place-items-center border border-red-950/80 bg-zinc-950/70 text-red-700 lg:grid">
            <Zap size={17} />
          </div>

          <div className="flex items-center gap-5">
            <div className="text-[34px] font-black italic leading-none tracking-[-0.06em]">
              <span className="text-white drop-shadow-[0_0_6px_rgba(255,255,255,.5)]">
                Boost
              </span>
              <span className="text-red-600 drop-shadow-[0_0_10px_rgba(220,38,38,.8)]">
                RAG
              </span>
            </div>

            <div className="hidden h-8 w-px bg-zinc-700 xl:block" />

            <p className="hidden text-[14px] font-semibold text-zinc-400 xl:block">
              AI-Powered Research for M340i Enthusiasts
            </p>
          </div>
        </div>

        <nav className="hidden h-full items-center gap-10 lg:flex">
          {navItems.map((item) => (
            <a
              key={item}
              href="#"
              className={`relative flex h-full items-center text-[13px] font-black uppercase tracking-wide transition hover:text-red-500 ${
                item === "Home" ? "text-red-500" : "text-zinc-200"
              }`}
            >
              {item}

              {item === "Home" && (
                <>
                  <span className="absolute bottom-0 left-0 h-[3px] w-full bg-red-600 shadow-[0_0_18px_rgba(220,38,38,.9)]" />
                  <span className="absolute bottom-0 left-1/2 h-2 w-9 -translate-x-1/2 skew-x-[-35deg] border-x border-t border-red-600 bg-black" />
                </>
              )}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <button className="hidden h-11 w-11 place-items-center border border-zinc-700 bg-zinc-950 text-zinc-300 shadow-[inset_0_0_14px_rgba(255,255,255,.05)] transition hover:border-red-600 hover:text-red-500 lg:grid">
            <Settings size={19} />
          </button>

          <button className="relative overflow-hidden bg-yellow-400 px-7 py-3 text-[13px] font-black uppercase tracking-wide text-black shadow-[0_0_24px_rgba(250,204,21,.24)] transition hover:bg-yellow-300">
            <span className="relative z-10">Start Research</span>
            <span className="absolute inset-y-0 right-0 w-6 skew-x-[-22deg] bg-yellow-200/60" />
          </button>
        </div>
      </div>
    </header>
  );
}

function SideRail() {
  return (
    <aside className="pointer-events-none fixed left-0 top-[72px] z-20 hidden h-[560px] w-[86px] xl:block">
      <div className="absolute inset-0 border-r border-zinc-900/80 bg-black/18" />

      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rotate-[-90deg] whitespace-nowrap text-[11px] font-black uppercase tracking-[0.42em] text-zinc-500">
        RESEARCH · COMP · UPGRADE · B58
      </div>
    </aside>
  );
}

function Hero() {
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

function HeroMiniCard({ icon, title, text }) {
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

function SearchBand({ query, setQuery, askBoostRAG, isLoading }) {
  return (
    <section className="relative z-20 mx-auto -mt-2 max-w-[1580px] px-5 pt-8 lg:px-10">
      <div className="relative border border-zinc-700/80 bg-zinc-950/88 px-7 py-5 shadow-[0_12px_40px_rgba(0,0,0,.55)] backdrop-blur-md clip-search">
        <CornerMarks />

        <h2 className="mb-4 text-[20px] font-black italic uppercase tracking-wide text-yellow-400">
          Ask BoostRAG
        </h2>

        <form
          className="flex h-[46px] overflow-hidden border border-zinc-700 bg-black"
          onSubmit={(event) => {
            event.preventDefault();
            askBoostRAG();
          }}
        >
          <div className="grid w-14 place-items-center text-zinc-500">
            <Search size={22} />
          </div>

          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="min-w-0 flex-1 bg-transparent px-2 text-[15px] font-medium text-zinc-200 outline-none placeholder:text-zinc-500"
            placeholder="Ask anything about M340i performance parts, mods, fitment, results..."
          />

          <button
            type="submit"
            disabled={isLoading}
            className="relative w-[130px] bg-yellow-400 text-[13px] font-black uppercase text-black transition hover:bg-yellow-300 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoading ? "Thinking..." : "Search"}
          </button>
        </form>

        <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
          <span className="mr-2 text-[13px] font-semibold text-zinc-500">
            Try an example:
          </span>

          {examples.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => askBoostRAG(item)}
              disabled={isLoading}
              className="group flex items-center gap-3 border border-zinc-700 bg-black/60 px-4 py-2 text-[13px] font-bold text-zinc-300 transition hover:border-red-600 hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              {item}
              <Search size={14} className="text-red-600" />
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

function Dashboard({ answer, sources, error }) {
  return (
    <section className="relative z-10 mx-auto grid max-w-[1580px] gap-6 px-5 pt-3 pb-2 lg:grid-cols-[215px_1fr_390px] lg:px-10">
      <CategoryPanel />
      <SourceBackedAnswers answer={answer} sources={sources} error={error} />
      <TrendingPanel />
    </section>
  );
}

function CategoryPanel() {
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

function SourceBackedAnswers({ answer, sources, error }) {
  if (error) {
    return (
      <Panel className="p-4">
        <PanelHeader title="Source-Backed Answers" />
        <div className="border border-red-900/70 bg-red-950/20 p-5 text-sm font-semibold leading-6 text-red-200">
          {error}
        </div>
      </Panel>
    );
  }

  if (answer) {
    return (
      <Panel className="p-4">
        <PanelHeader title="BoostRAG Answer" />

        <div className="space-y-4">
          <div className="border border-zinc-800 bg-black/50 p-5 text-[15px] font-medium leading-7 text-zinc-200">
            <ReactMarkdown
              components={{
                strong: ({ children }) => (
                  <strong className="font-black text-white">{children}</strong>
                ),
                p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
                ul: ({ children }) => (
                  <ul className="mb-3 list-disc space-y-1 pl-5">{children}</ul>
                ),
                li: ({ children }) => <li>{children}</li>,
              }}
            >
              {answer}
            </ReactMarkdown>
          </div>

          <div>
            <h3 className="mb-3 text-sm font-black uppercase tracking-wide text-yellow-400">
              Sources Used
            </h3>

            <div className="grid gap-3 xl:grid-cols-2">
              {sources.map((source, index) => (
                <article
                  key={`${source.source_file}-${index}`}
                  className="border border-zinc-800 bg-zinc-950/90 p-4"
                >
                  <p className="text-[11px] font-black uppercase text-red-600">
                    {source.category || "Source"}
                  </p>

                  <h4 className="mt-1 text-[15px] font-black leading-5 text-white">
                    {source.product || source.source_file || "Unknown source"}
                  </h4>

                  <p className="mt-2 text-[12px] font-semibold text-zinc-500">
                    {source.brand || "Unknown brand"}
                    {source.price ? ` • ${source.price}` : ""}
                  </p>

                  {source.text_preview && (
                    <p className="mt-3 line-clamp-3 text-[12px] leading-5 text-zinc-400">
                      {source.text_preview}
                    </p>
                  )}

                  {source.url && (
                    <a
                      href={source.url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-3 inline-block text-[12px] font-black uppercase text-yellow-400 hover:text-yellow-300"
                    >
                      View Source
                    </a>
                  )}
                </article>
              ))}
            </div>
          </div>
        </div>
      </Panel>
    );
  }

  return (
    <Panel className="p-4">
      <PanelHeader title="Source-Backed Answers" />

      <div className="grid gap-3 xl:grid-cols-3">
        {answerCards.map((card) => (
          <article
            key={card.title}
            className="group relative grid min-h-[185px] grid-cols-[130px_1fr] overflow-hidden border border-zinc-800 bg-zinc-950/90 transition hover:border-red-700"
          >
            <div className="relative overflow-hidden bg-black">
              <img
                src={card.image}
                alt={card.title}
                className="h-full w-full object-cover opacity-90 grayscale-[25%] transition duration-500 group-hover:scale-110 group-hover:grayscale-0"
              />
              <div className="absolute inset-0 bg-gradient-to-r from-transparent to-black/45" />
            </div>

            <div className="flex flex-col p-4">
              <p className="text-[11px] font-black uppercase text-red-600">
                {card.tag}
              </p>

              <h3 className="mt-1 text-[16px] font-black leading-5 text-white">
                {card.title}
              </h3>

              <p className="mt-3 flex-1 text-[13px] font-medium leading-5 text-zinc-400">
                {card.copy}
              </p>

              <div className="mt-3 flex items-center justify-between text-[12px] font-bold text-zinc-500">
                <span>Sources: {card.sources}</span>
                <ChevronRight
                  size={18}
                  className="transition group-hover:translate-x-1 group-hover:text-red-500"
                />
              </div>
            </div>
          </article>
        ))}
      </div>
    </Panel>
  );
}

function TrendingPanel() {
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

function FooterStrip() {
  const items = [
    {
      icon: <Gauge size={52} />,
      title: "Unlock Real Performance",
      text: "Data-driven insights. Real-world results.",
    },
    {
      icon: <Flag size={52} />,
      title: "Research With Confidence",
      text: "Every answer backed by credible sources.",
    },
    {
      icon: <ShieldCheck size={52} />,
      title: "Build The Right Way",
      text: "Reduce guesswork. Maximize results.",
    },
    {
      icon: <TrendingUp size={52} />,
      title: "Drive Different",
      text: "Your car. Your build. Your advantage.",
    },
  ];

  return (
    <section className="relative z-10 mx-auto grid max-w-[1350px] gap-8 px-5 pb-10 pt-6 md:grid-cols-2 lg:grid-cols-4 lg:px-10">
      {items.map((item) => (
        <div
          key={item.title}
          className="flex items-center gap-4 border-r border-zinc-900/90 pr-6"
        >
          <div className="text-red-600 drop-shadow-[0_0_16px_rgba(220,38,38,.4)]">
            {item.icon}
          </div>

          <div>
            <h3 className="text-[13px] font-black uppercase text-yellow-400">
              {item.title}
            </h3>
            <p className="mt-1 text-[14px] font-semibold leading-5 text-zinc-400">
              {item.text}
            </p>
          </div>
        </div>
      ))}
    </section>
  );
}

function Panel({ children, className = "" }) {
  return (
    <div
      className={`relative border border-zinc-700/70 bg-zinc-950/80 shadow-[0_0_24px_rgba(0,0,0,.45)] backdrop-blur ${className}`}
    >
      <CornerMarks />
      {children}
    </div>
  );
}

function PanelHeader({ title }) {
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

function CornerMarks() {
  return (
    <>
      <span className="pointer-events-none absolute left-0 top-0 h-4 w-4 border-l border-t border-red-600/90" />
      <span className="pointer-events-none absolute bottom-0 right-0 h-4 w-4 border-b border-r border-red-600/90" />
    </>
  );
}

function SmallDot() {
  return (
    <span className="grid h-4 w-4 place-items-center rounded-full border border-zinc-500 text-[8px] text-zinc-400">
      •
    </span>
  );
}

function Sparkline() {
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

export default App;