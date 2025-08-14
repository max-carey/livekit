import os
from typing import TypedDict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langsmith import Client
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate
import asyncio


class GraphState(TypedDict):
    """State for our native explain graph."""
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


# Define tools that can be called by the LLM
@tool
async def correct_answer() -> str:
    """Call this tool when the user answers correctly."""
    # This will be executed automatically by LangGraph when the LLM calls this tool
    # The actual LiveKit session interaction will need to be handled through a callback
    print("✅ Tool executed: correct_answer")
    return "The user answered correctly! Generating congratulatory response in Spanish."


@tool  
async def wrong_answer() -> str:
    """Call this tool when the user answers incorrectly."""
    # This will be executed automatically by LangGraph when the LLM calls this tool
    print("❌ Tool executed: wrong_answer") 
    return "The user answered incorrectly. Generating encouragement response in Spanish."


def should_continue(state: GraphState) -> str:
    """Determine if we should continue to tools or end."""
    messages = state.get("messages", [])
    if not messages:
        return "end"
    
    last_message = messages[-1]
    # Check if the last message has tool calls
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        print(f"🔧 Tool calls detected: {len(last_message.tool_calls)} tools to execute")
        return "tools"
    return "end"


def custom_tool_node(state: GraphState) -> GraphState:
    """Custom tool execution node that preserves conversation history."""
    print("🔧 Custom Tool Node: Executing tools while preserving conversation")
    
    messages = state.get("messages", [])
    print(f"📨 Tool Node - Input messages ({len(messages)}):")
    for i, msg in enumerate(messages):
        print(f"  {i}: {type(msg).__name__} - {getattr(msg, 'role', 'no role')} - {getattr(msg, 'content', '')[:50]}...")
    
    # Find the last AI message with tool calls
    last_ai_message = None
    for msg in reversed(messages):
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            last_ai_message = msg
            break
    
    if not last_ai_message:
        print("❌ No AI message with tool calls found")
        return state
    
    print(f"🔧 Found AI message with {len(last_ai_message.tool_calls)} tool calls")
    
    # Execute tools and create tool messages
    tools_map = {tool.name: tool for tool in [correct_answer, wrong_answer]}
    tool_messages = []
    
    for tool_call in last_ai_message.tool_calls:
        tool_name = tool_call["name"]
        tool_call_id = tool_call["id"]
        
        if tool_name in tools_map:
            try:
                print(f"🔧 Executing tool: {tool_name}")
                # Execute the tool using LangChain's invoke method
                tool_args = tool_call.get("args", {})
                print(f"🔧 Tool args: {tool_args}")
                
                # Use the tool's async invoke method since our tools are async
                result = asyncio.run(tools_map[tool_name].ainvoke(tool_args))
                
                # Create tool message
                tool_message = ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call_id,
                    name=tool_name
                )
                tool_messages.append(tool_message)
                print(f"✅ Tool {tool_name} executed successfully: {result}")
                
            except Exception as e:
                print(f"❌ Error executing tool {tool_name}: {e}")
                error_message = ToolMessage(
                    content=f"Error executing {tool_name}: {str(e)}",
                    tool_call_id=tool_call_id,
                    name=tool_name
                )
                tool_messages.append(error_message)
    
    # Add tool messages to the conversation
    updated_messages = messages + tool_messages
    
    print(f"📤 Tool Node - Output messages ({len(updated_messages)}):")
    for i, msg in enumerate(updated_messages):
        print(f"  {i}: {type(msg).__name__} - {getattr(msg, 'role', 'no role')} - {getattr(msg, 'content', '')[:50]}...")
    
    processed_by = state.get("processed_by", []) + ["custom_tool_node"]
    return {
        "messages": updated_messages,
        "message": state.get("message", ""),
        "counter": state.get("counter", 0) + 1,
        "processed_by": processed_by,
        "llm_response": state.get("llm_response", "")
    }


def final_response_node(state: GraphState) -> GraphState:
    """Generate final response after tools have been executed."""
    print("🎯 Final Response Node: Generating response based on tool results")
    
    # Ensure OpenAI API key is set
    _set_env("OPENAI_API_KEY")
    
    # Initialize OpenAI chat model (no tools needed for final response)
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
    )
    
    messages = state.get("messages", [])
    print(f"📨 Processing {len(messages)} messages for final response")
    
    # Debug: print detailed message information
    print("🔍 Detailed message analysis:")
    for i, msg in enumerate(messages):
        msg_type = type(msg).__name__
        role = getattr(msg, 'role', 'no role')
        content = getattr(msg, 'content', 'no content')
        tool_calls = getattr(msg, 'tool_calls', None)
        tool_call_id = getattr(msg, 'tool_call_id', None)
        name = getattr(msg, 'name', None)
        
        print(f"  Message {i}: {msg_type}")
        print(f"    Role: {role}")
        print(f"    Content: {content[:100] if content else 'None'}...")
        print(f"    Tool calls: {len(tool_calls) if tool_calls else 'None'}")
        print(f"    Tool call ID: {tool_call_id}")
        print(f"    Name: {name}")
        print()
    
    llm_response = ""
    updated_messages = messages.copy()
    
    if messages:
        try:
            # With our custom tool node, messages should now be properly ordered
            print(f"📨 Sending {len(messages)} messages to LLM for final response")
            
            response = llm.invoke(messages)
            llm_response = response.content or ""
            print(f"✨ Final LLM Response: {llm_response}")
            
            # Add the final AI response to the messages
            updated_messages.append(response)
            
        except Exception as e:
            print(f"❌ Error in final response: {e}")
            print(f"❌ Messages that caused error: {[type(msg).__name__ for msg in messages]}")
            llm_response = f"Error generating final response: {str(e)}"
            error_message = AIMessage(content=llm_response)
            updated_messages.append(error_message)
    
    processed_by = state.get("processed_by", []) + ["final_response"]
    return {
        "messages": updated_messages,
        "message": state.get("message", ""),
        "counter": state.get("counter", 0) + 1,
        "processed_by": processed_by,
        "llm_response": llm_response
    }





def check_for_right_answer(state: GraphState) -> GraphState:
    """Check user's answer and determine if it's correct using LLM with tools."""
    print("🤖 Check for Right Answer: Calling OpenAI LLM with chat context and tools!")
    print("here is the state in check_for_right_answer", state)
    
    # Ensure OpenAI API key is set
    _set_env("OPENAI_API_KEY")
    
    # Initialize OpenAI chat model using LangChain and bind tools
    tools = [correct_answer, wrong_answer]
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
    ).bind_tools(tools)
    
    # Use the messages from LiveKit chat context (already converted to LangChain format)
    messages = state.get("messages", [])
    current_message = state.get("message", "")

    print(f"📨 Check Answer - Input messages ({len(messages)}):")
    for i, msg in enumerate(messages):
        print(f"  {i}: {type(msg).__name__} - {getattr(msg, 'role', 'no role')} - {getattr(msg, 'content', '')[:50]}...")
    print(f"📨 Current message: {current_message}")
    
    llm_response = ""
    updated_messages = messages.copy()
    
    # If we have chat context messages, use them; otherwise fall back to simple message
    if messages:
        print(f"📨 Using {len(messages)} messages from chat context")
        # Call the LLM with the full conversation history
        try:
            response = llm.invoke(messages)
            llm_response = response.content or ""
            print(f"✨ LLM Response: {llm_response}")
            print(f"🔧 Tool calls in response: {getattr(response, 'tool_calls', [])}")
            
            # Add the AI response to the messages
            updated_messages.append(response)
            
            print(f"📤 Check Answer - Output messages ({len(updated_messages)}):")
            for i, msg in enumerate(updated_messages):
                print(f"  {i}: {type(msg).__name__} - {getattr(msg, 'role', 'no role')} - {getattr(msg, 'content', '')[:50]}...")
            
        except Exception as e:
            print(f"❌ Error calling LLM: {e}")
            llm_response = f"Error: {str(e)}"
            # Add error message to conversation
            error_message = AIMessage(content=llm_response)
            updated_messages.append(error_message)
    else:
        # Fallback to simple message handling
        human_message = HumanMessage(
            content=f"Please respond to this greeting in a creative and friendly way: '{current_message}'"
        )
        try:
            response = llm.invoke([human_message])
            llm_response = response.content or ""
            print(f"✨ LLM Response: {llm_response}")
            print(f"🔧 Tool calls in response: {getattr(response, 'tool_calls', [])}")
            
            # Update messages with both human message and AI response
            updated_messages = [human_message, response]
            
        except Exception as e:
            print(f"❌ Error calling LLM: {e}")
            llm_response = f"Error: {str(e)}"
            error_message = AIMessage(content=llm_response)
            updated_messages = [human_message, error_message]
    
    processed_by = state.get("processed_by", []) + ["check_for_right_answer"]
    return {
        "messages": updated_messages,  # Return updated messages with AI response
        "message": current_message,
        "counter": state.get("counter", 0) + 1,
        "processed_by": processed_by,
        "llm_response": llm_response
    }




def create_native_explain_graph():
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
    
    # Add nodes
    workflow.add_node("check_answer", check_for_right_answer)
    workflow.add_node("tools", custom_tool_node)  # Use our custom tool node
    workflow.add_node("final_response", final_response_node)
    
    # Define the flow with conditional routing
    workflow.set_entry_point("check_answer")
    
    # Add conditional edge from check_answer
    workflow.add_conditional_edges(
        "check_answer",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        }
    )
    
    # After tools are executed, generate final response
    workflow.add_edge("tools", "final_response")
    # After final response, end the workflow
    workflow.add_edge("final_response", END)
    
    # Compile the graph
    graph = workflow.compile()
    
    print("🎯 Native Explain LangGraph: Check Answer -> Tools -> Final Response compiled successfully!")
    return graph


def create_workflow():
    """Simple wrapper function for LiveKit LangChain integration."""
    return create_native_explain_graph()


# Export the compiled graph
graph = create_native_explain_graph()

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


def run_native_explain_example():
    """Run the native explain graph with sample input."""
    print("\n" + "="*50)
    print("🎉 Running Native Explain LangGraph with OpenAI Example")
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
    run_native_explain_example()
