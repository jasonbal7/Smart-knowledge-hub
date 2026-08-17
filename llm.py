import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

groq_api_key = os.getenv("GROQ_API_KEY")

if groq_api_key: 
    client = OpenAI(api_key=groq_api_key, base_url="https://api.groq.com/openai/v1")
else:
    client = None
    
    
def generate_rag_answer(question: str, context_chunks: list[str]) -> str:
    """
    Synthesizes a response using Groq (Llama 3.1) strictly grounded
    in the provided context chunks.
    """
    if not context_chunks:
        return "I could not find any relevant information in your uploaded documents to answer this question."

    context_text = "\n\n---\n\n".join(context_chunks)

    system_instruction = (
        "You are an intelligent knowledge assistant. Answer the user's question using ONLY "
        "the provided document context. If the answer cannot be determined from the context, "
        "explicitly state: 'Based on your documents, I do not have enough information to answer that.' "
        "Keep your answer concise, accurate, and structured. Do not extrapolate beyond the text."
    )

    user_prompt = f"Document Context:\n{context_text}\n\nQuestion: {question}\n\nAnswer:"

    # Fallback if no API key is configured
    if not client or not groq_api_key or groq_api_key.startswith("gsk_your_actual"):
        return f"[MOCK RESPONSE]: Retrieved {len(context_chunks)} chunks from ChromaDB. Please set a valid GROQ_API_KEY in your .env file."

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,  # Low temperature for strict factual grounding
            max_tokens=600,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Error communicating with Groq API: {str(e)}"