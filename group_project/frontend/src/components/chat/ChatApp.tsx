import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { AlertCircle, BookOpen } from "lucide-react";
import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import { Message, MessageContent } from "@/components/ai-elements/message";
import {
  PromptInput,
  PromptInputTextarea,
  PromptInputFooter,
  PromptInputSubmit,
  type PromptInputMessage,
} from "@/components/ai-elements/prompt-input";
import { Sidebar, type HealthStatus } from "./Sidebar";
import { SourcePanel } from "./SourcePanel";
import {
  checkHealth,
  resolveBaseUrl,
  sendChat,
  type ChatMessage,
  type SourceItem,
} from "@/lib/chat-api";

interface UiMessage extends ChatMessage {
  id: string;
  sources?: SourceItem[];
  retrieval_source?: string;
}

const HISTORY_LIMIT = 8;
const STORAGE_KEY = "rag-chat:base-url";

export function ChatApp() {
  const [baseUrl, setBaseUrl] = useState<string>(() => {
    if (typeof window === "undefined") return resolveBaseUrl();
    return resolveBaseUrl(window.localStorage.getItem(STORAGE_KEY));
  });
  const [topK, setTopK] = useState(5);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [status, setStatus] = useState<"submitted" | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthStatus>("unknown");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, baseUrl);
    }
  }, [baseUrl]);

  const runHealth = useCallback(async () => {
    setHealth("checking");
    const ok = await checkHealth(baseUrl);
    setHealth(ok ? "ok" : "down");
  }, [baseUrl]);

  useEffect(() => {
    runHealth();
  }, [runHealth]);

  useEffect(() => {
    textareaRef.current?.focus();
  }, [status]);

  const ask = useCallback(
    async (question: string) => {
      const q = question.trim();
      if (!q || status === "submitted") return;
      setError(null);
      const userMsg: UiMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: q,
      };
      const nextMessages = [...messages, userMsg];
      setMessages(nextMessages);
      setStatus("submitted");

      const history = nextMessages
        .slice(-HISTORY_LIMIT)
        .map(({ role, content }) => ({ role, content }));

      try {
        const res = await sendChat(baseUrl, { question: q, top_k: topK, history });
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            content: res.answer,
            sources: res.sources,
            retrieval_source: res.retrieval_source,
          },
        ]);
        setHealth("ok");
      } catch (e) {
        console.error(e);
        setError(
          "Không kết nối được FastAPI backend. Hãy kiểm tra API URL và đảm bảo server đang chạy.",
        );
        setHealth("down");
      } finally {
        setStatus(undefined);
        requestAnimationFrame(() => textareaRef.current?.focus());
      }
    },
    [baseUrl, messages, status, topK],
  );

  const handleSubmit = (message: PromptInputMessage) => {
    if (message.text) void ask(message.text);
  };

  const today = new Date().toLocaleDateString("vi-VN", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });

  return (
    <div className="flex h-screen w-full bg-background text-foreground">
      <Sidebar
        baseUrl={baseUrl}
        onBaseUrlChange={setBaseUrl}
        topK={topK}
        onTopKChange={setTopK}
        onClear={() => {
          setMessages([]);
          setError(null);
        }}
        onExample={(q) => void ask(q)}
        health={health}
        onRecheck={runHealth}
      />

      <main className="relative flex flex-1 flex-col overflow-hidden">
        {/* Document masthead */}
        <header className="relative z-10 border-b border-border bg-card">
          <div className="mx-auto flex w-full max-w-3xl items-end justify-between gap-4 px-6 pt-5 pb-3">
            <div>
              <div className="eyebrow">Cộng hoà Xã hội Chủ nghĩa Việt Nam</div>
              <h1 className="font-serif text-[22px] leading-tight font-bold tracking-tight text-foreground">
                Trợ lý Nghiên cứu Pháp lý
              </h1>
              <p className="mt-0.5 text-[12px] text-muted-foreground">
                Luật Phòng, chống ma túy &amp; tài liệu liên quan
              </p>
            </div>
            <div className="text-right text-[11px] text-muted-foreground">
              <div className="eyebrow">Phiên làm việc</div>
              <div className="mt-0.5 font-mono">{today}</div>
            </div>
          </div>
          <div className="h-px w-full bg-border" />
          <div className="h-[3px] w-full bg-foreground/85" />
        </header>

        <Conversation className="relative z-10 flex-1 paper-grain">
          <ConversationContent className="mx-auto w-full max-w-3xl px-6 py-8">
            {messages.length === 0 && (
              <div className="animate-slide-up-fade rounded-sm border border-border bg-card p-7 shadow-[0_1px_0_oklch(0.18_0.03_264/0.04)]">
                <div className="mb-3 flex items-center gap-2 eyebrow">
                  <BookOpen className="h-3.5 w-3.5" />
                  Hướng dẫn truy vấn
                </div>
                <h2 className="font-serif text-lg font-bold text-foreground">
                  Bắt đầu phiên nghiên cứu
                </h2>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  Đặt câu hỏi pháp lý bằng tiếng Việt. Hệ thống truy hồi điều khoản, văn bản và tin
                  tức liên quan, sau đó tổng hợp câu trả lời có{" "}
                  <span className="font-semibold text-foreground">trích dẫn nguồn</span> đánh số
                  theo phong cách pháp lý.
                </p>
                <p className="mt-3 text-[12px] text-muted-foreground">
                  Lưu ý: kết quả chỉ mang tính tham khảo, không thay thế ý kiến luật sư.
                </p>
              </div>
            )}

            {messages.map((m, idx) => (
              <Message
                from={m.role}
                key={m.id}
                className="animate-slide-up-fade [&>div]:max-w-[88%]"
              >
                <div>
                  {m.role === "assistant" ? (
                    <article className="space-y-2">
                      <div className="flex items-center gap-2 eyebrow">
                        <span>Phúc đáp</span>
                        <span className="text-foreground/40">·</span>
                        <span className="font-mono normal-case tracking-normal">
                          № {String(Math.ceil((idx + 1) / 2)).padStart(2, "0")}
                        </span>
                      </div>
                      <MessageContent className="bg-transparent px-0 py-0">
                        <div className="prose prose-sm max-w-none font-serif text-[15px] leading-[1.75] text-foreground prose-headings:font-serif prose-headings:text-foreground prose-p:my-2 prose-strong:text-foreground prose-a:text-secondary prose-a:underline prose-a:decoration-secondary/40 prose-a:underline-offset-2">
                          <ReactMarkdown>{m.content}</ReactMarkdown>
                        </div>
                      </MessageContent>
                      {m.sources && m.sources.length > 0 && (
                        <SourcePanel
                          sources={m.sources}
                          retrievalSource={m.retrieval_source || "unknown"}
                        />
                      )}
                    </article>
                  ) : (
                    <div className="space-y-1.5">
                      <div className="text-right eyebrow">Câu hỏi</div>
                      <MessageContent className="border-l-2 border-foreground bg-card px-4 py-3 text-[14px] leading-relaxed text-foreground rounded-none">
                        {m.content}
                      </MessageContent>
                    </div>
                  )}
                </div>
              </Message>
            ))}

            {status === "submitted" && (
              <div className="animate-slide-up-fade space-y-2">
                <div className="flex items-center gap-2 eyebrow">
                  <span>Đang tra cứu</span>
                </div>
                <div className="flex items-center gap-3 rounded-sm border border-border bg-card px-4 py-3 text-[13px] text-muted-foreground">
                  <span className="font-serif italic text-foreground">
                    Đang đối chiếu điều khoản và nguồn tham khảo
                  </span>
                  <span className="typing-dots">
                    <span />
                    <span />
                    <span />
                  </span>
                </div>
              </div>
            )}

            {error && (
              <div className="mt-3 flex items-start gap-2 rounded-sm border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}
          </ConversationContent>
          <ConversationScrollButton />
        </Conversation>

        <div className="border-t border-border bg-card px-6 py-4">
          <div className="mx-auto w-full max-w-3xl">
            <PromptInput onSubmit={handleSubmit}>
              <PromptInputTextarea
                ref={textareaRef}
                placeholder="Nhập câu hỏi pháp lý bằng tiếng Việt…"
                disabled={status === "submitted"}
                className="font-serif text-[15px] leading-relaxed"
              />
              <PromptInputFooter className="justify-between">
                <span className="text-[11px] text-muted-foreground">
                  Gửi {Math.min(messages.length, HISTORY_LIMIT)} lượt gần nhất · top_k = {topK}
                </span>
                <PromptInputSubmit status={status} disabled={status === "submitted"} />
              </PromptInputFooter>
            </PromptInput>
            <p className="mt-2 text-center text-[10.5px] uppercase tracking-wider text-muted-foreground">
              Tài liệu tham khảo · Không thay thế tư vấn pháp lý chính thức
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
