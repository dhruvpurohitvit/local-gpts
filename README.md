# 🛡️ Sovereign AI Workbench

### Secure • Local • Private • Offline AI Assistant

Sovereign AI Workbench is a **fully local AI-powered workspace** designed for organizations that handle sensitive and confidential information.

The system enables users to interact with multiple local AI models, analyze documents and images, generate code, execute programs inside isolated Docker containers, perform Retrieval-Augmented Generation (RAG), and generate office documents — **without sending sensitive data to external cloud AI services**.

Built as a project for **Smart India Hackathon (SIH) 2026**.

---

# 🚀 Features

## 🤖 Local Multi-Model AI Routing

The system automatically selects the appropriate local model depending on the task.

| Task | Model |
|---|---|
| General conversation | `qwen2.5:3b` |
| Programming and debugging | `qwen2.5-coder:3b` |
| Images, PDFs and OCR | `qwen2.5vl:7b` |

Examples:

```text
"What is Retrieval Augmented Generation?"
→ General Model

"Write a Java program for Binary Search"
→ Coding Model

"Analyze this image"
→ Vision Model


## ?? Quick Start & Installation

Follow these steps to clone and run the Sovereign AI Workbench locally on your machine:

### 1. Clone the repository
`ash
git clone https://github.com/dhruvpurohitvit/local-gpts.git
cd local-gpts
``n
### 2. Install dependencies
Make sure you have Python 3.10+ installed. Then install the required packages:
`ash
pip install -r requirements.txt
``n
### 3. Ensure Ollama is running
You will need [Ollama](https://ollama.com/) installed to run the local models. Make sure Ollama is running in the background and pull the required models:
`ash
ollama pull qwen2.5:3b
ollama pull qwen2.5-coder:3b
ollama pull qwen2.5vl:7b
``n
### 4. Run the Backend API (Terminal 1)
Open a terminal and start the FastAPI backend server:
`ash
cd local-gpts
uvicorn backend.api:app --reload --port 8000
``n
### 5. Run the Frontend UI (Terminal 2)
Open a **second** terminal and start the Streamlit frontend:
`ash
cd local-gpts
python -m streamlit run frontend/app.py --server.port 8501
``n
That's it! ?? Open **http://localhost:8501** in your browser. Default login credentials:
- **Username:** dmin`n- **Password:** dmin123`n
