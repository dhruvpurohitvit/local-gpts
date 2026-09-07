import os
import hashlib

import chromadb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer


class LocalRAGEngine:
    """
    Fully local, air-gapped RAG engine.

    - ChromaDB runs locally.
    - Embedding model loads only from local disk.
    - No internet access is required during execution.
    """

    def __init__(
        self,
        persist_directory="chroma_db",
        embedding_model="models/all-MiniLM-L6-v2"
    ):
        self.persist_directory = os.path.abspath(
            persist_directory
        )

        self.embedding_model_path = os.path.abspath(
            embedding_model
        )

        os.makedirs(
            self.persist_directory,
            exist_ok=True
        )

        # Verify local embedding model exists
        if not os.path.exists(
            self.embedding_model_path
        ):
            raise FileNotFoundError(
                "Local embedding model not found.\n"
                f"Expected path: {self.embedding_model_path}\n"
                "Download the model on an internet-connected machine "
                "and copy it into the models directory."
            )

        # Local persistent ChromaDB
        self.client = chromadb.PersistentClient(
            path=self.persist_directory
        )

        # Load embedding model strictly from local disk
        self.embedding_model = SentenceTransformer(
            self.embedding_model_path,
            local_files_only=True
        )

        # Create or load local collection
        self.collection = self.client.get_or_create_collection(
            name="workbench_documents",
            metadata={
                "description": (
                    "Local Sovereign AI Workbench "
                    "document collection"
                )
            }
        )

    # --------------------------------------------------
    # READ TEXT FILE
    # --------------------------------------------------

    def _read_text_file(self, file_path: str) -> str:
        """
        Read a UTF-8 text file.
        """

        with open(
            file_path,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as file:
            return file.read()

    # --------------------------------------------------
    # READ PDF FILE
    # --------------------------------------------------

    def _read_pdf_file(self, file_path: str) -> str:
        """
        Extract readable text from a PDF.
        """

        reader = PdfReader(file_path)

        text_parts = []

        for page in reader.pages:
            page_text = page.extract_text()

            if page_text:
                text_parts.append(page_text)

        return "\n".join(text_parts)

    # --------------------------------------------------
    # EXTRACT DOCUMENT TEXT
    # --------------------------------------------------

    def _extract_text(self, file_path: str) -> str:
        """
        Extract text depending on the file type.
        """

        extension = os.path.splitext(
            file_path
        )[1].lower()

        if extension == ".txt":
            return self._read_text_file(
                file_path
            )

        if extension == ".pdf":
            return self._read_pdf_file(
                file_path
            )

        raise ValueError(
            f"Unsupported document type: {extension}"
        )

    # --------------------------------------------------
    # TEXT CHUNKING
    # --------------------------------------------------

    def _chunk_text(
        self,
        text: str,
        chunk_size: int = 800,
        overlap: int = 150
    ) -> list:
        """
        Split text into overlapping chunks.
        """

        if chunk_size <= overlap:
            raise ValueError(
                "chunk_size must be greater than overlap"
            )

        chunks = []

        start = 0
        text_length = len(text)

        while start < text_length:

            end = start + chunk_size

            chunk = text[start:end].strip()

            if chunk:
                chunks.append(chunk)

            start += chunk_size - overlap

        return chunks

    # --------------------------------------------------
    # INGEST DOCUMENT
    # --------------------------------------------------

    def ingest_document(
        self,
        file_path: str
    ) -> int:
        """
        Read, chunk, embed, and store a document locally.

        Returns:
            Number of chunks stored.
        """

        absolute_path = os.path.abspath(
            file_path
        )

        if not os.path.exists(
            absolute_path
        ):
            raise FileNotFoundError(
                f"File not found: {absolute_path}"
            )

        text = self._extract_text(
            absolute_path
        )

        if not text.strip():
            raise ValueError(
                "Document contains no readable text"
            )

        chunks = self._chunk_text(
            text
        )

        file_name = os.path.basename(
            absolute_path
        )

        # Generate a stable ID prefix based on the file path
        document_hash = hashlib.sha256(
            absolute_path.encode("utf-8")
        ).hexdigest()

        ids = []
        embeddings = []
        metadatas = []

        for index, chunk in enumerate(chunks):

            chunk_id = (
                f"{document_hash}_chunk_{index}"
            )

            embedding = self.embedding_model.encode(
                chunk,
                convert_to_numpy=True
            ).tolist()

            ids.append(chunk_id)

            embeddings.append(embedding)

            metadatas.append({
                "file_name": file_name,
                "file_path": absolute_path,
                "chunk_index": index
            })

        # Remove old entries for the same document
        try:
            self.collection.delete(
                where={
                    "file_path": absolute_path
                }
            )
        except Exception:
            pass

        # Store locally in ChromaDB
        self.collection.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas
        )

        return len(chunks)

    # --------------------------------------------------
    # QUERY RAG
    # --------------------------------------------------

    def query_rag(
        self,
        query_text: str,
        top_k: int = 3
    ) -> str:
        """
        Search the local ChromaDB collection.

        Returns formatted context for the LLM.
        """

        if not query_text.strip():
            return ""

        collection_count = self.collection.count()

        if collection_count == 0:
            return ""

        query_embedding = self.embedding_model.encode(
            query_text,
            convert_to_numpy=True
        ).tolist()

        results = self.collection.query(
            query_embeddings=[
                query_embedding
            ],
            n_results=min(
                top_k,
                collection_count
            )
        )

        documents = results.get(
            "documents",
            [[]]
        )

        metadatas = results.get(
            "metadatas",
            [[]]
        )

        if not documents or not documents[0]:
            return ""

        context_parts = []

        for index, document in enumerate(
            documents[0]
        ):

            metadata = {}

            if metadatas and metadatas[0]:
                metadata = metadatas[0][index]

            file_name = metadata.get(
                "file_name",
                "Unknown"
            )

            context_parts.append(
                f"[Context {index + 1} | Source: {file_name}]\n"
                f"{document}"
            )

        return "\n\n".join(
            context_parts
        )


# --------------------------------------------------
# LAZY LOCAL RAG ENGINE
# --------------------------------------------------

rag_engine = None
rag_engine_error = None


def get_rag_engine():
    global rag_engine, rag_engine_error

    if rag_engine is not None:
        return rag_engine

    if rag_engine_error is not None:
        raise rag_engine_error

    try:
        rag_engine = LocalRAGEngine()
        return rag_engine
    except Exception as error:
        rag_engine_error = error
        raise


# --------------------------------------------------
# CONVENIENCE FUNCTIONS
# --------------------------------------------------

def ingest_document(
    file_path: str
) -> int:
    """
    Ingest a document into the local ChromaDB.
    """

    return get_rag_engine().ingest_document(
        file_path
    )


def query_rag(
    query_text: str,
    top_k: int = 3
) -> str:
    """
    Query the local RAG database.
    """

    try:
        engine = get_rag_engine()
    except FileNotFoundError:
        return ""

    return engine.query_rag(
        query_text,
        top_k
    )