"""
Simple LangGraph Hello World example with 2 nodes and OpenAI integration.
"""

import os
import getpass
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langsmith import Client
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage


# Define the state structure
class GraphState(TypedDict):
    """State for our simple hello world graph."""
    messages: list  # LangChain messages from LiveKit chat context
    message: str
    counter: int
    processed_by: list[str]
    llm_response: str


def _set_env(var: str):
    """Helper function to set environment variable if not already set."""
    if not os.environ.get(var):
        # Try to load from .env file first
        from dotenv import load_dotenv
        load_dotenv()
        if not os.environ.get(var):
            print(f"⚠️  {var} not found in environment or .env file")


def node_one(state: GraphState) -> GraphState:
    """First node - processes the chat context messages."""
    print("🚀 Node One: Processing chat context messages!")
    print("here is the state in node one", state)
    
    # Get messages from LiveKit chat context (converted by LLMAdapter)
    messages = state.get("messages", [])
    print(f"📨 Received {len(messages)} messages from chat context")
    
    # Extract the latest user message if available
    latest_message = ""
    for msg in reversed(messages):
        if hasattr(msg, 'content') and msg.content:
            latest_message = msg.content
            break
    
    processed_by = state.get("processed_by", []) + ["node_one"]
    return {
        "messages": messages,  # Pass through the messages
        "message": latest_message or "Hello World",
        "counter": state.get("counter", 0) + 1,
        "processed_by": processed_by,
        "llm_response": state.get("llm_response", "")
    }


def node_two(state: GraphState) -> GraphState:
    """Second node - calls OpenAI LLM using the chat context messages."""
    print("🤖 Node Two: Calling OpenAI LLM with chat context!")
    print("here is the state in node two", state)
    
    # Ensure OpenAI API key is set
    _set_env("OPENAI_API_KEY")
    
    # Initialize OpenAI chat model using LangChain
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
        max_tokens=100
    )
    
    # Use the messages from LiveKit chat context (already converted to LangChain format)
    messages = state.get("messages", [])
    current_message = state.get("message", "")
    
    # If we have chat context messages, use them; otherwise fall back to simple message
    if messages:
        print(f"📨 Using {len(messages)} messages from chat context")
        # Call the LLM with the full conversation history
        try:
            response = llm.invoke(messages)
            llm_response = response.content
            print(f"✨ LLM Response: {llm_response}")
        except Exception as e:
            print(f"❌ Error calling LLM: {e}")
            llm_response = f"Error: {str(e)}"
    else:
        # Fallback to simple message handling
        human_message = HumanMessage(
            content=f"Please respond to this greeting in a creative and friendly way: '{current_message}'"
        )
        try:
            response = llm.invoke([human_message])
            llm_response = response.content
            print(f"✨ LLM Response: {llm_response}")
        except Exception as e:
            print(f"❌ Error calling LLM: {e}")
            llm_response = f"Error: {str(e)}"
    
    processed_by = state.get("processed_by", []) + ["node_two"]
    return {
        "messages": messages,  # Pass through the messages
        "message": current_message,
        "counter": state.get("counter", 0) + 1,
        "processed_by": processed_by,
        "llm_response": llm_response
    }


def create_hello_world_graph():
    """Create and return the compiled LangGraph."""
    
    # Load environment variables from .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    # Configure LangSmith tracing if API key is available
    if os.getenv("LANGSMITH_API_KEY"):
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = "livekit-langgraph-integration"
        
        try:
            client = Client()
            print("📊 LangSmith tracing enabled for project: livekit-langgraph-integration")
        except Exception as e:
            print(f"⚠️  LangSmith setup warning: {e}")
    else:
        print("⚠️  LANGSMITH_API_KEY not found in .env file. Running without tracing.")
    
    # Create the state graph
    workflow = StateGraph(GraphState)
    
    # Add nodes (only two nodes now)
    workflow.add_node("node_one", node_one)
    workflow.add_node("node_two", node_two)
    
    # Define the flow
    workflow.set_entry_point("node_one")
    workflow.add_edge("node_one", "node_two")
    workflow.add_edge("node_two", END)
    
    # Compile the graph
    graph = workflow.compile()
    
    print("🎯 Hello World LangGraph with OpenAI integration compiled successfully!")
    return graph


def create_workflow():
    """Simple wrapper function for LiveKit LangChain integration."""
    return create_hello_world_graph()


# Export the compiled graph
graph = create_hello_world_graph()

# Example usage with LangGraphAdapter pattern
def create_langgraph_adapter():
    """Create a LangGraphAdapter with the compiled graph."""
    # This is an example of how you would use the graph with LangGraphAdapter
    # Uncomment and modify based on your actual LangGraphAdapter implementation
    
    # from your_langgraph_adapter import LangGraphAdapter  # Replace with actual import
    # lm = LangGraphAdapter(graph, config={"configurable": {"thread_id": '12345'}})
    # return lm
    
    # For now, return the graph directly
    return graph


def run_hello_world_example():
    """Run the hello world graph with sample input."""
    print("\n" + "="*50)
    print("🎉 Running Hello World LangGraph with OpenAI Example")
    print("="*50)
    
    # Initial state
    initial_state = {
        "messages": [],  # Will be populated by LLMAdapter in LiveKit
        "message": "",
        "counter": 0,
        "processed_by": [],
        "llm_response": ""
    }
    
    # Run the graph
    result = graph.invoke(initial_state)
    
    print("\n📋 Final Result:")
    print(f"   Message: {result['message']}")
    print(f"   Counter: {result['counter']}")
    print(f"   Processed by: {result['processed_by']}")
    print(f"   LLM Response: {result['llm_response']}")
    print("\n" + "="*50)
    
    return result


if __name__ == "__main__":
    # Run the example
    run_hello_world_example()
