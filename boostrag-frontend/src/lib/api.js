const API_BASE =
  import.meta.env.VITE_BOOSTRAG_API_URL || "http://127.0.0.1:8000";

export async function askBoostRAG(query, topK = 2) {
  const response = await fetch(`${API_BASE}/ask`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      query,
      top_k: topK,
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
