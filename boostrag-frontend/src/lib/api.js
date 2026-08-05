import { supabase } from "./supabase";

const API_BASE =
  import.meta.env.VITE_BOOSTRAG_API_URL || "http://127.0.0.1:8000";

// Attach the current Supabase JWT when signed in; otherwise send nothing
// (backend treats the request as anonymous).
async function authHeaders() {
  if (!supabase) return {};
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function askBoostRAG(query, topK = 2, useContext = true) {
  const response = await fetch(`${API_BASE}/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(await authHeaders()),
    },
    body: JSON.stringify({
      query,
      top_k: topK,
      use_context: useContext,
    }),
  });

  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }

  return response.json();
}

export async function browseCategory(slug) {
  const response = await fetch(
    `${API_BASE}/browse?category=${encodeURIComponent(slug)}`
  );

  if (!response.ok) {
    throw new Error(`Browse failed (${response.status})`);
  }

  return response.json();
}

// --- Garage (all require a signed-in session; 401 if not) ---

async function garageFetch(path, { method = "GET", body } = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(await authHeaders()),
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const err = new Error(`Garage request failed (${response.status})`);
    err.status = response.status;
    throw err;
  }

  return response.status === 204 ? null : response.json();
}

export function getGarage() {
  return garageFetch("/garage");
}

export function putGarage(body) {
  return garageFetch("/garage", { method: "PUT", body });
}

export function addMod(body) {
  return garageFetch("/garage/mods", { method: "POST", body });
}

export function deleteMod(id) {
  return garageFetch(`/garage/mods/${id}`, { method: "DELETE" });
}
