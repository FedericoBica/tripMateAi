import os
from typing import TypedDict, Annotated, Callable
 
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.tools import BaseTool
from langchain_groq import ChatGroq
 
load_dotenv()
 
 
class _SubagentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]

def make_tool_subagent(
    tools: list[BaseTool],
    system_prompt: str,
    model: str = "llama-3.3-70b-versatile",
    recursion_limit: int = 8,
) -> Callable[[str], tuple[str, int]]:
    """
    Fábrica de sub-agentes ReAct de un solo especialista.
 
    Arma un LLM con `tools` bindeadas + su propio loop agent<->tools — el
    mismo patrón StateGraph/ToolNode/tools_condition de tu chatbot original,
    empaquetado para no repetirlo a mano por cada especialista nuevo.
 
    Devuelve una función run(query) -> (resumen_final, llm_calls_hechos),
    lista para usar directo como el "motor" de un nodo del grafo padre.
    """
    llm = ChatGroq(
        model=model, 
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
    ).bind_tools(tools)
 
    def _llm_node(state: _SubagentState):
        messages = [SystemMessage(content=system_prompt), *state["messages"]]

        last_error = None
        for attempt in range(3):
            try:
                return {"messages": [llm.invoke(messages)]}
            except Exception as e:
                last_error = e
        # Esto se ejecuta SOLO si las 3 vueltas del for fallaron.
        return {
            "messages": [
                AIMessage(
                    content=(
                        "No pude completar esta búsqueda por un error del "
                        f"proveedor del modelo: {last_error}"
                    )
                )
            ]
        }
    

    graph = StateGraph(_SubagentState)
    graph.add_node("agent", _llm_node)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
 
    # Sin checkpointer a propósito: cada sub-agente nace y muere dentro de
    # una sola llamada al nodo padre. La persistencia entre threads ya la
    # maneja el checkpointer del grafo padre (Postgres, en tu caso).
    compiled = graph.compile()
 
    def run(user_query: str) -> tuple[str, int, list[AnyMessage]]:
        result = compiled.invoke(
            {"messages": [HumanMessage(content=user_query)]},
            config={"recursion_limit": recursion_limit},
        )
        final_summary = result["messages"][-1].content
        llm_call_count = sum(1 for m in result["messages"] if isinstance(m, AIMessage))
        return final_summary, llm_call_count, result["messages"]
 
    return run