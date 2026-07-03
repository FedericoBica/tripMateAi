# ✈️ TripMate AI — A Multi-Agent Travel Planner with LangGraph

TripMate AI is an open-source AI travel planner that turns a natural-language trip request into a practical travel plan with flight suggestions, hotel ideas, and a day-by-day itinerary.

The project uses a multi-agent workflow built with **LangGraph**, **LangChain**, **FastAPI**, and **Groq LLMs**.

---

## 🌍 Why this project?

Planning a trip usually means jumping between multiple websites, tools, and spreadsheets.

TripMate AI brings that flow into one experience by combining:

- a flight-search agent,
- a hotel-research agent,
- an itinerary-planning agent,
- and a final response agent,

all coordinated through a **LangGraph workflow**.

---

## ✨ Features

- ✈️ Flight research using **AviationStack**
- 🏨 Hotel suggestions using **Tavily Search**
- 🧠 Multi-agent orchestration with **LangGraph**
- 📝 Structured travel itinerary generation
- 🌐 FastAPI backend with a simple web interface
- 💾 Conversation state persistence using **PostgreSQL**
- ⚡ LLM-powered responses with **Groq**

---

## 🧱 Tech Stack

- Python 3.10+
- FastAPI
- Jinja2
- HTML / CSS / JavaScript
- LangGraph
- LangChain
- Groq LLMs
- PostgreSQL
- Tavily API
- AviationStack API

---

## ✅ Prerequisites

Before running the project locally, make sure you have:

- Python 3.10 or newer installed
- PostgreSQL running and accessible
- API keys for:
  - Groq
  - Tavily
  - AviationStack

---

## 🔐 Environment Variables

Create a `.env` file in the project root with the following variables:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/travel_db
GROQ_API_KEY=your_groq_api_key
AVIATIONSTACK_API_KEY=your_aviationstack_api_key
TAVILY_API_KEY=your_tavily_api_key
DEFAULT_ORIGIN_IATA=DAC

## How to run

uv init

1. Create the Virtual Environment

'''bash
uv venv 
'''

2. Activate the Environment
'''bash
source .venv/bin/activate
'''

3. Install the requirements
'''bash
uv add -r requirements.txt
'''
