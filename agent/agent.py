





# from ragatouille import RAGPretrainedModel
from langchain_core.vectorstores import VectorStore
from langchain_core.language_models.llms import LLM
from typing import Tuple
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.documents import Document as LangchainDocument



from langchain.chat_models import init_chat_model
from langchain_community.embeddings import HuggingFaceEmbeddings
import faiss
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.vectorstores import FAISS




def predict(message, history, retriever, llm):
    # Build conversation history
    history_langchain_format = []
    for msg in history:
        if msg['role'] == "user":
            history_langchain_format.append(HumanMessage(content=msg['content']))
        elif msg['role'] == "assistant":
            history_langchain_format.append(AIMessage(content=msg['content']))
    

    # Retrieve relevant documents for the current message
    relevant_docs = retriever.similarity_search(message,k=2)  # Your retriever
    
    # Build context from retrieved documents
    context = "\nExtracted documents:\n" + "\n".join([
        f"Document {i}: Content: {doc.page_content}\n\n context_source_url: {doc.metadata.get('source_url')}\n context_date: {doc.metadata.get('date')}\n---"
        for i, doc in enumerate(relevant_docs)
    ])

    RAG_PROMPT_TEMPLATE="""Using the information contained in the context,
                        give a comprehensive answer to the question.
                        Respond only to the question asked, response should be concise and relevant to the question.
                        Provide the context source url and context date of the source document when relevant.
                        If the answer cannot be deduced from the context, do not give an answer.
                        """


    # Create the prompt with system message, context, and conversation history
    messages = [
        SystemMessage(content=RAG_PROMPT_TEMPLATE),
        history_langchain_format
    ]
    combined_message = f"Context: {context}\n\nQuestion: {message}"
    messages.append(HumanMessage(content=combined_message))
    
    # Get response with tracking metadata
    gpt_response = llm.invoke(
        messages,
        config={
            "tags": ["Testing", 'RAG-Bot', 'V1'],
            "metadata": {
                "rag_llm": "gpt-5-nano",
                "num_retrieved_docs": len(relevant_docs),
            }
        }
    )
    
    source_context = "\nSources:\n" + "\n".join([
        f"{doc.metadata.get('source_url')} ({doc.metadata.get('date')})\n---"
        for i, doc in enumerate(relevant_docs)])
    
    return gpt_response.content + source_context
