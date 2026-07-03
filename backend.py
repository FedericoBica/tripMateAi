import os 
import certifi
from dotenv import load_dotenv

load_dotenv()

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

from typing import TypedDict, Annotated
import operator
import uuid

import psycopg
from psycopg.rows import dict_row

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.messages import (
    AnyMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
)
from langchain_groq import ChatGroq
from agents.flight_agent import run_flight_agent
from agents.hotel_agent import run_hotel_agent

def get_database_url():
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError(
            "DATABASE_URL is missing. Please add your Render PostgreSQL External Database URL to .env"
        )

    if "sslmode=" not in database_url:
        separator = "&" if "?" in database_url else "?"
        database_url = f"{database_url}{separator}sslmode=require"

    return database_url

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing. Please add it to your .env file.")

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=GROQ_API_KEY
)

class TravelState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    user_query: str
    flight_results: str
    hotel_results: str
    itinerary: str
    llm_calls: int


# =========================
# Flight Agent
# Delega al sub-agente con su propio loop (tools/flight_tool.py +
# agents/flight_agent.py). Este nodo del grafo padre ya no llama
# a ninguna tool directamente.
# =========================

def flight_agent(state: TravelState):
    flight_summary, calls_made, flights_found = run_flight_agent(state["user_query"])
    return {
        "flight_results": flight_summary,
        "flights_found": flights_found,
        "messages": [
            AIMessage(content="Flight results fetched.")
        ],
        "llm_calls": state.get("llm_calls", 0) + calls_made
    }


# =========================
# Hotel Agent
# =========================
 
def hotel_agent(state: TravelState):
    hotel_summary, calls_made, _messages = run_hotel_agent(state["user_query"]) 
    return {
        "hotel_results": hotel_summary,
        "messages": [
            AIMessage(content="Hotel information fetched.")
        ],
        "llm_calls": state.get("llm_calls", 0) + calls_made
    }

# =========================
# Itinerary Agent
# =========================

def itinerary_agent(state: TravelState):
    flights_note = (
        ""
        if state.get("flights_found", True)
        else "\nNota: no se encontraron vuelos reales para este pedido. "
             "No inventes vuelos ni los incluyas en el presupuesto estimado; "
             "mencioná que el usuario debería buscar opciones de vuelo por su cuenta.\n"
    )
    prompt = f"""
Create a complete travel itinerary.

User Query:
{state['user_query']}
{flights_note}
Flight Results:
{state['flight_results']}

Hotel Results:
{state['hotel_results']}

Reglas estrictas:
- No inventes precios, nombres de hoteles o vuelos, ni ningún dato numérico
  que no aparezca en Flight Results o Hotel Results de arriba. Si esa
  información no está disponible para algún tramo, decilo explícitamente
  en esa sección ("no se encontraron opciones para X") en vez de
  completarla con un número o nombre plausible.
- Si el destino es un país o región y el viaje dura varios días, dividilo
  en ciudades/paradas concretas (podés apoyarte en cómo vienen organizados
  los Hotel Results). Para cada parada, dá actividades por franja horaria
  (mañana/tarde/noche) en vez de solo nombrar la ciudad. Está bien sugerir
  tipos de comida o zonas para comer sin inventar el nombre de un
  restaurante puntual.
 
Make the itinerary practical, budget-aware, and easy to follow.

"""

    response = llm.invoke([
        SystemMessage(content="You are an expert travel planner."),
        HumanMessage(content=prompt)
    ])

    return {
        "itinerary": response.content,
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1
    }

# =========================
# Final Response Agent
# =========================

def final_agent(state: TravelState):
    final_prompt = f"""
Generate the final travel response for the user.

User Request:
{state['user_query']}

Flights:
{state['flight_results']}

Hotels:
{state['hotel_results']}

Itinerary:
{state['itinerary']}

Format the final answer beautifully using these sections:

1. Trip Summary
2. Flight Information
3. Hotel Suggestions
4. Day-by-Day Itinerary
5. Estimated Budget
6. Final Recommendations

Important:
- Be clear and practical.
- Mention that live flight API may not provide ticket prices if pricing is unavailable.
- Keep the response useful for real travel planning.
"""

    response = llm.invoke([
        SystemMessage(content="You are a professional AI travel booking assistant."),
        HumanMessage(content=final_prompt)
    ])

    return {
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1
    }

# =========================
# Build Graph
# =========================

graph = StateGraph(TravelState)

graph.add_node("flight_agent", flight_agent)
graph.add_node("hotel_agent", hotel_agent)
graph.add_node("itinerary_agent", itinerary_agent)
graph.add_node("final_agent", final_agent)

graph.add_edge(START,"flight_agent")
graph.add_edge("flight_agent","hotel_agent")
graph.add_edge("hotel_agent","itinerary_agent")
graph.add_edge("itinerary_agent","final_agent")
graph.add_edge("final_agent", END)


# =========================
# PostgreSQL Checkpointer
# =========================
DATABASE_URL = get_database_url()

_conn = psycopg.connect(
    DATABASE_URL,
    autocommit=True,
    row_factory=dict_row
)

checkpointer = PostgresSaver(_conn)
checkpointer.setup()

travel_graph = graph.compile(checkpointer=checkpointer)

# =========================
# Function for FastAPI
# =========================

def run_travel_agent(user_input: str, thread_id: str | None = None):
    if not thread_id:
        thread_id = f"user_{uuid.uuid4().hex}"

    config = {
        "configurable": {
            "thread_id": thread_id
        }
    }
    result = travel_graph.invoke(
        {
            "messages": [
                HumanMessage(content=user_input)
            ],
            "user_query": user_input,
            "flight_results": "",
            "hotel_results": "",
            "itinerary": "",
            "llm_calls": 0
        },
        config=config
    )

    final_answer = result["messages"][-1].content
    return{
        "thread_id": thread_id,
        "answer": final_answer,
        "flight_results": result.get("flight_results", ""),
        "hotel_results": result.get("hotel_results", ""),
        "itinerary": result.get("itinerary", ""),
        "llm_calls": result.get("llm_calls", 0),
    }