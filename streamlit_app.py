import base64
import json
import html
import os
from datetime import datetime
from io import BytesIO
from pathlib import Path
import xml.etree.ElementTree as ET
import uuid
import zipfile

import requests
import streamlit as st
import streamlit.components.v1 as components
from io import BytesIO
import pandas as pd

from frontend_history_client import BackendHistoryClient

#DEFAULT_BACKEND_API_URL = "https://hsbc-ominiaidatafabric.onrender.com"
DEFAULT_BACKEND_API_URL = "http://127.0.0.1:8000"
DEFAULT_PROJECT_REPOSITORY_PATH = Path(__file__).with_name("project_repository")


def get_backend_api_url() -> str:
    backend_url = os.getenv("BACKEND_API_URL", "").strip()
    if not backend_url:
        try:
            backend_url = str(st.secrets.get("BACKEND_API_URL", "")).strip()
        except Exception:
            backend_url = ""
    return (backend_url or DEFAULT_BACKEND_API_URL).rstrip("/")

LOGO_PATH = Path(__file__).with_name("kpmg-logo-png_seeklogo-290229.png")
EXAMPLE_IMAGE_PATH = Path(__file__).with_name("example.jpeg")
# POC mode: always use the app-local folder and ignore old Render disk env vars.
PROJECT_REPOSITORY_PATH = DEFAULT_PROJECT_REPOSITORY_PATH
PROJECT_STORE_FILE = PROJECT_REPOSITORY_PATH / "history.json"
LEGACY_PROJECT_STORE_FILE = PROJECT_REPOSITORY_PATH / "projects.json"
USE_CASE_REQUIREMENTS = {
    "usecase_1": "Design a full conceptual, logical, and physical data model for the loan credit risk domain.",
    "usecase_2": "Create a data model for customer, facility, loan, collateral, default, recovery, and provision reporting.",
}
LANDING_TOOL_CARDS = [
    {
        "phase": "Phase 1:",
        "title": "Conceptual",
        "description": "Business-level ER model with core entities and table-to-table relationships for review.",
    },
    {
        "phase": "Phase 2:",
        "title": "Logical",
        "description": "Low-level structure with tables, columns, primary keys, foreign keys, and relationships.",
    },
    {
        "phase": "Phase 3:",
        "title": "Physical",
        "description": "Developer-ready database design with datatypes, constraints, indexes, ER diagram, and DDL.",
    },
    {
        "phase": "Phase 4:",
        "title": "Upcoming",
        "description": "Reserved for Semantic Layer, Ontology, and Dimensional Modeling workflows.",
    },
]
TECH_USED = [
    "Python",
    "FastAPI",
    "Streamlit",
    "Gemini",
    "LangGraph",
    "LangChain",
    "Mermaid.js",
]
ANALYTICS_PRODUCT_LABEL = "Digiatal DA"
DATA_PRODUCTS = [
    "Conceptual",
    "Logical",
    "Physical",
    ANALYTICS_PRODUCT_LABEL,
    "Ontology",
    "Dimensional Modeling",
]
MODELING_PRODUCTS = [
    "Conceptual",
    "Logical",
    "Physical",
    "Ontology",
    "Dimensional Modeling",
]

st.set_page_config(page_title="OmniModel.AI", layout="wide")

API = get_backend_api_url()
HISTORY_CLIENT = BackendHistoryClient(API)

def render_app_logo() -> None:
    if not LOGO_PATH.exists():
        return

    encoded_logo = base64.b64encode(LOGO_PATH.read_bytes()).decode("utf-8")
    st.markdown(
        f"""
        <style>
        .app-fixed-header-bg {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 5.75rem;
            background: rgb(14, 17, 23);
            z-index: 999988;
            pointer-events: none;
        }}
        .app-fixed-header {{
            position: fixed;
            top: 0.95rem;
            left: 3.6rem;
            right: 1.25rem;
            z-index: 999990;
            display: flex;
            align-items: center;
            gap: 0.9rem;
            pointer-events: none;
            transition: left 180ms ease;
        }}
        .app-fixed-header img {{
            height: 46px;
            width: auto;
            display: block;
        }}
        .app-fixed-header-title {{
            margin: 0;
            color: rgba(250, 250, 250, 0.98);
            max-width: calc(100vw - 28rem);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 30px !important;
            font-weight: 700 !important;
            line-height: 1.05 !important;
            letter-spacing: -0.02em !important;
        }}
        div.block-container {{
            padding-top: 6.6rem;
        }}
        body:has(section[data-testid="stSidebar"][aria-expanded="true"]) .app-fixed-header {{
            left: 21rem;
        }}
        body:has(section[data-testid="stSidebar"][aria-expanded="false"]) .app-fixed-header {{
            left: 3.6rem;
        }}
        @media (max-width: 768px) {{
            .app-fixed-header-bg {{
                height: 5.9rem;
            }}
            .app-fixed-header {{
                top: 1rem;
                left: 4.2rem;
                right: 0.75rem;
            }}
            .app-fixed-header-title {{
                max-width: calc(100vw - 6rem);
                font-size: 20px !important;
            }}
            body:has(section[data-testid="stSidebar"][aria-expanded="true"]) .app-fixed-header {{
                left: 4.2rem;
            }}
            div.block-container {{
                padding-top: 6.8rem;
            }}
        }}
        </style>
        <div class="app-fixed-header-bg"></div>
        <div class="app-fixed-header">
            <img src="data:image/png;base64,{encoded_logo}" alt="KPMG logo" />
            <h1 class="app-fixed-header-title">OmniModel.AI</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )


render_app_logo()

st.markdown(
    """
    <style>
    div.block-container {
        font-size: 15px;
    }
    div.block-container h1 {
        font-size: 34px !important;
        line-height: 1.15 !important;
        letter-spacing: -0.02em !important;
    }
    div.block-container h2 {
        font-size: 30px !important;
        line-height: 1.16 !important;
        letter-spacing: -0.02em !important;
    }
    div.block-container h3 {
        font-size: 20px !important;
        line-height: 1.2 !important;
    }
    div.block-container label,
    div.block-container input,
    div.block-container textarea,
    div.block-container button,
    div.block-container p {
        font-size: 15px;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        font-size: 22px !important;
        line-height: 1.2 !important;
    }
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] button,
    section[data-testid="stSidebar"] span {
        font-size: 15px !important;
    }
    .workflow-stepper {
        display: flex;
        flex-wrap: nowrap;
        align-items: center;
        gap: 0.55rem;
        overflow-x: auto;
        white-space: nowrap;
        scrollbar-width: none;
    }
    .workflow-stepper::-webkit-scrollbar {
        display: none;
    }
    .workflow-stepper-shell {
        display: block;
        padding: 0.2rem 0;
    }
    .workflow-step {
        display: inline-flex;
        align-items: center;
        gap: 0.55rem;
        min-height: 2.25rem;
        padding: 0.4rem 0.8rem;
        border-radius: 999px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        background: rgba(255, 255, 255, 0.04);
        color: rgba(250, 250, 250, 0.68);
        font-size: 13px;
        font-weight: 600;
        transition: all 180ms ease;
    }
    .workflow-step.completed {
        background: rgba(35, 182, 120, 0.16);
        border-color: rgba(35, 182, 120, 0.34);
        color: rgba(188, 255, 220, 0.98);
    }
    .workflow-step.current {
        background: rgba(43, 108, 255, 0.18);
        border-color: rgba(43, 108, 255, 0.4);
        color: rgba(229, 239, 255, 0.98);
        box-shadow: 0 0 0 0.2rem rgba(43, 108, 255, 0.14);
    }
    .workflow-step.completed.current {
        background: rgba(35, 182, 120, 0.16);
        border-color: rgba(35, 182, 120, 0.34);
        color: rgba(188, 255, 220, 0.98);
        box-shadow: 0 0 0 0.2rem rgba(35, 182, 120, 0.12);
    }
    .workflow-step-index {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 1.2rem;
        height: 1.2rem;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.14);
        font-size: 11px;
        font-weight: 800;
        color: inherit;
        flex: 0 0 auto;
    }
    .workflow-arrow {
        color: rgba(250, 250, 250, 0.34);
        font-size: 15px;
        font-weight: 700;
    }
    .landing-hero {
        max-width: 86rem;
        padding: 1rem 0 0.75rem;
    }
    .landing-hero h2 {
        margin: 0;
        color: rgba(250, 250, 250, 0.98);
        font-size: clamp(2.3rem, 4vw, 4.4rem);
        line-height: 1.02;
        letter-spacing: -0.04em;
    }
    .landing-hero p {
        max-width: 58rem;
        margin: 1rem 0 0;
        color: rgba(250, 250, 250, 0.62);
        font-size: 1.02rem;
        line-height: 1.6;
    }
    .landing-cta-panel {
        margin: 1.35rem 0 1.5rem;
        padding: 1rem;
        border-radius: 1.35rem;
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 20px 56px rgba(0, 0, 0, 0.2);
    }
    .landing-section-title {
        margin: 0.4rem 0 0.85rem;
        color: rgba(250, 250, 250, 0.92);
        font-size: 1.05rem;
        font-weight: 800;
        letter-spacing: 0.02em;
    }
    .landing-card {
        min-height: 13rem;
        padding: 1.25rem;
        border-radius: 1.25rem;
        background:
            radial-gradient(circle at 10% 0%, rgba(43, 108, 255, 0.24), transparent 32%),
            rgba(255, 255, 255, 0.045);
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 20px 56px rgba(0, 0, 0, 0.24);
    }
    .landing-card h3 {
        margin: 0;
        color: rgba(250, 250, 250, 0.96);
        font-size: 1.25rem;
        line-height: 1.2;
    }
    .landing-card p {
        margin: 0.75rem 0 0;
        color: rgba(250, 250, 250, 0.58);
        font-size: 0.92rem;
        line-height: 1.45;
    }
    .landing-card-count {
        display: block;
        margin-top: 1.2rem;
        text-align: center;
        color: rgba(188, 255, 220, 0.98);
        font-size: 3rem;
        font-weight: 800;
        line-height: 1;
        letter-spacing: -0.04em;
    }
    .landing-card-note {
        display: block;
        margin-top: 0.55rem;
        text-align: center;
        color: rgba(250, 250, 250, 0.58);
        font-size: 0.9rem;
        line-height: 1.35;
    }
    .landing-tool-card {
        height: 15.5rem;
        padding: 1.1rem;
        border-radius: 1.25rem;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        background:
            linear-gradient(140deg, rgba(18, 30, 52, 0.94), rgba(18, 22, 30, 0.78)),
            radial-gradient(circle at 90% 10%, rgba(255, 75, 82, 0.18), transparent 30%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 20px 56px rgba(0, 0, 0, 0.24);
    }
    .landing-tool-card h3 {
        margin: 0.2rem 0 0;
        color: rgba(250, 250, 250, 0.96);
        font-size: 1.2rem;
        line-height: 1.15;
    }
    .landing-tool-phase {
        display: block;
        color: rgba(188, 255, 220, 0.94);
        font-size: 0.88rem;
        font-weight: 800;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .landing-tool-card p {
        margin: 1.05rem 0 0;
        color: rgba(250, 250, 250, 0.62);
        font-size: 0.86rem;
        line-height: 1.5;
    }
    .landing-tool-card.is-upcoming {
        background:
            linear-gradient(140deg, rgba(33, 34, 40, 0.86), rgba(17, 20, 27, 0.78)),
            radial-gradient(circle at 90% 10%, rgba(255, 255, 255, 0.08), transparent 30%);
        border-style: dashed;
    }
    .landing-example-section {
        margin-top: 2.8rem;
    }
    .landing-example-frame {
        padding: 0.8rem;
        border-radius: 1.35rem;
        background:
            radial-gradient(circle at 8% 0%, rgba(43, 108, 255, 0.14), transparent 30%),
            rgba(255, 255, 255, 0.035);
        border: 1px solid rgba(255, 255, 255, 0.09);
        box-shadow: 0 20px 56px rgba(0, 0, 0, 0.2);
        max-width: 54rem;
        margin: 0 auto;
    }
    .landing-example-frame img {
        display: block;
        width: 100%;
        max-height: 18rem;
        object-fit: contain;
        border-radius: 1rem;
        background: rgba(0, 0, 0, 0.18);
    }
    .tech-stack-section {
        margin-top: 3rem;
        padding: 1rem 1.2rem;
        border-radius: 1.35rem;
        background:
            radial-gradient(circle at 10% 0%, rgba(255, 75, 82, 0.12), transparent 30%),
            rgba(255, 255, 255, 0.035);
        border: 1px solid rgba(255, 255, 255, 0.09);
        box-shadow: 0 20px 56px rgba(0, 0, 0, 0.18);
    }
    .tech-stack-list {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        align-items: center;
    }
    .tech-stack-label {
        color: rgba(250, 250, 250, 0.92);
        font-size: 0.95rem;
        font-weight: 800;
        margin-right: 0.25rem;
    }
    .tech-stack-pill {
        display: inline-flex;
        align-items: center;
        padding: 0.35rem 0.55rem;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.07);
        color: rgba(250, 250, 250, 0.68);
        font-size: 0.78rem;
        line-height: 1;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .project-picker {
        margin-top: 1.25rem;
        padding: 1.1rem;
        border-radius: 1.1rem;
        background: rgba(255, 255, 255, 0.045);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .chat-input-shell {
        margin-top: 1rem;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) {
        max-width: 82rem;
        min-height: 4.25rem;
        display: grid !important;
        grid-template-columns: 5.4rem minmax(0, 1fr) 5.4rem;
        align-items: center !important;
        gap: 0.75rem;
        padding: 0.55rem 0.85rem;
        border-radius: 999px;
        background: rgb(43, 43, 43);
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 22px 54px rgba(0, 0, 0, 0.24);
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) [data-testid="column"] {
        display: flex;
        align-items: center;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) > div {
        width: auto !important;
        min-width: 0 !important;
        max-width: none !important;
        flex: unset !important;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) > div:has([data-testid="stFileUploader"]) {
        justify-self: start;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) > div:has([data-testid="stTextArea"]) {
        justify-self: stretch;
        padding-left: 0.3rem !important;
        padding-right: 0.3rem !important;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) > div:has(.stButton) {
        justify-self: center;
    }
    .chat-input-shell [data-testid="column"] {
        padding-left: 0;
        padding-right: 0;
    }
    .chat-input-shell [data-testid="column"]:first-child {
        flex: unset !important;
        width: auto !important;
        min-width: 0 !important;
        padding-left: 0;
        padding-right: 0;
        justify-content: flex-start;
    }
    .chat-input-shell [data-testid="column"]:last-child {
        flex: unset !important;
        width: auto !important;
        min-width: 0 !important;
        padding-left: 0;
        padding-right: 0;
        justify-content: flex-end;
    }
    [data-testid="stFileUploader"] label,
    .chat-input-shell [data-testid="stTextArea"] label {
        display: none;
    }
    [data-testid="stFileUploader"] {
        width: 4.4rem !important;
        min-width: 4.4rem !important;
        max-width: 4.4rem !important;
        height: 3.2rem;
        min-height: 3.2rem !important;
        max-height: 3.2rem !important;
        overflow: hidden;
        border-radius: 999px;
        margin: 0;
        position: relative;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.16);
    }
    [data-testid="stFileUploader"]:before {
        content: "+";
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        color: rgba(250, 250, 250, 0.92);
        font-size: 2.15rem;
        font-weight: 300;
        line-height: 1;
        pointer-events: none;
        z-index: 2;
    }
    [data-testid="stFileUploader"] section {
        width: 4.4rem !important;
        min-width: 4.4rem !important;
        max-width: 4.4rem !important;
        height: 3.2rem !important;
        min-height: 3.2rem !important;
        max-height: 3.2rem !important;
        padding: 0 !important;
        border-radius: 999px !important;
        border: 0 !important;
        background: transparent !important;
        overflow: hidden;
    }
    [data-testid="stFileUploader"] > div,
    [data-testid="stFileUploader"] section > div,
    [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"],
    [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] {
        width: 4.4rem !important;
        min-width: 4.4rem !important;
        max-width: 4.4rem !important;
        height: 3.2rem !important;
        min-height: 3.2rem !important;
        max-height: 3.2rem !important;
        overflow: hidden !important;
        border: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
    }
    [data-testid="stFileUploader"] section > div:first-child,
    [data-testid="stFileUploader"] small,
    [data-testid="stFileUploader"] span,
    [data-testid="stFileUploader"] p,
    [data-testid="stFileUploader"] svg,
    [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] * {
        visibility: hidden !important;
        opacity: 0 !important;
        color: transparent !important;
    }
    [data-testid="stFileUploader"] button {
        width: 4.4rem;
        height: 3.2rem;
        padding: 0;
        border: 0;
        background: transparent;
        color: transparent;
        opacity: 0;
    }
    [data-testid="stFileUploader"]:hover {
        background: rgba(255, 255, 255, 0.14);
        transform: translateY(-1px);
        box-shadow: 0 10px 28px rgba(0, 0, 0, 0.28);
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) [data-testid="stTextArea"] {
        width: 100%;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) [data-testid="stTextArea"] textarea {
        height: auto !important;
        min-height: 3.2rem !important;
        max-height: 12rem;
        field-sizing: content;
        resize: none;
        border: 0 !important;
        outline: 0 !important;
        background: transparent !important;
        background-color: transparent !important;
        color: rgba(250, 250, 250, 0.95);
        padding: 0.72rem 0.85rem;
        font-size: 16px !important;
        line-height: 1.45;
        box-shadow: none !important;
        overflow-y: auto;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) [data-testid="stTextArea"] > div,
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) [data-testid="stTextArea"] > div > div,
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) [data-testid="stTextArea"] [data-baseweb="base-input"],
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) [data-testid="stTextArea"] [data-baseweb="textarea"],
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) [data-testid="stTextArea"] [data-baseweb="textarea"] > div {
        background: transparent !important;
        background-color: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) [data-testid="stTextArea"] * {
        background-color: transparent !important;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) [data-testid="stTextArea"] [data-baseweb="textarea"]:focus-within {
        background: transparent !important;
        background-color: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) [data-testid="stTextArea"] textarea:focus {
        border: 0 !important;
        box-shadow: none !important;
        background: transparent !important;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) [data-testid="InputInstructions"] {
        display: none !important;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) .stButton > button {
        position: relative;
        width: 4.4rem;
        min-width: 4.4rem;
        min-height: 3.2rem;
        border-radius: 999px;
        border: 1px solid rgba(255, 255, 255, 0.16);
        background: rgba(255, 255, 255, 0.08);
        color: rgba(250, 250, 250, 0.95);
        padding: 0 0.75rem;
        font-size: 15px !important;
        font-weight: 700;
        line-height: 1;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) .stButton > button:hover {
        background: rgba(255, 255, 255, 0.14);
        transform: translateY(-1px);
        box-shadow: 0 10px 28px rgba(0, 0, 0, 0.28);
    }
    .chat-input-helper {
        margin-top: 0.45rem;
        color: rgba(250, 250, 250, 0.5);
        font-size: 0.86rem;
    }
    .attachment-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.55rem;
        max-width: 42rem;
        margin-top: 0.75rem;
        margin-bottom: 0.35rem;
        padding: 0.45rem 0.7rem 0.45rem 0.85rem;
        border-radius: 999px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        background: rgba(255, 255, 255, 0.06);
        color: rgba(250, 250, 250, 0.9);
        font-size: 0.9rem;
        font-weight: 600;
    }
    .attachment-chip-type {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 2.8rem;
        padding: 0.16rem 0.4rem;
        border-radius: 999px;
        background: rgba(43, 108, 255, 0.22);
        color: rgba(229, 239, 255, 0.98);
        font-size: 0.68rem;
        font-weight: 800;
        letter-spacing: 0.04em;
    }
    .attachment-chip-name {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    div[data-testid="stHorizontalBlock"]:has(.attachment-chip) {
        max-width: 82rem;
        align-items: center;
        gap: 0.35rem;
        margin-top: 0.55rem;
        margin-bottom: -0.35rem;
    }
    div[data-testid="stHorizontalBlock"]:has(.attachment-chip) [data-testid="column"] {
        display: flex;
        align-items: center;
    }
    div[data-testid="stHorizontalBlock"]:has(.attachment-chip) .stButton > button {
        width: 2.1rem;
        min-width: 2.1rem;
        min-height: 2.1rem;
        padding: 0;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 800;
        color: rgba(250, 250, 250, 0.82);
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.12);
    }
    div[data-testid="stHorizontalBlock"]:has(.attachment-chip) .stButton > button:hover {
        color: white;
        background: rgba(255, 85, 105, 0.18);
        border-color: rgba(255, 85, 105, 0.32);
    }
    @media (max-width: 768px) {
        .app-corner-logo {
            float: none;
            margin-right: 0;
            margin-bottom: 0.65rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

def render_workflow_stepper() -> None:
    requirement_ready = (
        bool(st.session_state.get("requirement_input", "").strip())
        or bool(st.session_state.get("supportive_requirement_input", "").strip())
        or bool(st.session_state.get("artifact_id"))
    )
    conceptual_ready = st.session_state.get("conceptual") is not None
    update_or_approve_ready = (
        st.session_state.get("conceptual_updated", False)
        or st.session_state.get("conceptual_approved", False)
        or st.session_state.get("conceptual_status") == "approved"
        or st.session_state.get("logical") is not None
        or st.session_state.get("physical") is not None
    )
    logical_ready = st.session_state.get("logical") is not None
    physical_ready = st.session_state.get("physical") is not None
    logical_and_physical_ready = (
        st.session_state.get("conceptual_approved", False)
        or st.session_state.get("conceptual_status") == "approved"
        or logical_ready
        or physical_ready
    )

    step_completion = [
        ("Requirement", requirement_ready),
        ("Conceptual draft", conceptual_ready),
        ("Update/Approve", update_or_approve_ready),
        ("Logical & Physical", logical_and_physical_ready),
    ]

    if not requirement_ready:
        current_step = "Requirement"
    elif not conceptual_ready:
        current_step = "Conceptual draft"
    elif not logical_and_physical_ready:
        current_step = "Update/Approve"
    else:
        current_step = "Logical & Physical"

    html_parts = ["<div class='workflow-stepper-shell'><div class='workflow-stepper'>"]

    for index, (label, is_complete) in enumerate(step_completion, start=1):
        classes = ["workflow-step"]
        if is_complete:
            classes.append("completed")
        if label == current_step:
            classes.append("current")

        html_parts.append(
            f"<div class='{' '.join(classes)}'>"
            f"<span class='workflow-step-index'>{index}</span>"
            f"<span>{label}</span>"
            f"</div>"
        )
        if index < len(step_completion):
            html_parts.append("<span class='workflow-arrow'>&rarr;</span>")

    html_parts.append("</div></div><div style='clear: both;'></div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


if "app_page" not in st.session_state:
    st.session_state.app_page = "home"
if "show_project_picker" not in st.session_state:
    st.session_state.show_project_picker = False
if "selected_product" not in st.session_state or st.session_state.selected_product not in DATA_PRODUCTS:
    st.session_state.selected_product = DATA_PRODUCTS[0]

DEFAULTS = {
    "artifact_id": None,
    "conceptual_status": None,
    "conceptual": None,
    "logical": None,
    "physical": None,
    "conceptual_url": None,
    "logical_url": None,
    "physical_url": None,
    "conceptual_diagram_version": 0,
    "logical_diagram_version": 0,
    "physical_diagram_version": 0,
    "conceptual_updated": False,
    "conceptual_approved": False,
    "agent_final_answer": "",
    "brd_upload_reset": 0,
}


for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

if "current_project_id" not in st.session_state:
    st.session_state.current_project_id = None
if "current_project_name" not in st.session_state:
    st.session_state.current_project_name = None
if "current_project_from_history" not in st.session_state:
    st.session_state.current_project_from_history = False
if "project_name_input" not in st.session_state:
    st.session_state.project_name_input = ""


def reset_workflow_state() -> None:
    upload_reset = st.session_state.get("brd_upload_reset", 0) + 1
    for key, value in DEFAULTS.items():
        st.session_state[key] = value
    st.session_state.brd_upload_reset = upload_reset
    st.session_state.pop("requirement_input", None)
    st.session_state.pop("supportive_requirement_input", None)
    st.session_state.pop("conceptual_change_request", None)
    for key in list(st.session_state.keys()):
        if key.startswith("brd_upload_") and key != "brd_upload_reset":
            st.session_state.pop(key, None)


def extract_docx_text(uploaded_file) -> str:
    try:
        with zipfile.ZipFile(BytesIO(uploaded_file.getvalue())) as docx_zip:
            document_xml = docx_zip.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile) as exc:
        raise ValueError("Please upload a valid .docx Word document.") from exc

    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

    try:
        root = ET.fromstring(document_xml)
    except ET.ParseError as exc:
        raise ValueError("Could not read text from the uploaded Word document.") from exc

    paragraphs = []
    for paragraph in root.findall(".//w:p", namespace):
        text_parts = [node.text for node in paragraph.findall(".//w:t", namespace) if node.text]
        paragraph_text = "".join(text_parts).strip()
        if paragraph_text:
            paragraphs.append(paragraph_text)

    return "\n".join(paragraphs).strip()


def build_requirement_text(brd_text: str, supportive_text: str) -> str:
    sections = []
    if brd_text.strip():
        sections.append(f"BRD Document Content:\n{brd_text.strip()}")
    if supportive_text.strip():
        sections.append(f"Additional User Context:\n{supportive_text.strip()}")
    return "\n\n".join(sections).strip()


def current_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_project_repository() -> None:
    PROJECT_REPOSITORY_PATH.mkdir(parents=True, exist_ok=True)


def project_file_path(project_id: str) -> Path:
    return PROJECT_REPOSITORY_PATH / f"{project_id}.json"


def read_store_file(store_file: Path) -> dict:
    if not store_file.exists():
        return {}

    try:
        store = json.loads(store_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

    return store if isinstance(store, dict) else {}


#editd by mani
def normalize_project_for_history(project: dict) -> bool:
    changed = False
    timestamp = current_timestamp()

    if not project.get("project_id"):
        project["project_id"] = uuid.uuid4().hex
        changed = True

    if not project.get("project_name"):
        project["project_name"] = project.get("name") or f"Project {timestamp}"
        changed = True

    if not project.get("created_at"):
        project["created_at"] = project.get("updated_at") or timestamp
        changed = True

    if not project.get("updated_at"):
        project["updated_at"] = project.get("created_at") or timestamp
        changed = True

    if not isinstance(project.get("chat_history"), list):
        project["chat_history"] = []
        changed = True

    if not isinstance(project.get("state"), dict):
        project["state"] = {}
        changed = True

    state = project["state"]
    for state_key in (
        "artifact_id",
        "conceptual_url",
        "logical_url",
        "physical_url",
    ):
        if state.get(state_key) is not None:
            state[state_key] = None
            changed = True

    if not isinstance(project.get("diagram_json"), dict):
        project["diagram_json"] = diagram_json_from_state(project.get("state", {}))
        changed = True
    elif not project.get("diagram_json"):
        project["diagram_json"] = diagram_json_from_state(project.get("state", {}))
        changed = True

    for layer_data in (project.get("diagram_json") or {}).values():
        if isinstance(layer_data, dict) and layer_data.get("diagram_url") is not None:
            layer_data["diagram_url"] = None
            changed = True

    return changed


def read_project_store() -> dict:
    backend_store = read_backend_project_store()
    if backend_store is not None:
        return backend_store

    ensure_project_repository()
    projects = []
    known_project_ids = set()
    migrated_project = False

    for store_file in (PROJECT_STORE_FILE, LEGACY_PROJECT_STORE_FILE):
        store = read_store_file(store_file)
        store_projects = store.get("projects") if isinstance(store, dict) else None
        if not isinstance(store_projects, list):
            continue

        for project in store_projects:
            if not isinstance(project, dict):
                continue

            project_id = project.get("project_id")
            if not project_id:
                normalize_project_for_history(project)
                project_id = project.get("project_id")

            if project_id in known_project_ids:
                continue

            projects.append(project)
            known_project_ids.add(project_id)
            if store_file == LEGACY_PROJECT_STORE_FILE:
                migrated_project = True

    if not PROJECT_STORE_FILE.exists() and not projects:
        migrated_project = True

    for project_path in PROJECT_REPOSITORY_PATH.glob("*.json"):
        if project_path.name in {
            PROJECT_STORE_FILE.name,
            LEGACY_PROJECT_STORE_FILE.name,
        }:
            continue

        try:
            project = json.loads(project_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        project_id = project.get("project_id") if isinstance(project, dict) else None
        if project_id and project_id not in known_project_ids:
            projects.append(project)
            known_project_ids.add(project_id)
            migrated_project = True

    for project in projects:
        if not isinstance(project, dict):
            continue
        if normalize_project_for_history(project):
            migrated_project = True

    store = {
        "version": 2,
        "updated_at": current_timestamp(),
        "projects": projects,
    }
    if migrated_project or not PROJECT_STORE_FILE.exists():
        write_project_store(store)

    return store


def write_project_store(store: dict) -> None:
    if write_backend_project_store(store) is not None:
        return

    ensure_project_repository()
    store["updated_at"] = current_timestamp()
    PROJECT_STORE_FILE.write_text(
        json.dumps(store, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def read_project(project_id: str) -> dict | None:
    backend_project = read_backend_project(project_id)
    if backend_project is not None:
        return backend_project

    store = read_project_store()
    for project in store.get("projects", []):
        if project.get("project_id") == project_id:
            return project

    project_path = project_file_path(project_id)
    if not project_path.exists():
        return None

    try:
        project = json.loads(project_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

    if project.get("project_id"):
        normalize_project_for_history(project)
        store.setdefault("projects", []).append(project)
        write_project_store(store)

    return project


def write_project(project: dict) -> None:
    normalize_project_for_history(project)
    if write_backend_project(project) is not None:
        return

    store = read_project_store()
    projects = store.setdefault("projects", [])
    project_written = False

    for index, existing_project in enumerate(projects):
        if existing_project.get("project_id") == project["project_id"]:
            projects[index] = project
            project_written = True
            break

    if not project_written:
        projects.append(project)

    write_project_store(store)


def list_saved_projects() -> list[dict]:
    store = read_project_store()
    projects = [
        project
        for project in store.get("projects", [])
        if isinstance(project, dict)
        and project.get("project_id")
        and project_has_saved_content(project)
    ]

    return sorted(projects, key=lambda item: item.get("updated_at", ""), reverse=True)


def project_has_saved_content(project: dict) -> bool:
    if project.get("chat_history"):
        return True

    state = project.get("state", {})
    if isinstance(state, dict) and any(
        state.get(key) is not None
        for key in (
            "conceptual",
            "logical",
            "physical",
        )
    ):
        return True

    diagram_json = project.get("diagram_json", {})
    if isinstance(diagram_json, dict):
        return any(
            isinstance(layer_data, dict)
            and layer_data.get("model_json") is not None
            for layer_data in diagram_json.values()
        )

    return False


def create_project(project_name: str | None = None) -> dict:
    timestamp = current_timestamp()
    project_id = uuid.uuid4().hex
    name = project_name.strip() if project_name and project_name.strip() else f"Project {timestamp}"
    project = {
        "project_id": project_id,
        "project_name": name,
        "created_at": timestamp,
        "updated_at": timestamp,
        "chat_history": [],
        "state": {},
        "diagram_json": {},
    }
    write_project(project)
    return project


def export_workflow_state() -> dict:
    state = {key: st.session_state.get(key) for key in DEFAULTS}
    state["artifact_id"] = None
    state["conceptual_url"] = None
    state["logical_url"] = None
    state["physical_url"] = None
    state["requirement_input"] = st.session_state.get("requirement_input", "")
    state["supportive_requirement_input"] = st.session_state.get("supportive_requirement_input", "")
    state["conceptual_change_request"] = st.session_state.get("conceptual_change_request", "")
    return state


def export_diagram_json() -> dict:
    return {
        "conceptual": {
            "model_json": st.session_state.get("conceptual"),
            "diagram_url": None,
            "diagram_version": st.session_state.get("conceptual_diagram_version", 0),
        },
        "logical": {
            "model_json": st.session_state.get("logical"),
            "diagram_url": None,
            "diagram_version": st.session_state.get("logical_diagram_version", 0),
        },
        "physical": {
            "model_json": st.session_state.get("physical"),
            "diagram_url": None,
            "diagram_version": st.session_state.get("physical_diagram_version", 0),
        },
    }


def diagram_json_from_state(state: dict) -> dict:
    if not isinstance(state, dict):
        state = {}

    return {
        "conceptual": {
            "model_json": state.get("conceptual"),
            "diagram_url": None,
            "diagram_version": state.get("conceptual_diagram_version", 0),
        },
        "logical": {
            "model_json": state.get("logical"),
            "diagram_url": None,
            "diagram_version": state.get("logical_diagram_version", 0),
        },
        "physical": {
            "model_json": state.get("physical"),
            "diagram_url": None,
            "diagram_version": state.get("physical_diagram_version", 0),
        },
    }


def workflow_state_from_diagram_json(diagram_json: dict) -> dict:
    if not isinstance(diagram_json, dict):
        return {}

    conceptual = diagram_json.get("conceptual", {})
    logical = diagram_json.get("logical", {})
    physical = diagram_json.get("physical", {})

    return {
        "artifact_id": None,
        "conceptual": conceptual.get("model_json"),
        "logical": logical.get("model_json"),
        "physical": physical.get("model_json"),
        "conceptual_url": None,
        "logical_url": None,
        "physical_url": None,
        "conceptual_diagram_version": conceptual.get("diagram_version", 0),
        "logical_diagram_version": logical.get("diagram_version", 0),
        "physical_diagram_version": physical.get("diagram_version", 0),
    }


def load_workflow_state(state: dict) -> None:
    reset_workflow_state()

    for key, value in state.items():
        if key in DEFAULTS or key in {
            "requirement_input",
            "supportive_requirement_input",
            "conceptual_change_request",
        }:
            st.session_state[key] = value

    st.session_state.artifact_id = None


def save_current_project(
    action_label: str,
    user_message: str = "",
    assistant_message: str = "",
) -> None:
    project_id = st.session_state.get("current_project_id")
    if not project_id:
        return

    project = read_project(project_id)
    if project is None:
        project = {
            "project_id": project_id,
            "project_name": st.session_state.get("current_project_name") or "Untitled Project",
            "created_at": current_timestamp(),
            "updated_at": current_timestamp(),
            "chat_history": [],
            "state": {},
        }

    timestamp = current_timestamp()
    if user_message:
        project.setdefault("chat_history", []).append(
            {
                "timestamp": timestamp,
                "role": "user",
                "action": action_label,
                "message": user_message,
            }
        )
    if assistant_message:
        project.setdefault("chat_history", []).append(
            {
                "timestamp": timestamp,
                "role": "assistant",
                "action": action_label,
                "message": assistant_message,
            }
        )

    project["project_name"] = st.session_state.get("current_project_name") or project.get("project_name")
    project["updated_at"] = timestamp
    project["state"] = export_workflow_state()
    project["diagram_json"] = export_diagram_json()
    write_project(project)


#editd by mani
def update_current_project_name(project_name: str) -> None:
    clean_project_name = project_name.strip()
    project_id = st.session_state.get("current_project_id")

    if not clean_project_name or not project_id:
        return
    if clean_project_name == st.session_state.get("current_project_name"):
        return

    project = read_project(project_id)
    if project is None:
        return

    project["project_name"] = clean_project_name
    project["updated_at"] = current_timestamp()
    st.session_state.current_project_name = clean_project_name
    write_project(project)


def open_project(project: dict) -> None:
    st.session_state.current_project_id = project["project_id"]
    st.session_state.current_project_name = project.get("project_name", "Untitled Project")
    diagram_state = workflow_state_from_diagram_json(project.get("diagram_json", {}))
    state = {
        **(project.get("state") or {}),
        **{key: value for key, value in diagram_state.items() if value is not None},
        "artifact_id": None,
        "conceptual_url": None,
        "logical_url": None,
        "physical_url": None,
    }
    load_workflow_state(state)
    st.session_state.current_project_id = project["project_id"]
    st.session_state.current_project_name = project.get("project_name", "Untitled Project")
    st.session_state.current_project_from_history = True
    st.session_state.project_name_input = st.session_state.current_project_name
    st.session_state.app_page = "main"
    if st.session_state.get("selected_product") not in MODELING_PRODUCTS:
        st.session_state.selected_product = MODELING_PRODUCTS[0]
    st.session_state.show_project_picker = False


def start_new_project(project_name: str = "") -> None:
    reset_workflow_state()
    project = create_project(project_name)
    st.session_state.current_project_id = project["project_id"]
    st.session_state.current_project_name = project["project_name"]
    st.session_state.current_project_from_history = False
    st.session_state.project_name_input = project_name.strip()
    st.session_state.app_page = "main"
    st.session_state.selected_product = MODELING_PRODUCTS[0]
    st.session_state.show_project_picker = False


def render_project_picker(projects: list[dict]) -> None:
    st.markdown("<div class='project-picker'>", unsafe_allow_html=True)
    st.subheader("Previous Projects")

    if not projects:
        st.info("No saved projects found yet. Create a new project first.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    project_options = {
        f"{project.get('project_name', 'Untitled Project')} | Updated {project.get('updated_at', 'unknown')}": project
        for project in projects
    }
    selected_label = st.selectbox(
        "Select project",
        list(project_options.keys()),
        label_visibility="collapsed",
    )

    open_col, cancel_col = st.columns([1, 1])
    with open_col:
        if st.button("Open Selected Project", use_container_width=True):
            open_project(project_options[selected_label])
            st.rerun()

    with cancel_col:
        if st.button("Cancel", use_container_width=True):
            st.session_state.show_project_picker = False
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_home_page() -> None:
    st.markdown("<div style='height: 30vh;'></div>", unsafe_allow_html=True)
    st.markdown(
        """
        <style>
        [data-testid="column"]:has(.home-action-marker) [data-testid="stButton"] > button {
            width: 100%;
            min-height: 7rem !important;
            height: 7rem !important;
            border-radius: 1rem !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            text-align: center !important;
            white-space: normal !important;
            line-height: 1.35 !important;
            padding: 0.85rem 1rem !important;
        }
        .home-action-marker {
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    left_pad, modeling_col, da_col, right_pad = st.columns([4.2, 1.35, 1.35, 4.2])

    with modeling_col:
        st.markdown("<div class='home-action-marker'></div>", unsafe_allow_html=True)
        if st.button("Data Modeling", use_container_width=True):
            st.session_state.app_page = "landing"
            if st.session_state.get("selected_product") not in MODELING_PRODUCTS:
                st.session_state.selected_product = MODELING_PRODUCTS[0]
            st.rerun()

    with da_col:
        st.markdown("<div class='home-action-marker'></div>", unsafe_allow_html=True)
        if st.button("Digital DA", use_container_width=True):
            st.session_state.app_page = "analytics"
            st.session_state.selected_product = ANALYTICS_PRODUCT_LABEL
            st.rerun()


def render_landing_page() -> None:
    saved_projects = list_saved_projects()

    home_col, usecase_1_col, usecase_2_col, old_repo_col, docs_col = st.columns([0.7, 1, 1, 1.45, 0.8])

    with home_col:
        if st.button("Home", use_container_width=True):
            st.session_state.app_page = "home"
            st.rerun()

    with usecase_1_col:
        if st.button("Core Banking", use_container_width=True):
            start_new_project()
            st.rerun()

    with usecase_2_col:
        if st.button("Loan", use_container_width=True):
            start_new_project()
            st.rerun()

    with old_repo_col:
        if saved_projects:
            project_options = {
                f"{project.get('project_name', 'Untitled Project')} | {project.get('updated_at', 'unknown')}": project
                for project in saved_projects
            }
            selected_project_label = st.selectbox(
                "Old repo",
                ["Select old repo"] + list(project_options.keys()),
                label_visibility="collapsed",
            )
            if selected_project_label != "Select old repo":
                open_project(project_options[selected_project_label])
                st.rerun()
        else:
            st.button("Old Repo (0)", disabled=True, use_container_width=True)

    with docs_col:
        if st.button("Data Catalog", use_container_width=True):
            st.session_state.landing_notice = "Docs placeholder: add your project documentation link here."
            st.rerun()

    if st.session_state.get("landing_notice"):
        st.info(st.session_state.landing_notice)

    st.markdown("<div class='landing-section-title'>Data Modeling Flow</div>", unsafe_allow_html=True)
    card_columns = st.columns(len(LANDING_TOOL_CARDS))
    for index, card in enumerate(LANDING_TOOL_CARDS):
        with card_columns[index]:
            upcoming_class = " is-upcoming" if card["title"] == "Upcoming" else ""
            st.markdown(
                f"""
                <div class="landing-tool-card{upcoming_class}">
                    <span class="landing-tool-phase">{html.escape(card["phase"])}</span>
                    <h3>{html.escape(card["title"])}</h3>
                    <p>{html.escape(card["description"])}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if EXAMPLE_IMAGE_PATH.exists():
        encoded_example = base64.b64encode(EXAMPLE_IMAGE_PATH.read_bytes()).decode("utf-8")
        st.markdown(
            f"""
            <section class="landing-example-section">
                <div class="landing-example-frame">
                    <img src="data:image/jpeg;base64,{encoded_example}" alt="Example workflow preview" />
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("example.jpeg is not available in the project root.")

    tech_used_pills = "".join(
        f"<span class='tech-stack-pill'>{html.escape(tech)}</span>"
        for tech in TECH_USED
    )

    st.markdown(
        f"""
        <section class="tech-stack-section">
            <div class="tech-stack-list">
                <span class="tech-stack-label">Tech Stack:</span>
                {tech_used_pills}
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def api_post(payload: dict, action_label: str) -> requests.Response:
    try:
        with st.spinner(f"{action_label}..."):
            return requests.post(
                f"{API}/orchestrate",
                json=payload,
                timeout=300,
            )
    except requests.exceptions.ConnectionError:
        st.error(f"FastAPI backend is not reachable at {API}.")
        st.info("For local work, run: uvicorn api:app --reload. For Streamlit Cloud, set BACKEND_API_URL to your Render service URL.")
        st.stop()
    except Exception as exc:  # pragma: no cover - UI-only safeguard
        st.error(str(exc))
        st.stop()


def read_backend_project_store() -> dict | None:
    return HISTORY_CLIENT.get_store()


def write_backend_project_store(store: dict) -> dict | None:
    return HISTORY_CLIENT.put_store(store)


def read_backend_project(project_id: str) -> dict | None:
    return HISTORY_CLIENT.get_project(project_id)


def write_backend_project(project: dict) -> dict | None:
    return HISTORY_CLIENT.put_project(project)


#editd by mani
def build_conceptual_continuation_payload(requirement: str) -> dict:
    return {
        "artifact_id": st.session_state.artifact_id,
        "requirement": requirement,
    }


def diagram_layer_from_title(title: str) -> str:
    return title.split(" ", 1)[0].lower()


#editd by mani
def get_saved_mermaid(layer: str) -> str | None:
    model_json = st.session_state.get(layer)

    if not isinstance(model_json, dict):
        return None

    mermaid_text = model_json.get("er_diagram_mermaid")
    if isinstance(mermaid_text, str) and mermaid_text.strip():
        return mermaid_text

    return None


#editd by mani
def build_saved_mermaid_html(title: str, payload: dict, mermaid_text: str) -> str:
    payload_json = json.dumps(payload, indent=2)
    safe_mermaid_text = html.escape(mermaid_text)
    mermaid_js = json.dumps(mermaid_text)
    payload_js = json.dumps(payload_json)
    json_filename = f"{diagram_layer_from_title(title)}_model.json"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
  </script>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; background: #f7f7fb; color: #1f2937; }}
    .wrap {{ max-width: 1180px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 24px; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08); }}
    h1 {{ margin-top: 0; }}
    .toolbar {{ display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }}
    button {{ border: 0; border-radius: 8px; padding: 10px 14px; background: #0f766e; color: #ffffff; cursor: pointer; font-size: 14px; }}
    pre {{ background: #111827; color: #e5e7eb; padding: 16px; border-radius: 10px; overflow-x: auto; white-space: pre-wrap; }}
    .section {{ margin-top: 24px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>{html.escape(title)}</h1>
    <div class="toolbar">
      <button onclick="downloadMermaid()">Download .mmd</button>
      <button onclick="downloadJson()">Download JSON</button>
    </div>
    <div class="mermaid">
{safe_mermaid_text}
    </div>
    <div class="section"><h2>Mermaid Source</h2><pre id="source"></pre></div>
  </div>
  <script>
    const mermaidText = {mermaid_js};
    const modelJson = {payload_js};
    document.getElementById("source").textContent = mermaidText;
    function downloadMermaid() {{
      const blob = new Blob([mermaidText], {{ type: "text/plain;charset=utf-8" }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "er_diagram.mmd";
      link.click();
      URL.revokeObjectURL(url);
    }}
    function downloadJson() {{
      const blob = new Blob([modelJson], {{ type: "application/json;charset=utf-8" }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = {json.dumps(json_filename)};
      link.click();
      URL.revokeObjectURL(url);
    }}
  </script>
</body>
</html>"""


def show_diagram(title: str, url: str | None, height: int = 760) -> None:
    st.subheader(title)
    layer = diagram_layer_from_title(title)
    saved_mermaid = get_saved_mermaid(layer)

    if saved_mermaid:
        model_json = st.session_state.get(layer, {})
        st.components.v1.html(
            build_saved_mermaid_html(title, model_json, saved_mermaid),
            height=height,
            scrolling=True,
        )
        return

    if not url:
        st.info("Diagram is not available yet.")
        return

    if title == "Conceptual Diagram":
        version = st.session_state.conceptual_diagram_version
    elif title == "Logical Diagram":
        version = st.session_state.logical_diagram_version
    else:
        version = st.session_state.physical_diagram_version

    separator = "&" if "?" in url else "?"
    cache_busted_url = f"{url}{separator}v={version}"

    st.link_button(f"Open {title} in new tab", cache_busted_url, use_container_width=True)
    st.components.v1.iframe(cache_busted_url, height=height, scrolling=True)


def store_orchestrate_response(data: dict) -> None:
    if data.get("conceptual_artifact_id"):
        st.session_state.artifact_id = data["conceptual_artifact_id"]

    conceptual_output = data.get("conceptual_output", st.session_state.get("conceptual"))
    logical_output = data.get("logical_output", st.session_state.get("logical"))
    physical_output = data.get("physical_output", st.session_state.get("physical"))

    st.session_state.conceptual_status = data.get(
        "conceptual_status",
        st.session_state.get("conceptual_status"),
    )
    st.session_state.conceptual = conceptual_output
    st.session_state.logical = logical_output
    st.session_state.physical = physical_output
    st.session_state.conceptual_url = data.get("conceptual_view_url", st.session_state.get("conceptual_url"))
    st.session_state.logical_url = data.get("logical_view_url", st.session_state.get("logical_url"))
    st.session_state.physical_url = data.get("physical_view_url", st.session_state.get("physical_url"))
    st.session_state.agent_final_answer = data.get(
        "agent_final_answer",
        st.session_state.get("agent_final_answer", ""),
    )

    if conceptual_output and st.session_state.conceptual_url:
        st.session_state.conceptual_diagram_version += 1
    if logical_output and st.session_state.logical_url:
        st.session_state.logical_diagram_version += 1
    if physical_output and st.session_state.physical_url:
        st.session_state.physical_diagram_version += 1
    if (
        st.session_state.conceptual_status == "approved"
        or logical_output is not None
        or physical_output is not None
    ):
        st.session_state.conceptual_approved = True


if st.session_state.app_page == "home":
    render_home_page()
    st.stop()

if st.session_state.app_page == "landing":
    render_landing_page()
    st.stop()

if st.session_state.app_page == "main" and not st.session_state.current_project_id:
    start_new_project()

if st.session_state.app_page == "analytics":
    selected_product = ANALYTICS_PRODUCT_LABEL
else:
    if st.session_state.selected_product not in MODELING_PRODUCTS:
        st.session_state.selected_product = MODELING_PRODUCTS[0]
    selected_product = st.session_state.selected_product

with st.sidebar:
    back_label = "Back to Home" if st.session_state.app_page == "analytics" else "Back to Data Modeling"
    back_target = "home" if st.session_state.app_page == "analytics" else "landing"
    if st.button(back_label, use_container_width=True):
        st.session_state.app_page = back_target
        st.rerun()

    if st.session_state.app_page == "main":
        st.caption("Current Project")
        st.info(st.session_state.current_project_name or "Untitled Project")

        st.header("Data Products")
        selected_product = st.radio(
            "Data Products",
            MODELING_PRODUCTS,
            key="selected_product",
            label_visibility="collapsed",
        )

        st.divider()
        if st.button("Start New Workflow", use_container_width=True):
            start_new_project()
            st.rerun()

if st.session_state.app_page == "main":
    render_workflow_stepper()

if selected_product == "Conceptual":
    st.header("Enter Business Requirement")

    if st.session_state.get("current_project_from_history"):
        st.caption(f"Project: {st.session_state.current_project_name or 'Untitled Project'}")
    else:
        project_name_value = st.text_input(
            "Project Name",
            key="project_name_input",
            placeholder="Enter project name",
        )
        update_current_project_name(project_name_value)

    upload_key = f"brd_upload_{st.session_state.brd_upload_reset}"
    attached_brd = st.session_state.get(upload_key)

    if attached_brd is not None:
        attached_name = html.escape(getattr(attached_brd, "name", "Attached BRD document"))
        chip_col, remove_col = st.columns([7.8, 0.45])

        with chip_col:
            st.markdown(
                f"""
                <div class="attachment-chip">
                    <span class="attachment-chip-type">DOCX</span>
                    <span class="attachment-chip-name">{attached_name}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with remove_col:
            if st.button("x", key="remove_brd_attachment", help="Remove attachment"):
                st.session_state.pop(upload_key, None)
                st.session_state.brd_upload_reset += 1
                st.rerun()

    st.markdown("<div class='chat-input-shell'>", unsafe_allow_html=True)
    attach_col, text_col, action_col = st.columns([0.62, 6.4, 0.72])

    with attach_col:
        uploaded_brd = st.file_uploader(
            "Attach BRD .docx",
            type=["docx"],
            key=upload_key,
            disabled=st.session_state.artifact_id is not None,
            label_visibility="collapsed",
        )

    with text_col:
        supportive_text = st.text_area(
            "Supportive Text / Additional Requirement",
            key="supportive_requirement_input",
            placeholder="Enter/Upload your BRD document  draft.",
            height=68,
            disabled=st.session_state.artifact_id is not None,
            label_visibility="collapsed",
        )

    generate_disabled = st.session_state.artifact_id is not None
    with action_col:
        generate_clicked = st.button("Run", disabled=generate_disabled, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)
    # st.markdown(
    #     "<div class='chat-input-helper'>Use + to attach a BRD .docx. Attachment text and prompt are combined as the requirement.</div>",
    #     unsafe_allow_html=True,
    # )

    if generate_clicked:
        brd_text = ""
        if uploaded_brd is not None:
            try:
                brd_text = extract_docx_text(uploaded_brd)
            except ValueError as exc:
                st.error(str(exc))
                st.stop()

        requirement = build_requirement_text(brd_text, supportive_text)

        if not requirement:
            st.warning("Please upload a BRD document or enter supportive text.")
            st.stop()

        reset_workflow_state()
        st.session_state.requirement_input = requirement
        response = api_post(
            payload={"requirement": requirement},
            action_label="Generating conceptual draft",
        )

        if response.status_code != 200:
            st.error(response.text)
            st.stop()

        response_data = response.json()
        store_orchestrate_response(response_data)
        save_current_project(
            action_label="Generate Conceptual Draft",
            user_message=requirement,
            assistant_message=response_data.get("agent_final_answer", "Conceptual draft generated."),
        )
        st.success("Conceptual draft generated.")
        st.rerun()

    st.divider()
    st.header("Conceptual")

    if not st.session_state.conceptual:
        st.info("Generate the conceptual draft first.")
    else:
        st.subheader("Update Conceptual")
        if st.session_state.conceptual_status == "approved":
            st.success("Conceptual draft is already approved.")
        else:
            change_request = st.text_area(
                "Conceptual update request",
                key="conceptual_change_request",
                height=180,
                placeholder="Example: Create a direct connection between Loan and Customer_KYC, and add a new entity Customer_CIBIL connected to Customer_KYC.",
            )

            update_col, approve_col = st.columns(2)

            with update_col:
                if st.button("Apply Conceptual Update", use_container_width=True):
                    if not st.session_state.artifact_id:
                        st.error("No conceptual artifact found. Generate the conceptual draft first.")
                        st.stop()
                    if not change_request.strip():
                        st.warning("Please describe the conceptual update.")
                        st.stop()

                    response = api_post(
                        payload=build_conceptual_continuation_payload(change_request),
                        action_label="Updating conceptual draft",
                    )

                    if response.status_code != 200:
                        st.error(response.text)
                        st.stop()

                    response_data = response.json()
                    store_orchestrate_response(response_data)
                    st.session_state.conceptual_updated = True
                    save_current_project(
                        action_label="Update Conceptual Draft",
                        user_message=change_request,
                        assistant_message=response_data.get("agent_final_answer", "Conceptual draft updated."),
                    )
                    st.success("Conceptual draft updated.")
                    st.rerun()

            with approve_col:
                if st.button("Approve Conceptual", use_container_width=True):
                    if not st.session_state.artifact_id:
                        st.error("No conceptual artifact found. Generate the conceptual draft first.")
                        st.stop()

                    response = api_post(
                        payload=build_conceptual_continuation_payload("approve"),
                        action_label="Approving conceptual draft",
                    )

                    if response.status_code != 200:
                        st.error(response.text)
                        st.stop()

                    response_data = response.json()
                    store_orchestrate_response(response_data)
                    st.session_state.conceptual_updated = True
                    st.session_state.conceptual_approved = True
                    st.session_state.conceptual_status = "approved"
                    save_current_project(
                        action_label="Approve Conceptual Draft",
                        user_message="approve",
                        assistant_message=response_data.get(
                            "agent_final_answer",
                            "Conceptual draft approved. Logical and physical outputs generated.",
                        ),
                    )
                    st.success("Conceptual draft approved.")
                    st.rerun()

        st.divider()
        show_diagram("Conceptual Diagram", st.session_state.conceptual_url, height=900)


elif selected_product == "Logical":
    st.divider()
    st.header("Logical")

    if not st.session_state.logical:
        if st.session_state.conceptual:
            st.info("Approve the conceptual draft to generate the logical output.")
        else:
            st.info("Generate and approve the conceptual draft first.")
    else:
        show_diagram("Logical Diagram", st.session_state.logical_url, height=900)
        st.divider()
        st.success("Logical model generated successfully.")
        if st.session_state.logical_url:
            st.caption("Use the diagram to inspect tables, columns, and PK/FK structure.")


elif selected_product == "Physical":
    st.divider()
    st.header("Physical")

    if not st.session_state.physical:
        if st.session_state.conceptual:
            st.info("Approve the conceptual draft to generate the physical output.")
        else:
            st.info("Generate and approve the conceptual draft first.")
    else:
        show_diagram("Physical Diagram", st.session_state.physical_url, height=900)
        st.divider()
        st.subheader("DDL")
        ddl = None
        if isinstance(st.session_state.physical, dict):
            ddl = st.session_state.physical.get("ddl")

        if ddl:
            if isinstance(ddl, list):
                st.code("\n".join(ddl), language="sql")
            else:
                st.code(str(ddl), language="sql")
        else:
            st.info("DDL is not available yet.")

elif selected_product == ANALYTICS_PRODUCT_LABEL:

    def build_excel_from_ui(rag_results):
        output = BytesIO()

        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            summary_df = pd.DataFrame([{
                "Total Results": len(rag_results),
            }])
            summary_df.to_excel(writer, sheet_name="Summary", index=False)

            df = pd.DataFrame(rag_results)

            export_columns = [
                "attribute_name",
                "attribute_description",
                "region",
                "Layer",
                "Value Stream Name",
                "Selected Attributes",
                "Status",
                "Action",
            ]
            df = df[[column for column in export_columns if column in df.columns]]

            for internal_column in ["Relevant Matches", "Backend Answer", "Selected Match Label"]:
                if internal_column in df.columns:
                    df = df.drop(columns=[internal_column])

            df.to_excel(writer, sheet_name="Value Streams", index=False)

        output.seek(0)
        return output

    def describe_transformation(sql):
        sql_lower = sql.lower()
        descriptions = []

        if "concat_ws" in sql_lower or "concat(" in sql_lower:
            descriptions.append("Combines multiple attributes")

        if " join " in sql_lower:
            descriptions.append("Joins multiple tables")

        if "group by" in sql_lower or any(func in sql_lower for func in ["sum(", "count(", "avg(", "max(", "min("]):
            descriptions.append("Aggregates data")

        if " where " in sql_lower:
            descriptions.append("Filters records")

        if " over (" in sql_lower:
            descriptions.append("Applies window function")

        if "cast(" in sql_lower:
            descriptions.append("Converts data types")

        if "distinct" in sql_lower:
            descriptions.append("Removes duplicates")

        if not descriptions:
            return "Applies custom transformation logic"

        return ", ".join(descriptions)

    def _normalize_uploaded_column_name(column):
        return str(column).strip().lower().replace("_", " ")

    def build_requirement_query(field_name, field_definition, region):
        clean_field_name = "" if pd.isna(field_name) else str(field_name).strip()
        clean_definition = "" if pd.isna(field_definition) else str(field_definition).strip()
        clean_region = "" if pd.isna(region) else str(region).strip()

        parts = [part for part in [clean_field_name, clean_definition] if part]
        if clean_region:
            parts.append(f"Region: {clean_region}")
        if parts:
            return " | ".join(parts)
        if clean_field_name and clean_definition:
            return f"{clean_field_name} | {clean_definition}"
        if clean_field_name:
            return clean_field_name
        if clean_definition:
            return clean_definition
        return ""

    def extract_requirements_from_upload(uploaded_file):
        file_name = uploaded_file.name.lower()
        if file_name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)

        if df.empty:
            return []

        column_lookup = {_normalize_uploaded_column_name(column): column for column in df.columns}
        field_name_column = column_lookup.get("attribute name")
        field_definition_column = column_lookup.get("attribute description")
        region_column = column_lookup.get("region") or column_lookup.get("physical region")

        if field_name_column is None or field_definition_column is None or region_column is None:
            raise ValueError(
                "Uploaded file must contain attribute_name, attribute_description, and region columns."
            )

        requirements = []
        for _, row in df.iterrows():
            field_name = row.get(field_name_column, "")
            field_definition = row.get(field_definition_column, "")
            region = row.get(region_column, "") if region_column else ""
            query_text = build_requirement_query(
                field_name,
                field_definition,
                region,
            )
            if query_text:
                requirements.append({
                    "attribute_name": "" if pd.isna(field_name) else str(field_name).strip(),
                    "attribute_description": "" if pd.isna(field_definition) else str(field_definition).strip(),
                    "region": "" if pd.isna(region) else str(region).strip(),
                    "Field Name": "" if pd.isna(field_name) else str(field_name).strip(),
                    "Field Definition & Criteria": "" if pd.isna(field_definition) else str(field_definition).strip(),
                    "Region": "" if pd.isna(region) else str(region).strip(),
                    "Query": query_text,
                })
        return requirements

    def build_layer_count_summary(layer_summary):
        counts = []
        for layer_result in layer_summary or []:
            layer = layer_result.get("layer", "")
            total_attributes = layer_result.get("relevant_match_count", 0)
            if layer:
                counts.append(f"{layer}:{total_attributes}")
        return ", ".join(counts)

    def get_match_value_stream(match):
        match = match or {}
        return (
            match.get("value_stream", "")
            or match.get("entity_name", "")
            or match.get("value_stream_name", "")
        )

    def get_match_layer(match):
        match = match or {}
        return match.get("layer", "")

    def get_match_value_stream_name(match):
        match = match or {}
        return match.get("value_stream_name", "")

    def get_match_asset_name(match):
        match = match or {}
        return (
            match.get("value_stream_name", "")
            or match.get("asset_name", "")
            or match.get("value_stream", "")
            or match.get("entity_name", "")
        )

    def get_match_attribute(match):
        match = match or {}
        return (
            match.get("attribute_name", "")
            or match.get("value_stream_attribute", "")
        )

    def build_lineage_text(match):
        if not match:
            return ""

        lineage_parts = []
        lineage_details = match.get("lineage_details", []) or []
        source_description = str(match.get("source_description", "") or "").strip()
        lineage_value_streams = match.get("lineage_value_streams", []) or []
        join_keys = match.get("join_keys", []) or []

        if lineage_details:
            for detail in lineage_details:
                source = ".".join(
                    part
                    for part in [
                        str(detail.get("source_asset", "") or "").strip(),
                        str(detail.get("source_attribute", "") or "").strip(),
                    ]
                    if part
                )
                target = ".".join(
                    part
                    for part in [
                        str(detail.get("target_asset", "") or "").strip(),
                        str(detail.get("target_attribute", "") or "").strip(),
                    ]
                    if part
                )
                transformation = str(detail.get("transformation_logic", "") or "").strip()
                if source and target and transformation:
                    lineage_parts.append(f"{source} -> {target}: {transformation}")
                elif source and target:
                    lineage_parts.append(f"{source} -> {target}")
        elif source_description:
            lineage_parts.append(source_description)
        if lineage_value_streams:
            lineage_parts.append(f"Lineage value streams: {', '.join(str(value_stream) for value_stream in lineage_value_streams if value_stream)}")
        if join_keys:
            lineage_parts.append(f"Join keys: {', '.join(str(join_key) for join_key in join_keys if join_key)}")
        if not lineage_parts:
            value_stream = get_match_value_stream(match)
            if value_stream:
                lineage_parts.append(f"Origin details are available in the glossary for {value_stream}.")
        return " ".join(lineage_parts)

    def build_analytics_match_option_label(match):
        value_stream = get_match_value_stream(match) or "Unknown Value Stream"
        attribute_name = get_match_attribute(match)
        layer = get_match_layer(match)
        region = match.get("region", "")
        parts = [value_stream]
        if attribute_name:
            parts.append(attribute_name)
        if layer:
            parts.append(layer)
        if region:
            parts.append(region)
        return " | ".join(parts)

    def find_match_for_value_stream_name(relevant_matches, value_stream_name):
        for match in relevant_matches or []:
            if get_match_value_stream_name(match) == value_stream_name:
                return match
        return None

    def _first_detail_for_value_stream(details_by_value_stream, value_stream_name):
        details = (details_by_value_stream or {}).get(value_stream_name, []) or []
        return details[0] if details else None

    def get_preferred_analytics_match(data):
        selected_details = data.get("selected_details", {}) or {}
        relevant_matches = data.get("relevant_matches", []) or []
        preferred_layer = selected_details.get("preferred_layer", "")

        if preferred_layer == "GDA":
            gda_value_streams = (
                selected_details.get("gda_value_streams", [])
                or data.get("human_selection_options", [])
                or []
            )
            gda_value_stream_details = (
                selected_details.get("gda_value_stream_details", {})
                or {}
            )
            selected_value_stream = (
                selected_details.get("selected_gda_value_stream")
                or (gda_value_streams[0] if gda_value_streams else "")
            )
            selected_match = (
                _first_detail_for_value_stream(gda_value_stream_details, selected_value_stream)
                or find_match_for_value_stream_name(relevant_matches, selected_value_stream)
            )
            return preferred_layer, selected_value_stream, selected_match

        if preferred_layer == "MDA":
            mda_value_streams = selected_details.get("mda_value_streams", []) or []
            mda_value_stream_details = (
                selected_details.get("mda_value_stream_details", {})
                or {}
            )
            selected_value_stream = (
                selected_details.get("selected_mda_value_stream")
                or (mda_value_streams[0] if mda_value_streams else "")
            )
            selected_match = (
                _first_detail_for_value_stream(mda_value_stream_details, selected_value_stream)
                or find_match_for_value_stream_name(relevant_matches, selected_value_stream)
            )
            return preferred_layer, selected_value_stream, selected_match

        selected_match = relevant_matches[0] if relevant_matches else None
        return preferred_layer, get_match_value_stream_name(selected_match) if selected_match else "", selected_match

    def apply_selected_analytics_match(row, match):
        if not row or not match:
            return row

        relevant_matches = row.get("Relevant Matches") or []
        option_count = len(row.get("Human Selection Options") or []) or len(relevant_matches) or 1
        selected_attribute = get_match_attribute(match)
        value_stream = get_match_value_stream(match)
        lineage_text = build_lineage_text(match)
        row["Layer"] = get_match_layer(match)
        row["Value Stream Name"] = get_match_value_stream_name(match)
        row["Value Stream"] = value_stream
        row["Attribute"] = match.get("value_stream_attribute", "")
        row["Selected Attributes"] = selected_attribute
        row["Lineage"] = lineage_text
        row["Transformation"] = match.get("justification", "") or row.get("Transformation", "")
        row["Source"] = match.get("region", row.get("Region", "")) or "All Regions"
        row["Match Phase"] = match.get("match_phase", "")
        row["Match Score"] = round(float(match.get("phase_weight", 0.0) or 0.0), 4)
        row["Selected Match Label"] = build_analytics_match_option_label(match)
        row["Status"] = f"Available at {row['Layer']}" if row.get("Layer") else "Data is not found"
        row["Answer"] = (
            f"{option_count} value stream option(s) found. Current selection: "
            f"{match.get('value_stream_attribute', '') or selected_attribute}."
        )
        return row

    def analytics_row_from_response(requirement, data):
        relevant_matches = data.get("relevant_matches", []) or []
        preferred_layer, selected_value_stream, selected_match = get_preferred_analytics_match(data)
        if not selected_match:
            return None
        layer_summary = data.get("layer_summary", [])
        row = {
            "attribute_name": requirement.get("attribute_name", requirement.get("Field Name", "")),
            "attribute_description": requirement.get("attribute_description", requirement.get("Field Definition & Criteria", "")),
            "region": requirement.get("region", requirement.get("Region", "")),
            "Field Name": requirement.get("Field Name", ""),
            "Field Definition & Criteria": requirement.get("Field Definition & Criteria", ""),
            "Region": requirement.get("Region", ""),
            "Query": requirement.get("Query", ""),
            "Layer": "",
            "Value Stream Name": selected_value_stream,
            "Value Stream": "",
            "Attribute": "",
            "Selected Attributes": "",
            "Lineage": "",
            "Transformation": selected_match.get("justification", ""),
            "Status": f"Available at {preferred_layer}" if preferred_layer else "",
            "Answer": data.get("answer", ""),
            "Backend Answer": data.get("answer", ""),
            "Source": requirement.get("Region", "") or "All Regions",
            "Match Phase": data.get("match_phase", "") or selected_match.get("match_phase", ""),
            "Match Score": round(float(selected_match.get("phase_weight", 0.0) or 0.0), 4),
            "Layer Match Counts": build_layer_count_summary(layer_summary),
            "Relevant Matches": relevant_matches,
            "Human Selection Required": bool(data.get("human_in_loop_required", False)),
            "Human Selection Prompt": data.get("human_in_loop_prompt", ""),
            "Human Selection Options": data.get("human_selection_options", []) or [],
            "Human Value Stream Options": data.get("human_selection_options", []) or [],
            "Selected Match Label": "",
            "Action": "Decline",
            "Approved": False
        }
        return apply_selected_analytics_match(row, selected_match)

    def analytics_row_from_no_match(requirement, data=None):
        backend_data = data or {}
        return {
            "attribute_name": requirement.get("attribute_name", requirement.get("Field Name", "")),
            "attribute_description": requirement.get("attribute_description", requirement.get("Field Definition & Criteria", "")),
            "region": requirement.get("region", requirement.get("Region", "")),
            "Field Name": requirement.get("Field Name", ""),
            "Field Definition & Criteria": requirement.get("Field Definition & Criteria", ""),
            "Region": requirement.get("Region", ""),
            "Query": requirement.get("Query", ""),
            "Layer": "OUT OF SCOPE",
            "Value Stream Name": "Data is not found",
            "Value Stream": "",
            "Attribute": "",
            "Selected Attributes": "",
            "Lineage": "",
            "Transformation": "No matching value stream or attribute found in the global glossary for the supplied request.",
            "Status": "Data is not found",
            "Answer": backend_data.get("answer", "This requirement is not available in the global glossary."),
            "Backend Answer": backend_data.get("answer", "This requirement is not available in the global glossary."),
            "Source": "No Match",
            "Match Phase": "",
            "Match Score": 0.0,
            "Layer Match Counts": "",
            "Relevant Matches": backend_data.get("relevant_matches", []),
            "Human Selection Required": bool(backend_data.get("human_in_loop_required", False)),
            "Human Selection Prompt": backend_data.get("human_in_loop_prompt", ""),
            "Human Selection Options": backend_data.get("human_selection_options", []) or [],
            "Human Value Stream Options": backend_data.get("human_selection_options", []) or [],
            "Selected Match Label": "",
            "Action": "Feedback",
            "Approved": False
        }

    def analytics_is_out_of_scope(row):
        return (row or {}).get("Source") == "No Match" or (row or {}).get("Layer", "") == "OUT OF SCOPE"

    def sort_analytics_rows(rows):
        return sorted(rows, key=lambda row: 1 if analytics_is_out_of_scope(row) else 0)

    def analytics_badge_class(row):
        category = (row or {}).get("Layer", "")
        if analytics_is_out_of_scope(row) or category == "OUT OF SCOPE":
            return "out-of-scope"
        if category == "GDA":
            return "gda"
        if category == "MDA":
            return "mda"
        return "cda"

    ANALYTICS_COLUMN_WIDTHS = [1.7, 2.2, 0.9, 0.8, 1.7, 0.9, 1.4]
    ANALYTICS_COLUMN_GAP = "large"
    ANALYTICS_HEADER_LABELS = [
        "Attribute Name",
        "Description",
        "Region",
        "Layer",
        "Status",
        "Matched Attribute",
        "Action",
    ]

    def analytics_badge_text(row):
        category = (row or {}).get("Layer", "")
        if analytics_is_out_of_scope(row) or category == "OUT OF SCOPE":
            return "OUT"
        return category

    def render_analytics_text(value, classes="analytics-cell", max_chars=None):
        raw_value = "" if value is None else str(value)
        display_value = raw_value
        if max_chars and len(raw_value) > max_chars:
            display_value = raw_value[: max_chars - 1].rstrip() + "…"
        safe_value = html.escape(display_value, quote=True)
        full_value = html.escape(raw_value, quote=True)
        st.markdown(
            f'<div class="{classes}" title="{full_value}">{safe_value}</div>',
            unsafe_allow_html=True,
        )

    def render_analytics_wrapped_text(value, classes="analytics-cell", max_chars=None, title=None):
        raw_value = "" if value is None else str(value).strip()
        if not raw_value:
            raw_value = "-"
        class_names = classes
        if max_chars and len(raw_value) > max_chars:
            class_names = f"{classes} analytics-clamp"
        safe_value = html.escape(raw_value, quote=True).replace("\n", "<br />")
        full_value = html.escape(title if title is not None else raw_value, quote=True)
        st.markdown(
            f'<div class="{class_names}" title="{full_value}">{safe_value}</div>',
            unsafe_allow_html=True,
        )

    def format_match_phase_label(match_phase):
        phase = str(match_phase or "").lower()
        if "exact" in phase:
            return "Exact Match"
        if "fuzzy" in phase:
            return "Approximate Match"
        if "semantic" in phase:
            return "Semantic Match"
        return "Match Selected"

    def format_confidence_score(score):
        try:
            score_value = float(score or 0)
        except (TypeError, ValueError):
            return "-"
        if score_value <= 1:
            score_value *= 100
        return f"{round(score_value):.0f}%"

    def build_layer_availability_steps(row, selected_match=None):
        row = row or {}
        relevant_matches = row.get("Relevant Matches") or []
        selected_layer = str(row.get("Layer", "") or get_match_layer(selected_match) or "").upper()
        layer_assets = {"GDA": [], "MDA": [], "CDA": []}

        for match in relevant_matches:
            layer = str(get_match_layer(match) or "").upper()
            asset_name = get_match_asset_name(match)
            if layer in layer_assets and asset_name and asset_name not in layer_assets[layer]:
                layer_assets[layer].append(asset_name)

        if selected_layer and selected_layer not in layer_assets:
            layer_assets[selected_layer] = []

        if selected_layer and not layer_assets.get(selected_layer) and selected_match:
            selected_asset_name = get_match_asset_name(selected_match)
            if selected_asset_name:
                layer_assets[selected_layer] = [selected_asset_name]

        has_gda = bool(layer_assets.get("GDA"))
        has_mda = bool(layer_assets.get("MDA"))
        has_cda = bool(layer_assets.get("CDA"))

        if has_gda and has_mda:
            availability = "Data is available in Multiple MDA and GDA asset"
            status = "priority" if selected_layer == "GDA" else "warning"
        elif has_gda:
            availability = (
                "Data is available in Multiple GDA asset"
                if len(layer_assets["GDA"]) > 1
                else "Data is available in GDA asset"
            )
            status = "success"
        elif has_mda:
            availability = (
                "Data is available in Multiple MDA asset"
                if len(layer_assets["MDA"]) > 1
                else "Data is available in MDA asset"
            )
            status = "warning" if selected_layer == "MDA" else "success"
        elif has_cda:
            availability = (
                "Data is available in Multiple CDA asset"
                if len(layer_assets["CDA"]) > 1
                else "Data is available in CDA asset"
            )
            status = "success"
        else:
            availability = "Data is available in the selected asset"
            status = "success"

        if selected_layer == "GDA":
            decision = "Considering the GDA value_streams"
        elif selected_layer == "MDA":
            decision = "Considering the MDA value_streams"
        elif selected_layer == "CDA":
            decision = "Considering the CDA value_streams"
        else:
            decision = "Considering the selected value_streams"

        return [
            ("", availability, status),
            ("", decision, status),
        ]

    def render_mapping_flow(row, selected_match=None):
        row = row or {}
        requested_attribute = (
            row.get("attribute_name")
            or row.get("Field Name")
            or "-"
        )

        if analytics_is_out_of_scope(row) or not selected_match:
            steps = [
                ("Requested Attribute", requested_attribute, "neutral"),
                ("Glossary Search", "No matching value stream or attribute found", "warning"),
                ("Mapped To", "Out of Scope", "danger"),
                ("Next Action", "Feedback Required", "neutral"),
            ]
        else:
            matched_attribute = row.get("Selected Attributes") or get_match_attribute(selected_match) or "-"
            region = row.get("region") or row.get("Region") or selected_match.get("region") or "All Regions"
            match_phase = row.get("Match Phase") or selected_match.get("match_phase")
            match_status = "warning" if "fuzzy" in str(match_phase or "").lower() else "success"
            score = row.get("Match Score", selected_match.get("phase_weight", 0.0))

            steps = [
                ("Requested Attribute", requested_attribute, "success"),
                ("Match Type", format_match_phase_label(match_phase), match_status),
                ("Matched Attribute", matched_attribute, "success"),
                ("Business Description", "Validated", "success"),
                ("Region", f"Validated: {region}", "success"),
            ]
            steps.extend(build_layer_availability_steps(row, selected_match))
            steps.append(("Confidence Score", format_confidence_score(score), "success"))

        step_html = []
        for index, (label, value, status) in enumerate(steps):
            safe_label = html.escape(str(label), quote=True)
            safe_value = html.escape(str(value), quote=True)
            step_class = f"mapping-flow-step {status}"
            if not safe_label:
                step_class = f"{step_class} mapping-flow-step-message"
            label_html = f'<span class="mapping-flow-label">{safe_label}</span>' if safe_label else ""
            step_html.append(
                f"""
                <div class="{step_class}">
                    <span class="mapping-flow-dot"></span>
                    {label_html}
                    <span class="mapping-flow-value" title="{safe_value}">{safe_value}</span>
                    <span class="mapping-flow-step-number">{index + 1}</span>
                    <span class="mapping-flow-card-arrow">&rarr;</span>
                </div>
                """
            )

        components.html(
            f"""
            <style>
            body {{
                margin: 0;
                color: #000000;
                font-family: "Source Sans Pro", sans-serif;
            }}
            .mapping-flow-shell {{
                width: 100%;
                padding: 0.25rem 0 0.4rem;
            }}
            .mapping-flow-track {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(8.4rem, 1fr));
                gap: 0.65rem 1.25rem;
                padding: 0.2rem 0.05rem 0.35rem;
            }}
            .mapping-flow-step {{
                position: relative;
                display: grid;
                grid-template-columns: 0.65rem minmax(7rem, 11rem);
                grid-template-rows: auto auto;
                column-gap: 0.48rem;
                row-gap: 0.14rem;
                align-items: start;
                min-height: 4.25rem;
                padding: 0.6rem 1.5rem 0.62rem 0.68rem;
                border-radius: 8px;
                border: 1px solid rgba(49, 51, 63, 0.14);
                background: #ffffff;
                box-shadow: 0 8px 20px rgba(0, 0, 0, 0.06);
            }}
            .mapping-flow-step:last-child .mapping-flow-card-arrow {{
                display: none;
            }}
            .mapping-flow-step.success {{
                border-color: rgba(46, 204, 113, 0.42);
                background: rgba(46, 204, 113, 0.08);
            }}
            .mapping-flow-step.warning {{
                border-color: rgba(241, 196, 15, 0.48);
                background: rgba(241, 196, 15, 0.12);
            }}
            .mapping-flow-step.priority {{
                border-color: rgba(52, 152, 219, 0.45);
                background: rgba(52, 152, 219, 0.1);
            }}
            .mapping-flow-step.danger {{
                border-color: rgba(231, 76, 60, 0.4);
                background: rgba(231, 76, 60, 0.1);
            }}
            .mapping-flow-step.neutral {{
                border-color: rgba(49, 51, 63, 0.14);
                background: rgba(49, 51, 63, 0.04);
            }}
            .mapping-flow-dot {{
                grid-row: 1 / span 2;
                width: 0.58rem;
                height: 0.58rem;
                margin-top: 0.22rem;
                border-radius: 999px;
                background: #2ecc71;
                box-shadow: 0 0 0 0.18rem rgba(46, 204, 113, 0.18);
            }}
            .mapping-flow-step.warning .mapping-flow-dot {{
                background: #f1c40f;
                box-shadow: 0 0 0 0.18rem rgba(241, 196, 15, 0.2);
            }}
            .mapping-flow-step.priority .mapping-flow-dot {{
                background: #3498db;
                box-shadow: 0 0 0 0.18rem rgba(52, 152, 219, 0.18);
            }}
            .mapping-flow-step.danger .mapping-flow-dot {{
                background: #e74c3c;
                box-shadow: 0 0 0 0.18rem rgba(231, 76, 60, 0.16);
            }}
            .mapping-flow-step.neutral .mapping-flow-dot {{
                background: #7f8c8d;
                box-shadow: 0 0 0 0.18rem rgba(127, 140, 141, 0.16);
            }}
            .mapping-flow-label {{
                display: block;
                font-size: 0.72rem;
                font-weight: 700;
                line-height: 1.2;
                color: rgba(0, 0, 0, 0.58);
            }}
            .mapping-flow-value {{
                display: -webkit-box;
                -webkit-box-orient: vertical;
                -webkit-line-clamp: 2;
                overflow: hidden;
                font-size: 0.8rem;
                font-weight: 700;
                line-height: 1.22;
                color: #000000;
                overflow-wrap: anywhere;
                word-break: break-word;
            }}
            .mapping-flow-step-message {{
                grid-template-rows: auto;
                align-items: center;
            }}
            .mapping-flow-step-message .mapping-flow-dot {{
                grid-row: 1;
                margin-top: 0.08rem;
            }}
            .mapping-flow-step-message .mapping-flow-value {{
                -webkit-line-clamp: 2;
            }}
            .mapping-flow-step-number {{
                position: absolute;
                top: 0.35rem;
                right: 0.42rem;
                min-width: 1rem;
                height: 1rem;
                border-radius: 999px;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                background: rgba(255, 255, 255, 0.72);
                color: rgba(0, 0, 0, 0.48);
                font-size: 0.62rem;
                font-weight: 700;
            }}
            .mapping-flow-card-arrow {{
                position: absolute;
                right: -1rem;
                top: 50%;
                transform: translateY(-50%);
                color: rgba(0, 0, 0, 0.42);
                font-size: 1rem;
                font-weight: 800;
                pointer-events: none;
                z-index: 2;
            }}
            @media (max-width: 700px) {{
                .mapping-flow-track {{
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }}
            }}
            </style>
            <div class="mapping-flow-shell">
                <div class="mapping-flow-track">
                    {''.join(step_html)}
                </div>
            </div>
            """,
            height=210,
            scrolling=False,
        )

    def render_analytics_value_stream_cell(row, key_suffix):
        value_stream_options = row.get("Human Value Stream Options") or row.get("Human Selection Options") or []
        if row.get("Human Selection Required") and len(value_stream_options) > 1:
            current_value_stream = row.get("Value Stream Name", "")
            if current_value_stream not in value_stream_options:
                current_value_stream = value_stream_options[0]
            current_match = find_match_for_value_stream_name(row.get("Relevant Matches") or [], current_value_stream)
            current_lineage = build_lineage_text(current_match) if current_match else row.get("Lineage", "")
            option_lineage = []
            for option in value_stream_options:
                option_match = find_match_for_value_stream_name(row.get("Relevant Matches") or [], option)
                option_lineage_text = build_lineage_text(option_match) if option_match else ""
                if option_lineage_text:
                    option_lineage.append(f"{option}: {option_lineage_text}")
            selected_value_stream = st.selectbox(
                "Choose GDA Value Stream",
                value_stream_options,
                index=value_stream_options.index(current_value_stream),
                key=f"{key_suffix}_gda_value_stream",
                label_visibility="collapsed",
                help="\n\n".join(option_lineage) or current_lineage or row.get("Human Selection Prompt", ""),
            )
            selected_match = find_match_for_value_stream_name(row.get("Relevant Matches") or [], selected_value_stream)
            if selected_match:
                apply_selected_analytics_match(row, selected_match)
               
            return

        render_analytics_wrapped_text(
            row.get("Value Stream Name", ""),
            "value-stream-name",
            max_chars=34,
            title=row.get("Lineage", "") or row.get("Value Stream Name", ""),
        )
        selected_match = find_match_for_value_stream_name(
            row.get("Relevant Matches") or [],
            row.get("Value Stream Name", ""),
        )
        if selected_match and selected_match.get("lineage_details"):
            st.download_button(
                "Lineage Excel",
                data=build_lineage_excel([selected_match]),
                file_name=f"{row.get('Value Stream Name', 'lineage').split('.')[-1]}_lineage.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"{key_suffix}_selected_lineage_download",
                use_container_width=True,
            )

    def render_analytics_headers():
        columns = st.columns(ANALYTICS_COLUMN_WIDTHS, gap=ANALYTICS_COLUMN_GAP)
        for column, label in zip(columns, ANALYTICS_HEADER_LABELS):
            with column:
                st.markdown(
                    f'<div class="analytics-header" title="{html.escape(label, quote=True)}">{html.escape(label)}</div>',
                    unsafe_allow_html=True,
                )
        st.divider()

    def get_lineage_matches_for_row(row, relevant_matches):
        value_stream_options = row.get("Human Value Stream Options") or row.get("Human Selection Options") or []
        if value_stream_options:
            matches = [
                find_match_for_value_stream_name(relevant_matches, value_stream_name)
                for value_stream_name in value_stream_options
            ]
            return [match for match in matches if match]

        selected_match = find_match_for_value_stream_name(
            relevant_matches,
            row.get("Value Stream Name", ""),
        )
        return [selected_match] if selected_match else []

    def build_lineage_excel(lineage_matches):
        output = BytesIO()
        all_rows = []
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            for match in lineage_matches:
                value_stream_name = get_match_value_stream_name(match)
                lineage_details = match.get("lineage_details", []) or []
                if not lineage_details:
                    continue
                df = pd.DataFrame(lineage_details)
                df.to_excel(
                    writer,
                    sheet_name=value_stream_name.split(".")[-1][:31] or "Lineage",
                    index=False,
                )
                all_rows.extend(lineage_details)
            if all_rows:
                pd.DataFrame(all_rows).to_excel(writer, sheet_name="All_Lineage", index=False)
            else:
                pd.DataFrame([{"message": "No lineage details available."}]).to_excel(
                    writer,
                    sheet_name="Lineage",
                    index=False,
                )
        output.seek(0)
        return output

    def compact_value_stream_name(value_stream_name):
        value = str(value_stream_name or "").strip()
        return value.split(".")[-1] if value else "-"

    def first_lineage_detail(match):
        details = (match or {}).get("lineage_details", []) or []
        return details[0] if details else {}

    def lineage_detail_summary(match):
        detail = first_lineage_detail(match)
        if not detail:
            return build_lineage_text(match) or "Lineage details not available"

        source = ".".join(
            part
            for part in [
                str(detail.get("source_asset", "") or "").strip(),
                str(detail.get("source_attribute", "") or "").strip(),
            ]
            if part
        )
        target = ".".join(
            part
            for part in [
                str(detail.get("target_asset", "") or "").strip(),
                str(detail.get("target_attribute", "") or "").strip(),
            ]
            if part
        )
        if source and target:
            return f"{source} -> {target}"
        return build_lineage_text(match) or "Lineage details not available"

    def set_gda_value_stream(selection_key, value_stream_name):
        st.session_state[selection_key] = value_stream_name

    def get_recommended_value_stream(value_stream_options, relevant_matches):
        scored_options = []
        for index, value_stream_name in enumerate(value_stream_options or []):
            match = find_match_for_value_stream_name(relevant_matches, value_stream_name) or {}
            try:
                score = float(match.get("phase_weight", 0.0) or 0.0)
            except (TypeError, ValueError):
                score = 0.0
            scored_options.append((score, -index, value_stream_name))
        if not scored_options:
            return ""
        return max(scored_options)[2]

    def render_gda_value_stream_cards(row, relevant_matches, value_stream_options, key_suffix):
        if not value_stream_options:
            return relevant_matches[0] if relevant_matches else None

        selection_key = f"{key_suffix}_selected_gda_value_stream"
        recommended_value_stream = get_recommended_value_stream(value_stream_options, relevant_matches) or value_stream_options[0]
        current_value_stream = row.get("Value Stream Name", "")
        if current_value_stream not in value_stream_options:
            current_value_stream = recommended_value_stream
        if st.session_state.get(selection_key) not in value_stream_options:
            st.session_state[selection_key] = current_value_stream

        selected_value_stream = st.session_state[selection_key]
        st.markdown("**Compare GDA Value Streams**")

        for start in range(0, len(value_stream_options), 3):
            option_group = value_stream_options[start:start + 3]
            columns = st.columns(len(option_group), gap="medium")
            for column, option in zip(columns, option_group):
                match = find_match_for_value_stream_name(relevant_matches, option) or {}
                is_recommended = option == recommended_value_stream
                is_selected = option == selected_value_stream
                role_label = "Recommended" if is_recommended else "Alternative"
                selected_label = "Selected" if is_selected else ""
                match_type = format_match_phase_label(match.get("match_phase"))
                confidence = format_confidence_score(match.get("phase_weight", 0.0))
                matched_attribute = get_match_attribute(match) or "-"
                region = match.get("region") or row.get("region") or row.get("Region") or "All Regions"
                lineage_summary = lineage_detail_summary(match)
                transformation = first_lineage_detail(match).get("transformation_logic", "") or match.get("justification", "")

                safe_role = html.escape(role_label, quote=True)
                safe_selected = html.escape(selected_label, quote=True)
                safe_name = html.escape(compact_value_stream_name(option), quote=True)
                safe_match_type = html.escape(match_type, quote=True)
                safe_confidence = html.escape(confidence, quote=True)
                safe_attribute = html.escape(matched_attribute, quote=True)
                safe_region = html.escape(f"{region} Region Match", quote=True)
                safe_lineage = html.escape(lineage_summary, quote=True)
                safe_transformation = html.escape(transformation or "-", quote=True)
                recommendation_reason = (
                    "Highest confidence among GDA options"
                    if is_recommended
                    else "Available GDA alternative"
                )
                safe_reason = html.escape(recommendation_reason, quote=True)
                card_class = "gda-option-card selected" if is_selected else "gda-option-card"

                with column:
                    st.markdown(
                        f"""
                        <div class="{card_class}">
                            <div class="gda-option-topline">
                                <span>{safe_role}</span>
                                <span>{safe_selected}</span>
                            </div>
                            <div class="gda-option-title">{safe_name}</div>
                            <div class="gda-option-metric">
                                <span>{safe_match_type}</span>
                                <strong>{safe_confidence}</strong>
                            </div>
                            <div class="gda-option-attribute">{safe_attribute}</div>
                            <div class="gda-option-region">{safe_region}</div>
                            <div class="gda-option-lineage" title="{safe_transformation}">{safe_lineage}</div>
                            <div class="gda-option-reason">{safe_reason}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "Selected" if is_selected else "Select",
                        key=f"{key_suffix}_select_{start}_{option}",
                        on_click=set_gda_value_stream,
                        args=(selection_key, option),
                        type="primary" if is_selected else "secondary",
                        disabled=is_selected,
                        use_container_width=True,
                    ):
                        selected_value_stream = option

        return find_match_for_value_stream_name(relevant_matches, selected_value_stream) or relevant_matches[0]

    def build_lineage_comparison_rows(lineage_matches, selected_value_stream):
        rows = []
        for match in lineage_matches:
            value_stream_name = get_match_value_stream_name(match)
            lineage_details = match.get("lineage_details", []) or []
            if not lineage_details:
                rows.append({
                    "Selection": "Selected" if value_stream_name == selected_value_stream else "Alternative",
                    "Value Stream": value_stream_name,
                    "Source": "-",
                    "Target": "-",
                    "Transformation": "No lineage details available",
                })
                continue
            for detail in lineage_details:
                source = ".".join(
                    part
                    for part in [
                        str(detail.get("source_asset", "") or "").strip(),
                        str(detail.get("source_attribute", "") or "").strip(),
                    ]
                    if part
                )
                target = ".".join(
                    part
                    for part in [
                        str(detail.get("target_asset", "") or "").strip(),
                        str(detail.get("target_attribute", "") or "").strip(),
                    ]
                    if part
                )
                rows.append({
                    "Selection": "Selected" if value_stream_name == selected_value_stream else "Alternative",
                    "Value Stream": value_stream_name,
                    "Source": source or "-",
                    "Target": target or "-",
                    "Transformation": detail.get("transformation_logic", "") or "-",
                })
        return rows

    def render_analytics_full_details(row, key_suffix):
        field_name = row.get("Field Name", "Field")
        with st.expander(f"View full content: {field_name}", expanded=bool(row.get("Human Selection Required"))):
            relevant_matches = row.get("Relevant Matches") or []
            selected_match = None
            if relevant_matches:
                if row.get("Human Selection Required"):
                    value_stream_options = row.get("Human Value Stream Options") or row.get("Human Selection Options") or []
                    if not value_stream_options:
                        value_stream_options = list(dict.fromkeys(
                            get_match_value_stream_name(match)
                            for match in relevant_matches
                            if get_match_layer(match) == "GDA" and get_match_value_stream_name(match)
                        ))
                    st.info(row.get("Human Selection Prompt") or "Multiple GDA value streams are available. Compare and select the best fit.")
                    selected_match = render_gda_value_stream_cards(
                        row,
                        relevant_matches,
                        value_stream_options,
                        key_suffix,
                    )
                else:
                    option_labels = [build_analytics_match_option_label(match) for match in relevant_matches]
                    current_label = row.get("Selected Match Label") or option_labels[0]
                    if current_label not in option_labels:
                        current_label = option_labels[0]
                    st.markdown("**Choose Relevant Match**")
                    selected_label = st.selectbox(
                        "Choose Relevant Match",
                        option_labels,
                        index=option_labels.index(current_label),
                        key=f"{key_suffix}_entity_option",
                        label_visibility="collapsed",
                    )
                    selected_match = relevant_matches[option_labels.index(selected_label)]
                apply_selected_analytics_match(row, selected_match)
                #st.caption(f"{len(relevant_matches)} relevant match(es) returned for this request.")

            st.markdown("**Mapping Flow**")
            render_mapping_flow(row, selected_match)

            left, right = st.columns(2)
            with left:
                #st.markdown("**attribute_name**")
                #st.code(row.get("attribute_name", row.get("Field Name", "")) or "-", language="text")
                #st.markdown("**attribute_description**")
                #st.write(row.get("attribute_description", row.get("Field Definition & Criteria", "")) or "-")
                #st.markdown("**region**")
                #st.write(row.get("region", row.get("Region", "")) or "All Regions")
                st.markdown("**GDA/MDA Value Stream**")
                st.write(row.get("Value Stream Name", "") or "-")
                #st.markdown("**Value Stream**")
                #st.write(row.get("Value Stream", "") or "-")
                st.markdown("**Matched Attribute**")
                st.code(row.get("Selected Attributes", "") or "-", language="text")
            with right:
                #st.markdown("**Region Used**")
                #st.write(row.get("Source", "") or "-")
                st.markdown("**Match Phase**")
                st.write(format_match_phase_label(row.get("Match Phase", "")))
                #st.write(row.get("phase_type", "") or "-")

                st.markdown("**Confidence Score**")
                st.write(format_confidence_score(row.get("Match Score", "")))
                #st.markdown("**Answer**")
                #st.write(row.get("Answer", "") or "-")
                #st.markdown("**Status**")
                #st.write(row.get("Status", "") or row.get("Layer", "") or "-")
            if row.get("Layer Match Counts"):
                st.markdown("**Layer Relevant Match Counts**")
                st.write(row.get("Layer Match Counts"))

            lineage_matches = get_lineage_matches_for_row(row, relevant_matches)
            if lineage_matches:
                st.markdown("**Lineage Comparison**")
                lineage_comparison_rows = build_lineage_comparison_rows(
                    lineage_matches,
                    row.get("Value Stream Name", ""),
                )
                st.dataframe(
                    pd.DataFrame(lineage_comparison_rows),
                    use_container_width=True,
                    hide_index=True,
                )

                if any((match.get("lineage_details", []) or []) for match in lineage_matches):
                    st.download_button(
                        "Download Lineage Excel",
                        data=build_lineage_excel(lineage_matches),
                        file_name=f"{row.get('attribute_name', 'lineage')}_lineage.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key=f"{key_suffix}_lineage_download",
                    )

            if relevant_matches:
                st.markdown("**Relevant Matches**")
                relevant_df = pd.DataFrame(
                    [
                        {
                            "layer": get_match_layer(match),
                            "value_stream_name": get_match_value_stream_name(match),
                            "value_stream": get_match_value_stream(match),
                            "attribute_name": match.get("attribute_name", ""),
                            "attribute_desc": match.get("attribute_description", ""),
                            "value_stream_desc": match.get("value_stream_description", "") or match.get("entity_description", ""),
                            "lineage": build_lineage_text(match),
                            "justification": match.get("justification", ""),
                            "region": match.get("region", ""),
                            "phase": match.get("match_phase", ""),
                            "score": match.get("phase_weight", 0.0),
                        }
                        for match in relevant_matches
                    ]
                )
                st.dataframe(relevant_df, use_container_width=True, hide_index=True)

    def analytics_action_key(row_index):
        return f"analytics_action_{row_index}"

    def sync_analytics_actions_from_widgets():
        for row_index, row in enumerate(st.session_state.get("rag_results", [])):
            key = analytics_action_key(row_index)
            if key in st.session_state:
                row["Action"] = st.session_state[key]
            row["Approved"] = row.get("Action") == "Approve"

    def get_analytics_backend_status():
        try:
            response = requests.get(f"{API}/health", timeout=3)
            if response.status_code == 200:
                return "Connected"
            return f"HTTP {response.status_code}"
        except Exception:
            return "Unavailable"

    st.divider()
    st.header("Query Data Value Streams")
    # 🔹 Minimal CSS - Remove the styling that makes it look like multiple buttons
    st.markdown("""
    <style>
    div.block-container :where(h1, h2, h3, h4, h5, h6, p, span, label, div, small, code):not(.app-fixed-header-title) {
        color: #000000 !important;
    }
    div.block-container [data-testid="stMarkdownContainer"] *:not(.app-fixed-header-title),
    div.block-container [data-testid="stCaptionContainer"] *,
    div.block-container [data-testid="stExpander"] *,
    div.block-container [data-testid="stDataFrame"] *,
    div.block-container [data-baseweb="select"] * {
        color: #000000 !important;
    }
    .analytics-header {
        font-size: 0.76rem;
        font-weight: 700;
        letter-spacing: 0;
        text-transform: none;
        color: #000000;
        line-height: 1.35;
        min-height: 2.35rem;
        padding: 0 0.35rem 0.35rem 0;
        margin-bottom: 0.15rem;
        white-space: normal;
        overflow-wrap: normal;
        word-break: normal;
    }
    .analytics-cell {
        font-size: 0.9rem;
        line-height: 1.45;
        color: #000000;
        white-space: normal;
        overflow-wrap: anywhere;
        word-break: break-word;
    }
    .analytics-clamp {
        display: -webkit-box;
        -webkit-box-orient: vertical;
        -webkit-line-clamp: 4;
        overflow: hidden;
    }
    .analytics-code {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size: 0.82rem;
        line-height: 1.35;
    }
    .analytics-source {
        font-size: 0.88rem;
        color: #000000;
        white-space: nowrap;
        overflow-wrap: normal;
        word-break: normal;
    }
    .value-stream-name {
        font-weight: 600;
        font-size: 0.94rem;
        line-height: 1.4;
        color: #000000;
        white-space: normal;
        overflow-wrap: anywhere;
        word-break: break-word;
    }
    .gda-option-card {
        min-height: 15.6rem;
        padding: 0.95rem 1rem;
        border: 1px solid rgba(49, 51, 63, 0.16);
        border-radius: 8px;
        background: #ffffff;
        box-shadow: 0 8px 22px rgba(0, 0, 0, 0.06);
    }
    .gda-option-card.selected {
        border-color: rgba(52, 152, 219, 0.62);
        background: rgba(52, 152, 219, 0.08);
        box-shadow: 0 10px 24px rgba(52, 152, 219, 0.12);
    }
    .gda-option-topline {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.5rem;
        min-height: 1.25rem;
        margin-bottom: 0.35rem;
        font-size: 0.74rem;
        font-weight: 700;
        color: rgba(0, 0, 0, 0.62) !important;
    }
    .gda-option-title {
        min-height: 2.15rem;
        margin-bottom: 0.75rem;
        font-size: 0.95rem;
        font-weight: 800;
        line-height: 1.25;
        color: #000000 !important;
        overflow-wrap: anywhere;
        word-break: break-word;
    }
    .gda-option-metric {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.75rem;
        min-height: 2.2rem;
        padding: 0.48rem 0.55rem;
        margin-bottom: 0.7rem;
        border-radius: 8px;
        background: rgba(49, 51, 63, 0.05);
        font-size: 0.82rem;
        font-weight: 700;
        color: #000000 !important;
    }
    .gda-option-metric strong {
        font-size: 0.92rem;
        color: #000000 !important;
        white-space: nowrap;
    }
    .gda-option-attribute {
        min-height: 2.35rem;
        padding: 0.55rem 0.62rem;
        margin-bottom: 0.7rem;
        border-radius: 8px;
        background: rgba(49, 51, 63, 0.04);
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
        font-size: 0.84rem;
        font-weight: 700;
        color: #000000 !important;
        overflow-wrap: anywhere;
    }
    .gda-option-region {
        margin-bottom: 0.6rem;
        font-size: 0.82rem;
        font-weight: 700;
        color: #000000 !important;
    }
    .gda-option-lineage {
        display: -webkit-box;
        -webkit-box-orient: vertical;
        -webkit-line-clamp: 2;
        min-height: 2.3rem;
        overflow: hidden;
        font-size: 0.78rem;
        line-height: 1.32;
        color: rgba(0, 0, 0, 0.68) !important;
        overflow-wrap: anywhere;
        word-break: break-word;
    }
    .gda-option-reason {
        margin-top: 0.65rem;
        padding-top: 0.55rem;
        border-top: 1px solid rgba(49, 51, 63, 0.1);
        font-size: 0.76rem;
        font-weight: 700;
        line-height: 1.25;
        color: rgba(0, 0, 0, 0.62) !important;
    }
    .badge {
        padding: 0.32rem 0.75rem;
        border-radius: 999px;
        font-size: 0.74rem;
        font-weight: 600;
        display: inline-block;
        white-space: nowrap;
    }
    .gda { background: rgba(46,204,113,0.2); color: #000000; }
    .mda { background: rgba(241,196,15,0.2); color: #000000; }
    .cda { background: rgba(52,152,219,0.2); color: #000000; }
    .out-of-scope { background: rgba(231,76,60,0.18); color: #000000; }
    .mapping-flow-shell {
        width: 100%;
        overflow-x: auto;
        padding: 0.25rem 0 0.6rem;
        scrollbar-width: thin;
    }
    .mapping-flow-track {
        display: flex;
        align-items: stretch;
        gap: 0.55rem;
        min-width: max-content;
        padding: 0.2rem 0.05rem;
    }
    .mapping-flow-step {
        display: grid;
        grid-template-columns: 0.65rem minmax(7rem, 11rem);
        grid-template-rows: auto auto;
        column-gap: 0.48rem;
        row-gap: 0.14rem;
        align-items: start;
        min-width: 10.5rem;
        max-width: 13rem;
        padding: 0.68rem 0.75rem;
        border-radius: 8px;
        border: 1px solid rgba(49, 51, 63, 0.14);
        background: #ffffff;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.06);
    }
    .mapping-flow-step.success {
        border-color: rgba(46, 204, 113, 0.42);
        background: rgba(46, 204, 113, 0.08);
    }
    .mapping-flow-step.warning {
        border-color: rgba(241, 196, 15, 0.48);
        background: rgba(241, 196, 15, 0.12);
    }
    .mapping-flow-step.priority {
        border-color: rgba(52, 152, 219, 0.45);
        background: rgba(52, 152, 219, 0.1);
    }
    .mapping-flow-step.danger {
        border-color: rgba(231, 76, 60, 0.4);
        background: rgba(231, 76, 60, 0.1);
    }
    .mapping-flow-step.neutral {
        border-color: rgba(49, 51, 63, 0.14);
        background: rgba(49, 51, 63, 0.04);
    }
    .mapping-flow-dot {
        grid-row: 1 / span 2;
        width: 0.58rem;
        height: 0.58rem;
        margin-top: 0.22rem;
        border-radius: 999px;
        background: #2ecc71;
        box-shadow: 0 0 0 0.18rem rgba(46, 204, 113, 0.18);
    }
    .mapping-flow-step.warning .mapping-flow-dot {
        background: #f1c40f;
        box-shadow: 0 0 0 0.18rem rgba(241, 196, 15, 0.2);
    }
    .mapping-flow-step.priority .mapping-flow-dot {
        background: #3498db;
        box-shadow: 0 0 0 0.18rem rgba(52, 152, 219, 0.18);
    }
    .mapping-flow-step.danger .mapping-flow-dot {
        background: #e74c3c;
        box-shadow: 0 0 0 0.18rem rgba(231, 76, 60, 0.16);
    }
    .mapping-flow-step.neutral .mapping-flow-dot {
        background: #7f8c8d;
        box-shadow: 0 0 0 0.18rem rgba(127, 140, 141, 0.16);
    }
    .mapping-flow-label {
        display: block;
        font-size: 0.72rem;
        font-weight: 700;
        line-height: 1.2;
        color: rgba(0, 0, 0, 0.58) !important;
    }
    .mapping-flow-value {
        display: -webkit-box;
        -webkit-box-orient: vertical;
        -webkit-line-clamp: 2;
        overflow: hidden;
        font-size: 0.84rem;
        font-weight: 700;
        line-height: 1.22;
        color: #000000 !important;
        overflow-wrap: anywhere;
        word-break: break-word;
    }
    .mapping-flow-arrow {
        display: flex;
        align-items: center;
        justify-content: center;
        flex: 0 0 1.1rem;
        min-height: 4.25rem;
        color: rgba(0, 0, 0, 0.42) !important;
        font-size: 1.15rem;
        font-weight: 800;
    }
    div[data-testid="stButton"] > button {
        min-height: 2.35rem !important;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        border-radius: 0.8rem !important;
        padding: 0.2rem 0.6rem !important;
        white-space: nowrap !important;
    }
    div[data-baseweb="select"] > div {
        min-height: 2.35rem !important;
        border-radius: 0.8rem !important;
    }
    div[data-baseweb="select"] * {
        font-size: 0.9rem !important;
    }
    [data-testid="stFileUploader"] {
        width: 100% !important;
        min-width: 0 !important;
        max-width: none !important;
        height: auto !important;
        min-height: 0 !important;
        max-height: none !important;
        overflow: visible !important;
        border-radius: 0 !important;
        margin: 0 0 0.75rem 0 !important;
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
        transform: none !important;
    }
    [data-testid="stFileUploader"]:before {
        content: none !important;
    }
    [data-testid="stFileUploader"] label {
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        color: inherit !important;
    }
    [data-testid="stFileUploader"] section,
    [data-testid="stFileUploader"] > div,
    [data-testid="stFileUploader"] section > div,
    [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"],
    [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] {
        width: 100% !important;
        min-width: 0 !important;
        max-width: none !important;
        height: auto !important;
        min-height: 4rem !important;
        max-height: none !important;
        overflow: visible !important;
        border-radius: 8px !important;
        background: rgba(255, 255, 255, 0.02) !important;
    }
    [data-testid="stFileUploader"] section > div:first-child,
    [data-testid="stFileUploader"] small,
    [data-testid="stFileUploader"] span,
    [data-testid="stFileUploader"] p,
    [data-testid="stFileUploader"] svg,
    [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] * {
        visibility: visible !important;
        opacity: 1 !important;
        color: inherit !important;
    }
    [data-testid="stFileUploader"] button {
        width: auto !important;
        height: auto !important;
        padding: 0.35rem 0.75rem !important;
        border: 1px solid rgba(49, 51, 63, 0.2) !important;
        background: #ffffff !important;
        color: #31333f !important;
        opacity: 1 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    uploaded_query_file = st.file_uploader(
        "Upload Requirement",
        type=["xlsx", "xls", "csv"],
        help="The file must include attribute_name, attribute_description, and region columns.",
        label_visibility="visible",
        key="analytics_requirement_upload",
    )

    st.caption(
        "Upload requirement rows with attribute_name, attribute_description, and region to identify whether each attribute is available at GDA or MDA level."
    )

    uploaded_requirements = []
    if uploaded_query_file is not None:
        upload_progress = st.progress(10, text="Reading uploaded file... 10%")
        try:
            uploaded_requirements = extract_requirements_from_upload(uploaded_query_file)
            upload_progress.progress(20, text="Validating requirement columns... 20%")
            upload_progress.progress(100, text="Uploaded")
            st.session_state.no_results = False
            st.success(f"Uploaded {len(uploaded_requirements)} requirement row(s).")
        except Exception as e:
            upload_progress.empty()
            st.error(f"Could not read uploaded requirement file: {str(e)}")
            uploaded_requirements = []

    # 🔹 Process Button (Right aligned)
    process_col1, process_col2 = st.columns([5, 2])
    with process_col2:
        process_clicked = st.button(
            "Process Requirements",
            use_container_width=True,
            disabled=not uploaded_requirements,
        )

    # 🔹 Process Logic
    if process_clicked:
        if not uploaded_requirements:
            st.warning("Please upload a requirement file with at least one valid row.")
        else:
            processing_progress = st.progress(10, text="Preparing requirement rows... 10%")
            live_results_placeholder = st.empty()
            with st.spinner("Processing requirements..."):
                try:
                    results = []
                    total_requirements = len(uploaded_requirements)

                    for index, requirement in enumerate(uploaded_requirements, start=1):
                        progress_value = 20 + int((index - 1) / max(total_requirements, 1) * 70)
                        processing_progress.progress(
                            progress_value,
                            text=f"Processing row {index} of {total_requirements}..."
                        )
                        response = requests.post(
                            f"{API}/analytics",
                            json={
                                "attribute_name": requirement["attribute_name"],
                                "attribute_description": requirement["attribute_description"],
                                "region": requirement.get("region", ""),
                            },
                            timeout=60,
                        )

                        if response.status_code != 200:
                            st.error(
                                f"API Error while processing row {index}: "
                                f"{response.status_code} - {response.text}"
                            )
                            st.stop()

                        backend_data = response.json()
                        row = analytics_row_from_response(requirement, backend_data)
                        if row is None:
                            row = analytics_row_from_no_match(requirement, backend_data)
                        if row:
                            results.append(row)
                            results = sort_analytics_rows(results)
                            st.session_state.rag_results = results
                            with live_results_placeholder.container():
                                st.subheader("Suggested Data Value Streams")
                                st.caption(f"{len(results)} of {total_requirements} row(s) processed")
                                render_analytics_headers()

                                for preview_index, preview_row in enumerate(results):
                                    key_prefix = f"live_{index}_{preview_index}"
                                    r1, r2, r3, r4, r5, r6, r7 = st.columns(
                                        ANALYTICS_COLUMN_WIDTHS,
                                        gap=ANALYTICS_COLUMN_GAP,
                                    )
                                    with r1:
                                        render_analytics_wrapped_text(preview_row.get("attribute_name", ""), "analytics-cell analytics-code", max_chars=26)
                                    with r2:
                                        render_analytics_wrapped_text(preview_row.get("attribute_description", ""), "analytics-cell", max_chars=95)
                                    with r3:
                                        render_analytics_wrapped_text(preview_row.get("region", "All Regions"), "analytics-cell analytics-source", max_chars=16)
                                    with r4:
                                        st.markdown(f'<span class="badge {analytics_badge_class(preview_row)}">{analytics_badge_text(preview_row)}</span>', unsafe_allow_html=True)
                                    with r5:
                                        render_analytics_value_stream_cell(preview_row, f"{key_prefix}_value_stream")
                                    with r6:
                                        render_analytics_wrapped_text(preview_row.get("Selected Attributes", ""), "analytics-cell analytics-code", max_chars=58)
                                    with r7:
                                        selected_action = st.selectbox(
                                            "Action",
                                            ["Approve", "Decline", "Feedback"],
                                            index=1,
                                            key=f"{key_prefix}_action",
                                            label_visibility="collapsed",
                                        )
                                        st.session_state.rag_results[preview_index]["Action"] = selected_action
                                        st.session_state.rag_results[preview_index]["Approved"] = selected_action == "Approve"
                                    render_analytics_full_details(preview_row, f"{key_prefix}_details")

                    processing_progress.progress(95, text="Building frontend result table... 95%")
                    live_results_placeholder.empty()
                    st.session_state.analytics_output_json_path = ""
                    
                    keys_to_delete = [
                        k for k in st.session_state.keys()
                        if k.startswith("approve_") or k.startswith("action_") or k.startswith("analytics_action_")
                    ]
                    for k in keys_to_delete:
                        del st.session_state[k]                        

                    st.session_state.rag_results = results

                    if results:
                        st.session_state.rag_results = sort_analytics_rows(results)
                        st.session_state.no_results = False
                        processing_progress.progress(100, text="Processing complete")
                        #st.success(f"Found {len(results)} matching value stream(s)")
                    else:
                        processing_progress.empty()
                        st.warning("No matching value streams found for your query")
                        st.session_state.no_results = True
                        st.rerun()
                    
                except requests.exceptions.Timeout:
                    processing_progress.empty()
                    st.error("Request timed out. Please try again.")
                except requests.exceptions.ConnectionError:
                    processing_progress.empty()
                    st.error(f"Cannot connect to API at {API}")
                except Exception as e:
                    processing_progress.empty()
                    st.error(f"Error: {str(e)}")

    if st.session_state.get("no_results", False):
        st.warning("No matching value streams found. Please upload a revised requirement file.")

    if "rag_results" in st.session_state and st.session_state.rag_results:
        sync_analytics_actions_from_widgets()
        st.subheader("Suggested Data Value Streams")
        total = len(st.session_state.rag_results)
        approved = sum(1 for r in st.session_state.rag_results if r.get("Action") == "Approve")
        st.caption(f"{total} suggestions • {approved} approved")
        if st.session_state.get("analytics_output_json_path"):
            st.caption(f"Backend JSON saved at {st.session_state.analytics_output_json_path}")

        render_analytics_headers()

        # 🔹 Data Rows
        for idx, row in enumerate(st.session_state.rag_results):
            unique_id = f"{row.get('Value Stream Name', '')}_{idx}"
            key_action = analytics_action_key(idx)
            badge_class = analytics_badge_class(row)

            c1, c2, c3, c4, c5, c6, c7 = st.columns(
                ANALYTICS_COLUMN_WIDTHS,
                gap=ANALYTICS_COLUMN_GAP,
            )

            with c1:
                render_analytics_wrapped_text(row.get("attribute_name", ""), "analytics-cell analytics-code", max_chars=26)

            with c2:
                render_analytics_wrapped_text(row.get("attribute_description", ""), "analytics-cell", max_chars=95)

            with c3:
                render_analytics_wrapped_text(row.get("region", "All Regions"), "analytics-cell analytics-source", max_chars=16)

            with c4:
                st.markdown(f'<span class="badge {badge_class}">{analytics_badge_text(row)}</span>', unsafe_allow_html=True)

            with c5:
                #render_analytics_value_stream_cell(row, f"final_{idx}_value_stream")
                if len(row["Selected Attributes"]) > 1:
                    st.markdown("Multiple matches found")
                else:
                    st.markdown("Single match found")

            with c6:
                render_analytics_wrapped_text(row["Selected Attributes"], "analytics-cell analytics-code", max_chars=58)

            with c7:
                current_action = row.get("Action") or ("Approve" if row.get("Approved") else "Decline")
                selected_action = st.selectbox(
                    "Action",
                    ["Approve", "Decline", "Feedback"],
                    index=["Approve", "Decline", "Feedback"].index(current_action)
                    if current_action in {"Approve", "Decline", "Feedback"}
                    else 0,
                    key=key_action,
                    label_visibility="collapsed",
                )
                st.session_state.rag_results[idx]["Action"] = selected_action
                st.session_state.rag_results[idx]["Approved"] = selected_action == "Approve"

            render_analytics_full_details(row, f"final_{idx}")
           
        st.markdown(" ")

        col1, col2 = st.columns([6, 1])  # right align
        
        with col2:
            approved_rows = [r for r in st.session_state.rag_results if r.get("Action") == "Approve"]
            if approved_rows:
                excel_file = build_excel_from_ui(approved_rows)
                st.download_button(
                    label="📥 Download Excel",
                    data=excel_file,
                    file_name="analytics_plan.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )


elif selected_product == "Ontology":
    st.divider()
    st.header("Ontology")
    st.info("Ontology workflow is not added yet.")


elif selected_product == "Dimensional Modeling":
    st.divider()
    st.header("Dimensional Modeling")
    st.info("Dimensional Modeling workflow is not added yet.")
