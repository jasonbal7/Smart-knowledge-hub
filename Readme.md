# Smart Knowledge Hub (SKH)

A production-grade Retrieval-Augmented Generation (RAG) platform and personal knowledge assistant built with FastAPI, SQLite, ChromaDB, and Groq.

Smart Knowledge Hub provides a clean Single-Page Application interface for managing notes, indexing PDF/text documents into a high-dimensional vector store, and asking grounded natural language questions strictly synthesized from your uploaded materials.

---

## Key Features

* **Multi-Tenant User Authentication:** Cryptographic password hashing using `bcrypt` and stateless JWT-based session security (`PyJWT`).
* **Relational Storage:** SQLite database managed through SQLAlchemy ORM for handling users, notes, and document metadata.
* **Vector Embeddings & Semantic Search:** Document ingestion pipeline that extracts, chunks, and indexes text into a persistent ChromaDB vector store.
* **Grounded RAG Pipeline:** Context retrieval filtered strictly by authenticated `user_id` and synthesized via Groq Cloud LLM inference with strict anti-hallucination prompting.
* **Cascade Lifecycle Management:** Deleting a document seamlessly purges records from SQLite and cleans up orphaned embeddings from ChromaDB.
* **Single-Page Application (SPA):** Lightweight, zero-dependency frontend written in vanilla HTML5, CSS3, and modern JavaScript.
* **API Security & Abuse Protection:** Implements CORS origin scoping, rate-limiting on authentication routes via `slowapi`, and explicit Pydantic validation.

---

## Tech Stack

* **Backend Framework:** [FastAPI](https://fastapi.tiangolo.com/) (ASGI via Uvicorn)
* **LLM & Inference:** [Groq](https://groq.com/) Cloud API
* **Vector Database:** [ChromaDB](https://www.trychroma.com/)
* **Relational Database & ORM:** SQLite + [SQLAlchemy](https://www.sqlalchemy.org/)
* **Data Validation & Schemas:** [Pydantic v2](https://docs.pydantic.dev/)
* **Security & Auth:** `bcrypt`, `PyJWT`, `OAuth2PasswordBearer`
* **Frontend:** Vanilla HTML/CSS/JavaScript (Self-contained SPA)

---

## Architecture Overview

```text
               +-----------------------------------+
               |        Frontend (index.html)       |
               +-----------------+-----------------+
                                 |  HTTP (Bearer JWT)
                                 v
               +-----------------+-----------------+
               |       FastAPI Backend Server      |
               +--------+-----------------+--------+
                        |                 |
         +--------------+                 +--------------+
         |                                               |
         v                                               v
+--------+--------+                             +--------+--------+
|  SQLite Database|                             | ChromaDB Store  |
|  (app.db)       |                             | (chroma_db/)    |
| - Users         |                             | - Embeddings    |
| - Notes         |                             | - User Metadata |
| - Doc Metadata  |                             +--------+--------+
+-----------------+                                      |
                                                         | (Top-k Chunks)
                                                         v
                                                +--------+--------+
                                                |  Groq API (LLM) |
                                                |  Synthesizer    |
                                                +-----------------+