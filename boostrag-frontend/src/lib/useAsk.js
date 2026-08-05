import { useState } from "react";
import { askBoostRAG } from "./api";

export function useAsk(initialQuery = "") {
  const [query, setQuery] = useState(initialQuery);
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [origin, setOrigin] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  // Per-request personalization toggle (does not mutate the stored garage setting).
  const [useContext, setUseContext] = useState(true);

  async function submit(question = query) {
    const cleanedQuery = (question || "").trim();

    if (!cleanedQuery) {
      setError("Please enter a question first.");
      return;
    }

    setIsLoading(true);
    setError("");
    setAnswer("");
    setSources([]);
    setOrigin("");

    try {
      const data = await askBoostRAG(cleanedQuery, 2, useContext);

      setAnswer(data.answer);
      setSources(data.sources || []);
      setOrigin(data.origin || "");
      setQuery(cleanedQuery);
    } catch {
      setError(
        "Something went wrong while asking BoostRAG. Make sure the FastAPI backend is running."
      );
    } finally {
      setIsLoading(false);
    }
  }

  return {
    query, setQuery, answer, sources, origin, error, isLoading, submit,
    useContext, setUseContext,
  };
}
