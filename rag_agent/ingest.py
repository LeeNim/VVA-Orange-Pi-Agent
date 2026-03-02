import os
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

DATA_PATH = "data/"
VECTOR_STORE_PATH = "vector_store/"

def ingest():
    print("Loading documents...")
    loader = DirectoryLoader(DATA_PATH, glob="**/*.txt", loader_cls=TextLoader)
    documents = loader.load()
    print(f"Loaded {len(documents)} documents.")

    print("Splitting documents...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    texts = text_splitter.split_documents(documents)
    print(f"Split into {len(texts)} chunks.")

    print("Embedding documents...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    
    print("Creating vector store...")
    db = FAISS.from_documents(texts, embeddings)
    
    print("Saving vector store...")
    db.save_local(VECTOR_STORE_PATH)
    print("Ingestion complete.")

if __name__ == "__main__":
    ingest()
