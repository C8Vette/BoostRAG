import { Search } from "lucide-react";
import { CornerMarks } from "./primitives";
import { Swell } from "./motion";

const examples = [
  "Best intake for B58 reliability?",
  "Catted vs catless downpipe gains?",
  'Will 19" wheels affect ride quality?',
  "Best cooling upgrades for Stage 2?",
];

export function SearchBand({ query, setQuery, askBoostRAG, isLoading, onChipSelect }) {
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

          <Swell className="flex! h-full">
            <button
              type="submit"
              disabled={isLoading}
              className="relative w-[130px] bg-yellow-400 text-[13px] font-black uppercase text-black transition hover:bg-yellow-300 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isLoading ? "Thinking..." : "Search"}
            </button>
          </Swell>
        </form>

        <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
          <span className="mr-2 text-[13px] font-semibold text-zinc-500">
            Try an example:
          </span>

          {examples.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => (onChipSelect ? onChipSelect(item) : askBoostRAG(item))}
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
