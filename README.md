# AI Data Modeling And Discovery API

This repository now runs as a single FastAPI application that serves:

- the modeling APIs at `/docs`
- the Digital DA HTML page at `/`
- the analytics APIs at `/analytics`, `/analytics/batch`, and `/analytics/requirements/process`

## Architecture

- `orchestrator.py`: stage-based router for conceptual, logical, and physical flows
- `tools.py`: one-shot core banking glossary prompt context and generation tools
- `prompts.py`: detailed prompts for each modeling stage
- `schemas.py`: request and response contracts used by Swagger
- `api.py`: FastAPI entry point
- `rag.py`: legacy optional RAG helper, not used by the active API flow
- `analytics_service.py`: Digital DA analytics retrieval service
- `analytics_workbook.py`: workbook-to-JSON glossary builder and requirement workbook parser
- `AI Data Discovery.html`: browser frontend for the Digital DA workflow

For a more junior-friendly walkthrough of the codebase, see `ARCHITECTURE.md`.

## Recommended demo path

Use Swagger at `http://127.0.0.1:8000/docs` and call:

1. `POST /orchestrate` with the business requirement
2. Review the returned conceptual JSON, Mermaid text, and artifact links
3. Open `conceptual_view_url` to visualize the ER diagram
4. Use the returned download links for JSON and Mermaid artifacts
5. Send an approval request to `POST /orchestrate` with the same `artifact_id`
   to generate logical and physical outputs

## Run

```bash
pip install -r requirements-backend.txt
uvicorn api:app --reload
```

Then open:

- `http://127.0.0.1:8000/` for the Digital DA HTML page
- `http://127.0.0.1:8000/docs` for Swagger

## Deployment

Use `render.yaml` to deploy the single FastAPI service on Render. The same
service exposes the HTML frontend and all APIs. See `DEPLOYMENT.md` for the
full checklist.

Create a local `.env` file in the repository root:

```bash
cp .env.example .env
```

Then set:

```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

Never commit `.env`; it is ignored by `.gitignore`.

## Example Swagger request

```json
{
  "requirement": "Design a retail banking data model where a customer can hold multiple accounts and each account can have many transactions.",
  "artifact_id": null
}
```

## Analytics API

Use `POST /analytics` to search the glossary JSON with three deterministic
matching phases: exact attribute match, RapidFuzz partial/abbreviation match,
and FAISS semantic search over attribute name plus description.

Example request:

```json
{
  "attribute_name": "cust_id",
  "attribute_description": "Borrower or customer identifier",
  "region": "UK"
}
```

## Digital DA workbook flow

- Global glossary source:
  `DATA/RISK_MultiScenario_Unified_Business_Glossary 1.xlsx`
  sheet: `Glossary_All`
- Requirement upload source:
  `DATA/Shubhangi_testfiles-RISK_Requirement.xlsx`
  sheet: `Requirement`
- Required requirement columns:
  `Business Attribute`, `Business Definition`
- Optional requirement columns:
  `Region`, `Value Stream`, `Brief Problem Statement / Use Case`, `System Requirements`

The backend automatically converts the glossary workbook into
`DATA/Business_Glossary_Output.json` when the workbook changes, then uses that
JSON for retrieval and semantic indexing.

## Notes

- Conceptual generation sends the full core banking glossary into the prompt as one-shot context instead of using RAG retrieval.
- Conceptual modeling should use a structured output schema, not a physical database schema.
- Mermaid is generated from the conceptual model structure using `utils/mermaid_builder.py`.
- The active frontend is `AI Data Discovery.html`, served directly by FastAPI.
- The analytics backend now depends on `RapidFuzz`, `sentence-transformers`, `numpy`, and `faiss-cpu` for fuzzy and semantic ranking.
