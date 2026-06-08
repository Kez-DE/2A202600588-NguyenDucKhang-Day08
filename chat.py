"""Streamlit RAG chatbot for the group project."""

from __future__ import annotations

import time
from pathlib import Path

import streamlit as st

from src.task10_generation import generate_with_citation


st.set_page_config(
    page_title="Drug Law RAG Chatbot",
    page_icon="⚖️",
    layout="wide",
)


def _init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Xin chào. Tôi có thể trả lời câu hỏi về pháp luật ma túy và các bài báo đã thu thập.",
                "sources": [],
            }
        ]
    if "top_k" not in st.session_state:
        st.session_state.top_k = 5


def _format_source(source: dict, index: int) -> None:
    metadata = source.get("metadata", {})
    title = metadata.get("title") or metadata.get("source") or metadata.get("source_path") or f"Nguồn {index}"
    score = source.get("score", 0.0)
    retrieval_source = source.get("source", "unknown")

    with st.expander(f"{index}. {title} · {retrieval_source} · score {score:.3f}"):
        st.caption(metadata)
        st.write(source.get("content", "")[:2500])


def _conversation_context(limit: int = 4) -> str:
    recent = st.session_state.messages[-limit * 2 :]
    lines = []
    for item in recent:
        role = "User" if item["role"] == "user" else "Assistant"
        lines.append(f"{role}: {item['content']}")
    return "\n".join(lines)


def main() -> None:
    _init_state()

    st.title("RAG Chatbot: Pháp luật ma túy & tin tức")
    st.caption("Streamlit demo dùng Task 9 retrieval và Task 10 generation có citation.")

    with st.sidebar:
        st.header("Cấu hình")
        st.session_state.top_k = st.slider("Số nguồn truy xuất", min_value=3, max_value=8, value=st.session_state.top_k)
        if st.button("Xóa hội thoại"):
            st.session_state.messages = []
            st.rerun()

        st.divider()
        st.subheader("Ví dụ câu hỏi")
        examples = [
            "Cai nghiện ma túy bắt buộc được quy định thế nào?",
            "Những nghệ sĩ nào liên quan tới ma túy trong dữ liệu?",
            "Địa bàn trọng điểm phức tạp về ma túy được xác định theo tiêu chí nào?",
        ]
        for example in examples:
            if st.button(example, use_container_width=True):
                st.session_state.pending_prompt = example

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                for i, source in enumerate(message["sources"], 1):
                    _format_source(source, i)

    prompt = st.chat_input("Nhập câu hỏi...")
    if "pending_prompt" in st.session_state:
        prompt = st.session_state.pop("pending_prompt")

    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt, "sources": []})
    with st.chat_message("user"):
        st.markdown(prompt)

    enriched_prompt = prompt
    history = _conversation_context()
    if history:
        enriched_prompt = f"Lịch sử hội thoại gần đây:\n{history}\n\nCâu hỏi hiện tại: {prompt}"

    with st.chat_message("assistant"):
        status = st.status("Đang truy xuất nguồn và sinh câu trả lời...", expanded=False)
        started = time.time()
        result = generate_with_citation(enriched_prompt, top_k=st.session_state.top_k)
        status.update(label=f"Hoàn tất trong {time.time() - started:.1f}s", state="complete")

        answer = result["answer"]
        st.markdown(answer)

        sources = result.get("sources", [])
        if sources:
            st.subheader("Nguồn đã dùng")
            for i, source in enumerate(sources, 1):
                _format_source(source, i)

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "retrieval_source": result.get("retrieval_source", "unknown"),
        }
    )


if __name__ == "__main__":
    main()
