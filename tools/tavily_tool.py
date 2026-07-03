from tavily import TavilyClient
import os
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()

client = TavilyClient(
    api_key=os.getenv("TAVILY_API_KEY")
)

def _format_results(results: list) -> str:
    formatted = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "Unknown")
        url = r.get("url", "")
        snippet = r.get("content", "").strip()
        # keep only the first 300 characters to avoid wall-of-text
        if len(snippet) > 300:
            snippet = snippet[:300].rsplit(" ", 1)[0] + "..."
        formatted.append(f"{i}. **{title}**\n {url}\n {snippet}")
    return "\n\n".join(formatted)


@tool
def search_hotels(destination:str, notes: str | None = None) -> str:
    """
    Busca hoteles recomendados para un destino mediante búsqueda web.
 
    Args:
        destination: Ciudad o zona donde buscar alojamiento.
        notes: Detalles opcionales que afinen la búsqueda (presupuesto,
               fechas, tipo de viaje, zona preferida), si el usuario los dio.
    """
    if not os.getenv("TAVILY_API_KEY"):
        return (
            "Hotel search error: TAVILY_API_KEY is missing.\n"
            "Please add it to your .env file."
        )
    query = f"best hotels in {destination}"
    if notes:
        query += f", {notes}"