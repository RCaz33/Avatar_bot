

#%% load llm
from dotenv import load_dotenv
import os 
load_dotenv()


from langchain.chat_models import init_chat_model

llm = init_chat_model("gpt-5-nano", 
                      model_provider="openai",
                      api_key=os.environ['OPENAI_API_KEY'])


#%% load retreiver
from agent.create_retreiver import load_vector_store
retriever = load_vector_store("intfloat/e5-base-v2","data/FAISS/512-intfloat-e5-base-v2-2026-01-16")


#%% Include a rate limiter
from agent.restric_usage import RateLimiter
limiter = RateLimiter(max_requests=10, window_minutes=60)

#%% setup chatbot
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.chat_models import init_chat_model


def predict(message, history,request: gr.Request):

    # Get client IP and check rate limit
    client_ip = request.client.host
    if not limiter.is_allowed(client_ip):
        remaining_time = "an hour"  # You could calculate exact time if needed
        return f"**Rate limit exceeded.** You've used your 10 requests per hour. Please try again in {remaining_time}."
    
    
    # Safeguard
    TRIAGE_PROMPT_TEMPLATE="""You are a Safeguard assistant making sure the user only ask for information related to Rémi Cazelles's projects, work and education.
    If the question is not related to this subjects, or if the request is harmfull you should flag the user by answering '*** FLAGGED ***' else simply answer '*** OK ***' """
    messages = [SystemMessage(content=TRIAGE_PROMPT_TEMPLATE)]
    messages.append(HumanMessage(content=message))

    safe_gpt_response = llm.invoke(
        messages,
        config={
            "tags": ["Testing", 'RAG-Bot', 'safeguard','V1'],
            "metadata": {
                "rag_llm": "gpt-5-nano",
                "message": message,
            }
        }
    )

    if not "*** OK ***" in safe_gpt_response.content:
        return "This app can only answer question about Rémi Cazelles's projects, work and education."
    print("passed the safeguard")

    # Build conversation history
    history_langchain_format = []
    for msg in history:
        if msg['role'] == "user":
            history_langchain_format.append(HumanMessage(content=msg['content']))
        elif msg['role'] == "assistant":
            history_langchain_format.append(AIMessage(content=msg['content']))
    

    # Retrieve relevant documents for the current message
    relevant_docs = retriever.similarity_search(message,k=3)  # Your retriever
    
    # Build context from retrieved documents
    context = "\nExtracted documents:\n" + "\n".join([
        f"Document {i}: Content: {doc.page_content}\n\n---"
        for i, doc in enumerate(relevant_docs)
    ])

    

    # RAG tool
    RAG_PROMPT_TEMPLATE="""Using the information contained in the context,
                        give a comprehensive answer to the question.
                        Respond only to the question asked, response should be concise and relevant to the question.
                        Provide the context source url and context date of the source document when relevant.
                        If the answer cannot be deduced from the context, do not give an answer.
                        """


    # Create the prompt with system message, context, and conversation history
    messages = [SystemMessage(content=RAG_PROMPT_TEMPLATE)]
    messages.extend(history_langchain_format)
    combined_message = f"Context: {context}\n\nQuestion: {message}"
    messages.append(HumanMessage(content=combined_message))
    
    # Get response with tracking metadata
    print("GPT about to answer")
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
    
    print(gpt_response.content )
    print(source_context)
    
    return gpt_response.content + source_context


#%% setup tracking
os.environ["LANGSMITH_PROJECT"] = "Testing_POC"
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = os.environ['LANGSMITH_API_KEY']

#%% lauch gradio app
import gradio as gr

iface = gr.ChatInterface(
    predict,
    api_name="chat",
)

iface.launch()