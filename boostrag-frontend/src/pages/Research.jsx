import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Header } from "../components/Header";
import { SideRail } from "../components/SideRail";
import { SearchBand } from "../components/SearchBand";
import { Dashboard } from "../components/Dashboard";
import { FooterStrip } from "../components/FooterStrip";
import { useAsk } from "../lib/useAsk";
import { useAuth } from "../lib/auth";
import { getGarage } from "../lib/api";

export default function Research() {
  const [params] = useSearchParams();
  const seeded = params.get("q") || "";
  const ask = useAsk(seeded);
  const { user } = useAuth();
  const [garageCar, setGarageCar] = useState(null);
  const seededOnce = useRef(false);

  // Know whether to offer personalization (logged in + a saved car).
  const loadGarageCar = useCallback(async () => {
    try {
      const data = await getGarage();
      setGarageCar(data?.garage ?? null);
    } catch {
      setGarageCar(null);
    }
  }, []);

  useEffect(() => {
    // On logout garageCar may be stale, but `personalizable` also gates on `user`,
    // so no synchronous clear is needed here.
    // eslint-disable-next-line react-hooks/set-state-in-effect -- awaits getGarage before setState; no synchronous cascade
    if (user) loadGarageCar();
  }, [user, loadGarageCar]);

  useEffect(() => {
    if (seeded && !seededOnce.current) {
      seededOnce.current = true;
      ask.setQuery(seeded);
    }
    // prefill only — never auto-submit (no surprise token spend)
    // eslint-disable-next-line react-hooks/exhaustive-deps -- ask.setQuery is a stable setState identity; omitting the rest of `ask` avoids re-running on every render
  }, [seeded, ask.setQuery]);

  return (
    <main className="min-h-screen overflow-x-hidden bg-black text-zinc-100">
      <div className="fixed inset-0 bg-black" />

      <div className="fixed inset-0 opacity-[0.12] bg-[radial-gradient(circle_at_75%_8%,rgba(220,38,38,0.5),transparent_24%),radial-gradient(circle_at_28%_22%,rgba(127,29,29,0.28),transparent_20%),linear-gradient(180deg,#030303_0%,#050505_45%,#000_100%)]" />

      <div className="fixed inset-0 opacity-[0.055] [background-image:linear-gradient(rgba(255,255,255,.45)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.45)_1px,transparent_1px)] [background-size:52px_52px]" />

      <div className="relative z-10">
        <Header />

        <SideRail />

        <SearchBand
          query={ask.query}
          setQuery={ask.setQuery}
          askBoostRAG={(question) => ask.submit(question)}
          isLoading={ask.isLoading}
          personalizable={Boolean(user && garageCar)}
          garageModel={garageCar?.model}
          useContext={ask.useContext}
          setUseContext={ask.setUseContext}
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
