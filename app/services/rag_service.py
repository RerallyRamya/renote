import os
from groq import Groq

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """You are a helpful assistant that answers questions based strictly on the provided document context.

Rules:
- Answer ONLY from the context provided.
- If the answer is not in the context, say: "I couldn't find an answer to that in the uploaded documents."
- Be concise and accurate.
- Do not make up information."""


def build_context(chunks: list[str]) -> str:
    return "\n\n---\n\n".join(
        f"[Excerpt {i+1}]\n{chunk}" for i, chunk in enumerate(chunks)
    )


def generate_answer(question: str, chunks: list[str]) -> str:
    if not chunks:
        return "I couldn't find an answer to that in the uploaded documents."

    context = build_context(chunks)
    user_message = f"""Context from uploaded documents:

{context}

Question: {question}"""

    response = _client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        max_tokens=1024,
    )
    return response.choices[0].message.content