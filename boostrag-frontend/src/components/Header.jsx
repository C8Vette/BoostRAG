import { Link } from "react-router-dom";
import { Settings, Zap } from "lucide-react";

const navItems = ["Home", "Performance Areas", "Parts Library", "Guides", "About"];

export function Header() {
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

          <Link
            to="/research"
            className="relative overflow-hidden bg-yellow-400 px-7 py-3 text-[13px] font-black uppercase tracking-wide text-black shadow-[0_0_24px_rgba(250,204,21,.24)] transition hover:bg-yellow-300"
          >
            <span className="relative z-10">Start Research</span>
            <span className="absolute inset-y-0 right-0 w-6 skew-x-[-22deg] bg-yellow-200/60" />
          </Link>
        </div>
      </div>
    </header>
  );
}
