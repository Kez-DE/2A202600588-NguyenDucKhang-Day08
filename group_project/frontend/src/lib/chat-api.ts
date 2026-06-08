export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface SourceItem {
  content: string;
  score: number;
  metadata: Record<string, unknown> & {
    source?: string;
    source_path?: string;
    doc_type?: string;
    title?: string;
  };
  source: string;
}

export interface ChatResponse {
  answer: string;
  retrieval_source: string;
  sources: SourceItem[];
}

export interface ChatRequest {
  question: string;
  top_k: number;
  history: ChatMessage[];
}

const DEFAULT_BASE = "http://localhost:8000";

export function resolveBaseUrl(userConfigured?: string | null): string {
  const env = (import.meta.env.VITE_API_BASE_URL as string | undefined) || "";
  const chosen = (userConfigured && userConfigured.trim()) || env || DEFAULT_BASE;
  return chosen.replace(/\/+$/, "");
}

export async function checkHealth(baseUrl: string, signal?: AbortSignal): Promise<boolean> {
  try {
    const res = await fetch(`${baseUrl}/health`, { signal });
    if (!res.ok) return false;
    const data = (await res.json()) as { status?: string };
    return data.status === "ok";
  } catch {
    return false;
  }
}

export async function sendChat(
  baseUrl: string,
  body: ChatRequest,
  signal?: AbortSignal,
): Promise<ChatResponse> {
  const res = await fetch(`${baseUrl}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`);
  }
  return (await res.json()) as ChatResponse;
}
