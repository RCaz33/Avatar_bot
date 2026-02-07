#%% import gradio
import gradio as gr

#%% load llm
from dotenv import load_dotenv
import os 
load_dotenv()


from langchain.chat_models import init_chat_model

llm = init_chat_model("gpt-5-nano", 
                      model_provider="openai",
                      api_key=os.environ['OPENAI_API_KEY'],
                      temperature=1)


#%% load retreiver
from agent.create_retreiver import load_vector_store
retriever = load_vector_store("intfloat/e5-base-v2","data/FAISS")


#%% Include a rate limiter
from agent.restrict_usage import RateLimiter
limiter = RateLimiter(max_requests=5, window_minutes=60)

#%% helper function
def format_source(doc):
    """
    format source according to its path 
    handles github api, internet page and uploaded files (pdf)

    Args:
        doc: a langchain Document
    Returns:
        str : formated_source from langchain Document"""
    source = doc.metadata["source"]
    if 'api.github' in source:
        return source.split("/blob")[0].replace("api.","")
    elif "https://" in source:
        return source
    elif "data" in source:
        try:
            page_label = doc.metadata["page_label"]
            total_page = doc.metadata["total_pages"]
            return f"{source.split('/')[-1]} page({page_label/total_page})"
        except:
            return f"{source.split('/')[-1]}"
    
#%% setup chatbot
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain.chat_models import init_chat_model


def predict(message, history,request: gr.Request):

    # Get client IP and check rate limit
    client_ip = request.client.host
    if not limiter.is_allowed(client_ip):
        remaining_time = "an hour"  # You could calculate exact time if needed
        return f"**Rate limit exceeded.** You've used your 5 requests per hour. Please try again in {remaining_time}.\n LinkedIn Profile : https://www.linkedin.com/in/rcaz33/"
    
    
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

    # Route: Check if RAG is needed
    ROUTING_PROMPT = """Does this question require specific information about Rémi Cazelles's projects, work, or education details?
    Answer ONLY 'RAG' if it needs specific facts/details, or 'CHAT' if it's a general greeting/chitchat.
    Question: {message}"""

    route_response = llm.invoke([HumanMessage(content=ROUTING_PROMPT.format(message=message))])

    if "CHAT" in route_response.content:
        # Simple chat response without RAG
        messages = [SystemMessage(content="You are a helpful assistant providing information about Rémi Cazelles professional career. Keep responses brief and friendly.")]
        messages.extend(history_langchain_format)
        messages.append(HumanMessage(content=message))
        response = llm.invoke(messages)
        return response.content

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
    RAG_PROMPT_TEMPLATE="""You will be asked information related to Rémi Cazelles's specific projects, work and education.
                        Using the information contained in the context, provide a comprehensive answer to the question.
                        Respond to the question asked with enought details, response should be precise and relevant to the question.
                        All the information retreive in the context are exclusivelly related to Rémi Cazelles work and education.
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
    
    source_context = "\n\nSources:\n" + "\n".join([
        f"{i+1} - {format_source(doc)}"
        for i, doc in enumerate(relevant_docs)])
    
    print(gpt_response.content )
    print(source_context)
    
    return f"{gpt_response.content} + {source_context}"


#%% setup tracking
os.environ["LANGSMITH_PROJECT"] = "Test_avatar_bot"
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_API_KEY"] = os.environ['LANGSMITH_API_KEY']
os.environ["LANGSMITH_ENDPOINT"]="https://api.smith.langchain.com"

#%% lauch gradio app
import gradio as gr

iface = gr.ChatInterface(
    predict,
    api_name="chat",
    chatbot=gr.Chatbot(placeholder="Hello! This app can help answering question about Rémi Cazelles's projects, work and education."),
    description="Ask me anything about Rémi’s work, projects, or education. I’ll cite the source documents.",
    examples=["How many years of experience does Rémi have in python, what significant project did he work on?", 
              "When did Rémi graduate from his doctorate, what was his research topic about?", 
              "I have a project in DataENgineering using Microsoft Fabrics for data pipeline, how good is Rémi experience to join a team ASAP?"]
)

iface.launch()