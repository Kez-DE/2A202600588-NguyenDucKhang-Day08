# Prompt Notes

## Prompt cho FastAPI RAG endpoint

```text
Bạn là backend RAG assistant cho chủ đề pháp luật Việt Nam về ma túy và các bài báo liên quan.

Input:
- question: câu hỏi hiện tại của người dùng
- history: tối đa 8 lượt hội thoại gần nhất
- top_k: số nguồn truy xuất

Yêu cầu xử lý:
1. Kết hợp history để hiểu follow-up question.
2. Gọi pipeline retrieval/generation nội bộ.
3. Chỉ trả lời bằng thông tin có trong context.
4. Mỗi nhận định phải có citation dạng [Nguồn, Năm].
5. Nếu thiếu evidence, trả lời: "Tôi không thể xác minh thông tin này từ nguồn hiện có".
6. Trả JSON gồm answer, retrieval_source, sources.
```

## Prompt cho Lovable xây UI

```text
Build a Vietnamese RAG chatbot UI for a drug-law knowledge base.

Use this API:
- POST /chat
- Request JSON: { "question": string, "top_k": number, "history": [{ "role": "user" | "assistant", "content": string }] }
- Response JSON: { "answer": string, "retrieval_source": string, "sources": [{ "content": string, "score": number, "metadata": object, "source": string }] }

UI requirements:
- Main screen is the chat, not a landing page.
- Left sidebar contains top_k selector, clear chat button, and 3 example questions.
- Assistant answers render markdown and preserve citations.
- Under each assistant answer, show collapsible source cards with title, score, retrieval type, metadata, and content preview.
- Keep conversation memory client-side and send it in every /chat request.
- Use a restrained professional dashboard style suitable for legal research.
- Use compact cards, clear typography, and avoid decorative gradients.
- Include loading, empty, and error states.
```
