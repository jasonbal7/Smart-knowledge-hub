import chromadb
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
import io

# Loaded once at startup — this model runs locally, no API key needed
embedder = SentenceTransformer("all-MiniLM-L6-v2")

chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="study_docs")

# Function to extract the text from a PDF
def extract_text(filename: str, file_bytes: bytes) -> str:
    
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(file_bytes))          # reader is an object for pdf in order to read pages
        
        text = ""                                           
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"

        return text
    
    return file_bytes.decode("utf-8", errors="ignore")

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:       # overlap mean the next chunk starts 50 words before the previous chunk
    
    words = text.split()            # words becomes a list of words: "Hello world" -> ["Hello", "World"]
    chunks = []
    start = 0
    
    while start < len(words):
        end = start + chunk_size
        chunks.append(" ".join(words[start:end]))           # combine to the chunk list all the words of the words list with a space 
        start += chunk_size - overlap                       # go back 50 words to create the overlap
        
    return chunks
      
def embed_and_store(chunks: list[str], user_id: int, doc_id: int, filename: str): 
    
    
    # Convert each text chunk into an embedding (a vector of numbers)
    # so it can be stored and searched in the vector database.
    embeddings = embedder.encode(chunks).tolist()
    
    
    # Example: user5_doc12_chunk0
    ids = []
    for i in range(len(chunks)):
        chunk_id = f"user{user_id}_doc{doc_id}_chunk{i}"
        ids.append(chunk_id)
    
    # create metadata for each chunk
    metadatas = []
    for _ in chunks:
        metadata = {"user_id": user_id, "doc_id": doc_id, "filename": filename}
        metadatas.append(metadata)
        
    # Store the chunks, their embeddings, unique IDs, and metadata
    # in the vector database.
    collection.add(documents=chunks, embeddings=embeddings, ids=ids, metadatas=metadatas)

def retrieve_context(query: str, user_id: int, top_k: int = 4) -> list[str]:
    
    # turn the users question into an embedding
    query_embedding = embedder.encode([query]).tolist()
    
    # search for similar chunks belonging to this user
    results = collection.query(query_embedding=query_embedding, n_results=top_k, where={"user_id": user_id},)
    
    # return documents if we have found any else empty list 
    documents = results["documents"]    
    if documents:
        return documents[0]
    
    return []
    
    