"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { AuthGuard } from "@/lib/auth-guard";

interface Citation {
  chunk_id: string;
  document_version_id: string;
  quote: string;
  score: number;
}

interface SearchResult {
  document_id: string;
  version_id: string;
  chunk_id: string;
  score: number;
  snippet: string;
  citation: { document_title?: string; source?: string };
}

interface AnswerResponse {
  answer: string | null;
  citations?: Citation[];
  confidence: number;
  dont_know?: boolean;
  suggested_owner?: { space_name: string };
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [answer, setAnswer] = useState<AnswerResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<"search" | "ask">("search");

  const handleSearch = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      if (mode === "search") {
        const data = await api.post<{ results: SearchResult[] }>("/v1/search", { query });
        setResults(data.results);
        setAnswer(null);
      } else {
        const data = await api.post<AnswerResponse>("/v1/assistant/answer", { query });
        setAnswer(data);
        setResults([]);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthGuard>
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setMode("search")}
          className={`px-4 py-2 rounded text-sm font-medium ${mode === "search" ? "bg-blue-600 text-white" : "bg-white border"}`}
        >
          Search
        </button>
        <button
          onClick={() => setMode("ask")}
          className={`px-4 py-2 rounded text-sm font-medium ${mode === "ask" ? "bg-blue-600 text-white" : "bg-white border"}`}
        >
          Ask Assistant
        </button>
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder={mode === "search" ? "Search documentation..." : "Ask a question..."}
          className="flex-1 border rounded px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleSearch}
          disabled={loading}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium disabled:opacity-50"
        >
          {loading ? "..." : mode === "search" ? "Search" : "Ask"}
        </button>
      </div>

      {answer && (
        <div className="bg-white rounded border p-4 space-y-3">
          {answer.dont_know ? (
            <div className="text-gray-500 italic">
              <p>I don&apos;t have enough information to answer this question.</p>
              {answer.suggested_owner && (
                <p className="mt-1 text-sm">
                  Try asking the owner of{" "}
                  <strong>{answer.suggested_owner.space_name}</strong>
                </p>
              )}
            </div>
          ) : (
            <>
              <div className="prose prose-sm max-w-none">{answer.answer}</div>
              {answer.citations && answer.citations.length > 0 && (
                <div className="border-t pt-3 space-y-2">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Sources
                  </p>
                  {answer.citations.map((c, i) => (
                    <button
                      key={c.chunk_id}
                      className="block w-full text-left text-xs bg-gray-50 rounded p-2 hover:bg-gray-100"
                      title={`Score: ${c.score.toFixed(2)}`}
                    >
                      [{i + 1}] {c.quote}
                    </button>
                  ))}
                </div>
              )}
            </>
          )}
          <p className="text-xs text-gray-400">Confidence: {(answer.confidence * 100).toFixed(0)}%</p>
        </div>
      )}

      {results.length > 0 && (
        <div className="space-y-3">
          {results.map((r) => (
            <div key={r.chunk_id} className="bg-white rounded border p-4">
              <div className="flex justify-between items-start mb-2">
                <span className="text-xs text-gray-400">
                  Score: {(r.score * 100).toFixed(0)}%
                </span>
              </div>
              <p className="text-sm text-gray-700">{r.snippet}</p>
              {r.citation.document_title && (
                <p className="text-xs text-blue-600 mt-2">{r.citation.document_title}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
    </AuthGuard>
  );
}
