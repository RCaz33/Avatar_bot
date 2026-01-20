# --------------------------------------------------------------
#  Test suite for the helpers in ``agent.knowledge_management``
# --------------------------------------------------------------
import os
from pathlib import Path

import pytest
from unittest import mock

from langchain_core.documents import Document

from agent.create_retreiver import (
    load_docs,
    load_markdowns_from_repos,
    split_documents,
    create_or_load_embeddings,
    load_vector_store,
    upload_index_to_azure,
)



@pytest.fixture
def dummy_pdf(tmp_path: Path) -> Path:
    """
    Create a *tiny* PDF file (just a few bytes are enough) and return the
    temporary directory that contains it.
    """
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.7\n%@mypdfcontents\n")
    return tmp_path


@pytest.fixture
def dummy_env_token(monkeypatch):
    """
    Provide a dummy GitHub token for the markdown loader.
    An empty token works – the loader only checks that something is present.
    """
    monkeypatch.setenv("GITHUB_PERSONAL_ACCESS_TOKEN", "dummy-token")



def test_load_docs_returns_documents(tmp_path: Path, dummy_pdf: Path):
    """
    ``load_docs`` should find at least one PDF inside the temporary folder.
    The loader expects a **relative** pattern, therefore we temporarily
    change the CWD to ``tmp_path`` and call the loader with ``"."``.
    """

    with mock.patch("os.getcwd", return_value=tmp_path):

        docs = load_docs("data/source/*")  
    assert isinstance(docs, list)
    assert len(docs) > 0                     
    assert all(isinstance(d, Document) for d in docs)



def test_load_markdowns_missing_token_raises(dummy_env_token):
    """
    When the required ``GITHUB_PERSONAL_ACCESS_TOKEN`` env‑var is **absent**
    the loader must raise ``RuntimeError`` before trying to contact GitHub.
    """
    # Delete the variable completely – the loader sees it as missing.
    with mock.patch.dict(os.environ, {"GITHUB_PERSONAL_ACCESS_TOKEN": ""}, clear=True):
        with pytest.raises(RuntimeError, match="Environment variable"):
            load_markdowns_from_repos(["someuser/some-repo"])



def test_split_documents_produces_unique_chunks():
    """
    After splitting duplicated ``page_content`` values should be removed.
    """

    dup = Document(page_content="same content")
    diff = Document(page_content="unique text")
    raw_docs = [dup, dup, diff]

    chunked = split_documents(
        chunk_size=5,
        raw_knowledge_base=raw_docs,
        tokenizer_name="bert-base-uncased",
    )
    # Two distinct contents → two Document objects
    assert len(chunked) == 2
    assert any(d.page_content == "same content" for d in chunked)


def test_create_or_load_embeddings_loads_existing_index(tmp_path: Path):
    """
    When a persisted FAISS index exists, ``load_vector_store`` should load it
    and be able to retrieve the original document.
    """
    from langchain_community.embeddings import HuggingFaceEmbeddings  # noqa: E402
    from langchain_community.vectorstores import FAISS               # noqa: E402

    embedder = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        encode_kwargs={"normalize_embeddings": True},
    )
    docs = [Document(page_content="hello world")]
    store_path = tmp_path / "faiss_store"

    # Build a tiny index and **persist** it on disk
    vecstore = FAISS.from_documents(docs, embedder)
    vecstore.save_local(str(store_path))

    # Load it again – this is the function we want to test
    loaded = load_vector_store(
        embedding_model_name="sentence-transformers/all-MiniLM-L6-v2",
        vector_db_path=str(store_path),
    )
    assert isinstance(loaded, FAISS)

    # Verify a similarity search works
    retrieved = loaded.similarity_search("hello")
    assert len(retrieved) == 1
    assert retrieved[0].page_content == "hello world"


import io
import pathlib
import unittest.mock as mock

def test_upload_index_to_azure_calls_blob_client(tmp_path: pathlib.Path):
    """
    The Azure uploader should walk through every file in the supplied
    folder and call ``BlobClient.upload_blob`` exactly once per file.
    """

    dummy_folder = tmp_path / "azure_fixture"
    dummy_folder.mkdir()
    (dummy_folder / "index.faiss").touch()
    (dummy_folder / "index.index").touch()
    (dummy_folder / "index.meta").touch()

    # Set up the mock hierarchy
    mock_blob_service_client = mock.Mock()
    mock_blob_client = mock.Mock()
    mock_container_client = mock.Mock()

    with mock.patch(
        "azure.storage.blob.BlobServiceClient.from_connection_string"
    ) as mock_from_conn:
        # Chain the mocks
        mock_from_conn.return_value.get_container_client.return_value = mock_container_client
        mock_container_client.get_blob_client.return_value = mock_blob_client

        # Run the function under test
        upload_index_to_azure(
            local_folder=str(dummy_folder),
            container_name="my-container",
            connection_string=(
                "DefaultEndpointsProtocol=https;AccountName=myacct;"
                "AccountKey=...;EndpointSuffix=core.windows.net"
            ),
        )

        # ---- Fix: verify that upload_blob was called for each file ----
        expected_names = ["index.faiss", "index.index", "index.meta"]
        # Retrieve the list of calls in order
        call_list = mock_blob_client.upload_blob.call_args_list

        # There should be as many calls as there are files
        assert len(call_list) == len(expected_names), (
            f"Expected {len(expected_names)} upload_blob calls, got {len(call_list)}"
        )

        # Iterate over the calls and assert overwrite=True
        for i, name in enumerate(expected_names):
            args, kwargs = call_list[i]
            assert isinstance(args[0], (str, bytes, pathlib.Path, io.BufferedReader)), "Unexpected blob name type"
            assert kwargs.get("overwrite") is True, (
                f"Upload call {i} did not have overwrite=True"
            )