# Project Architecture

This app has two deployable services:

- FastAPI backend: generates models, stores temporary artifacts, and saves POC project history.
- Streamlit frontend: collects user input, displays diagrams, and calls the backend.

## Request Flow

1. User enters a BRD or requirement in Streamlit.
2. Streamlit posts to `POST /orchestrate` on the FastAPI backend.
3. Backend creates a conceptual model using the full core banking glossary.
4. User reviews or updates the conceptual model.
5. On approval, backend generates logical and physical models.
6. Streamlit saves project history through backend `/projects/...` APIs.

## Main Files

- `api.py`: FastAPI routes. Keep HTTP concerns here.
- `schemas.py`: Pydantic request and response models.
- `tools.py`: model-generation functions, output normalization, and Gemini calls.
- `prompts.py`: prompts sent to Gemini.
- `project_history_store.py`: backend JSON storage for POC project history.
- `artifact_store.py`: in-memory artifact storage for diagram links during one backend runtime.
- `streamlit_app.py`: Streamlit UI and workflow state.
- `frontend_history_client.py`: frontend HTTP client for backend history APIs.
- `frontend/streamlit_app.py`: Render/Streamlit Cloud wrapper for the frontend entrypoint.
- `utils/mermaid_builder.py`: Mermaid diagram generation.

## Storage Notes

For the current POC:

- Project history is saved by the backend to `project_repository/history.json`.
- Artifact links are stored in backend memory through `artifact_store.py`.
- On Render free instances, local files and memory can reset after redeploys or restarts.

For production, replace both JSON and memory storage with a durable database such
as Supabase, Neon Postgres, or MongoDB Atlas.

## Naming Rules

Logical and physical table names must use canonical table names only:

- Good: `CUSTOMER_CONTACT`, `ACCOUNT_BALANCE`
- Bad: `DIM_CUSTOMER_CONTACT`, `FACT_ACCOUNT_BALANCE`

The prompts tell Gemini this rule, and `tools.py` also normalizes model output as
a guardrail.

## Junior Developer Tips

- Start reading at `api.py` if you want to understand backend endpoints.
- Start reading at `streamlit_app.py` if you want to understand the user journey.
- Treat `schemas.py` as the contract between frontend and backend.
- When changing Gemini behavior, update `prompts.py` first, then add a normalizer
  in `tools.py` if correctness matters.
- Do not put secrets in code. Use `.env` locally and Render environment variables
  in deployment.
