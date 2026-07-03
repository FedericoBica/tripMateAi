
from langchain_core.messages import ToolMessage

from agents.subagents_factory import make_tool_subagent
from tools.flight_tool import search_flights
 
FLIGHT_AGENT_SYSTEM_PROMPT = """Sos un especialista en búsqueda de vuelos.
 
Usá la tool `search_flights` para buscar vuelos en vivo. Podés llamarla más
de una vez si la primera búsqueda no da resultados útiles — por ejemplo,
probando sin fecha, o con un aeropuerto alternativo de la misma ciudad.
 
No inventes vuelos ni precios que la tool no haya devuelto.
Cuando tengas suficiente información (o hayas confirmado que no hay vuelos),
respondé con un resumen breve y claro para el agente que arma el itinerario.
No llames a más tools después de eso.
"""
 
_run_flight_subagent = make_tool_subagent(
    tools=[search_flights],
    system_prompt=FLIGHT_AGENT_SYSTEM_PROMPT,
)

def run_flight_agent(user_query: str) -> tuple[str, int, bool]:
    """
    Corre el sub-agente de vuelos y determina si encontró vuelos reales.
 
    El flag `flights_found` NO se saca del resumen en texto del LLM (que
    puede decir "no hay vuelos disponibles" de mil formas distintas y no
    querés andar haciendo pattern-matching sobre eso). Se saca del
    ToolMessage crudo: search_flights() siempre empieza su respuesta con
    "Live flights from ..." cuando sí encontró algo, y con otra cosa
    ("No live flight data found...", "Flight API error...", etc.) cuando no.
    Esa es la señal determinística — la definimos nosotros en la tool.
 
    Devuelve (resumen_final, llm_calls_hechos, flights_found).
    """
    summary, llm_calls, messages = _run_flight_subagent(user_query)
 
    flights_found = any(
        isinstance(m, ToolMessage) and str(m.content).startswith("Live flights from")
        for m in messages
    )
 
    return summary, llm_calls, flights_found

 