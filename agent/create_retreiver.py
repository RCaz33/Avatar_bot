# Create embeddings with Langchain docs

# torch
import torch

# load files 
from langchain_community.document_loaders import FileSystemBlobLoader
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers import PyPDFParser
from langchain_community.document_loaders import GithubFileLoader
from langchain_community.document_loaders import WebBaseLoader

# split docs
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from transformers import AutoTokenizer
from typing import List, Optional
from tqdm import tqdm

# create or load embeds
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy

from langchain_community.embeddings import HuggingFaceEmbeddings  # noqa: E402
# from langchain_huggingface import HuggingFaceEmbeddings  # deprecated


def load_docs(root_path: str) -> List[Document]:
    """
    Load all PDF documents from a folder called ``root_path``.

    Args:
        root_path: Path to the directory that contains the PDFs.

    Returns:
        A list of :class:`~langchain_core.documents.Document` objects.
    """
    loader = GenericLoader(
        blob_loader=FileSystemBlobLoader(
            path=".",  # relative to the script location
            glob=f"{root_path}/*.pdf",
        ),
        blob_parser=PyPDFParser(),
    )

    docs = loader.load()
    return docs


import os
from typing import List, Sequence

from langchain_community.document_loaders import GithubFileLoader  # type: ignore
from langchain_core.documents import Document  # type: ignore


def load_markdowns_from_repos(
    repos: Sequence[str],
    branch: str = "main",
    token_env_var: str = "GITHUB_PERSONAL_ACCESS_TOKEN",
) -> List[Document]:
    """
    Load all markdown (``.md``) files from a collection of GitHub repositories.

    Args:
        repos: Iterable of repository identifiers (e.g. ``["langchain-ai/langchain"]``).
        branch: The branch name to clone. Defaults to ``"main"``.
        token_env_var: Name of the environment variable that stores the personal
            access token. Defaults to ``"GITHUB_PERSONAL_ACCESS_TOKEN"``.

    Returns:
        A list of :class:`~langchain_core.documents.Document` objects.


    Raises:
        RuntimeError: If the required token is not found in the environment.
    """
    # Resolve the token – fail fast if it is missing.
    token = os.getenv(token_env_var)
    if not token:
        raise RuntimeError(
            f"Environment variable {token_env_var!r} not set. "
            "Provide a GitHub personal access token."
        )

    # Load markdown files from each repository and concatenate the results.
    all_documents: List[Document] = []
    for repo in repos:
        loader = GithubFileLoader(
            repo=repo,
            branch=branch,
            access_token=token,
            github_api_url="https://api.github.com",
            file_filter=lambda file_path: file_path.lower().endswith(".md"),
        )
        all_documents.extend(loader.load())

    return all_documents


def load_given_webpages(url_list:List) -> List[Document]:
    """
    Load all webpages from a list of urls
        
    Args:
        url_list: List to the urls.

    Returns:
        A list of :class:`~langchain_core.documents.Document` objects.

    """

    loader_multiple_pages = WebBaseLoader(url_list)
    docs = loader_multiple_pages.load()

    return docs




# Split Langchain Document at ``chunk_size`` tokens to embed
def split_documents(
    chunk_size: int,
    raw_knowledge_base: List[Document],
    tokenizer_name: Optional[str],
) -> List[Document]:
    """
    Split documents into chunks of ``chunk_size`` tokens.

    The function uses the tokenizer attached to ``tokenizer_name`` to count tokens.
    It also removes duplicate ``page_content`` values.

    Args:
        chunk_size: Maximum number of tokens per chunk.
        raw_knowledge_base: List of ``Document`` objects to split.
        tokenizer_name: Name or path of the tokenizer model.

    Returns:
        A list of unique ``Document`` objects after splitting.
    """
    text_splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
        AutoTokenizer.from_pretrained(tokenizer_name),
        chunk_size=chunk_size,
        chunk_overlap=int(chunk_size / 10),
        add_start_index=True,
        strip_whitespace=True,
        separators=".",
    )

    docs_processed = text_splitter.split_documents(raw_knowledge_base)

    # Remove duplicates
    unique_texts = {}
    docs_processed_unique = []
    for doc in docs_processed:
        if doc.page_content not in unique_texts:
            unique_texts[doc.page_content] = True
            docs_processed_unique.append(doc)

    return docs_processed_unique


def create_or_load_embeddings(
    docs_processed: List[Document],
    embedding_model_name: str,
    vector_db_path: str,
) -> FAISS:
    """
    Load an existing vector store from ``vector_db_path`` or create a new one.

    Args:
        docs_processed: List of ``Document`` objects after splitting.
        embedding_model_name: Name of the embedding model to use.
        vector_db_path: Directory where the FAISS index will be stored.

    Returns:
        The loaded or newly created ``FAISS`` vector store.
    """
    # Create the embedding model base on engine

    device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")

    embedding_model = HuggingFaceEmbeddings(
        model_name=embedding_model_name,
        # multi_process=True,
        model_kwargs={"device": device},  # use mps (or cuda) for faster embeddings
        encode_kwargs={"normalize_embeddings": True},
    )

    try:
        # Load the vector database from the folder
        knowledge_vector_database = FAISS.load_local(
            vector_db_path,
            embedding_model,
            allow_dangerous_deserialization=True,
        )
        return knowledge_vector_database

    except Exception:  # pylint: disable=broad-except
        # Create the vector store from scratch
        knowledge_vector_database = FAISS.from_documents(
            docs_processed,
            embedding_model,
            distance_strategy=DistanceStrategy.COSINE,
        )
        knowledge_vector_database.save_local(vector_db_path)
        return knowledge_vector_database


def load_vector_store(embedding_model_name: str, vector_db_path: str) -> FAISS:
    """
    Load a persisted FAISS vector store.

    Raises:
        Exception: If the store cannot be found/loaded.
    """

    device = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")

    embedding_model = HuggingFaceEmbeddings(
        model_name=embedding_model_name,
        # multi_process=True,
        model_kwargs={"device": device},
        encode_kwargs={"normalize_embeddings": True},
    )

    try:
        knowledge_vector_database = FAISS.load_local(
            vector_db_path,
            embedding_model,
            allow_dangerous_deserialization=True,
        )
        return knowledge_vector_database

    except Exception:  # pylint: disable=broad-except
        raise RuntimeError("no vector store found") from None


# Azure blob uploader -----------------------------------------------------------
from azure.storage.blob import BlobServiceClient

def upload_index_to_azure(
    local_folder: str,
    container_name: str,
    connection_string: str,
) -> None:
    """
    Upload all files from ``local_folder`` to an Azure Blob container.

    Args:
        local_folder: Path to the directory containing files to upload.
        container_name: Name of the Azure container.
        connection_string: Azure Storage account connection string.
    """
    client = BlobServiceClient.from_connection_string(connection_string)
    container_client = client.get_container_client(container_name)

    for filename in os.listdir(local_folder):

        full_path = os.path.join(local_folder, filename)
        if not os.path.isfile(full_path):
            continue

        blob_client = container_client.get_blob_client(filename)
        with open(full_path, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)

    print("Upload complete.")



if __name__ == "__main__":

    import os 
    from dotenv import load_dotenv
    load_dotenv()

    connection_string = os.getenv("AZURE_CONN_STR")
    container_name = os.getenv("container_name")
    # local_path = "../data/FAISS/512-intfloat-e5-base-v2-2026-01-16"

    if not connection_string or not container_name:
        raise RuntimeError("Missing Azure connection settings in .env file.")

    vector_db_path = "data/FAISS"  
    embeddings_size = 256
    embeddings_name = "intfloat/e5-base-v2"

    try:
        # load pdfs
        print("Creating embeddings...")
        print("... from pdfs ...")
        raw_knowledge = load_docs("data/source/CV_competences")
        print(f"Found {len(raw_knowledge)} raw documents.")
        # load md from git
        repos_to_fetch: List[str] = [
            "RCaz33/MCP-1st-Birthday_Hackathon",
            "RCaz33/Smolagent_GAIA_Benchmark", 
            "RCaz33/DataBricks_Hackathon",
            # "RCaz33/Microchip_Health_Monitoring",
            "RCaz33/End-to-end-ML-pipeline",
            "RCaz33/ExplainableAI_XAI_DogBreedClassification",
            "RCaz33/Time-series_Multiclass-classification_Reservoir-computing-INRIA",
            "RCaz33/Digital_production-line",
            "RCaz33/Pipeline_data_process",
            "RCaz33/Meetings_summaries"]
        print("... from git ...")
        markdown_docs = load_markdowns_from_repos(repos_to_fetch)
        print(f"Collected {len(markdown_docs)} markdown documents.")
        raw_knowledge.extend(markdown_docs)
        # load from urls
        urls = ["https://github.com/RCaz33?tab=repositories",
                "https://scholar.google.com/citations?user=0q1atkkAAAAJ&hl=fr",
                "https://cordis.europa.eu/project/id/844746/reporting",
                "https://stochelec.weebly.com/",
                "https://www.linkedin.com/in/rcaz33/recent-activity/all/"]
        print("... from urls ...")
        urls_docs = load_given_webpages(urls)
        print(f"Collected {len(urls_docs)} markdown documents.")
        raw_knowledge.extend(urls_docs)


        ready_knowledge = split_documents(embeddings_size, raw_knowledge, embeddings_name)
        vector_store = create_or_load_embeddings(
            ready_knowledge,
            embeddings_name,
            vector_db_path,
        )
        upload_index_to_azure(vector_db_path, container_name,connection_string)

    except Exception as e:  
        print(f"Error: {e}")
