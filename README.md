# RecruiterRadar MVP 🎯

RecruiterRadar MVP is an AI-powered talent search demonstration platform. It allows users to query a static pool of candidate profiles using natural language and generate personalized outreach message drafts. This project showcases the practical application of Retrieval-Augmented Generation (RAG) for talent discovery and LLM-powered message personalization.


**Live Demo (Stretch Goal):** [Link to be added if deployed]

## ✨ Core Features (MVP)

* **AI-Powered RAG Search:** Input natural language queries (e.g., "Python developers with Neo4j experience") to find relevant candidates from a static dataset.
* **Contextual Results:** View candidate profiles with snippets highlighting why they matched your query.
* **LLM-Based Outreach Generation:** Automatically draft personalized outreach messages for selected candidates tailored to specific job roles.
* **Simple Web Interface:** An intuitive React frontend for easy interaction and demonstration.
* **FastAPI Backend:** A modern Python backend serving the AI/RAG logic.
* **Local Vector Storage:** Utilizes ChromaDB for efficient local similarity search.

## 🛠️ Technology Stack

* **Backend:**
    * Python 3.9+
    * FastAPI (Web Framework)
    * Uvicorn (ASGI Server)
    * Pydantic (Data Validation & Settings Management)
    * LangChain / LlamaIndex (RAG Orchestration)
    * OpenAI API Client (for `gpt-4o-mini` and `text-embedding-3-small`)
    * ChromaDB (Local Vector Store)
* **Frontend:**
    * React (v18+)
    * JavaScript (ES6+)
    * HTML5 & CSS3 (Basic styling)
    * Fetch API / Axios (for API communication)
    * Node.js & npm/yarn (for build & package management)
* **Development Tools:**
    * Git & GitHub (Version Control)
    * (Optional) Docker & Docker Compose
* **Linters & Formatters:**
    * Backend: Black, Flake8 (or Ruff)
    * Frontend: ESLint, Prettier

## 🚀 Getting Started

Follow these instructions to set up and run the RecruiterRadar MVP locally.

### Prerequisites

* Python 3.9 or higher
* Node.js and npm (or yarn)
* Git
* An OpenAI API Key

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd recruiter-radar-mvp