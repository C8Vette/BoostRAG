import { createContext, useContext, useEffect, useState } from "react";
import { supabase } from "./supabase";

const AuthContext = createContext(null);

const DISABLED = {
  error: {
    message:
      "Sign-in isn't configured in this environment. You can still research anonymously.",
  },
};

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(Boolean(supabase));

  useEffect(() => {
    if (!supabase) return; // auth disabled → stay logged-out, no listener
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session ?? null);
      setLoading(false);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next ?? null);
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  const value = {
    user: session?.user ?? null,
    session,
    loading,
    async signInWithPassword(email, password) {
      if (!supabase) return DISABLED;
      return supabase.auth.signInWithPassword({ email, password });
    },
    async signUp(email, password) {
      if (!supabase) return DISABLED;
      return supabase.auth.signUp({ email, password });
    },
    async signInWithGoogle() {
      if (!supabase) return DISABLED;
      return supabase.auth.signInWithOAuth({
        provider: "google",
        options: { redirectTo: `${window.location.origin}/garage` },
      });
    },
    async signOut() {
      if (!supabase) return DISABLED;
      return supabase.auth.signOut();
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components -- context hook colocated with its provider (standard pattern)
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
