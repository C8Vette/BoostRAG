import { Header } from "../components/Header";
import { SideRail } from "../components/SideRail";
import { Hero } from "../components/Hero";
import { SearchBand } from "../components/SearchBand";
import { Dashboard } from "../components/Dashboard";
import { FooterStrip } from "../components/FooterStrip";
import { useAsk } from "../lib/useAsk";

export default function Landing() {
  const ask = useAsk();

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
          query={ask.query}
          setQuery={ask.setQuery}
          askBoostRAG={(question) => ask.submit(question)}
          isLoading={ask.isLoading}
        />

        <Dashboard
          answer={ask.answer}
          sources={ask.sources}
          origin={ask.origin}
          error={ask.error}
        />

        <FooterStrip />
      </div>
    </main>
  );
}
