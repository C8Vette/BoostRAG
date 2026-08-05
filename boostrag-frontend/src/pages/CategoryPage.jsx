import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Header } from "../components/Header";
import { FooterStrip } from "../components/FooterStrip";
import { Panel, PanelHeader } from "../components/primitives";
import { Swell, Reveal } from "../components/motion";
import { browseCategory } from "../lib/api";
import { friendlyTier, AddToGarageButton } from "../components/AnswerPanel";

// eslint-disable-next-line react-refresh/only-export-components -- shared slug/label map is the Task 3 interface contract for nav reuse (Dashboard's CategoryPanel imports it); splitting it into its own file would break that contract
export const CATEGORY_LABELS = {
  overview: "Overview", engine: "Engine", "intake-exhaust": "Intake & Exhaust",
  cooling: "Cooling", suspension: "Suspension", "wheels-tires": "Wheels & Tires",
  braking: "Braking", electronics: "Electronics",
};

// eslint-disable-next-line react-refresh/only-export-components -- shared copy map, same interface-contract reasoning as CATEGORY_LABELS above
export const CATEGORY_INTROS = {
  overview:
    "Every build starts with a map. This is BoostRAG's library at a glance — every vetted source we hold on the M340i, across every system, growing with every question the community asks.",
  engine:
    "The B58 is the reason you bought the car. Tunes, turbo inlets, and the supporting mods that wake it up — with sources that separate proven power from forum folklore.",
  "intake-exhaust":
    "Airflow in, exhaust out — the first mods most builds touch and the ones with the most noise (in every sense). Catted vs. catless, intake gains, charge pipes: here's what the evidence actually says.",
  cooling:
    "Heat is the tax every tune pays. Intercoolers and heat exchangers keep the B58's power consistent on the third pull, not just the first — especially in summer traffic.",
  suspension:
    "Power is only half the build. Springs, coilovers, and the geometry that turns straight-line speed into a car that feels planted everywhere.",
  "wheels-tires":
    "Grip is the cheapest horsepower you'll ever buy. Fitment, widths, and the rubber that decides whether your build hooks or spins.",
  braking:
    "The fastest builds are the ones that can stop. Pads, rotors, and fluid that hold up after the fun starts — because fade is not a personality trait.",
  electronics:
    "The quiet layer that ties a modern build together — gauges, logging, and the data side of making a G20 do what you tell it.",
};

export default function CategoryPage() {
  const { slug } = useParams();
  // key={slug} below fully remounts CategoryPageBody on category change,
  // giving each category a clean state slate without setState-in-effect resets
  return <CategoryPageBody key={slug} slug={slug} />;
}

function CategoryPageBody({ slug }) {
  const navigate = useNavigate();
  const label = CATEGORY_LABELS[slug];
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [ask, setAsk] = useState("");

  useEffect(() => {
    if (!label) return;
    browseCategory(slug).then(setData).catch((e) => setError(e.message));
  }, [slug, label]);

  if (!label) {
    return (
      <main className="min-h-screen bg-black p-10 text-zinc-200">
        <p>Unknown category.</p><Link className="text-yellow-400" to="/">Back home</Link>
      </main>
    );
  }

  const items = data?.items ?? [];
  const scopedPlaceholder = `Ask about ${label.toLowerCase()} for the M340i...`;

  return (
    <main className="min-h-screen bg-black">
      <Header />
      <section className="mx-auto max-w-[1200px] px-5 py-10 lg:px-10">
        <h1 className="text-4xl font-black uppercase text-white">{label}</h1>

        <Reveal>
          <p className="mt-4 max-w-2xl text-zinc-400 leading-7">{CATEGORY_INTROS[slug]}</p>
        </Reveal>

        <Reveal>
          <Panel className="mt-8 p-4">
            <PanelHeader title="In the library" />
            {error && <p className="text-red-400">{error}</p>}
            {!data && !error && <p className="text-zinc-500">Loading…</p>}
            {data && items.length === 0 && (
              <p className="text-zinc-400">
                This section of the library is growing. Ask BoostRAG anything about{" "}
                {label.toLowerCase()} below — it researches the live web and the best
                sources it finds join the library automatically.
              </p>
            )}
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {items.map((item, i) => (
                <article key={i} className="border border-zinc-800 bg-zinc-950/90 p-4">
                  <h3 className="text-[15px] font-black text-white">
                    {item.product || "Unknown source"}
                    {item.trust_tier && (
                      <span
                        title={item.trust_tier}
                        className="ml-2 rounded bg-neutral-700/50 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-neutral-300"
                      >
                        {friendlyTier(item.trust_tier)}
                      </span>
                    )}
                  </h3>
                  <p className="mt-1 text-[12px] font-semibold text-zinc-500">
                    {item.brand || "—"}{item.price ? ` • ${item.price}` : ""}
                  </p>
                  {item.text_preview && (
                    <p className="mt-2 line-clamp-3 text-[12px] text-zinc-400">{item.text_preview}</p>
                  )}
                  {item.url && (
                    <a href={item.url} target="_blank" rel="noreferrer"
                       className="mt-2 inline-block text-[12px] font-black uppercase text-yellow-400">
                      View Source
                    </a>
                  )}
                  <div>
                    <AddToGarageButton category={label} name={item.product} url={item.url} />
                  </div>
                </article>
              ))}
            </div>
          </Panel>
        </Reveal>

        <Reveal>
          <form className="mt-8 flex gap-2"
                onSubmit={(e) => { e.preventDefault();
                  if (ask.trim()) navigate(`/research?q=${encodeURIComponent(ask.trim())}`); }}>
            <input value={ask} onChange={(e) => setAsk(e.target.value)}
                   placeholder={scopedPlaceholder}
                   className="flex-1 border border-zinc-700 bg-black px-4 py-3 text-zinc-100" />
            <Swell className="flex!">
              <button type="submit"
                      className="bg-yellow-400 px-6 py-3 font-black uppercase text-black">
                Ask
              </button>
            </Swell>
          </form>
        </Reveal>
      </section>
      <FooterStrip />
    </main>
  );
}
