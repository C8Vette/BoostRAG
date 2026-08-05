import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Settings, Zap, ChevronDown } from "lucide-react";
import { Swell } from "./motion";
import { useAuth } from "../lib/auth";

const navItems = ["Home", "Performance Areas", "Parts Library", "Guides", "About"];

function AuthControl({ light }) {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  if (!user) {
    return (
      <Link
        to="/login"
        className={`hidden h-11 items-center whitespace-nowrap border px-4 text-[13px] font-black uppercase tracking-wide transition lg:inline-flex ${
          light
            ? "border-zinc-300 bg-white text-zinc-700 hover:border-red-600 hover:text-red-500"
            : "border-zinc-700 bg-zinc-950 text-zinc-200 hover:border-red-600 hover:text-red-500"
        }`}
      >
        Sign in
      </Link>
    );
  }

  const label = user.email || "Account";

  return (
    <div className="relative hidden lg:block">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`flex h-11 max-w-[220px] items-center gap-2 border px-3 text-[13px] font-bold transition ${
          light
            ? "border-zinc-300 bg-white text-zinc-700 hover:border-zinc-900"
            : "border-zinc-700 bg-zinc-950 text-zinc-200 hover:border-zinc-400"
        }`}
      >
        <span className="grid h-6 w-6 place-items-center bg-red-600 text-[11px] font-black uppercase text-white">
          {label[0]?.toUpperCase() || "U"}
        </span>
        <span className="truncate">{label}</span>
        <ChevronDown size={15} className="shrink-0" />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
          <div
            className={`absolute right-0 z-50 mt-1 w-48 border shadow-lg ${
              light ? "border-zinc-300 bg-white" : "border-zinc-700 bg-zinc-950"
            }`}
          >
            <Link
              to="/garage"
              onClick={() => setOpen(false)}
              className={`block px-4 py-3 text-[13px] font-bold uppercase tracking-wide transition ${
                light
                  ? "text-zinc-700 hover:bg-zinc-100"
                  : "text-zinc-200 hover:bg-zinc-900"
              }`}
            >
              My Garage
            </Link>
            <button
              type="button"
              onClick={async () => {
                setOpen(false);
                await signOut();
                navigate("/");
              }}
              className={`block w-full px-4 py-3 text-left text-[13px] font-bold uppercase tracking-wide transition ${
                light
                  ? "text-red-600 hover:bg-zinc-100"
                  : "text-red-500 hover:bg-zinc-900"
              }`}
            >
              Sign out
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export function Header({ light = false }) {
  return (
    <header
      className={`relative z-30 h-[72px] border-b backdrop-blur ${
        light ? "border-zinc-300 bg-[#F6F6F4]/90" : "border-zinc-800/80 bg-black/90"
      }`}
    >
      <div className="mx-auto flex h-full max-w-[1780px] items-center justify-between gap-4 px-5 lg:px-8">
        <div className="flex items-center gap-4 lg:gap-6">
          <div
            className={`hidden h-10 w-10 place-items-center border lg:grid ${
              light
                ? "border-red-700/40 bg-white text-red-700"
                : "border-red-950/80 bg-zinc-950/70 text-red-700"
            }`}
          >
            <Zap size={17} />
          </div>

          <div className="flex items-center gap-5">
            <div className="text-[34px] font-black italic leading-none tracking-[-0.06em]">
              <span
                className={
                  light
                    ? "text-zinc-900"
                    : "text-white drop-shadow-[0_0_6px_rgba(255,255,255,.5)]"
                }
              >
                Boost
              </span>
              <span className="text-red-600 drop-shadow-[0_0_10px_rgba(220,38,38,.8)]">
                RAG
              </span>
            </div>

            <div className={`hidden h-8 w-px 2xl:block ${light ? "bg-zinc-300" : "bg-zinc-700"}`} />

            <p
              className={`hidden whitespace-nowrap text-[14px] font-semibold 2xl:block ${
                light ? "text-zinc-500" : "text-zinc-400"
              }`}
            >
              AI-Powered Research for M340i Enthusiasts
            </p>
          </div>
        </div>

        <nav className="hidden h-full items-center gap-5 xl:flex xl:gap-7">
          {navItems.map((item) => (
            <a
              key={item}
              href="#"
              className={`relative flex h-full items-center whitespace-nowrap text-[13px] font-black uppercase tracking-wide transition hover:text-red-500 ${
                item === "Home"
                  ? "text-red-500"
                  : light
                  ? "text-zinc-700"
                  : "text-zinc-200"
              }`}
            >
              {item}

              {item === "Home" && (
                <>
                  <span className="absolute bottom-0 left-0 h-[3px] w-full bg-red-600 shadow-[0_0_18px_rgba(220,38,38,.9)]" />
                  <span
                    className={`absolute bottom-0 left-1/2 h-2 w-9 -translate-x-1/2 skew-x-[-35deg] border-x border-t border-red-600 ${
                      light ? "bg-[#F6F6F4]" : "bg-black"
                    }`}
                  />
                </>
              )}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <button
            className={`hidden h-11 w-11 place-items-center border transition xl:grid ${
              light
                ? "border-zinc-300 bg-white text-zinc-500 shadow-[inset_0_0_14px_rgba(0,0,0,.03)] hover:border-red-600 hover:text-red-500"
                : "border-zinc-700 bg-zinc-950 text-zinc-300 shadow-[inset_0_0_14px_rgba(255,255,255,.05)] hover:border-red-600 hover:text-red-500"
            }`}
          >
            <Settings size={19} />
          </button>

          <AuthControl light={light} />

          <Swell className="inline-flex! h-full">
            <Link
              to="/research"
              className="relative flex h-full items-center overflow-hidden whitespace-nowrap bg-yellow-400 px-5 py-3 text-[13px] font-black uppercase tracking-wide text-black shadow-[0_0_24px_rgba(250,204,21,.24)] transition hover:bg-yellow-300 lg:px-7"
            >
              <span className="relative z-10">Start Research</span>
              <span className="absolute inset-y-0 right-0 w-6 skew-x-[-22deg] bg-yellow-200/60" />
            </Link>
          </Swell>
        </div>
      </div>
    </header>
  );
}
