import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Header } from "../components/Header";
import { FooterStrip } from "../components/FooterStrip";
import { Panel } from "../components/primitives";
import { Swell, Reveal } from "../components/motion";
import { useAuth } from "../lib/auth";
import { getGarage, putGarage, addMod, deleteMod, browseCategory } from "../lib/api";
import { CATEGORY_LABELS } from "./CategoryPage";

const YEARS = [2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019];
// Mod categories = the part systems (drop the "overview" pseudo-category).
const MOD_CATEGORIES = Object.entries(CATEGORY_LABELS).filter(
  ([slug]) => slug !== "overview"
);

export default function Garage() {
  const { user, loading: authLoading } = useAuth();
  const navigate = useNavigate();

  const [state, setState] = useState("loading"); // loading | ready | unavailable | error
  const [garage, setGarage] = useState(null);
  const [mods, setMods] = useState([]);

  // Car form
  const [year, setYear] = useState(2021);
  const [model, setModel] = useState("M340i");
  const [trim, setTrim] = useState("");
  const [savingCar, setSavingCar] = useState(false);

  // Add-mod form + autocomplete cache
  const [modCat, setModCat] = useState("engine");
  const [modName, setModName] = useState("");
  const [suggestions, setSuggestions] = useState({}); // slug -> [names]
  const [addingMod, setAddingMod] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await getGarage();
      const g = data?.garage ?? null;
      setGarage(g);
      setMods(data?.mods ?? []);
      if (g) {
        setYear(g.year ?? 2021);
        setModel(g.model ?? "M340i");
        setTrim(g.trim ?? "");
      }
      setState("ready");
    } catch (err) {
      setState(err.status === 503 ? "unavailable" : "error");
    }
  }, []);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      navigate("/login");
      return;
    }
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load() awaits before any setState; canonical load-on-mount, no synchronous cascade
    load();
  }, [authLoading, user, navigate, load]);

  // Fetch product-name suggestions for a mod category (cached per slug).
  const loadSuggestions = useCallback(async (slug) => {
    try {
      const data = await browseCategory(slug);
      const names = (data?.items ?? []).map((it) => it.product).filter(Boolean);
      setSuggestions((s) => (s[slug] ? s : { ...s, [slug]: [...new Set(names)] }));
    } catch {
      setSuggestions((s) => (s[slug] ? s : { ...s, [slug]: [] }));
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- awaits browseCategory before setState; no synchronous cascade
    loadSuggestions(modCat);
  }, [modCat, loadSuggestions]);

  async function saveCar(e) {
    e.preventDefault();
    setSavingCar(true);
    try {
      await putGarage({
        year: Number(year),
        model: model.trim() || "M340i",
        trim: trim.trim() || null,
        context_on: garage?.context_on ?? true,
      });
      await load();
    } catch (err) {
      setState(err.status === 503 ? "unavailable" : "error");
    } finally {
      setSavingCar(false);
    }
  }

  async function toggleContext() {
    if (!garage) return;
    const next = !garage.context_on;
    setGarage({ ...garage, context_on: next }); // optimistic
    try {
      await putGarage({
        year: garage.year,
        model: garage.model,
        trim: garage.trim,
        context_on: next,
      });
    } catch {
      setGarage({ ...garage, context_on: !next }); // revert
    }
  }

  async function submitMod(e) {
    e.preventDefault();
    if (!modName.trim()) return;
    setAddingMod(true);
    try {
      await addMod({
        category: CATEGORY_LABELS[modCat],
        name: modName.trim(),
        source_url: null,
      });
      setModName("");
      await load();
    } catch (err) {
      setState(err.status === 503 ? "unavailable" : "error");
    } finally {
      setAddingMod(false);
    }
  }

  async function removeMod(id) {
    const prev = mods;
    setMods(mods.filter((m) => m.id !== id)); // optimistic
    try {
      await deleteMod(id);
    } catch {
      setMods(prev); // revert
    }
  }

  return (
    <main className="min-h-screen bg-black text-zinc-100">
      <Header />
      <section className="mx-auto max-w-[1100px] px-5 py-10 lg:px-10">
        <h1 className="text-4xl font-black uppercase text-white">My Garage</h1>
        <p className="mt-3 max-w-2xl text-zinc-400">
          The car in your driveway — and every part on it. Turn it on and
          BoostRAG tailors research answers to your exact build.
        </p>

        {state === "loading" && (
          <p className="mt-10 text-zinc-500">Opening the garage…</p>
        )}

        {state === "unavailable" && (
          <Panel className="mt-10 p-6">
            <p className="text-lg font-black uppercase text-yellow-400">
              Garage is taking a break
            </p>
            <p className="mt-2 text-zinc-400">
              Your account service is momentarily unavailable — but research
              still works. Try again in a minute.
            </p>
          </Panel>
        )}

        {state === "error" && (
          <Panel className="mt-10 p-6">
            <p className="text-red-400">
              Something went wrong loading your garage.{" "}
              <button
                onClick={() => {
                  setState("loading");
                  load();
                }}
                className="font-black underline"
              >
                Retry
              </button>
            </p>
          </Panel>
        )}

        {state === "ready" && (
          <div className="mt-10 grid gap-6 lg:grid-cols-[1fr_1.1fr]">
            {/* Car panel */}
            <Reveal>
              <Panel className="p-6">
                <div className="mb-4 flex items-center justify-between border-b border-zinc-800 pb-3">
                  <h2 className="text-[18px] font-black italic uppercase tracking-wide text-yellow-400">
                    {garage ? "Your car" : "Add your car"}
                  </h2>
                  {garage && (
                    <button
                      type="button"
                      onClick={toggleContext}
                      role="switch"
                      aria-checked={garage.context_on}
                      className={`flex items-center gap-2 text-[11px] font-black uppercase tracking-wide ${
                        garage.context_on ? "text-green-400" : "text-zinc-500"
                      }`}
                    >
                      <span
                        className={`relative h-5 w-9 rounded-full transition ${
                          garage.context_on ? "bg-green-500/80" : "bg-zinc-700"
                        }`}
                      >
                        <span
                          className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all ${
                            garage.context_on ? "left-4" : "left-0.5"
                          }`}
                        />
                      </span>
                      Use in answers
                    </button>
                  )}
                </div>

                <form onSubmit={saveCar} className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <label className="block">
                      <span className="text-xs font-bold uppercase text-zinc-500">
                        Year
                      </span>
                      <select
                        value={year}
                        onChange={(e) => setYear(e.target.value)}
                        className="mt-1 w-full border border-zinc-700 bg-black px-3 py-2.5 text-zinc-100"
                      >
                        {YEARS.map((y) => (
                          <option key={y} value={y}>
                            {y}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label className="block">
                      <span className="text-xs font-bold uppercase text-zinc-500">
                        Model
                      </span>
                      <input
                        value={model}
                        onChange={(e) => setModel(e.target.value)}
                        className="mt-1 w-full border border-zinc-700 bg-black px-3 py-2.5 text-zinc-100"
                      />
                    </label>
                  </div>
                  <label className="block">
                    <span className="text-xs font-bold uppercase text-zinc-500">
                      Trim <span className="normal-case text-zinc-600">(optional)</span>
                    </span>
                    <input
                      value={trim}
                      onChange={(e) => setTrim(e.target.value)}
                      placeholder="xDrive, Competition…"
                      className="mt-1 w-full border border-zinc-700 bg-black px-3 py-2.5 text-zinc-100 placeholder:text-zinc-600"
                    />
                  </label>
                  <Swell className="block!">
                    <button
                      type="submit"
                      disabled={savingCar}
                      className="bg-yellow-400 px-6 py-3 font-black uppercase text-black disabled:opacity-50"
                    >
                      {savingCar ? "Saving…" : garage ? "Update car" : "Save car"}
                    </button>
                  </Swell>
                </form>
              </Panel>
            </Reveal>

            {/* Mods panel */}
            <Reveal>
              <Panel className="p-6">
                <h2 className="mb-4 border-b border-zinc-800 pb-3 text-[18px] font-black italic uppercase tracking-wide text-yellow-400">
                  Installed mods
                </h2>

                {!garage ? (
                  <p className="text-zinc-500">
                    Save your car first, then start logging the parts on it.
                  </p>
                ) : (
                  <>
                    {mods.length === 0 && (
                      <p className="text-zinc-500">
                        No mods yet. Add the first part below — or tag parts
                        straight from research and category pages.
                      </p>
                    )}
                    <ul className="space-y-2">
                      {mods.map((m) => (
                        <li
                          key={m.id}
                          className="flex items-center justify-between border border-zinc-800 bg-zinc-950/70 px-3 py-2.5"
                        >
                          <span>
                            <span className="font-bold text-zinc-100">
                              {m.name}
                            </span>
                            <span className="ml-2 text-[11px] font-semibold uppercase text-zinc-500">
                              {m.category}
                            </span>
                          </span>
                          <button
                            type="button"
                            onClick={() => removeMod(m.id)}
                            aria-label={`Remove ${m.name}`}
                            className="text-[11px] font-black uppercase text-zinc-500 transition hover:text-red-500"
                          >
                            Remove
                          </button>
                        </li>
                      ))}
                    </ul>

                    <form onSubmit={submitMod} className="mt-4 space-y-3">
                      <div className="grid grid-cols-[minmax(0,140px)_1fr] gap-2">
                        <select
                          value={modCat}
                          onChange={(e) => setModCat(e.target.value)}
                          className="border border-zinc-700 bg-black px-2 py-2.5 text-zinc-100"
                        >
                          {MOD_CATEGORIES.map(([slug, label]) => (
                            <option key={slug} value={slug}>
                              {label}
                            </option>
                          ))}
                        </select>
                        <input
                          value={modName}
                          onChange={(e) => setModName(e.target.value)}
                          list="mod-suggestions"
                          placeholder="Part name (e.g. VRSF Downpipe)"
                          className="border border-zinc-700 bg-black px-3 py-2.5 text-zinc-100 placeholder:text-zinc-600"
                        />
                        <datalist id="mod-suggestions">
                          {(suggestions[modCat] ?? []).map((n) => (
                            <option key={n} value={n} />
                          ))}
                        </datalist>
                      </div>
                      <button
                        type="submit"
                        disabled={addingMod || !modName.trim()}
                        className="border border-zinc-600 px-5 py-2.5 font-black uppercase text-zinc-100 transition hover:border-yellow-400 disabled:opacity-40"
                      >
                        {addingMod ? "Adding…" : "Add mod"}
                      </button>
                    </form>
                  </>
                )}
              </Panel>
            </Reveal>
          </div>
        )}
      </section>
      <FooterStrip />
    </main>
  );
}
