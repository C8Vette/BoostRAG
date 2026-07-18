import { Link } from "react-router-dom";
import { Header } from "../components/Header";
import { FooterStrip } from "../components/FooterStrip";
import { OriginBadge } from "../components/AnswerPanel";
import { Swell, Reveal } from "../components/motion";
import { CATEGORY_LABELS } from "./CategoryPage";
import hero from "../assets/hero-studio.jpg";

// Real answer captured from production 2026-07-13 — static proof, zero token cost.
const PROOF = {
  origin: "corpus",
  question: "What downpipe options are there for the M340i?",
  answer:
    "For the BMW M340i, the main choices are VRSF's Track Limited Racing Downpipe (race) and the High Flow Catted Downpipe — catted keeps the CEL away; race maximizes flow.",
  source: { product: "VRSF B58 Downpipe", trust_tier: "Tier 1", price: "From $299.99" },
};

export default function Landing() {
  return (
    <main className="min-h-screen bg-[#F6F6F4] text-zinc-900">
      <Header light />

      {/* Hero — white studio, Ken Burns */}
      <section className="relative overflow-hidden">
        <img
          src={hero}
          alt="Performance car in a white studio"
          className="kenburns h-[70vh] w-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-[#F6F6F4]/95 via-[#F6F6F4]/55 to-transparent" />
        <div className="absolute inset-0 flex flex-col items-start justify-center px-8 lg:px-24">
          <p className="text-sm font-bold uppercase tracking-[0.3em] text-zinc-600">
            Research smart. Build fast. Drive hard.
          </p>
          <h1 className="mt-4 max-w-3xl text-6xl font-black uppercase leading-none">
            The M340i Performance Advantage
          </h1>
          <Swell className="mt-8 block!">
            <Link
              to="/research"
              className="inline-block bg-zinc-900 px-8 py-4 font-black uppercase text-white"
            >
              Start Research
              <span className="ml-3 inline-block h-3 w-1 bg-[#0066B1]" />
              <span className="inline-block h-3 w-1 bg-[#E7222E]" />
            </Link>
          </Swell>
        </div>
      </section>

      {/* Value props */}
      <section className="mx-auto grid max-w-6xl gap-10 px-8 py-24 md:grid-cols-3">
        {[
          ["Precise Answers", "Backed by trusted sources & data"],
          ["Real-World Insights", "Community tested. Proven results."],
          ["Build Confidently", "The right parts. The right way."],
        ].map(([t, s]) => (
          <Reveal key={t}>
            <h2 className="text-xl font-black uppercase">{t}</h2>
            <p className="mt-2 text-zinc-600">{s}</p>
          </Reveal>
        ))}
      </section>

      {/* Live proof strip */}
      <Reveal className="mx-auto max-w-3xl px-8 pb-24">
        <div className="border border-zinc-300 bg-white p-6 shadow-sm">
          <p className="text-sm font-semibold text-zinc-500">&ldquo;{PROOF.question}&rdquo;</p>
          <div className="mt-3">
            <OriginBadge origin={PROOF.origin} variant="light" />
          </div>
          <p className="mt-2 text-[15px] leading-7">{PROOF.answer}</p>
          <p className="mt-3 text-xs font-bold uppercase text-zinc-500">
            {PROOF.source.product} · {PROOF.source.trust_tier} · {PROOF.source.price}
          </p>
        </div>
      </Reveal>

      {/* Category doorways — into the garage */}
      <section className="bg-zinc-900 px-8 py-24">
        <h2 className="mx-auto max-w-6xl text-3xl font-black uppercase text-white">
          Enter the garage
        </h2>
        <div className="mx-auto mt-10 grid max-w-6xl grid-cols-2 gap-4 md:grid-cols-4">
          {Object.entries(CATEGORY_LABELS).map(([slug, label]) => (
            <Swell key={slug} className="block!">
              <Link
                to={`/category/${slug}`}
                className="block border border-zinc-700 bg-black p-6 font-black uppercase text-zinc-100 hover:border-yellow-400"
              >
                {label}
              </Link>
            </Swell>
          ))}
        </div>
      </section>

      <FooterStrip />
    </main>
  );
}
