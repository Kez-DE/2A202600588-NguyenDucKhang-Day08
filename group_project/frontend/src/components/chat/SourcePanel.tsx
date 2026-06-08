import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { SourceItem } from "@/lib/chat-api";
import { cn } from "@/lib/utils";

interface Props {
  sources: SourceItem[];
  retrievalSource: string;
}

export function SourcePanel({ sources, retrievalSource }: Props) {
  if (!sources?.length) return null;
  return (
    <section className="mt-5">
      <div className="mb-2 flex items-center justify-between border-b border-foreground/80 pb-1">
        <span className="eyebrow">Trích dẫn nguồn ({sources.length})</span>
        <span className="font-mono text-[10px] uppercase tracking-wider text-muted-foreground">
          {retrievalSource}
        </span>
      </div>
      <ol className="divide-y divide-border border-b border-border">
        {sources.map((s, i) => (
          <SourceRow key={i} source={s} index={i} />
        ))}
      </ol>
    </section>
  );
}

function SourceRow({ source, index }: { source: SourceItem; index: number }) {
  const [open, setOpen] = useState(false);
  const [contentExpanded, setContentExpanded] = useState(false);
  const title =
    (source.metadata?.title as string) ||
    (source.metadata?.source as string) ||
    `Nguồn ${index + 1}`;

  const preview = contentExpanded
    ? source.content
    : source.content.slice(0, 280) + (source.content.length > 280 ? "…" : "");

  return (
    <li>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start gap-3 py-2.5 text-left hover:bg-muted/40"
      >
        <span className="cite-marker mt-0.5 shrink-0">{index + 1}</span>
        <span className="flex-1 font-serif text-[13.5px] leading-snug text-foreground">
          {title}
        </span>
        <span className="mt-1 font-mono text-[10.5px] text-muted-foreground">
          {source.score.toFixed(3)}
        </span>
        <span className="mt-1 hidden font-mono text-[10px] uppercase tracking-wider text-muted-foreground sm:inline">
          {source.source}
        </span>
        {open ? (
          <ChevronDown className="mt-1 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="mt-1 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
        )}
      </button>
      {open && (
        <div className="space-y-3 border-t border-border bg-muted/30 px-3 py-3">
          <dl className="grid grid-cols-[max-content_1fr] gap-x-4 gap-y-1 text-[11.5px]">
            {Object.entries(source.metadata || {}).map(([k, v]) => (
              <div key={k} className="contents">
                <dt className="font-mono uppercase tracking-wider text-muted-foreground">{k}</dt>
                <dd className={cn("break-all font-serif text-foreground")}>{String(v)}</dd>
              </div>
            ))}
          </dl>
          <blockquote className="border-l-2 border-foreground/70 bg-card px-3 py-2 font-serif text-[13px] leading-relaxed whitespace-pre-wrap text-foreground">
            {preview}
          </blockquote>
          {source.content.length > 280 && (
            <button
              type="button"
              onClick={() => setContentExpanded((v) => !v)}
              className="text-[11.5px] font-medium text-secondary underline underline-offset-2 hover:text-foreground"
            >
              {contentExpanded ? "Thu gọn" : "Xem toàn văn"}
            </button>
          )}
        </div>
      )}
    </li>
  );
}
