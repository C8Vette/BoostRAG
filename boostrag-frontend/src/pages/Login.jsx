import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { supabase } from "../lib/supabase";
import { Swell } from "../components/motion";
// Reusing the in-repo studio hero (already licensed & shipping). A licensed
// aggressive M-car front-end can drop in later by swapping this one import.
import heroImg from "../assets/hero-studio.jpg";

// Turn raw Supabase/network errors into on-brand, human copy.
function friendlyAuthError(err) {
  const raw = (err?.message || "").toLowerCase();
  if (
    err?.name === "AuthRetryableFetchError" ||
    raw.includes("fetch") ||
    raw.includes("network") ||
    raw.includes("load failed")
  ) {
    return "Can't reach the garage right now — check your connection and try again in a moment.";
  }
  if (raw.includes("invalid login") || raw.includes("invalid credentials")) {
    return "That email and password don't match. Give it another shot.";
  }
  if (raw.includes("already registered") || raw.includes("already been registered")) {
    return "There's already an account with this email — try signing in instead.";
  }
  if (raw.includes("email not confirmed")) {
    return "Confirm your email first, then sign in.";
  }
  if (raw.includes("password") && (raw.includes("6") || raw.includes("short") || raw.includes("least"))) {
    return "Password needs to be at least 6 characters.";
  }
  return err?.message || "Something went wrong. Please try again.";
}

export default function Login() {
  const { signInWithPassword, signUp, signInWithGoogle } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState("signin"); // "signin" | "signup"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const configured = Boolean(supabase);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setNotice("");
    setBusy(true);
    const fn = mode === "signup" ? signUp : signInWithPassword;
    const { data, error: err } = await fn(email.trim(), password);
    setBusy(false);
    if (err) {
      setError(friendlyAuthError(err));
      return;
    }
    if (mode === "signup" && !data?.session) {
      // Email confirmation is on — no session yet.
      setNotice("Check your email to confirm your account, then sign in.");
      setMode("signin");
      return;
    }
    navigate("/garage");
  }

  async function handleGoogle() {
    setError("");
    const { error: err } = await signInWithGoogle();
    if (err) setError(friendlyAuthError(err));
    // On success the browser redirects to Google, then back to /garage.
  }

  return (
    <main className="grid min-h-screen grid-cols-1 bg-[#F6F6F4] text-zinc-900 lg:grid-cols-[1.1fr_1fr]">
      {/* Aggressive hero panel — the "garage downstairs" mood */}
      <section className="relative hidden overflow-hidden bg-black lg:block">
        <img
          src={heroImg}
          alt=""
          aria-hidden="true"
          className="h-full w-full object-cover opacity-70 [filter:contrast(1.1)_saturate(0.9)]"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black via-black/55 to-black/20" />
        <div className="absolute inset-0 bg-gradient-to-r from-transparent to-black/70" />
        <div className="absolute inset-x-0 bottom-0 p-12">
          <p className="text-xs font-bold uppercase tracking-[0.35em] text-yellow-400">
            Your build. Remembered.
          </p>
          <h2 className="mt-4 max-w-xl text-5xl font-black uppercase leading-[0.95] text-white">
            Sign in to your garage
          </h2>
          <p className="mt-4 max-w-md text-sm leading-6 text-zinc-300">
            Save your M340i, log every mod, and get research answers tuned to the
            exact car in your driveway.
          </p>
          <span className="mt-6 inline-flex gap-1">
            <span className="h-1.5 w-8 bg-[#0066B1]" />
            <span className="h-1.5 w-8 bg-[#E7222E]" />
          </span>
        </div>
      </section>

      {/* Sign-in card — the "showroom" clarity */}
      <section className="flex flex-col justify-center px-6 py-14 sm:px-12 lg:px-16">
        <div className="mx-auto w-full max-w-sm">
          <Link
            to="/"
            className="text-[28px] font-black italic leading-none tracking-[-0.06em]"
          >
            <span className="text-zinc-900">Boost</span>
            <span className="text-red-600">RAG</span>
          </Link>

          <h1 className="mt-10 text-3xl font-black uppercase">
            {mode === "signup" ? "Create account" : "Welcome back"}
          </h1>
          <p className="mt-2 text-sm text-zinc-500">
            {mode === "signup"
              ? "Start your garage in seconds."
              : "Sign in to reach your garage."}
          </p>

          {!configured && (
            <div className="mt-6 border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800">
              Sign-in isn&apos;t configured in this environment. You can still{" "}
              <Link to="/research" className="font-bold underline">
                research anonymously
              </Link>
              .
            </div>
          )}

          <form onSubmit={handleSubmit} className="mt-8 space-y-4">
            <label className="block">
              <span className="text-xs font-bold uppercase tracking-wide text-zinc-500">
                Email
              </span>
              <input
                type="email"
                required
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={!configured || busy}
                className="mt-1 w-full border border-zinc-300 bg-white px-3 py-2.5 text-[15px] outline-none focus:border-zinc-900 disabled:opacity-50"
              />
            </label>

            <label className="block">
              <span className="text-xs font-bold uppercase tracking-wide text-zinc-500">
                Password
              </span>
              <input
                type="password"
                required
                minLength={6}
                autoComplete={
                  mode === "signup" ? "new-password" : "current-password"
                }
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={!configured || busy}
                className="mt-1 w-full border border-zinc-300 bg-white px-3 py-2.5 text-[15px] outline-none focus:border-zinc-900 disabled:opacity-50"
              />
            </label>

            {error && (
              <p className="text-sm font-semibold text-red-600" role="alert">
                {error}
              </p>
            )}
            {notice && (
              <p className="text-sm font-semibold text-green-700" role="status">
                {notice}
              </p>
            )}

            <Swell className="block!">
              <button
                type="submit"
                disabled={!configured || busy}
                className="w-full bg-zinc-900 px-6 py-3 font-black uppercase tracking-wide text-white transition hover:bg-black disabled:opacity-50"
              >
                {busy
                  ? "Working…"
                  : mode === "signup"
                  ? "Create account"
                  : "Sign in"}
              </button>
            </Swell>
          </form>

          <div className="my-6 flex items-center gap-3 text-xs uppercase text-zinc-400">
            <span className="h-px flex-1 bg-zinc-300" />
            or
            <span className="h-px flex-1 bg-zinc-300" />
          </div>

          <button
            type="button"
            onClick={handleGoogle}
            disabled={!configured || busy}
            className="w-full border border-zinc-300 bg-white px-6 py-3 font-bold uppercase tracking-wide text-zinc-700 transition hover:border-zinc-900 disabled:opacity-50"
          >
            Continue with Google
          </button>

          <p className="mt-8 text-center text-sm text-zinc-500">
            {mode === "signup" ? "Already have an account?" : "New here?"}{" "}
            <button
              type="button"
              onClick={() => {
                setMode(mode === "signup" ? "signin" : "signup");
                setError("");
                setNotice("");
              }}
              className="font-bold text-zinc-900 underline"
            >
              {mode === "signup" ? "Sign in" : "Create one"}
            </button>
          </p>
        </div>
      </section>
    </main>
  );
}
