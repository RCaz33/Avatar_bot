
# load files 
from langchain_community.document_loaders import FileSystemBlobLoader
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers import PyPDFParser

# split docs
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document 
from transformers import AutoTokenizer
from typing import List, Optional
from tqdm import tqdm

# create or load embeds
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy

from langchain_community.embeddings import HuggingFaceEmbeddings # deprecated
# from langchain_huggingface import HuggingFaceEmbeddings



def load_docs(root_path):
    """ load all pdf documents from root folder 'data'"""
    loader = GenericLoader(
        blob_loader=FileSystemBlobLoader(
            path="../",
            glob=f"{root_path}/**/*.pdf",
        ),
        blob_parser=PyPDFParser(),
    )

    docs = loader.load()
    return docs


# Split Langchain Document at 512 tokens to embed

def split_documents(
    chunk_size: int,
    RAW_KNOWLEDGE_BASE: List[Document],
    tokenizer_name: Optional[str] ,
) -> List[Document]:
    """
    Split documents into chunks of maximum size `chunk_size` tokens and return a list of documents.
    """
    text_splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        AutoTokenizer.from_pretrained(tokenizer_name),
        chunk_size=chunk_size,
        chunk_overlap=int(chunk_size / 10),
        add_start_index=True,
        strip_whitespace=True,
        separators=".",
    )

    docs_processed = text_splitter.split_documents(RAW_KNOWLEDGE_BASE)

    # Remove duplicates
    unique_texts = {}
    docs_processed_unique = []
    for doc in docs_processed:
        if doc.page_content not in unique_texts:
            unique_texts[doc.page_content] = True
            docs_processed_unique.append(doc)

    return docs_processed_unique





def create_or_load_embeddings(docs_processed,EMBEDDING_MODEL_NAME,VECTOR_DB_PATH):
    # create the embedding model
    embedding_model = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        # multi_process=True,
        model_kwargs={"device": "mps"},  # use cuda for faster embeddings on nbidia GPUs
        encode_kwargs={"normalize_embeddings": True},  # Set `True` for cosine similarity
    )

    try:
        # Load the vector database from the folder
        KNOWLEDGE_VECTOR_DATABASE = FAISS.load_local(
            VECTOR_DB_PATH, 
            embedding_model, 
            allow_dangerous_deserialization=True  # Required for security in newer LangChain versions
        )
        return KNOWLEDGE_VECTOR_DATABASE

    except:
        # create the vector store
        KNOWLEDGE_VECTOR_DATABASE = FAISS.from_documents(
            docs_processed, embedding_model, distance_strategy=DistanceStrategy.COSINE
        )
        # Save the vector database
        KNOWLEDGE_VECTOR_DATABASE.save_local(VECTOR_DB_PATH)
        return KNOWLEDGE_VECTOR_DATABASE


def load_vector_store(EMBEDDING_MODEL_NAME,VECTOR_DB_PATH):
    # create the embedding model
    embedding_model = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        # multi_process=True,
        model_kwargs={"device": "mps"},  # use cuda for faster embeddings on nbidia GPUs
        encode_kwargs={"normalize_embeddings": True},  # Set `True` for cosine similarity
    )

    try:
        # Load the vector database from the folder
        KNOWLEDGE_VECTOR_DATABASE = FAISS.load_local(
            VECTOR_DB_PATH, 
            embedding_model, 
            allow_dangerous_deserialization=True  # Required for security in newer LangChain versions
        )
        return KNOWLEDGE_VECTOR_DATABASE

    except:
        raise "no vector store"

if __name__ == "__main__":
    try:
        print("create embeddings")
        raw_knowledge = load_docs("data")
        print(f"found {len(raw_knowledge)} chunks")
        ready_knowledge = split_documents(512,raw_knowledge,"intfloat/e5-base-v2")
        vector_store = create_or_load_embeddings(ready_knowledge,"intfloat/e5-base-v2","data")
        retriever = vector_store

    except Exception as e:
        print(e)


# # load files 
# root_path = "data"
# RAW_KNOWLEDGE_BASE = load_docs(root_path)

# # split docs
# chunk_size=512
# # RAW_KNOWLEDGE_BASE = [
# #     Document(page_content="\n".join([row["source"]] + row["text"].split("\n")[1:]), 
# #                       metadata={"source": row["source"],
# #                                 "date": row["text"].split("\n")[0]})
                                
# #     for _, row in tqdm(df.iterrows(), total=len(df))
# # ]
# EMBEDDING_MODEL_NAME =  "BAAI/bge-large-en-v1.5" # "sentence-transformers/all-MiniLM-L6-v2"

# docs_processed = split_documents(
#     512,  # We choose a chunk size adapted to our model
#     RAW_KNOWLEDGE_BASE,
#     tokenizer_name=EMBEDDING_MODEL_NAME,
# )

# # create or load vector store
# EMBEDDING_MODEL_NAME =  "BAAI/bge-large-en-v1.5" # "sentence-transformers/all-MiniLM-L6-v2"
# VECTOR_DB_PATH = f"./path/to/vector_store"

# vector_store = create_or_load_embeddings(docs_processed,EMBEDDING_MODEL_NAME,VECTOR_DB_PATH)
