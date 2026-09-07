"""
Local, air-gapped RAG engine.

Key design decisions:
- ChromaDB persists locally — no internet required.
- SentenceTransformer is loaded strictly from local disk.
- Documents are stored with a `session_id` metadata field so each query
  is scoped to only that session's uploaded files. No cross-session bleed.
- Supported formats: PDF, TXT, MD, CSV (read as plain text).
"""

import csv
import hashlib
import io
import os

import chromadb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer


class LocalRAGEngine:
    """
    Fully local, air-gapped RAG engine with session isolation.
    """

    def __init__(
        self,
        persist_directory="chroma_db",
        embedding_model="models/all-MiniLM-L6-v2",
    ):
        self.persist_directory = os.path.abspath(persist_directory)
        self.embedding_model_path = os.path.abspath(embedding_model)

        os.makedirs(self.persist_directory, exist_ok=True)

        if not os.path.exists(self.embedding_model_path):
            raise FileNotFoundError(
                "Local embedding model not found.\n"
                f"Expected path: {self.embedding_model_path}\n"
                "Download the model on an internet-connected machine "
                "and copy it into the models directory."
            )

        self.client = chromadb.PersistentClient(path=self.persist_directory)

        self.embedding_model = SentenceTransformer(
            self.embedding_model_path, local_files_only=True
        )

        # Single global collection — session isolation is via metadata filtering
        self.collection = self.client.get_or_create_collection(
            name="workbench_documents",
            metadata={"description": "Sovereign AI Workbench document collection"},
        )

    # ------------------------------------------------------------------
    # TEXT EXTRACTION
    # ------------------------------------------------------------------

    def _read_text_file(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def _read_pdf_file(self, file_path: str) -> str:
        reader = PdfReader(file_path)
        parts = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                parts.append(f"[Page {i + 1}]\n{text.strip()}")
        if not parts:
            raise ValueError(
                "PDF contains no extractable text (may be scanned/image-only)."
            )
        return "\n\n".join(parts)

    def _read_csv_file(self, file_path: str) -> str:
        """
        Read a CSV and convert it to a readable text table so the LLM can
        understand the actual data, not just column names.
        """
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read()

        try:
            reader = csv.reader(io.StringIO(raw))
            rows = list(reader)
        except Exception:
            # Fall back to plain text if CSV parsing fails
            return raw

        if not rows:
            return raw

        headers = rows[0]
        data_rows = rows[1:]

        lines = ["CSV DATA — " + ", ".join(headers)]
        for row in data_rows:
            # Pair each header with its value for clarity
            if len(row) == len(headers):
                pairs = " | ".join(f"{h}: {v}" for h, v in zip(headers, row))
            else:
                pairs = " | ".join(row)
            lines.append(pairs)

        return "\n".join(lines)

    def _extract_text(self, file_path: str) -> str:
        ext = os.path.splitext(file_path)[1].lower()

        if ext in (".txt", ".md"):
            return self._read_text_file(file_path)
        if ext == ".pdf":
            return self._read_pdf_file(file_path)
        if ext == ".csv":
            return self._read_csv_file(file_path)

        raise ValueError(f"Unsupported document type: {ext}")

    # ------------------------------------------------------------------
    # CHUNKING
    # ------------------------------------------------------------------

    def _chunk_text(
        self, text: str, chunk_size: int = 800, overlap: int = 150
    ) -> list:
        if chunk_size <= overlap:
            raise ValueError("chunk_size must be greater than overlap")

        chunks = []
        start = 0
        length = len(text)

        while start < length:
            chunk = text[start : start + chunk_size].strip()
            if chunk:
                chunks.append(chunk)
            start += chunk_size - overlap

        return chunks

    # ------------------------------------------------------------------
    # INGEST
    # ------------------------------------------------------------------

    def ingest_document(self, file_path: str, session_id: str = "global") -> int:
        """
        Read, chunk, embed, and store a document.

        Documents are tagged with `session_id` so queries can be scoped
        to only the files uploaded in the same session.

        Returns the number of chunks stored.
        """
        absolute_path = os.path.abspath(file_path)

        if not os.path.exists(absolute_path):
            raise FileNotFoundError(f"File not found: {absolute_path}")

        text = self._extract_text(absolute_path)

        if not text.strip():
            raise ValueError("Document contains no readable text.")

        chunks = self._chunk_text(text)
        file_name = os.path.basename(absolute_path)

        # Stable ID prefix based on session + file path
        doc_hash = hashlib.sha256(
            f"{session_id}:{absolute_path}".encode("utf-8")
        ).hexdigest()

        ids, embeddings, metadatas, documents = [], [], [], []

        for idx, chunk in enumerate(chunks):
            chunk_id = f"{doc_hash}_chunk_{idx}"
            embedding = self.embedding_model.encode(
                chunk, convert_to_numpy=True
            ).tolist()

            ids.append(chunk_id)
            embeddings.append(embedding)
            documents.append(chunk)
            metadatas.append(
                {
                    "file_name": file_name,
                    "file_path": absolute_path,
                    "session_id": session_id,
                    "chunk_index": idx,
                }
            )

        # Remove old chunks for the same file in the same session
        try:
            self.collection.delete(
                where={"$and": [{"file_path": absolute_path}, {"session_id": session_id}]}
            )
        except Exception:
            # If the collection is empty the delete will fail — that's OK
            pass

        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        return len(chunks)

    # ------------------------------------------------------------------
    # QUERY  (session-scoped)
    # ------------------------------------------------------------------

    def query_rag(
        self,
        query_text: str,
        session_id: str = "global",
        top_k: int = 5,
    ) -> str:
        """
        Retrieve the most relevant chunks for `query_text`, restricted to
        chunks that belong to `session_id`.

        Returns a formatted context string ready for the LLM.
        """
        if not query_text.strip():
            return ""

        total = self.collection.count()
        if total == 0:
            return ""

        query_embedding = self.embedding_model.encode(
            query_text, convert_to_numpy=True
        ).tolist()

        # Filter to this session only
        where_filter = {"session_id": session_id}

        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, total),
                where=where_filter,
            )
        except Exception:
            # If there are fewer documents than top_k, ChromaDB may error —
            # fall back to an unfiltered query
            try:
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=min(top_k, total),
                )
            except Exception:
                return ""

        documents = results.get("documents", [[]])
        metadatas = results.get("metadatas", [[]])

        if not documents or not documents[0]:
            return ""

        context_parts = []
        for idx, doc in enumerate(documents[0]):
            meta = metadatas[0][idx] if metadatas and metadatas[0] else {}
            fname = meta.get("file_name", "Unknown")
            context_parts.append(f"[Source: {fname} | Chunk {idx + 1}]\n{doc}")

        return "\n\n---\n\n".join(context_parts)


# ------------------------------------------------------------------
# LAZY SINGLETON
# ------------------------------------------------------------------

_rag_engine: LocalRAGEngine | None = None
_rag_engine_error: Exception | None = None


def get_rag_engine() -> LocalRAGEngine:
    global _rag_engine, _rag_engine_error

    if _rag_engine is not None:
        return _rag_engine

    if _rag_engine_error is not None:
        raise _rag_engine_error

    try:
        _rag_engine = LocalRAGEngine()
        return _rag_engine
    except Exception as error:
        _rag_engine_error = error
        raise


# ------------------------------------------------------------------
# PUBLIC CONVENIENCE FUNCTIONS
# ------------------------------------------------------------------

def ingest_document(file_path: str, session_id: str = "global") -> int:
    """Ingest a document into the local ChromaDB for a specific session."""
    return get_rag_engine().ingest_document(file_path, session_id=session_id)


def query_rag(query_text: str, session_id: str = "global", top_k: int = 5) -> str:
    """Query the RAG store, scoped to the given session."""
    try:
        engine = get_rag_engine()
    except FileNotFoundError:
        return ""
    except Exception:
        return ""

    return engine.query_rag(query_text, session_id=session_id, top_k=top_k)