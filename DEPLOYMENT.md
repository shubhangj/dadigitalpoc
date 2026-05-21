# Deployment Guide

This project is set up for:

- Single service: FastAPI on Render
- Frontend: served by the same FastAPI app from `AI Data Discovery.html`

## 1. Prepare GitHub

Push this repository to GitHub. Do not commit `.env`; it is ignored by `.gitignore`.

If a real API key was ever committed or pasted into a shared place, rotate it before deployment.

## 2. Deploy On Render

This repository includes `render.yaml`, so the easiest path is Render Blueprint deployment.

1. Open Render and create a new Blueprint from this GitHub repo.
2. Render will use:
   - Build command: `pip install -r requirements-backend.txt`
   - Start command: `uvicorn api:app --host 0.0.0.0 --port $PORT`
   - Health check: `/health`
3. When Render asks for secret values, set:
   - `GEMINI_API_KEY`: your Gemini key
4. Keep:
   - `GEMINI_MODEL=gemini-2.5-flash`
   - `PYTHON_VERSION=3.11.11`
   - `WARM_MODELS_ON_STARTUP=false`
   - `ANALYTICS_EMBEDDINGS_ENABLED=false`
   - `RAG_EMBEDDINGS_ENABLED=false`
   - Optional: `ANALYTICS_GLOSSARY_XLSX_PATH=/path/to/RISK_MultiScenario_Unified_Business_Glossary 1.xlsx`
5. After deployment, verify:
   - `https://your-render-service-name.onrender.com/health`
   - `https://your-render-service-name.onrender.com/`
   - `https://your-render-service-name.onrender.com/docs`

Do not set `PROJECT_REPOSITORY_DIR` for this POC. If it already exists in
Render from an older disk-based setup, remove it before redeploying.

For this POC, project history is saved through the backend API into the backend
service's local `project_repository/history.json` file.

## 3. Local Development

Start the backend locally:

```bash
pip install -r requirements-backend.txt
uvicorn api:app --reload
```

Then open:

- `http://127.0.0.1:8000/` for the Digital DA page
- `http://127.0.0.1:8000/docs` for Swagger

## 4. Important Notes

- Render free services can sleep when idle, so the first browser request may be slow.
- Render free services use an ephemeral filesystem. The POC history API saves to backend-local JSON, so history can still reset if the backend service redeploys or restarts.
- The Digital DA backend uses `DATA/RISK_MultiScenario_Unified_Business_Glossary 1.xlsx` as the glossary source and regenerates `DATA/Business_Glossary_Output.json` automatically when needed.
- Requirement uploads should follow `DATA/Shubhangi_testfiles-RISK_Requirement.xlsx` with required columns `Business Attribute` and `Business Definition`.
- The browser frontend calls the same FastAPI origin, so extra browser CORS setup is not needed for the current flow.
- Keep all real credentials in Render environment variables.
- The backend dependency file should not include `google-generativeai` together with `langchain-google-genai`; the backend uses `langchain-google-genai` only.
- Render free backend should use `requirements-backend.txt` and install the analytics ranking dependencies required for RapidFuzz and FAISS semantic search.
- If Render logs show `Using Python version 3.14.3 (default)` and `pydantic-core` fails to build, the Python pin was not applied. Confirm `.python-version` is pushed to GitHub or set `PYTHON_VERSION=3.11.11` in the Render service environment variables, then clear the build cache and redeploy.
