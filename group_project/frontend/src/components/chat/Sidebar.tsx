import { Trash2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export type HealthStatus = "unknown" | "checking" | "ok" | "down";

interface Props {
  baseUrl: string;
  onBaseUrlChange: (v: string) => void;
  topK: number;
  onTopKChange: (v: number) => void;
  onClear: () => void;
  onExample: (q: string) => void;
  health: HealthStatus;
  onRecheck: () => void;
}

const EXAMPLES = [
  "Cai nghiện ma túy bắt buộc được quy định thế nào?",
  "Những nghệ sĩ nào liên quan tới ma túy trong dữ liệu?",
  "Địa bàn trọng điểm phức tạp về ma túy được xác định theo tiêu chí nào?",
];

const STATUS_LABEL: Record<HealthStatus, string> = {
  unknown: "Chưa kiểm tra",
  checking: "Đang kiểm tra",
  ok: "Trực tuyến",
  down: "Mất kết nối",
};

export function Sidebar({
  baseUrl,
  onBaseUrlChange,
  topK,
  onTopKChange,
  onClear,
  onExample,
  health,
  onRecheck,
}: Props) {
  const dotColor =
    health === "ok"
      ? "bg-emerald-600"
      : health === "down"
        ? "bg-destructive"
        : health === "checking"
          ? "bg-amber-500"
          : "bg-muted-foreground";

  return (
    <aside className="flex h-full w-80 shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground">
      {/* Masthead */}
      <div className="border-b border-sidebar-border px-5 pt-5 pb-4">
        <div className="eyebrow">Hồ sơ phiên</div>
        <h1 className="mt-1 font-serif text-[17px] leading-tight font-bold tracking-tight">
          Văn phòng Pháp lý
        </h1>
        <p className="mt-1 text-[11.5px] leading-snug text-muted-foreground">
          Hệ thống tra cứu nội bộ · phiên bản nghiên cứu
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-5 space-y-6">
        {/* Status */}
        <section className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="eyebrow">Trạng thái dịch vụ</span>
            <button
              type="button"
              onClick={onRecheck}
              className="text-[11px] text-muted-foreground hover:text-foreground hover:underline"
            >
              Kiểm tra lại
            </button>
          </div>
          <div className="flex items-center gap-2.5 rounded-sm border border-sidebar-border bg-card px-3 py-2 text-[12px]">
            {health === "checking" ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
            ) : (
              <span className={`inline-block h-2 w-2 rounded-full ${dotColor}`} />
            )}
            <span className="text-foreground">{STATUS_LABEL[health]}</span>
          </div>
        </section>

        {/* Endpoint */}
        <section className="space-y-1.5">
          <Label htmlFor="base-url" className="eyebrow">
            Điểm cuối API
          </Label>
          <Input
            id="base-url"
            value={baseUrl}
            onChange={(e) => onBaseUrlChange(e.target.value)}
            placeholder="http://localhost:8000"
            className="h-8 rounded-sm font-mono text-[11.5px]"
          />
        </section>

        {/* top_k */}
        <section className="space-y-1.5">
          <Label className="eyebrow">Số trích dẫn (top_k)</Label>
          <Select value={String(topK)} onValueChange={(v) => onTopKChange(Number(v))}>
            <SelectTrigger className="h-8 rounded-sm text-[12px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {[3, 4, 5, 6, 7, 8].map((n) => (
                <SelectItem key={n} value={String(n)} className="text-[12px]">
                  {n}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </section>

        {/* Mục lục câu hỏi */}
        <section className="space-y-2">
          <div className="flex items-baseline justify-between">
            <span className="eyebrow">Mục lục câu hỏi</span>
            <span className="font-mono text-[10px] text-muted-foreground">
              {String(EXAMPLES.length).padStart(2, "0")}
            </span>
          </div>
          <ol className="divide-y divide-sidebar-border border-y border-sidebar-border">
            {EXAMPLES.map((q, i) => (
              <li key={q}>
                <button
                  type="button"
                  onClick={() => onExample(q)}
                  className="group flex w-full items-baseline gap-3 px-1 py-2.5 text-left transition-colors hover:bg-sidebar-accent"
                >
                  <span className="font-mono text-[10.5px] text-muted-foreground group-hover:text-foreground">
                    §{String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="flex-1 font-serif text-[13px] leading-snug text-foreground">
                    {q}
                  </span>
                </button>
              </li>
            ))}
          </ol>
        </section>
      </div>

      {/* Footer actions */}
      <div className="border-t border-sidebar-border px-5 py-4 space-y-3">
        <Button
          variant="outline"
          size="sm"
          onClick={onClear}
          className="w-full justify-start rounded-sm text-[12px]"
        >
          <Trash2 className="mr-2 h-3.5 w-3.5" />
          Đóng hồ sơ phiên
        </Button>
        <details className="rounded-sm border border-sidebar-border bg-card p-2.5 text-[11.5px]">
          <summary className="cursor-pointer font-medium text-foreground">
            Hướng dẫn vận hành backend
          </summary>
          <div className="mt-2 space-y-2 text-muted-foreground">
            <pre className="overflow-x-auto rounded bg-muted/60 p-2 font-mono text-[10.5px] text-foreground">
              uvicorn api:app --reload --port 8000
            </pre>
            <p>Hoặc qua ngrok:</p>
            <pre className="overflow-x-auto rounded bg-muted/60 p-2 font-mono text-[10.5px] text-foreground">
              ngrok http 8000
            </pre>
            <pre className="overflow-x-auto rounded bg-muted/60 p-2 font-mono text-[10.5px] text-foreground">
              VITE_API_BASE_URL=https://...
            </pre>
          </div>
        </details>
      </div>
    </aside>
  );
}
