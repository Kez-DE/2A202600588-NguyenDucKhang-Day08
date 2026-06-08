import { createFileRoute } from "@tanstack/react-router";
import { ChatApp } from "@/components/chat/ChatApp";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Trợ lý nghiên cứu pháp lý Việt Nam — RAG" },
      {
        name: "description",
        content:
          "Tra cứu luật phòng chống ma túy và tin tức liên quan bằng tiếng Việt qua hệ thống RAG kết nối FastAPI backend.",
      },
    ],
  }),
  component: ChatApp,
});
