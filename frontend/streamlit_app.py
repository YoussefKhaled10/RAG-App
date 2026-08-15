import json
import os
import re
import time
from html import escape
from typing import Any
from urllib.parse import quote

import requests
import streamlit as st


API_URL = os.getenv("RAG_API_URL", "http://127.0.0.1:8000").rstrip("/")
REQUEST_TIMEOUT = 60

st.set_page_config(
    page_title="NexaDocs AI",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Space+Grotesk:wght@600;700&display=swap');

:root {
  --ink: #111827;
  --navy: #07111f;
  --panel: #0d1b2e;
  --primary: #6d5dfc;
  --primary-dark: #5546ea;
  --cyan: #19c7d8;
  --surface: #ffffff;
  --soft: #f5f7fb;
  --line: #e5e9f2;
  --muted: #667085;
  --success: #079669;
  --danger: #dc3545;
  --warning: #d97706;
  --shadow-sm: 0 8px 24px rgba(16, 24, 40, .055);
  --shadow-lg: 0 24px 70px rgba(16, 24, 40, .13);
}

html, body, [class*="css"] {font-family: 'Manrope', sans-serif;}
html {scroll-behavior:smooth;}
.stApp {
  color:var(--ink);
  background:
    radial-gradient(circle at 78% -10%, rgba(109,93,252,.10), transparent 27%),
    radial-gradient(circle at 15% 45%, rgba(25,199,216,.055), transparent 23%),
    #f7f8fc;
}
.block-container {max-width:1320px; padding:1.55rem 2.2rem 5rem;}

/* Sidebar */
[data-testid="stSidebar"] {
  background:
    radial-gradient(circle at 10% 0%, rgba(109,93,252,.28), transparent 27%),
    linear-gradient(180deg, #081321 0%, #0b1728 55%, #07111f 100%);
  border-right:1px solid rgba(255,255,255,.055);
}
[data-testid="stSidebar"] > div:first-child {padding-top:1.2rem;}
[data-testid="stSidebar"] * {color:#edf3fc;}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {color:#afbdd0;}
[data-testid="stSidebar"] hr {border-color:rgba(255,255,255,.09); margin:.7rem 0;}
[data-testid="stSidebar"] [role="radiogroup"] {gap:.28rem;}
[data-testid="stSidebar"] [role="radiogroup"] label {
  padding:.62rem .72rem;
  border:1px solid transparent;
  border-radius:12px;
  min-height:2.7rem;
  transition:all .18s ease;
}
[data-testid="stSidebar"] [role="radiogroup"] label:hover {
  background:rgba(255,255,255,.065);
  border-color:rgba(255,255,255,.06);
  transform:translateX(2px);
}
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
  background:linear-gradient(90deg, rgba(109,93,252,.30), rgba(109,93,252,.12));
  border-color:rgba(148,134,255,.33);
  box-shadow:inset 3px 0 0 #8b7dff;
}
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
  color:#7f90a8; font-size:.68rem; font-weight:800; letter-spacing:.09em; text-transform:uppercase;
}
[data-testid="stSidebar"] .stButton button {
  border:1px solid rgba(255,255,255,.13);
  background:rgba(255,255,255,.055);
  color:#fff;
  box-shadow:none;
}
[data-testid="stSidebar"] .stButton button:hover {background:rgba(255,255,255,.1); border-color:rgba(255,255,255,.22);}
[data-testid="stSidebar"] .stTextInput input {
  background:rgba(255,255,255,.055);
  color:#fff;
  border-color:rgba(255,255,255,.12);
}
[data-testid="stSidebar"] [data-testid="stExpander"] {background:rgba(255,255,255,.04); border-color:rgba(255,255,255,.09); box-shadow:none;}
[data-testid="stSidebar"] [data-testid="stExpander"] details summary:hover {background:rgba(255,255,255,.055);}

.brand {display:flex; align-items:center; gap:.78rem; margin:.1rem 0 1.15rem; padding:.25rem .1rem;}
.brand-mark {
  width:44px; height:44px; border-radius:14px; display:grid; place-items:center;
  background:linear-gradient(145deg,#8b7dff 0%,#6d5dfc 45%,#19c7d8 120%);
  box-shadow:0 12px 30px rgba(109,93,252,.35), inset 0 1px 0 rgba(255,255,255,.35);
  position:relative;
}
.brand-mark:before {content:'✦'; font-size:1.18rem; color:white; filter:drop-shadow(0 2px 5px rgba(0,0,0,.2));}
.brand-name {font-family:'Space Grotesk',sans-serif; font-size:1.08rem; font-weight:700; color:#fff; line-height:1.1; letter-spacing:-.02em;}
.brand-sub {font-size:.67rem; color:#8294ae; margin-top:.23rem; letter-spacing:.055em; text-transform:uppercase;}
.workspace-card {
  padding:.9rem; border:1px solid rgba(255,255,255,.09); border-radius:14px;
  background:linear-gradient(145deg,rgba(255,255,255,.075),rgba(255,255,255,.025));
  box-shadow:inset 0 1px 0 rgba(255,255,255,.04); margin-bottom:.95rem;
}
.workspace-kicker {font-size:.61rem; text-transform:uppercase; letter-spacing:.13em; color:#7589a5; font-weight:800;}
.workspace-name {font-weight:800; margin-top:.32rem; color:#fff; font-size:.89rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}
.workspace-meta {font-size:.7rem; color:#9fb0c7; margin-top:.22rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;}

/* Page structure */
.page-header {display:flex; justify-content:space-between; align-items:flex-end; gap:1rem; margin:.25rem 0 1.35rem;}
.page-eyebrow {font-size:.67rem; font-weight:800; color:var(--primary); letter-spacing:.13em; text-transform:uppercase; margin-bottom:.3rem;}
.page-title {font-family:'Space Grotesk',sans-serif; font-size:2rem; font-weight:700; color:var(--navy); letter-spacing:-.045em; line-height:1.12;}
.page-subtitle {color:var(--muted); margin-top:.38rem; font-size:.9rem; max-width:780px; line-height:1.55;}
.badge {
  display:inline-flex; align-items:center; gap:.42rem; padding:.42rem .72rem; border-radius:999px;
  background:#ecfdf5; color:#067857; border:1px solid #c8f1df; font-size:.7rem; font-weight:800;
  box-shadow:0 4px 12px rgba(7,150,105,.08); white-space:nowrap;
}
.badge:before {content:''; width:7px; height:7px; background:#12b981; border-radius:50%; box-shadow:0 0 0 4px rgba(18,185,129,.12);}

.hero {
  position:relative; overflow:hidden; padding:1.5rem 1.65rem; border-radius:22px;
  background:
    radial-gradient(circle at 88% 12%,rgba(25,199,216,.33),transparent 25%),
    radial-gradient(circle at 70% 130%,rgba(109,93,252,.48),transparent 40%),
    linear-gradient(135deg,#07111f 0%,#102441 58%,#142d4d 100%);
  color:white; box-shadow:0 22px 52px rgba(7,17,31,.17); margin-bottom:1.25rem;
  border:1px solid rgba(255,255,255,.08);
}
.hero:after {content:''; position:absolute; width:220px; height:220px; border:1px solid rgba(255,255,255,.08); border-radius:50%; right:-75px; top:-100px; box-shadow:0 0 0 34px rgba(255,255,255,.025),0 0 0 70px rgba(255,255,255,.018);}
.hero h2 {font-family:'Space Grotesk',sans-serif; margin:0; font-size:1.48rem; color:#fff; letter-spacing:-.03em; position:relative; z-index:1;}
.hero p {margin:.45rem 0 0; color:#b9cae0; font-size:.86rem; max-width:760px; line-height:1.6; position:relative; z-index:1;}
.hero-kicker {font-size:.64rem; font-weight:800; text-transform:uppercase; letter-spacing:.12em; color:#80e8f2; margin-bottom:.45rem; position:relative; z-index:1;}

.section-heading {display:flex; align-items:center; justify-content:space-between; gap:1rem; margin:1.5rem 0 .75rem;}
.section-title {font-family:'Space Grotesk',sans-serif; font-size:1.02rem; font-weight:700; color:var(--navy);}
.section-meta {font-size:.72rem; color:var(--muted);}
.card {
  background:rgba(255,255,255,.92); border:1px solid var(--line); border-radius:17px;
  padding:1.05rem 1.1rem; box-shadow:var(--shadow-sm); transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease;
}
.card:hover {transform:translateY(-2px); box-shadow:0 14px 36px rgba(16,24,40,.085); border-color:#d9d5ff;}
.project-card {display:flex; align-items:center; gap:.85rem;}
.project-icon {width:42px; height:42px; flex:0 0 42px; display:grid; place-items:center; border-radius:13px; background:linear-gradient(145deg,#eeeaff,#e8f9fb); color:var(--primary); font-size:1.05rem;}
.project-name {font-weight:800; color:#182033; font-size:.9rem;}
.small-muted {font-size:.73rem; line-height:1.5; color:var(--muted); margin-top:.18rem;}

.metric-card {
  position:relative; overflow:hidden; min-height:128px; background:rgba(255,255,255,.93);
  border:1px solid var(--line); border-radius:18px; padding:1.08rem 1.12rem;
  box-shadow:var(--shadow-sm); transition:transform .18s ease,box-shadow .18s ease;
}
.metric-card:hover {transform:translateY(-3px); box-shadow:0 16px 38px rgba(16,24,40,.09);}
.metric-card:after {content:''; position:absolute; width:70px; height:70px; border-radius:50%; right:-27px; top:-27px; background:rgba(109,93,252,.08);}
.metric-top {display:flex; align-items:center; justify-content:space-between; gap:.5rem;}
.metric-icon {width:34px; height:34px; display:grid; place-items:center; border-radius:10px; background:#f0edff; color:var(--primary); font-size:.9rem;}
.metric-label {font-size:.65rem; color:#7b8495; text-transform:uppercase; letter-spacing:.09em; font-weight:800;}
.metric-value {font-family:'Space Grotesk',sans-serif; font-size:1.65rem; line-height:1; font-weight:700; color:var(--navy); margin-top:.72rem; letter-spacing:-.035em;}
.metric-note {font-size:.69rem; color:var(--muted); margin-top:.32rem;}

/* Forms and native widgets */
[data-testid="stForm"] {background:rgba(255,255,255,.94); border:1px solid var(--line); border-radius:18px; padding:1.15rem; box-shadow:var(--shadow-sm);}
.stButton button {
  border-radius:11px; font-weight:800; min-height:2.65rem; border:1px solid #dbe0eb;
  box-shadow:0 4px 12px rgba(16,24,40,.045); transition:all .16s ease;
}
.stButton button:hover {border-color:#bdb5ff; color:var(--primary-dark); transform:translateY(-1px); box-shadow:0 8px 18px rgba(16,24,40,.08);}
.stButton button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] {
  color:#fff; background:linear-gradient(135deg,#7767ff,#5c4bec); border:0;
  box-shadow:0 9px 24px rgba(109,93,252,.23);
}
.stButton button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] button[kind="primary"]:hover {color:#fff; box-shadow:0 13px 28px rgba(109,93,252,.31);}
.stTextInput input, .stTextArea textarea, .stNumberInput input, .stSelectbox [data-baseweb="select"] {
  border-radius:11px; border-color:#dfe3ec; background:#fff; transition:border-color .15s ease,box-shadow .15s ease;
}
.stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus {border-color:#8f82ff; box-shadow:0 0 0 3px rgba(109,93,252,.11);}
[data-testid="stFileUploader"] {padding:1.25rem; border:1px dashed #bcb4ff; border-radius:17px; background:linear-gradient(145deg,#fbfaff,#f7fbff);}
[data-testid="stFileUploaderDropzone"] {background:transparent; border:0;}
[data-testid="stExpander"] {background:rgba(255,255,255,.94); border:1px solid var(--line); border-radius:15px; overflow:hidden; box-shadow:0 5px 18px rgba(16,24,40,.035);}
[data-testid="stExpander"] details summary:hover {background:#fafaff;}
[data-testid="stMetric"] {background:#fff; border:1px solid var(--line); border-radius:14px; padding:.85rem .95rem; box-shadow:0 5px 18px rgba(16,24,40,.035);}
[data-testid="stMetricValue"] {font-family:'Space Grotesk',sans-serif; color:var(--navy);}
[data-testid="stTabs"] [data-baseweb="tab-list"] {gap:.3rem; background:#f1f3f8; border-radius:12px; padding:.3rem;}
[data-testid="stTabs"] [data-baseweb="tab"] {border-radius:9px; padding:.45rem .8rem;}
[data-testid="stTabs"] [aria-selected="true"] {background:#fff; box-shadow:0 3px 12px rgba(16,24,40,.08); color:var(--primary);}
[data-testid="stAlert"] {border-radius:14px; border-width:1px;}

/* Authentication */
.auth-visual {
  min-height:625px; position:relative; overflow:hidden; padding:2.35rem; border-radius:26px;
  background:
    radial-gradient(circle at 82% 15%,rgba(25,199,216,.37),transparent 27%),
    radial-gradient(circle at 40% 110%,rgba(109,93,252,.64),transparent 44%),
    linear-gradient(145deg,#07111f,#112a49);
  color:white; box-shadow:var(--shadow-lg); border:1px solid rgba(255,255,255,.08);
}
.auth-logo {display:inline-flex; align-items:center; gap:.65rem; font-family:'Space Grotesk',sans-serif; font-size:.95rem; font-weight:700;}
.auth-logo-mark {width:34px; height:34px; display:grid; place-items:center; border-radius:11px; background:linear-gradient(145deg,#8b7dff,#19c7d8);}
.auth-headline {font-family:'Space Grotesk',sans-serif; font-size:2.65rem; line-height:1.08; letter-spacing:-.055em; margin-top:4.7rem; max-width:480px;}
.auth-copy {color:#b7c8dd; font-size:.9rem; line-height:1.7; max-width:480px; margin-top:1rem;}
.auth-feature {display:flex; align-items:flex-start; gap:.7rem; margin-top:1rem; color:#d8e3f1; font-size:.79rem;}
.auth-feature-icon {width:27px; height:27px; flex:0 0 27px; display:grid; place-items:center; border-radius:8px; background:rgba(255,255,255,.09); color:#82eef5;}
.auth-proof {position:absolute; left:2.35rem; right:2.35rem; bottom:2rem; display:flex; justify-content:space-between; gap:.7rem; color:#8397b1; font-size:.67rem; text-transform:uppercase; letter-spacing:.09em;}
.auth-panel {padding:1.25rem .7rem 0;}
.auth-panel-kicker {font-size:.68rem; color:var(--primary); font-weight:800; letter-spacing:.12em; text-transform:uppercase;}
.auth-panel-title {font-family:'Space Grotesk',sans-serif; font-size:1.8rem; color:var(--navy); letter-spacing:-.04em; margin:.35rem 0 .2rem;}
.auth-panel-copy {font-size:.82rem; color:var(--muted); margin-bottom:1.2rem;}

/* Chat */
.chat-shell {background:rgba(255,255,255,.95); border:1px solid var(--line); border-radius:21px; padding:.55rem 1.05rem 1.1rem; box-shadow:0 15px 44px rgba(16,24,40,.07);}
[data-testid="stChatMessage"] {border:1px solid #e7eaf2; border-radius:17px; padding:.78rem .9rem; background:#fff; margin:.62rem 0; box-shadow:0 4px 15px rgba(16,24,40,.035);}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {background:linear-gradient(145deg,#f4f1ff,#f7f9ff); border-color:#ddd7ff;}
[data-testid="stChatMessage"] [data-testid="stChatMessageAvatarUser"] {background:#6d5dfc;}
[data-testid="stChatInput"] {border-radius:15px; border-color:#dcd7ff; box-shadow:0 12px 34px rgba(16,24,40,.09);}
.citation-card {display:flex; gap:.7rem; align-items:flex-start; padding:.7rem .78rem; margin:.45rem 0; border:1px solid #e2e5ee; border-radius:12px; background:linear-gradient(145deg,#fafaff,#f7fbff);}
.citation-icon {width:32px;height:32px;flex:0 0 32px;border-radius:9px;display:grid;place-items:center;background:#ebe8ff;color:var(--primary);}
.citation-name {font-weight:800;color:#26344a;font-size:.82rem;}
.citation-meta {font-size:.71rem;color:#6f7b8d;margin-top:.12rem;}
.file-status {display:inline-block;padding:.22rem .55rem;border-radius:999px;background:#ecfdf5;color:#067857;font-size:.68rem;font-weight:800;}

/* Details, account and API */
.account-profile {display:flex; align-items:center; gap:1rem; padding:1.35rem; background:linear-gradient(135deg,#07111f,#163656); color:white; border-radius:20px; box-shadow:0 17px 45px rgba(7,17,31,.16); margin-bottom:1rem;}
.account-avatar {width:58px; height:58px; border-radius:17px; display:grid; place-items:center; font-family:'Space Grotesk',sans-serif; font-size:1.35rem; font-weight:700; background:linear-gradient(135deg,#806fff,#19c7d8); box-shadow:0 10px 26px rgba(109,93,252,.28);}
.account-name {font-size:1.08rem; font-weight:800; color:white;}
.account-email {font-size:.78rem; color:#b9c9dc; margin-top:.2rem;}
.detail-grid {display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.8rem; margin-top:.8rem;}
.detail-card {padding:.95rem 1rem; background:rgba(255,255,255,.95); border:1px solid var(--line); border-radius:14px; box-shadow:0 6px 22px rgba(16,24,40,.04);}
.detail-label {color:#7c8493; font-size:.64rem; font-weight:800; text-transform:uppercase; letter-spacing:.09em;}
.detail-value {color:#192235; font-size:.91rem; font-weight:750; margin-top:.3rem; word-break:break-word;}
.status-pill {display:inline-flex; padding:.23rem .57rem; border-radius:999px; background:#ecfdf5; color:#067857; font-size:.7rem; font-weight:800;}
.role-pill {display:inline-flex; padding:.27rem .6rem; margin:.16rem .24rem .16rem 0; border:1px solid #ddd8ff; border-radius:999px; background:#f2f0ff; color:#5c4bec; font-size:.69rem; font-weight:800;}
.api-summary {display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:.92rem 1rem; margin:.5rem 0; border:1px solid var(--line); border-radius:14px; background:rgba(255,255,255,.94); box-shadow:0 5px 18px rgba(16,24,40,.035); transition:transform .15s ease,border-color .15s ease;}
.api-summary:hover {transform:translateX(3px); border-color:#d8d2ff;}
.api-method {display:inline-flex; min-width:60px; justify-content:center; padding:.27rem .5rem; border-radius:8px; color:white; font-size:.65rem; font-weight:800; letter-spacing:.04em;}
.api-get {background:#079669;}.api-post {background:#6657eb;}.api-patch {background:#d97706;}.api-put {background:#7c3aed;}.api-delete {background:#dc3545;}
.api-path {font-family:'Space Grotesk',monospace; color:#192235; font-size:.8rem; font-weight:700; word-break:break-all;}
.api-description {color:#6e788a; font-size:.72rem; margin-top:.16rem;}
.api-count {display:inline-flex; padding:.27rem .58rem; border-radius:999px; background:#f0eeff; color:#5b4bec; font-size:.69rem; font-weight:800;}

#MainMenu, footer {visibility:hidden;}
header[data-testid="stHeader"] {background:transparent;}
[data-testid="stDecoration"] {background:linear-gradient(90deg,#6d5dfc,#19c7d8); height:2px;}

@media (max-width: 900px) {
  .block-container {padding:1.2rem 1.15rem 4rem;}
  .auth-visual {min-height:430px; padding:1.6rem;}
  .auth-headline {font-size:2rem; margin-top:2.8rem;}
  .auth-proof {left:1.6rem; right:1.6rem;}
}
@media (max-width: 720px) {
  .page-header {align-items:flex-start; flex-direction:column;}
  .page-title {font-size:1.65rem;}
  .detail-grid {grid-template-columns:1fr;}
  .hero {padding:1.25rem; border-radius:18px;}
  .metric-card {min-height:116px;}
  .auth-visual {min-height:390px;}
  .auth-headline {font-size:1.7rem;}
}
</style>
""",
    unsafe_allow_html=True,
)


SENSITIVE_UI_FIELDS = {
    "password",
    "password_hash",
    "encrypted_password",
    "access_token",
    "refresh_token",
    "token",
    "secret",
    "api_key",
    "tenant_settings",
}

TECHNICAL_UI_FIELDS = {
    "user_id",
    "tenant_id",
    "asset_uuid",
    "project_uuid",
    "chunk_uuid",
    "execution_id",
    "celery_task_id",
    "task_args_hash",
}


def _friendly_label(key: str) -> str:
    aliases = {
        "user_email": "Email",
        "user_full_name": "Full name",
        "user_status": "Account status",
        "tenant_name": "Workspace",
        "tenant_status": "Workspace status",
        "project_name": "Project",
        "project_description": "Description",
        "asset_name": "File name",
        "asset_status": "Processing status",
        "asset_size": "File size",
        "asset_indexed_chunks": "Indexed chunks",
        "created_at": "Created",
        "updated_at": "Last updated",
        "last_login_at": "Last sign in",
        "task_id": "Task ID",
        "status": "Status",
        "ready": "Ready",
        "successful": "Successful",
        "error": "Error",
        "error_message": "Error message",
        "result": "Result",
        "roles": "Access roles",
        "permissions": "Permissions",
    }
    return aliases.get(
        str(key),
        str(key).replace("_", " ").strip().title(),
    )


def _friendly_value(value: Any) -> str:
    if value is None:
        return "Not available"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        return f"{value:.4f}"
    if isinstance(value, str):
        clean = value.replace("T", " ").replace("Z", " UTC")
        if len(clean) > 180:
            clean = clean[:177] + "..."
        return clean
    return str(value)


def _visible_items(data: dict) -> list[tuple[str, Any]]:
    visible = []
    for key, value in data.items():
        normalized_key = str(key).lower()
        if normalized_key in SENSITIVE_UI_FIELDS:
            continue
        if normalized_key in TECHNICAL_UI_FIELDS:
            continue
        visible.append((str(key), value))
    return visible


def render_friendly_data(
    data: Any,
    expanded: bool = False,
    title: str | None = None,
) -> None:
    """Render API data as readable cards and fields, never raw JSON."""

    if title:
        st.markdown(f"#### {escape(str(title))}")

    if data is None:
        st.info("No information is available.")
        return

    if isinstance(data, dict):
        items = _visible_items(data)
        if not items:
            st.info("No displayable information is available.")
            return

        scalar_items = []
        nested_items = []
        for key, value in items:
            if isinstance(value, (dict, list, tuple)):
                nested_items.append((key, value))
            else:
                scalar_items.append((key, value))

        if scalar_items:
            cards = []
            for key, value in scalar_items:
                label = escape(_friendly_label(key))
                display_value = escape(_friendly_value(value))
                cards.append(
                    f'<div class="detail-card">'
                    f'<div class="detail-label">{label}</div>'
                    f'<div class="detail-value">{display_value}</div>'
                    f'</div>'
                )
            st.markdown(
                '<div class="detail-grid">' + "".join(cards) + '</div>',
                unsafe_allow_html=True,
            )

        for key, value in nested_items:
            label = _friendly_label(key)
            with st.expander(label, expanded=expanded):
                render_friendly_data(value, expanded=expanded)
        return

    if isinstance(data, (list, tuple)):
        if not data:
            st.info("No items are available.")
            return
        for index, item in enumerate(data, start=1):
            if isinstance(item, dict):
                item_title = (
                    item.get("role_name")
                    or item.get("project_name")
                    or item.get("user_full_name")
                    or item.get("user_email")
                    or item.get("asset_name")
                    or f"Item {index}"
                )
                with st.expander(str(item_title), expanded=expanded):
                    render_friendly_data(item, expanded=expanded)
            else:
                st.markdown(f"- {escape(_friendly_value(item))}")
        return

    st.markdown(
        f'<div class="detail-card"><div class="detail-value">'
        f'{escape(_friendly_value(data))}</div></div>',
        unsafe_allow_html=True,
    )


def init_state() -> None:
    defaults = {
        "api_url": API_URL,
        "access_token": None,
        "refresh_token": None,
        "current_user": None,
        "chat_messages": [],
        "chat_project_id": None,
        "last_task_id": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()


def request_api(
    method: str,
    path: str,
    *,
    auth: bool = True,
    timeout: int = REQUEST_TIMEOUT,
    _allow_refresh: bool = True,
    **kwargs: Any,
):
    headers = dict(kwargs.pop("headers", {}))
    if auth and st.session_state.access_token:
        headers["Authorization"] = f"Bearer {st.session_state.access_token}"
    try:
        response = requests.request(method, f"{st.session_state.api_url}{path}", headers=headers, timeout=timeout, **kwargs)
    except requests.RequestException as exc:
        return False, f"Backend connection failed: {exc}", 0

    # Keep the Streamlit session alive by using the backend refresh endpoint.
    # The original request is retried once with the newly issued access token.
    if (
        response.status_code == 401
        and auth
        and _allow_refresh
        and st.session_state.refresh_token
        and path != "/api/v1/auth/refresh"
    ):
        try:
            refresh_response = requests.post(
                f"{st.session_state.api_url}/api/v1/auth/refresh",
                json={"refresh_token": st.session_state.refresh_token},
                timeout=timeout,
            )
            if refresh_response.ok:
                refreshed = refresh_response.json()
                st.session_state.access_token = refreshed.get("access_token")
                st.session_state.refresh_token = (
                    refreshed.get("refresh_token")
                    or st.session_state.refresh_token
                )
                retry_kwargs = dict(kwargs)
                retry_kwargs["headers"] = {
                    key: value
                    for key, value in headers.items()
                    if key.lower() != "authorization"
                }
                return request_api(
                    method,
                    path,
                    auth=auth,
                    timeout=timeout,
                    _allow_refresh=False,
                    **retry_kwargs,
                )
        except (requests.RequestException, ValueError):
            pass

    if response.status_code == 204:
        return True, None, 204
    try:
        payload = response.json()
    except ValueError:
        payload = response.content if response.ok else response.text
    if response.ok:
        return True, payload, response.status_code
    if isinstance(payload, dict):
        detail = payload.get("detail", payload)
        if isinstance(detail, dict):
            return False, detail.get("message", str(detail)), response.status_code
        return False, str(detail), response.status_code
    return False, str(payload), response.status_code


def load_me(show_error: bool = True) -> bool:
    ok, data, status = request_api("GET", "/api/v1/auth/me")
    if ok:
        st.session_state.current_user = data
        return True
    if status == 401:
        st.session_state.access_token = None
        st.session_state.refresh_token = None
    if show_error:
        st.error(data)
    return False


def logout() -> None:
    for key in ("access_token", "refresh_token", "current_user", "chat_messages", "chat_project_id", "last_task_id"):
        st.session_state[key] = None if key != "chat_messages" else []
    st.rerun()


def user_data() -> dict:
    return (st.session_state.current_user or {}).get("user") or {}


def tenant_data() -> dict:
    return (st.session_state.current_user or {}).get("tenant") or {}


def role_names() -> list[str]:
    return [x.get("role_name") for x in (st.session_state.current_user or {}).get("roles", []) if x.get("role_name")]


def is_admin() -> bool:
    return bool(user_data().get("is_tenant_admin"))


def can_manage_files() -> bool:
    return is_admin() or "Document Manager" in role_names()


def page_header(title: str, subtitle: str, badge: str | None = None) -> None:
    badge_html = f'<span class="badge">{escape(badge)}</span>' if badge else ""
    st.markdown(
        f'<div class="page-header"><div>'
        f'<div class="page-eyebrow">NexaDocs workspace</div>'
        f'<div class="page-title">{escape(title)}</div>'
        f'<div class="page-subtitle">{escape(subtitle)}</div>'
        f'</div>{badge_html}</div>',
        unsafe_allow_html=True,
    )


def auth_page() -> None:
    visual, panel = st.columns([1.12, .88], gap="large")
    with visual:
        st.markdown(
            '<div class="auth-visual">'
            '<div class="auth-logo"><span class="auth-logo-mark">✦</span>NexaDocs AI</div>'
            '<div class="auth-headline">Turn every document into an answer.</div>'
            '<div class="auth-copy">A secure intelligence workspace for teams that need fast, grounded answers — with every response connected to its original evidence.</div>'
            '<div class="auth-feature"><span class="auth-feature-icon">⌁</span><span>Hybrid semantic and keyword retrieval for higher-quality results.</span></div>'
            '<div class="auth-feature"><span class="auth-feature-icon">✓</span><span>Source-level citations make every generated answer easy to verify.</span></div>'
            '<div class="auth-feature"><span class="auth-feature-icon">⌾</span><span>Tenant isolation, role-based access, and secure document processing.</span></div>'
            '<div class="auth-proof"><span>Private by design</span><span>Evidence grounded</span><span>Team ready</span></div>'
            '</div>',
            unsafe_allow_html=True,
        )
    with panel:
        st.markdown(
            '<div class="auth-panel">'
            '<div class="auth-panel-kicker">Secure workspace</div>'
            '<div class="auth-panel-title">Welcome to NexaDocs</div>'
            '<div class="auth-panel-copy">Sign in to your workspace or create a new one in minutes.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        login_tab, register_tab = st.tabs(["Sign in", "Create workspace"])
        with login_tab:
            with st.form("login"):
                tenant_code = st.text_input("Workspace code", placeholder="e.g. acme-team")
                email = st.text_input("Email", placeholder="you@company.com")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submit = st.form_submit_button("Sign in", use_container_width=True, type="primary")
            if submit:
                ok, data, _ = request_api("POST", "/api/v1/auth/login", auth=False, json={"tenant_code": tenant_code, "email": email, "password": password})
                if ok:
                    st.session_state.access_token = data["access_token"]
                    st.session_state.refresh_token = data["refresh_token"]
                    load_me(False)
                    st.rerun()
                st.error(data)
        with register_tab:
            with st.form("register"):
                tenant_name = st.text_input("Workspace name", placeholder="Acme Knowledge Hub")
                tenant_code = st.text_input("Workspace code", key="reg_code", placeholder="acme-team")
                full_name = st.text_input("Administrator name", placeholder="Full name")
                email = st.text_input("Administrator email", key="reg_email", placeholder="admin@company.com")
                password = st.text_input("Password", type="password", key="reg_pass", placeholder="Create a strong password")
                confirm = st.text_input("Confirm password", type="password")
                submit = st.form_submit_button("Create workspace", use_container_width=True, type="primary")
            if submit:
                ok, data, _ = request_api("POST", "/api/v1/auth/register-tenant", auth=False, json={"tenant_name": tenant_name, "tenant_code": tenant_code, "admin_full_name": full_name, "admin_email": email, "password": password, "confirm_password": confirm})
                if ok:
                    st.session_state.access_token = data["access_token"]
                    st.session_state.refresh_token = data["refresh_token"]
                    load_me(False)
                    st.rerun()
                st.error(data)


def sidebar() -> str:
    with st.sidebar:
        st.markdown('<div class="brand"><div class="brand-mark"></div><div><div class="brand-name">NexaDocs AI</div><div class="brand-sub">Document Intelligence</div></div></div>', unsafe_allow_html=True)
        tenant = tenant_data()
        user = user_data()
        tenant_name = tenant.get("tenant_name") or "My Workspace"
        st.markdown(
            f'<div class="workspace-card">'
            f'<div class="workspace-kicker">Current workspace</div>'
            f'<div class="workspace-name">{escape(str(tenant_name))}</div>'
            f'<div class="workspace-meta">'
            f'{escape(str(user.get("user_full_name") or user.get("user_email", "User")))}'
            f'</div><div class="workspace-meta">'
            f'{escape(", ".join(role_names()) or "No role")}'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        navigation = [
            ("Overview", "◫  Overview"),
            ("Projects", "◇  Projects"),
            ("Documents", "▤  Documents"),
            ("AI Assistant", "✦  AI Assistant"),
            ("Database Access", "▦  Database Data"),
            ("Tasks", "◷  Tasks"),
            ("Account", "◎  Account"),
            ("API Explorer", "⌁  All Project APIs"),
        ]
        if is_admin():
            navigation += [
                ("Users", "♙  Users"),
                ("Roles", "⌘  Roles"),
                ("Database Connections", "◉  Database Connections"),
                ("Database Permissions", "⚿  Database Permissions"),
            ]
        labels = [label for _, label in navigation]
        selected = st.radio("Navigation", labels, label_visibility="collapsed")
        page = dict((label, name) for name, label in navigation)[selected]
        st.divider()
        with st.expander("Connection settings", expanded=False):
            st.session_state.api_url = st.text_input(
                "Backend URL",
                value=st.session_state.api_url,
                help="The FastAPI base URL used by this interface.",
            ).rstrip("/")
        if st.button("Sign out", use_container_width=True):
            logout()
    return page


def fetch_projects() -> list[dict[str, Any]]:
    ok, data, _ = request_api("GET", "/api/v1/projects", params={"page": 1, "page_size": 100})
    if not ok:
        st.error(data)
        return []
    return data.get("items", [])


def project_selector(key: str):
    projects = fetch_projects()
    if not projects:
        st.info("Create a project to get started.")
        return None, None
    mapping = {f"{p['project_name']}  ·  #{p['project_id']}": p for p in projects}
    label = st.selectbox("Knowledge project", list(mapping), key=key)
    return mapping[label]["project_id"], mapping[label]


def overview() -> None:
    welcome_ok, welcome_data, _ = request_api(
        "GET",
        "/api/v1/welcome",
        auth=False,
        timeout=10,
    )
    page_header(
        "Workspace overview",
        "Monitor projects, documents, and account access.",
        "Backend online" if welcome_ok else "Backend unavailable",
    )
    projects = fetch_projects()
    full_name = user_data().get("user_full_name") or "there"
    first_name = str(full_name).split()[0]
    workspace_name = tenant_data().get("tenant_name") or "your workspace"
    st.markdown(
        f'<div class="hero"><div class="hero-kicker">Intelligence workspace</div>'
        f'<h2>Good to see you, {escape(first_name)}.</h2>'
        f'<p>{escape(str(workspace_name))} is ready. Organize your knowledge, index new files, and ask evidence-grounded questions from one secure place.</p>'
        f'<p>{escape(str(welcome_data.get("message") if welcome_ok and isinstance(welcome_data, dict) else "FastAPI could not be reached."))}</p></div>',
        unsafe_allow_html=True,
    )
    cols = st.columns(3)
    values = [
        ("◇", "Projects", len(projects), "Knowledge spaces"),
        ("◎", "Account status", str(user_data().get("user_status", "-")).title(), "Authenticated user"),
        ("⌁", "Workspace status", str(tenant_data().get("tenant_status", "-")).title(), "Service availability"),
    ]
    for col, (icon, label, value, note) in zip(cols, values):
        col.markdown(
            f'<div class="metric-card"><div class="metric-top">'
            f'<div class="metric-label">{escape(str(label))}</div>'
            f'<div class="metric-icon">{escape(icon)}</div></div>'
            f'<div class="metric-value">{escape(str(value))}</div>'
            f'<div class="metric-note">{escape(str(note))}</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        f'<div class="section-heading"><div class="section-title">Recent projects</div>'
        f'<div class="section-meta">Showing up to 5 of {len(projects)}</div></div>',
        unsafe_allow_html=True,
    )
    if not projects:
        st.info("No projects yet.")
    for p in projects[:5]:
        st.markdown(
            f'<div class="card project-card"><div class="project-icon">◇</div><div>'
            f'<div class="project-name">{escape(p["project_name"])}</div>'
            f'<div class="small-muted">{escape(p.get("project_description") or "No description added yet")}</div>'
            f'</div></div><div style="height:.55rem"></div>',
            unsafe_allow_html=True,
        )


def projects_page() -> None:
    page_header(
        "Projects",
        "Create, inspect, update, and delete isolated knowledge spaces.",
        "5 project APIs",
    )
    if is_admin():
        with st.expander("＋ Create project"):
            with st.form("create_project"):
                name = st.text_input("Project name")
                desc = st.text_area("Description")
                submit = st.form_submit_button("Create", type="primary")
            if submit:
                ok, data, _ = request_api("POST", "/api/v1/projects", json={"project_name": name, "project_description": desc or None})
                if ok:
                    st.success("Project created.")
                    st.rerun()
                st.error(data)

    projects = fetch_projects()
    if not projects:
        st.info("No projects are available.")
        return

    for p in projects:
        project_id = int(p["project_id"])
        detail_key = f"project_api_details_{project_id}"
        with st.expander(f"{p['project_name']}  ·  Project #{p['project_id']}"):
            latest = st.session_state.get(detail_key) or p
            st.write(latest.get("project_description") or "No description")
            dates = st.columns(2)
            dates[0].caption(f"Created: {_friendly_datetime(latest.get('created_at'))}")
            dates[1].caption(f"Updated: {_friendly_datetime(latest.get('updated_at'))}")

            if st.button(
                "Load latest project details",
                use_container_width=True,
                key=f"get_project_{project_id}",
            ):
                ok, result, _ = request_api(
                    "GET",
                    f"/api/v1/projects/{project_id}",
                )
                if ok:
                    st.session_state[detail_key] = result
                    st.success("Project details loaded from the single-project API.")
                    st.rerun()
                else:
                    st.error(result)

            if not is_admin():
                continue

            st.markdown("#### Edit project")
            with st.form(f"edit_project_{project_id}"):
                updated_name = st.text_input(
                    "Project name",
                    value=str(latest.get("project_name") or ""),
                    key=f"project_name_{project_id}",
                )
                updated_description = st.text_area(
                    "Description",
                    value=str(latest.get("project_description") or ""),
                    key=f"project_description_{project_id}",
                )
                save_project = st.form_submit_button(
                    "Save project changes",
                    type="primary",
                    use_container_width=True,
                )
            if save_project:
                ok, result, _ = request_api(
                    "PATCH",
                    f"/api/v1/projects/{project_id}",
                    json={
                        "project_name": updated_name,
                        "project_description": updated_description or None,
                    },
                )
                if ok:
                    st.session_state[detail_key] = result
                    st.success("Project updated successfully.")
                    st.rerun()
                else:
                    st.error(result)

            st.markdown("#### Danger zone")
            delete_confirmed = st.checkbox(
                "Delete this project and its project data.",
                key=f"confirm_delete_project_{project_id}",
            )
            if st.button(
                "Delete project",
                use_container_width=True,
                key=f"delete_project_{project_id}",
                disabled=not delete_confirmed,
            ):
                ok, result, _ = request_api(
                    "DELETE",
                    f"/api/v1/projects/{project_id}",
                )
                if ok:
                    st.session_state.pop(detail_key, None)
                    st.success("Project deleted successfully.")
                    st.rerun()
                else:
                    st.error(result)


def documents_page() -> None:
    page_header(
        "Documents",
        "Upload, inspect, process, download, re-index, and delete project files.",
        "6 file APIs",
    )
    project_id, project = project_selector("docs_project")
    if project_id is None:
        return
    st.markdown(f'<div class="hero"><div class="hero-kicker">Document library</div><h2>{escape(project["project_name"])}</h2><p>Upload and index PDF, TXT, DOCX, CSV, XLSX, and XLS files. Every processed file becomes searchable by the AI assistant.</p></div>', unsafe_allow_html=True)
    if can_manage_files():
        file = st.file_uploader("Drop a document here", type=["pdf", "txt", "docx", "csv", "xlsx", "xls"])
        if st.button("Upload and index", type="primary", disabled=file is None):
            ok, data, _ = request_api("POST", f"/api/v1/projects/{project_id}/files", files={"file": (file.name, file.getvalue(), file.type or "application/octet-stream")}, timeout=120)
            if ok:
                st.session_state.last_task_id = data.get("task_id")
                st.success(f"Processing queued. Task: {data.get('task_id')}")
                st.rerun()
            st.error(data)
    ok, data, _ = request_api("GET", f"/api/v1/projects/{project_id}/files", params={"page": 1, "page_size": 100})
    if not ok:
        st.error(data)
        return
    for asset in data.get("items", []):
        cfg = asset.get("asset_config") or {}
        name = cfg.get("original_file_name") or asset.get("asset_name")
        with st.expander(f"📄 {name}"):
            asset_id = int(asset["asset_id"])
            metadata_key = f"file_api_details_{project_id}_{asset_id}"
            exact_asset = st.session_state.get(metadata_key) or asset
            c1, c2, c3 = st.columns(3)
            c1.metric("Status", exact_asset.get("asset_status", "-"))
            c2.metric("Size", f"{exact_asset.get('asset_size', 0):,} B")
            c3.metric("Chunks", exact_asset.get("asset_indexed_chunks", 0))
            if exact_asset.get("asset_error"):
                st.error(exact_asset["asset_error"])

            if st.button(
                "Refresh file metadata",
                use_container_width=True,
                key=f"get_file_metadata_{project_id}_{asset_id}",
            ):
                ok, result, _ = request_api(
                    "GET",
                    f"/api/v1/projects/{project_id}/files/{asset_id}",
                )
                if ok:
                    st.session_state[metadata_key] = result
                    st.success("File metadata refreshed.")
                    st.rerun()
                else:
                    st.error(result)

            d_ok, content, _ = request_api("GET", f"/api/v1/projects/{project_id}/files/{asset_id}/download", timeout=120)
            if d_ok and isinstance(content, bytes):
                st.download_button("Download", content, file_name=name, mime=cfg.get("content_type") or "application/octet-stream", key=f"dl_{asset_id}")
            if can_manage_files():
                b1, b2 = st.columns(2)
                if b1.button("Reprocess", key=f"rp_{asset_id}"):
                    ok, result, _ = request_api("POST", f"/api/v1/projects/{project_id}/files/{asset_id}/reprocess")
                    if ok:
                        st.session_state.last_task_id = result.get("task_id")
                        st.success("Reprocessing queued.")
                    else:
                        st.error(result)
                if b2.button("Delete", key=f"del_{asset_id}"):
                    ok, result, _ = request_api("DELETE", f"/api/v1/projects/{project_id}/files/{asset_id}")
                    if ok:
                        st.session_state.pop(metadata_key, None)
                        st.rerun()
                    st.error(result)


def clean_answer(value: str | None) -> str:
    text = str(value or "No answer was returned.")
    text = re.sub(r"\[\s*(?:Document|Source)\s+\d+\s*\]", "", text, flags=re.I)
    text = re.sub(r"\[\s*المستند\s+\d+\s*\]", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def citation_items(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output, seen = [], set()
    for source in sources or []:
        c = source.get("citation") or {}
        m = source.get("metadata") or {}
        item = {
            "file": c.get("file_name") or m.get("original_file_name") or m.get("file_id") or "Unknown file",
            "page": c.get("page_number") or m.get("page_number"),
            "sheet": c.get("sheet_name") or m.get("sheet_name"),
            "row_start": c.get("row_start") or m.get("row_start"),
            "row_end": c.get("row_end") or m.get("row_end"),
        }
        key = tuple(item.values())
        if key not in seen:
            seen.add(key)
            output.append(item)
    return output


def render_citations(sources: list[dict[str, Any]]) -> None:
    items = citation_items(sources)
    if not items:
        return
    with st.expander(f"Sources · {len(items)}", expanded=False):
        for item in items:
            meta = []
            if item["page"] is not None: meta.append(f"Page {item['page']}")
            if item["sheet"]: meta.append(f"Sheet {item['sheet']}")
            if item["row_start"] is not None:
                meta.append(f"Rows {item['row_start']}-{item['row_end']}" if item["row_end"] and item["row_end"] != item["row_start"] else f"Row {item['row_start']}")
            st.markdown(f'<div class="citation-card"><div class="citation-icon">📄</div><div><div class="citation-name">{escape(str(item["file"]))}</div><div class="citation-meta">{escape(" · ".join(meta) or "Document source")}</div></div></div>', unsafe_allow_html=True)


def build_conversation_history(
    messages: list[dict[str, Any]],
    max_messages: int = 6,
) -> list[dict[str, str]]:
    """Return only clean user/assistant text for the RAG API."""

    history: list[dict[str, str]] = []
    for message in messages:
        role = str(message.get("role") or "").strip().lower()
        content = str(message.get("content") or "").strip()

        if role not in {"user", "assistant"}:
            continue
        if not content or message.get("error"):
            continue

        history.append(
            {
                "role": role,
                "content": content[:4000],
            }
        )

    return history[-max(int(max_messages), 1):]


def assistant_page() -> None:
    page_header(
        "AI Assistant",
        "Run direct hybrid retrieval or ask grounded questions across indexed documents.",
        "2 search APIs",
    )
    project_id, project = project_selector("assistant_project")
    if project_id is None:
        return
    if st.session_state.chat_project_id != project_id:
        st.session_state.chat_project_id = project_id
        st.session_state.chat_messages = []
    st.markdown(f'<div class="hero"><div class="hero-kicker">Grounded AI assistant</div><h2>Chat with {escape(project["project_name"])}</h2><p>Ask in natural language and receive answers grounded in your indexed content. Open Sources under any response to verify the exact supporting file and location.</p></div>', unsafe_allow_html=True)

    with st.expander("⌕ Direct hybrid search API", expanded=False):
        st.caption(
            "Runs POST /api/v1/projects/{project_id}/search directly and "
            "returns the ranked chunks without generating an answer."
        )
        with st.form(f"hybrid_search_{project_id}"):
            search_query = st.text_input(
                "Search query",
                placeholder="Find the most relevant indexed passages",
            )
            s1, s2, s3 = st.columns(3)
            search_limit = s1.number_input("Final results", 1, 20, 5)
            semantic_limit = s2.number_input(
                "Semantic candidates",
                1,
                100,
                20,
                key="direct_semantic_limit",
            )
            keyword_limit = s3.number_input(
                "Keyword candidates",
                1,
                100,
                20,
                key="direct_keyword_limit",
            )
            rerank = st.checkbox("Use reranking when configured", value=True)
            run_search = st.form_submit_button(
                "Run hybrid search",
                type="primary",
                use_container_width=True,
            )
        if run_search:
            if not search_query.strip():
                st.error("Search query is required.")
            else:
                ok, result, _ = request_api(
                    "POST",
                    f"/api/v1/projects/{project_id}/search",
                    json={
                        "query": search_query.strip(),
                        "limit": int(search_limit),
                        "semantic_limit": int(semantic_limit),
                        "keyword_limit": int(keyword_limit),
                        "rrf_k": 60,
                        "rerank": rerank,
                        "rerank_candidates": max(
                            int(search_limit),
                            int(semantic_limit),
                            int(keyword_limit),
                            30,
                        ),
                    },
                    timeout=120,
                )
                if ok:
                    st.session_state[f"hybrid_search_result_{project_id}"] = result
                else:
                    st.error(result)

        direct_results = st.session_state.get(
            f"hybrid_search_result_{project_id}"
        )
        if isinstance(direct_results, dict):
            st.success(
                f"Returned {direct_results.get('total', 0)} ranked results."
            )
            render_friendly_data(direct_results.get("results") or [])

    c1, c2 = st.columns([5, 1])
    with c2:
        if st.button("Clear", use_container_width=True):
            st.session_state.chat_messages = []
            st.rerun()
    with st.expander("Retrieval settings"):
        a, b, c = st.columns(3)
        limit = a.number_input("Final sources", 1, 20, 5)
        semantic = b.number_input("Semantic candidates", 1, 100, 20)
        keyword = c.number_input("Keyword candidates", 1, 100, 20)
    st.markdown('<div class="chat-shell">', unsafe_allow_html=True)
    if not st.session_state.chat_messages:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown("Welcome. Ask a question about the selected project's files.")
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"], avatar="👤" if msg["role"] == "user" else "🤖"):
            st.markdown(msg["content"])
            if msg.get("error"): st.error(msg["error"])
            if msg["role"] == "assistant": render_citations(msg.get("sources") or [])
    prompt = st.chat_input("Ask about the project documents...")
    if prompt:
        # Build history before adding the current user message, otherwise
        # the current question would be sent twice to the backend.
        conversation_history = build_conversation_history(
            st.session_state.chat_messages,
            max_messages=6,
        )

        st.session_state.chat_messages.append(
            {"role": "user", "content": prompt}
        )
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Retrieving evidence and generating an answer..."):
                ok, data, _ = request_api(
                    "POST",
                    f"/api/v1/projects/{project_id}/ask",
                    json={
                        "question": prompt,
                        "limit": int(limit),
                        "semantic_limit": int(semantic),
                        "keyword_limit": int(keyword),
                        "rrf_k": 60,
                        "rerank": True,
                        "rerank_candidates": max(
                            int(limit),
                            int(semantic),
                            int(keyword),
                            30,
                        ),
                        "rewrite_query": True,
                        "conversation_history": conversation_history,
                    },
                    timeout=180,
                )
            if ok:
                answer = clean_answer(data.get("answer"))
                sources = data.get("sources") or []
                st.write_stream((word + " " for word in answer.split()))
                render_citations(sources)
                st.session_state.chat_messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                        # Kept for diagnostics and future admin-only debug UI.
                        # It is intentionally not rendered to normal users.
                        "search_query": data.get("search_query"),
                    }
                )
            else:
                st.error(data)
                st.session_state.chat_messages.append({"role": "assistant", "content": "The request could not be completed.", "error": str(data), "sources": []})
    st.markdown('</div>', unsafe_allow_html=True)


def tasks_page() -> None:
    page_header(
        "Tasks",
        "Track background document processing jobs.",
        "1 task API",
    )
    task_id = st.text_input("Task ID", value=st.session_state.last_task_id or "")
    auto = st.toggle("Auto refresh", value=False)
    if st.button("Check status", type="primary") or (auto and task_id):
        ok, data, _ = request_api("GET", f"/api/v1/tasks/{task_id}")
        if ok:
            render_friendly_data(data)
            if auto and data.get("status") in {"PENDING", "STARTED", "RETRY"}:
                time.sleep(3); st.rerun()
        else: st.error(data)


def _fetch_all_roles() -> list[dict[str, Any]]:
    ok, data, _ = request_api(
        "GET",
        "/api/v1/roles",
        params={"page": 1, "page_size": 100},
    )
    if not ok:
        st.error(data)
        return []
    return data.get("items", [])


def _fetch_user_roles(user_id: str) -> list[dict[str, Any]]:
    ok, data, _ = request_api(
        "GET",
        f"/api/v1/users/{user_id}/roles",
    )
    if not ok:
        st.error(data)
        return []
    return data.get("roles", [])


def users_page() -> None:
    page_header(
        "Users",
        "Create accounts, update access, change passwords, and manage roles.",
        "11 user APIs",
    )

    current_user_id = str(user_data().get("user_id") or "")
    all_roles = _fetch_all_roles()
    role_by_name = {
        role["role_name"]: role
        for role in all_roles
        if role.get("role_name") and role.get("role_id")
    }

    with st.expander("＋ Create user", expanded=False):
        with st.form("create_user_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            email = c1.text_input("Gmail address")
            full_name = c2.text_input("Full name")
            password = c1.text_input("Temporary password", type="password")
            status_value = c2.selectbox(
                "Account status",
                ["active", "inactive", "suspended"],
            )
            admin_value = st.checkbox("Workspace administrator")
            submitted = st.form_submit_button(
                "Create user",
                type="primary",
                use_container_width=True,
            )

        if submitted:
            ok, data, _ = request_api(
                "POST",
                "/api/v1/users",
                json={
                    "user_email": email,
                    "user_full_name": full_name,
                    "password": password,
                    "user_status": status_value,
                    "is_tenant_admin": admin_value,
                },
            )
            if ok:
                st.success("User created successfully.")
                st.rerun()
            else:
                st.error(data)

    ok, data, _ = request_api(
        "GET",
        "/api/v1/users",
        params={"page": 1, "page_size": 100},
    )
    if not ok:
        st.error(data)
        return

    users = data.get("items", [])
    if not users:
        st.info("No users are available.")
        return

    st.markdown("### Workspace members")
    for user in users:
        user_id = str(user["user_id"])
        is_current = user_id == current_user_id
        display_name = user.get("user_full_name") or user.get("user_email")
        current_status = user.get("user_status", "active")
        statuses = ["active", "inactive", "suspended"]
        selected_index = statuses.index(current_status) if current_status in statuses else 0
        assigned_roles = _fetch_user_roles(user_id)
        assigned_names = [
            role.get("role_name")
            for role in assigned_roles
            if role.get("role_name")
        ]

        suffix = " · Your account" if is_current else ""
        with st.expander(
            f"👤 {display_name} · {current_status.title()}{suffix}"
        ):
            info1, info2, info3 = st.columns(3)
            info1.text_input(
                "Email",
                value=user.get("user_email") or "",
                disabled=True,
                key=f"email_view_{user_id}",
            )
            info2.text_input(
                "Last sign in",
                value=_friendly_datetime(user.get("last_login_at")),
                disabled=True,
                key=f"last_login_{user_id}",
            )
            info3.text_input(
                "Member since",
                value=_friendly_datetime(user.get("created_at")),
                disabled=True,
                key=f"created_{user_id}",
            )
            if st.button(
                "Load exact user record",
                use_container_width=True,
                key=f"get_user_{user_id}",
            ):
                ok, result, _ = request_api(
                    "GET",
                    f"/api/v1/users/{user_id}",
                    params={"include_roles": True},
                )
                if ok:
                    st.session_state[f"exact_user_{user_id}"] = result
                    st.success("User record loaded from the single-user API.")
                else:
                    st.error(result)
            exact_user = st.session_state.get(f"exact_user_{user_id}")
            if isinstance(exact_user, dict):
                render_friendly_data(exact_user, title="Exact user response")
            st.caption("Email changes are not supported by the current backend API.")

            c1, c2 = st.columns(2)
            new_name = c1.text_input(
                "Full name",
                value=user.get("user_full_name") or "",
                key=f"name_{user_id}",
            )
            new_status = c2.selectbox(
                "Account status",
                statuses,
                index=selected_index,
                disabled=is_current,
                key=f"status_{user_id}",
            )
            new_admin = st.checkbox(
                "Workspace administrator",
                value=bool(user.get("is_tenant_admin")),
                disabled=is_current,
                key=f"admin_{user_id}",
            )

            if st.button(
                "Save profile and access",
                type="primary",
                use_container_width=True,
                key=f"save_{user_id}",
            ):
                payload = {"user_full_name": new_name}
                if not is_current:
                    payload.update(
                        {
                            "user_status": new_status,
                            "is_tenant_admin": new_admin,
                        }
                    )
                ok, result, _ = request_api(
                    "PATCH",
                    f"/api/v1/users/{user_id}",
                    json=payload,
                )
                if ok:
                    st.success("User updated successfully.")
                    st.rerun()
                else:
                    st.error(result)

            st.markdown("#### Change password")
            with st.form(f"password_form_{user_id}", clear_on_submit=True):
                p1, p2, p3 = st.columns(3)
                current_password = p1.text_input(
                    "Current password",
                    type="password",
                    key=f"current_password_{user_id}",
                )
                new_password = p2.text_input(
                    "New password",
                    type="password",
                    key=f"new_password_{user_id}",
                )
                confirm_password = p3.text_input(
                    "Confirm new password",
                    type="password",
                    key=f"confirm_password_{user_id}",
                )
                password_submit = st.form_submit_button(
                    "Update password",
                    use_container_width=True,
                )
            if password_submit:
                ok, result, _ = request_api(
                    "PATCH",
                    f"/api/v1/users/{user_id}/password",
                    json={
                        "current_password": current_password,
                        "new_password": new_password,
                        "confirm_new_password": confirm_password,
                    },
                )
                if ok:
                    st.success("Password updated successfully.")
                else:
                    st.error(result)

            st.markdown("#### Roles")
            if assigned_names:
                st.caption("Current roles: " + ", ".join(assigned_names))
            else:
                st.caption("Current roles: No roles assigned")

            available_names = list(role_by_name)
            single_role_options = [
                name for name in available_names if name not in assigned_names
            ]
            if single_role_options:
                single_role_name = st.selectbox(
                    "Assign one role with the single-role API",
                    options=single_role_options,
                    key=f"single_role_{user_id}",
                )
                if st.button(
                    "Assign this role",
                    use_container_width=True,
                    key=f"assign_single_role_{user_id}",
                ):
                    role_id = role_by_name[single_role_name]["role_id"]
                    ok, result, _ = request_api(
                        "POST",
                        f"/api/v1/users/{user_id}/roles/{role_id}",
                    )
                    if ok:
                        st.success("Role assigned successfully.")
                        st.rerun()
                    else:
                        st.error(result)

            selected_roles = st.multiselect(
                "Assign one or more roles",
                options=available_names,
                default=[],
                key=f"bulk_roles_{user_id}",
            )
            if st.button(
                "Assign selected roles",
                use_container_width=True,
                key=f"assign_roles_{user_id}",
                disabled=not selected_roles,
            ):
                ids = [role_by_name[name]["role_id"] for name in selected_roles]
                ok, result, _ = request_api(
                    "POST",
                    f"/api/v1/users/{user_id}/roles",
                    json={"role_ids": ids},
                )
                if ok:
                    st.success("Roles assigned successfully.")
                    st.rerun()
                else:
                    st.error(result)

            for role in assigned_roles:
                role_id = role.get("role_id")
                role_name = role.get("role_name") or "Role"
                left, right = st.columns([4, 1])
                left.markdown(f"**{role_name}**")
                if right.button(
                    "Remove",
                    key=f"remove_role_{user_id}_{role_id}",
                    disabled=(
                        role_name == "Tenant Admin"
                        and bool(user.get("is_tenant_admin"))
                    ),
                ):
                    ok, result, _ = request_api(
                        "DELETE",
                        f"/api/v1/users/{user_id}/roles/{role_id}",
                    )
                    if ok:
                        st.success("Role removed.")
                        st.rerun()
                    else:
                        st.error(result)

            if st.button(
                "Remove all roles",
                key=f"remove_all_roles_{user_id}",
                disabled=bool(user.get("is_tenant_admin")) or not assigned_roles,
            ):
                ok, result, _ = request_api(
                    "DELETE",
                    f"/api/v1/users/{user_id}/roles",
                )
                if ok:
                    st.success("All roles removed.")
                    st.rerun()
                else:
                    st.error(result)

            st.divider()
            if st.button(
                "Delete user",
                key=f"delete_{user_id}",
                disabled=is_current,
                use_container_width=True,
            ):
                ok, result, _ = request_api(
                    "DELETE",
                    f"/api/v1/users/{user_id}",
                )
                if ok:
                    st.success("User deleted.")
                    st.rerun()
                else:
                    st.error(result)


def roles_page() -> None:
    page_header(
        "Roles",
        "Create custom roles and manage the workspace role catalog.",
        "6 role APIs",
    )

    with st.expander("＋ Create custom role", expanded=False):
        with st.form("create_role_form", clear_on_submit=True):
            role_name = st.text_input("Role name")
            role_description = st.text_area("Description")
            create_role = st.form_submit_button(
                "Create role",
                type="primary",
                use_container_width=True,
            )
        if create_role:
            ok, result, _ = request_api(
                "POST",
                "/api/v1/roles",
                json={
                    "role_name": role_name,
                    "role_description": role_description or None,
                },
            )
            if ok:
                st.success("Role created successfully.")
                st.rerun()
            else:
                st.error(result)

    ok, data, _ = request_api(
        "GET",
        "/api/v1/roles",
        params={"page": 1, "page_size": 100},
    )
    if not ok:
        st.error(data)
        return
    roles = data.get("items", [])

    ok, catalog, _ = request_api("GET", "/api/v1/roles/catalog")
    system_details = {}
    if ok:
        system_details = {
            item.get("role_name"): item
            for item in catalog.get("items", [])
        }

    st.markdown("### Role catalog")
    for role in roles:
        role_id = str(role["role_id"])
        role_name = role.get("role_name") or "Role"
        is_system = bool(role.get("is_system_role"))
        label = f"🔒 {role_name} · System" if is_system else f"🛠️ {role_name} · Custom"

        with st.expander(label):
            if st.button(
                "Load exact role record",
                use_container_width=True,
                key=f"get_role_{role_id}",
            ):
                ok, result, _ = request_api(
                    "GET",
                    f"/api/v1/roles/{role_id}",
                )
                if ok:
                    st.session_state[f"exact_role_{role_id}"] = result
                    st.success("Role record loaded from the single-role API.")
                else:
                    st.error(result)
            exact_role = st.session_state.get(f"exact_role_{role_id}")
            if isinstance(exact_role, dict):
                render_friendly_data(exact_role, title="Exact role response")

            if is_system:
                details = system_details.get(role_name, {})
                st.write(details.get("description") or role.get("role_description") or "No description")
                permissions = details.get("permissions", [])
                if permissions:
                    st.markdown("**Capabilities**")
                    for permission in permissions:
                        st.markdown(f"- {permission}")
                st.caption("System roles cannot be edited or deleted.")
                continue

            new_name = st.text_input(
                "Role name",
                value=role_name,
                key=f"role_name_{role_id}",
            )
            new_description = st.text_area(
                "Description",
                value=role.get("role_description") or "",
                key=f"role_desc_{role_id}",
            )
            left, right = st.columns(2)
            if left.button(
                "Save role",
                type="primary",
                use_container_width=True,
                key=f"save_role_{role_id}",
            ):
                ok, result, _ = request_api(
                    "PATCH",
                    f"/api/v1/roles/{role_id}",
                    json={
                        "role_name": new_name,
                        "role_description": new_description or None,
                    },
                )
                if ok:
                    st.success("Role updated successfully.")
                    st.rerun()
                else:
                    st.error(result)

            if right.button(
                "Delete role",
                use_container_width=True,
                key=f"delete_role_{role_id}",
            ):
                ok, result, _ = request_api(
                    "DELETE",
                    f"/api/v1/roles/{role_id}",
                )
                if ok:
                    st.success("Role deleted.")
                    st.rerun()
                else:
                    st.error(result)


def _database_status_icon(status_value: str | None) -> str:
    status_name = str(status_value or "untested").lower()
    return {
        "connected": "🟢",
        "failed": "🔴",
        "disabled": "⚪",
        "untested": "🟡",
    }.get(status_name, "🟡")


def _fetch_database_connections() -> list[dict[str, Any]]:
    ok, data, _ = request_api(
        "GET",
        "/api/v1/database-connections",
        params={
            "page": 1,
            "page_size": 100,
            "include_disabled": True,
        },
    )
    if not ok:
        st.error(data)
        return []
    return data.get("items", [])


def _render_schema_metadata(data: dict[str, Any]) -> None:
    """Render discovered or cached database metadata without exposing rows."""
    if not isinstance(data, dict):
        st.error("The backend returned an invalid schema response.")
        return

    metric_values = [
        ("Schemas", data.get("schema_count", 0)),
        ("Tables / views", data.get("table_count", 0)),
        ("Columns", data.get("column_count", 0)),
        ("Primary keys", data.get("primary_key_count", 0)),
        ("Foreign keys", data.get("foreign_key_count", 0)),
        ("Relationships", data.get("relationship_count", 0)),
    ]
    for column, (label, value) in zip(st.columns(6), metric_values):
        column.metric(label, value)

    timestamp = data.get("synced_at") or data.get("discovered_at")
    if timestamp:
        st.caption("Metadata time: " + _friendly_datetime(str(timestamp)))
    if data.get("schema_hash"):
        st.code(str(data["schema_hash"]), language=None)
    if "changed" in data:
        if data.get("changed"):
            st.success("The database structure changed and the cache was updated.")
        else:
            st.info("No structural changes were detected since the previous sync.")
    if data.get("permissions_invalidated"):
        st.warning(
            "The schema changed, so the previous table/column permissions "
            "were removed. Review and publish fresh role policies."
        )

    schemas = data.get("schemas") or []
    if not schemas:
        st.info("No user schemas or tables were discovered.")
    for schema_index, schema in enumerate(schemas):
        schema_name = str(schema.get("schema_name") or "Unnamed schema")
        tables = schema.get("tables") or []
        with st.expander(
            f"Schema: {schema_name} · {len(tables)} tables/views",
            expanded=(schema_index == 0),
        ):
            for table_index, table in enumerate(tables):
                table_name = str(table.get("table_name") or "Unnamed table")
                table_type = str(table.get("table_type") or "table")
                st.markdown(f"#### {escape(table_name)} · {escape(table_type)}")
                columns = table.get("columns") or []
                if columns:
                    column_rows = [
                        {
                            "Column": column.get("column_name"),
                            "Type": column.get("data_type"),
                            "PostgreSQL type": column.get("udt_name"),
                            "Nullable": column.get("is_nullable"),
                            "Default": column.get("column_default"),
                            "Position": column.get("ordinal_position"),
                            **(
                                {
                                    "Read": column.get("can_read"),
                                    "Filter": column.get("can_filter"),
                                    "Aggregate": column.get("can_aggregate"),
                                    "Sensitive": column.get("is_sensitive"),
                                    "Masking": column.get("masking_type"),
                                }
                                if "can_read" in column
                                else {}
                            ),
                        }
                        for column in columns
                    ]
                    st.dataframe(
                        column_rows,
                        use_container_width=True,
                        hide_index=True,
                    )
                else:
                    st.caption("No columns were returned for this table.")

                primary_keys = table.get("primary_keys") or []
                foreign_keys = table.get("foreign_keys") or []
                if primary_keys:
                    st.markdown(
                        "**Primary keys:** "
                        + "; ".join(
                            f"{pk.get('constraint_name')}: "
                            + ", ".join(pk.get("columns") or [])
                            for pk in primary_keys
                        )
                    )
                if foreign_keys:
                    st.markdown("**Foreign keys**")
                    st.dataframe(
                        [
                            {
                                "Constraint": fk.get("constraint_name"),
                                "Columns": ", ".join(fk.get("columns") or []),
                                "References": (
                                    f"{fk.get('referenced_schema_name')}."
                                    f"{fk.get('referenced_table_name')}"
                                ),
                                "Target columns": ", ".join(
                                    fk.get("referenced_columns") or []
                                ),
                                "On update": fk.get("update_rule"),
                                "On delete": fk.get("delete_rule"),
                            }
                            for fk in foreign_keys
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )

    relationships = data.get("relationships") or []
    if relationships:
        st.markdown("### Relationships")
        st.dataframe(
            [
                {
                    "Constraint": item.get("constraint_name"),
                    "Source": (
                        f"{item.get('source_schema_name')}."
                        f"{item.get('source_table_name')}"
                    ),
                    "Source columns": ", ".join(
                        item.get("source_columns") or []
                    ),
                    "Target": (
                        f"{item.get('target_schema_name')}."
                        f"{item.get('target_table_name')}"
                    ),
                    "Target columns": ", ".join(
                        item.get("target_columns") or []
                    ),
                    "On update": item.get("update_rule"),
                    "On delete": item.get("delete_rule"),
                }
                for item in relationships
            ],
            use_container_width=True,
            hide_index=True,
        )


def _database_table_map(
    schema_data: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    tables: dict[str, dict[str, Any]] = {}
    for schema in schema_data.get("schemas") or []:
        schema_name = str(schema.get("schema_name") or "")
        for table in schema.get("tables") or []:
            table_name = str(table.get("table_name") or "")
            if schema_name and table_name:
                tables[f"{schema_name}.{table_name}"] = {
                    "schema_name": schema_name,
                    **table,
                }
    return tables


def database_access_page() -> None:
    page_header(
        "Database Data",
        "Query only the tables, columns, and rows allowed by your roles.",
        "Permission enforced",
    )
    st.info(
        "This page never sends free-form SQL. The backend validates every "
        "column, adds row filters, uses a read-only transaction, and masks "
        "sensitive values before returning data."
    )

    connections = _fetch_database_connections()
    if not connections:
        st.info("No database connections are available.")
        return
    connection_by_label = {
        (
            f"{item.get('connection_name') or 'Database'} · "
            f"#{item.get('connection_id')}"
        ): item
        for item in connections
        if item.get("connection_id") is not None
    }
    selected_connection_label = st.selectbox(
        "Database connection",
        list(connection_by_label),
        key="database_access_connection",
    )
    connection = connection_by_label[selected_connection_label]
    connection_id = int(connection["connection_id"])
    schema_state_key = f"filtered_database_schema_{connection_id}"

    load_col, refresh_col = st.columns(2)
    if load_col.button(
        "Load my permission-filtered schema",
        type="primary",
        use_container_width=True,
        key=f"load_filtered_schema_{connection_id}",
    ):
        ok, result, _ = request_api(
            "GET",
            f"/api/v1/database-connections/{connection_id}/schema/filtered",
            timeout=60,
        )
        if ok:
            st.session_state[schema_state_key] = result
            st.success("Your allowed database schema was loaded.")
        else:
            st.error(result)
    if refresh_col.button(
        "Clear loaded schema",
        use_container_width=True,
        key=f"clear_filtered_schema_{connection_id}",
    ):
        st.session_state.pop(schema_state_key, None)
        st.rerun()

    schema_data = st.session_state.get(schema_state_key)
    if not isinstance(schema_data, dict):
        st.caption(
            "Load the filtered schema first. If it is empty, an administrator "
            "must grant a database policy to one of your roles."
        )
        return

    _render_schema_metadata(schema_data)
    tables = _database_table_map(schema_data)
    if not tables:
        st.warning("Your roles do not currently grant access to any table.")
        return

    st.markdown("### Secure query builder")
    table_label = st.selectbox(
        "Allowed table",
        list(tables),
        key=f"query_table_{connection_id}",
    )
    table = tables[table_label]
    query_result_key = (
        f"secure_query_result_{connection_id}_"
        f"{table['schema_name']}_{table['table_name']}"
    )
    columns = table.get("columns") or []
    readable = [
        item["column_name"] for item in columns if item.get("can_read")
    ]
    filterable = [
        item["column_name"] for item in columns if item.get("can_filter")
    ]
    aggregatable = [
        item["column_name"]
        for item in columns
        if item.get("can_aggregate")
    ]
    masked = [
        f"{item['column_name']} ({item.get('masking_type')})"
        for item in columns
        if item.get("is_sensitive")
    ]
    capability_cols = st.columns(4)
    capability_cols[0].metric("Readable", len(readable))
    capability_cols[1].metric("Filterable", len(filterable))
    capability_cols[2].metric("Aggregatable", len(aggregatable))
    capability_cols[3].metric(
        "Row filters",
        int(table.get("row_filters_enforced") or 0),
    )
    if masked:
        st.caption("Masked on output: " + ", ".join(masked))

    with st.form(f"secure_query_form_{connection_id}_{table_label}"):
        selected_columns = st.multiselect(
            "Columns to return",
            readable,
            default=readable[: min(5, len(readable))],
        )
        st.caption(
            "Filterable columns: "
            + (", ".join(filterable) if filterable else "None")
        )
        filters_json = st.text_area(
            "Filters (JSON array)",
            value="[]",
            height=110,
            help=(
                'Example: [{"column_name":"status","operator":"eq",'
                '"value":"active"}]'
            ),
        )
        st.caption(
            "Aggregatable columns: "
            + (", ".join(aggregatable) if aggregatable else "None")
        )
        aggregates_json = st.text_area(
            "Aggregates (JSON array)",
            value="[]",
            height=110,
            help=(
                'Example: [{"function":"sum","column_name":"amount",'
                '"alias":"total_amount"}]'
            ),
        )
        order_by_json = st.text_area(
            "Order by (JSON array)",
            value="[]",
            height=90,
            help=(
                'Example: [{"field":"total_amount","direction":"desc"}]'
            ),
        )
        q1, q2 = st.columns(2)
        limit = q1.number_input(
            "Maximum rows",
            min_value=1,
            max_value=1000,
            value=100,
            step=1,
        )
        offset = q2.number_input(
            "Offset",
            min_value=0,
            max_value=1_000_000,
            value=0,
            step=1,
        )
        run_query = st.form_submit_button(
            "Run secure query",
            type="primary",
            use_container_width=True,
        )

    if run_query:
        try:
            filters = json.loads(filters_json or "[]")
            aggregates = json.loads(aggregates_json or "[]")
            order_by = json.loads(order_by_json or "[]")
            if not all(isinstance(value, list) for value in [
                filters,
                aggregates,
                order_by,
            ]):
                raise ValueError("Filters, aggregates, and order by must be arrays")
        except (json.JSONDecodeError, ValueError) as exc:
            st.error(f"Invalid query JSON: {exc}")
        else:
            ok, result, _ = request_api(
                "POST",
                f"/api/v1/database-connections/{connection_id}/query",
                json={
                    "schema_name": table["schema_name"],
                    "table_name": table["table_name"],
                    "columns": selected_columns,
                    "filters": filters,
                    "aggregates": aggregates,
                    "order_by": order_by,
                    "limit": int(limit),
                    "offset": int(offset),
                },
                timeout=120,
            )
            if ok:
                st.session_state[query_result_key] = result
                st.success(
                    f"Returned {result.get('row_count', 0)} permission-checked rows."
                )
            else:
                st.error(result)

    query_result = st.session_state.get(query_result_key)
    if isinstance(query_result, dict):
        if query_result.get("masked_columns"):
            st.warning(
                "Masked columns: "
                + ", ".join(query_result["masked_columns"])
            )
        st.caption(
            f"Row filters applied: {query_result.get('row_filters_applied', 0)}"
        )
        rows = query_result.get("rows") or []
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        else:
            st.info("The secure query returned no rows.")


def database_permissions_page() -> None:
    page_header(
        "Database Permissions",
        "Publish table, column, masking, aggregation, and row rules per role.",
        "Deny by default",
    )
    if not is_admin():
        st.error("Tenant administrator permission is required.")
        return

    connections = _fetch_database_connections()
    roles = _fetch_all_roles()
    if not connections or not roles:
        st.info("Create a database connection and at least one role first.")
        return
    connection_by_label = {
        f"{item.get('connection_name')} · #{item.get('connection_id')}": item
        for item in connections
    }
    role_by_label = {
        f"{item.get('role_name')} · {item.get('role_id')}": item
        for item in roles
    }
    s1, s2 = st.columns(2)
    connection_label = s1.selectbox(
        "Database connection",
        list(connection_by_label),
        key="permission_connection",
    )
    role_label = s2.selectbox(
        "Role to configure",
        list(role_by_label),
        key="permission_role",
    )
    connection_id = int(connection_by_label[connection_label]["connection_id"])
    role = role_by_label[role_label]
    role_id = str(role["role_id"])

    schema_ok, schema_data, _ = request_api(
        "GET",
        f"/api/v1/database-connections/{connection_id}/schema",
        timeout=60,
    )
    if not schema_ok:
        st.error(schema_data)
        st.caption("Synchronize the database schema before creating policies.")
        return
    catalog_ok, catalog, _ = request_api(
        "GET",
        f"/api/v1/database-connections/{connection_id}/permissions",
        timeout=60,
    )
    if not catalog_ok:
        st.error(catalog)
        return

    all_tables = _database_table_map(schema_data)
    role_policies = [
        item
        for item in (catalog.get("policies") or [])
        if str(item.get("role_id")) == role_id
    ]
    existing_by_table = {
        f"{item.get('schema_name')}.{item.get('table_name')}": item
        for item in role_policies
    }

    st.caption(
        "Capabilities from multiple roles are additive. Row-filter groups are "
        "ORed across roles and ANDed inside each role. Masking uses the most "
        "restrictive matching role."
    )
    if catalog.get("policies"):
        st.dataframe(
            [
                {
                    "Role": item.get("role_name") or item.get("role_id"),
                    "Table": (
                        f"{item.get('schema_name')}.{item.get('table_name')}"
                    ),
                    "Columns": len(item.get("columns") or []),
                    "Row filters": len(item.get("row_filters") or []),
                }
                for item in catalog["policies"]
            ],
            use_container_width=True,
            hide_index=True,
        )

    selected_tables = st.multiselect(
        "Tables this role can read",
        list(all_tables),
        default=[
            name for name in existing_by_table if name in all_tables
        ],
        key=f"permission_tables_{connection_id}_{role_id}",
    )
    with st.form(f"database_policy_{connection_id}_{role_id}"):
        table_forms: dict[str, dict[str, Any]] = {}
        for table_label in selected_tables:
            table = all_tables[table_label]
            existing = existing_by_table.get(table_label, {})
            existing_columns = {
                item.get("column_name"): item
                for item in existing.get("columns") or []
            }
            column_names = [
                item.get("column_name")
                for item in table.get("columns") or []
                if item.get("column_name")
            ]
            with st.expander(f"Policy · {table_label}", expanded=True):
                readable = st.multiselect(
                    "can_read",
                    column_names,
                    default=[
                        name
                        for name, item in existing_columns.items()
                        if item.get("can_read") and name in column_names
                    ],
                    key=f"perm_read_{connection_id}_{role_id}_{table_label}",
                )
                filterable = st.multiselect(
                    "can_filter",
                    column_names,
                    default=[
                        name
                        for name, item in existing_columns.items()
                        if item.get("can_filter") and name in column_names
                    ],
                    key=f"perm_filter_{connection_id}_{role_id}_{table_label}",
                )
                aggregatable = st.multiselect(
                    "can_aggregate",
                    column_names,
                    default=[
                        name
                        for name, item in existing_columns.items()
                        if item.get("can_aggregate") and name in column_names
                    ],
                    key=f"perm_aggregate_{connection_id}_{role_id}_{table_label}",
                )
                sensitive_options = sorted(
                    set(readable) | set(filterable) | set(aggregatable)
                )
                sensitive = st.multiselect(
                    "Sensitive columns",
                    sensitive_options,
                    default=[
                        name
                        for name, item in existing_columns.items()
                        if item.get("is_sensitive")
                        and name in sensitive_options
                    ],
                    key=f"perm_sensitive_{connection_id}_{role_id}_{table_label}",
                )
                masks: dict[str, str] = {}
                mask_options = [
                    "full",
                    "partial",
                    "email",
                    "phone",
                    "last4",
                    "hash",
                    "unmasked",
                ]
                for column_name in sensitive:
                    if column_name not in readable:
                        masks[column_name] = "none"
                        st.caption(
                            f"{column_name} is sensitive but not readable, "
                            "so no output mask is needed."
                        )
                        continue
                    previous_mask = str(
                        existing_columns.get(column_name, {}).get(
                            "masking_type", "full"
                        )
                    )
                    masks[column_name] = st.selectbox(
                        f"Masking · {column_name}",
                        mask_options,
                        index=(
                            mask_options.index(previous_mask)
                            if previous_mask in mask_options
                            else 0
                        ),
                        key=(
                            f"perm_mask_{connection_id}_{role_id}_"
                            f"{table_label}_{column_name}"
                        ),
                    )
                existing_filters = [
                    {
                        "filter_name": item.get("filter_name"),
                        "column_name": item.get("column_name"),
                        "operator": item.get("operator"),
                        "value_source": item.get("value_source"),
                        "value": item.get("value"),
                        "enabled": item.get("enabled", True),
                    }
                    for item in existing.get("row_filters") or []
                ]
                row_filters_json = st.text_area(
                    "Row filters (JSON array)",
                    value=json.dumps(
                        existing_filters,
                        ensure_ascii=False,
                        indent=2,
                    ),
                    height=155,
                    key=(
                        f"perm_rows_{connection_id}_{role_id}_{table_label}"
                    ),
                    help=(
                        "value_source can be literal, current_user_id, "
                        "current_tenant_id, or current_user_email."
                    ),
                )
                table_forms[table_label] = {
                    "readable": readable,
                    "filterable": filterable,
                    "aggregatable": aggregatable,
                    "sensitive": sensitive,
                    "masks": masks,
                    "row_filters_json": row_filters_json,
                }
        save_policy = st.form_submit_button(
            "Publish complete role policy",
            type="primary",
            use_container_width=True,
        )

    if save_policy:
        try:
            table_payloads = []
            for table_label in selected_tables:
                table = all_tables[table_label]
                values = table_forms[table_label]
                row_filters = json.loads(
                    values["row_filters_json"] or "[]"
                )
                if not isinstance(row_filters, list):
                    raise ValueError(
                        f"Row filters for {table_label} must be a JSON array"
                    )
                capability_columns = sorted(
                    set(values["readable"])
                    | set(values["filterable"])
                    | set(values["aggregatable"])
                )
                column_payloads = []
                for column_name in capability_columns:
                    is_sensitive_column = column_name in values["sensitive"]
                    column_payloads.append(
                        {
                            "column_name": column_name,
                            "can_read": column_name in values["readable"],
                            "can_filter": column_name in values["filterable"],
                            "can_aggregate": (
                                column_name in values["aggregatable"]
                            ),
                            "is_sensitive": is_sensitive_column,
                            "masking_type": (
                                values["masks"].get(column_name, "none")
                                if is_sensitive_column
                                else "none"
                            ),
                        }
                    )
                table_payloads.append(
                    {
                        "schema_name": table["schema_name"],
                        "table_name": table["table_name"],
                        "can_read": True,
                        "columns": column_payloads,
                        "row_filters": row_filters,
                    }
                )
        except (json.JSONDecodeError, ValueError) as exc:
            st.error(f"Invalid role policy: {exc}")
        else:
            ok, result, _ = request_api(
                "PUT",
                (
                    f"/api/v1/database-connections/{connection_id}/"
                    f"permissions/roles/{role_id}"
                ),
                json={"tables": table_payloads},
                timeout=120,
            )
            if ok:
                st.success("The complete role policy was published atomically.")
                st.rerun()
            else:
                st.error(result)

    action1, action2 = st.columns(2)
    if action1.button(
        "Preview this role's filtered schema",
        use_container_width=True,
        key=f"preview_policy_{connection_id}_{role_id}",
    ):
        ok, result, _ = request_api(
            "GET",
            f"/api/v1/database-connections/{connection_id}/schema/filtered",
            params={"role_id": role_id},
            timeout=60,
        )
        if ok:
            st.session_state[
                f"policy_preview_{connection_id}_{role_id}"
            ] = result
        else:
            st.error(result)
    if action2.button(
        "Delete this role's database policy",
        use_container_width=True,
        key=f"delete_policy_{connection_id}_{role_id}",
    ):
        ok, result, _ = request_api(
            "DELETE",
            (
                f"/api/v1/database-connections/{connection_id}/"
                f"permissions/roles/{role_id}"
            ),
        )
        if ok:
            st.success("The role policy was deleted; access is now denied by default.")
            st.rerun()
        else:
            st.error(result)

    preview = st.session_state.get(
        f"policy_preview_{connection_id}_{role_id}"
    )
    if isinstance(preview, dict):
        st.markdown("### Role preview")
        _render_schema_metadata(preview)


def database_connections_page() -> None:
    page_header(
        "Database Connections",
        "Securely manage and test workspace PostgreSQL connections.",
        "14 database APIs",
    )

    if not is_admin():
        st.error("Tenant administrator permission is required.")
        return

    st.markdown(
        "PostgreSQL passwords are encrypted by the backend and are never "
        "displayed again. Use a dedicated read-only database account."
    )

    with st.expander("＋ Add PostgreSQL connection", expanded=False):
        with st.form("create_database_connection", clear_on_submit=True):
            c1, c2 = st.columns(2)
            connection_name = c1.text_input(
                "Connection name",
                placeholder="Sales Database",
            )
            host = c2.text_input(
                "Host",
                placeholder="postgres or db.example.com",
            )
            port = c1.number_input(
                "Port",
                min_value=1,
                max_value=65535,
                value=5432,
                step=1,
            )
            database_name = c2.text_input("Database name")
            username = c1.text_input("Read-only username")
            password = c2.text_input("Password", type="password")
            ssl_mode = st.selectbox(
                "SSL mode",
                [
                    "disable",
                    "allow",
                    "prefer",
                    "require",
                    "verify-ca",
                    "verify-full",
                ],
                index=2,
            )
            submitted = st.form_submit_button(
                "Save connection",
                type="primary",
                use_container_width=True,
            )
            if submitted:
                ok, data, _ = request_api(
                    "POST",
                    "/api/v1/database-connections",
                    json={
                        "connection_name": connection_name,
                        "database_type": "postgresql",
                        "host": host,
                        "port": int(port),
                        "database_name": database_name,
                        "username": username,
                        "password": password,
                        "ssl_mode": ssl_mode,
                    },
                )
                if ok:
                    st.success("Database connection saved securely.")
                    st.rerun()
                else:
                    st.error(data)

    connections = _fetch_database_connections()
    st.markdown("### Workspace database connections")
    if not connections:
        st.info("No database connections have been configured.")
        return

    for connection in connections:
        connection_id = int(connection["connection_id"])
        connection_status = str(
            connection.get("connection_status") or "untested"
        ).lower()
        icon = _database_status_icon(connection_status)
        label = (
            f"{icon} {connection.get('connection_name') or 'Database'}"
            f" · {connection_status.title()}"
        )

        with st.expander(label, expanded=False):
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Status", connection_status.title())
            m2.metric(
                "Read-only credential",
                "Configured" if connection.get("has_password") else "Missing",
            )
            m3.metric("SSL mode", connection.get("ssl_mode") or "-")
            m4.metric("Port", connection.get("port") or "-")

            if st.button(
                "Load exact connection record",
                use_container_width=True,
                key=f"get_database_connection_{connection_id}",
            ):
                ok, result, _ = request_api(
                    "GET",
                    f"/api/v1/database-connections/{connection_id}",
                )
                if ok:
                    st.session_state[
                        f"exact_database_connection_{connection_id}"
                    ] = result
                    st.success(
                        "Connection loaded from the single-connection API."
                    )
                else:
                    st.error(result)
            exact_connection = st.session_state.get(
                f"exact_database_connection_{connection_id}"
            )
            if isinstance(exact_connection, dict):
                render_friendly_data(
                    exact_connection,
                    title="Exact connection response",
                )

            details1, details2 = st.columns(2)
            details1.text_input(
                "Host",
                value=str(connection.get("host") or ""),
                disabled=True,
                key=f"db_host_view_{connection_id}",
            )
            details2.text_input(
                "Database",
                value=str(connection.get("database_name") or ""),
                disabled=True,
                key=f"db_name_view_{connection_id}",
            )
            details1.text_input(
                "Username",
                value=str(connection.get("username") or ""),
                disabled=True,
                key=f"db_user_view_{connection_id}",
            )
            details2.text_input(
                "Last tested",
                value=_friendly_datetime(connection.get("last_tested_at")),
                disabled=True,
                key=f"db_tested_view_{connection_id}",
            )
            st.caption(
                "Last successful connection: "
                + _friendly_datetime(connection.get("last_success_at"))
            )
            if connection.get("last_error_message"):
                st.error(connection["last_error_message"])

            test_col, refresh_col = st.columns(2)
            if test_col.button(
                "Test connection",
                type="primary",
                use_container_width=True,
                key=f"test_db_{connection_id}",
                disabled=(connection_status == "disabled"),
            ):
                with st.spinner("Testing PostgreSQL connection..."):
                    ok, result, _ = request_api(
                        "POST",
                        f"/api/v1/database-connections/{connection_id}/test",
                        timeout=30,
                    )
                if not ok:
                    st.error(result)
                elif result.get("success"):
                    st.success(result.get("message") or "Connection succeeded.")
                    result_cols = st.columns(3)
                    result_cols[0].metric(
                        "Read only",
                        "Yes" if result.get("read_only") else "No",
                    )
                    ssl_value = result.get("ssl_in_use")
                    result_cols[1].metric(
                        "SSL in use",
                        "Unknown" if ssl_value is None else (
                            "Yes" if ssl_value else "No"
                        ),
                    )
                    result_cols[2].metric(
                        "PostgreSQL",
                        result.get("server_version") or "Unknown",
                    )
                    st.rerun()
                else:
                    st.error(result.get("message") or "Connection test failed.")
                    if result.get("error_code"):
                        st.caption(f"Error code: {result['error_code']}")
            if refresh_col.button(
                "Refresh status",
                use_container_width=True,
                key=f"refresh_db_{connection_id}",
            ):
                st.rerun()

            st.markdown("#### Schema discovery & metadata cache")
            st.caption(
                "Discover reads the live database structure without storing rows. "
                "Sync saves only schemas, tables, columns, keys, and relationships."
            )
            discover_col, sync_col, cache_col = st.columns(3)
            schema_state_key = f"database_schema_result_{connection_id}"

            if discover_col.button(
                "Discover live schema",
                use_container_width=True,
                key=f"discover_schema_{connection_id}",
                disabled=(connection_status == "disabled"),
            ):
                with st.spinner("Discovering schemas, tables, and columns..."):
                    ok, result, _ = request_api(
                        "POST",
                        (
                            "/api/v1/database-connections/"
                            f"{connection_id}/discover-schema"
                        ),
                        timeout=120,
                    )
                if ok:
                    st.session_state[schema_state_key] = result
                    st.success("Live database schema discovered.")
                else:
                    st.error(result)

            if sync_col.button(
                "Sync and cache schema",
                type="primary",
                use_container_width=True,
                key=f"sync_schema_{connection_id}",
                disabled=(connection_status == "disabled"),
            ):
                with st.spinner("Synchronizing schema metadata cache..."):
                    ok, result, _ = request_api(
                        "POST",
                        (
                            "/api/v1/database-connections/"
                            f"{connection_id}/sync-schema"
                        ),
                        timeout=120,
                    )
                if ok:
                    st.session_state[schema_state_key] = result
                    st.success("Schema metadata cache synchronized.")
                else:
                    st.error(result)

            if cache_col.button(
                "Load cached schema",
                use_container_width=True,
                key=f"load_schema_cache_{connection_id}",
            ):
                ok, result, _ = request_api(
                    "GET",
                    f"/api/v1/database-connections/{connection_id}/schema",
                    timeout=60,
                )
                if ok:
                    st.session_state[schema_state_key] = result
                    st.success("Latest cached schema loaded.")
                else:
                    st.error(result)

            schema_result = st.session_state.get(schema_state_key)
            if isinstance(schema_result, dict):
                _render_schema_metadata(
                    schema_result,
                )

            st.markdown("#### Edit connection")
            with st.form(f"edit_database_connection_{connection_id}"):
                e1, e2 = st.columns(2)
                new_name = e1.text_input(
                    "Connection name",
                    value=str(connection.get("connection_name") or ""),
                    key=f"db_edit_name_{connection_id}",
                )
                new_host = e2.text_input(
                    "Host",
                    value=str(connection.get("host") or ""),
                    key=f"db_edit_host_{connection_id}",
                )
                new_port = e1.number_input(
                    "Port",
                    min_value=1,
                    max_value=65535,
                    value=int(connection.get("port") or 5432),
                    step=1,
                    key=f"db_edit_port_{connection_id}",
                )
                new_database = e2.text_input(
                    "Database name",
                    value=str(connection.get("database_name") or ""),
                    key=f"db_edit_database_{connection_id}",
                )
                new_username = e1.text_input(
                    "Read-only username",
                    value=str(connection.get("username") or ""),
                    key=f"db_edit_username_{connection_id}",
                )
                new_password = e2.text_input(
                    "New password",
                    type="password",
                    help="Leave empty to keep the current encrypted password.",
                    key=f"db_edit_password_{connection_id}",
                )
                ssl_options = [
                    "disable",
                    "allow",
                    "prefer",
                    "require",
                    "verify-ca",
                    "verify-full",
                ]
                current_ssl = str(connection.get("ssl_mode") or "prefer")
                new_ssl = st.selectbox(
                    "SSL mode",
                    ssl_options,
                    index=(
                        ssl_options.index(current_ssl)
                        if current_ssl in ssl_options
                        else 2
                    ),
                    key=f"db_edit_ssl_{connection_id}",
                )
                save = st.form_submit_button(
                    "Save changes",
                    type="primary",
                    use_container_width=True,
                )
                if save:
                    payload = {
                        "connection_name": new_name,
                        "host": new_host,
                        "port": int(new_port),
                        "database_name": new_database,
                        "username": new_username,
                        "ssl_mode": new_ssl,
                    }
                    if new_password:
                        payload["password"] = new_password
                    ok, result, _ = request_api(
                        "PATCH",
                        f"/api/v1/database-connections/{connection_id}",
                        json=payload,
                    )
                    if ok:
                        st.session_state.pop(schema_state_key, None)
                        st.success(
                            "Connection updated. Test it again before use."
                        )
                        st.rerun()
                    else:
                        st.error(result)

            st.markdown("#### Danger zone")
            confirm_delete = st.checkbox(
                "I understand that deleting this connection cannot be undone.",
                key=f"confirm_delete_db_{connection_id}",
            )
            if st.button(
                "Delete database connection",
                use_container_width=True,
                key=f"delete_db_{connection_id}",
                disabled=not confirm_delete,
            ):
                ok, result, _ = request_api(
                    "DELETE",
                    f"/api/v1/database-connections/{connection_id}",
                )
                if ok:
                    st.session_state.pop(schema_state_key, None)
                    st.success("Database connection deleted.")
                    st.rerun()
                else:
                    st.error(result)


def _resolve_openapi_node(
    document: dict[str, Any],
    node: Any,
) -> dict[str, Any]:
    """Resolve local OpenAPI references used by parameters and schemas."""
    if not isinstance(node, dict):
        return {}
    reference = node.get("$ref")
    if not isinstance(reference, str) or not reference.startswith("#/"):
        return node
    current: Any = document
    for part in reference[2:].split("/"):
        if not isinstance(current, dict):
            return node
        current = current.get(part.replace("~1", "/").replace("~0", "~"))
    return current if isinstance(current, dict) else node


def _openapi_example(
    document: dict[str, Any],
    schema: Any,
    seen: set[str] | None = None,
) -> Any:
    """Build an editable request example from an OpenAPI schema."""
    if not isinstance(schema, dict):
        return None
    seen = set(seen or set())
    reference = schema.get("$ref")
    if isinstance(reference, str):
        if reference in seen:
            return None
        seen.add(reference)
        return _openapi_example(
            document,
            _resolve_openapi_node(document, schema),
            seen,
        )
    if "example" in schema:
        return schema["example"]
    if "default" in schema:
        return schema["default"]
    enum_values = schema.get("enum") or []
    if enum_values:
        return enum_values[0]

    schema_type = schema.get("type")
    if schema_type == "object" or schema.get("properties"):
        properties = schema.get("properties") or {}
        required = set(schema.get("required") or [])
        result = {}
        for name, property_schema in properties.items():
            resolved = _resolve_openapi_node(document, property_schema)
            if name not in required and not any(
                key in resolved for key in ("default", "example", "enum")
            ):
                continue
            result[name] = _openapi_example(document, property_schema, seen)
        return result
    if schema_type == "array":
        item_example = _openapi_example(document, schema.get("items") or {}, seen)
        return [] if item_example is None else [item_example]
    if schema_type == "boolean":
        return False
    if schema_type == "integer":
        return int(schema.get("minimum", 1))
    if schema_type == "number":
        return float(schema.get("minimum", 1))
    if schema_type == "string":
        value_format = schema.get("format")
        if value_format == "email":
            return "user@example.com"
        if value_format == "uuid":
            return "00000000-0000-0000-0000-000000000000"
        if value_format in {"date-time", "datetime"}:
            return "2026-08-11T12:00:00Z"
        if value_format == "date":
            return "2026-08-11"
        if value_format == "password":
            return "ChangeMe123!"
        return "string"
    for composed_key in ("allOf", "oneOf", "anyOf"):
        composed = schema.get(composed_key) or []
        if composed:
            if composed_key == "allOf":
                merged = {}
                for item in composed:
                    value = _openapi_example(document, item, seen)
                    if isinstance(value, dict):
                        merged.update(value)
                return merged
            return _openapi_example(document, composed[0], seen)
    return None


def _redact_api_payload(value: Any) -> Any:
    """Keep API Explorer useful without displaying secrets or tokens."""
    if isinstance(value, dict):
        redacted = {}
        for key, item in value.items():
            normalized = str(key).lower()
            if (
                normalized in SENSITIVE_UI_FIELDS
                or "password" in normalized
                or normalized.endswith("_token")
                or normalized.endswith("_secret")
            ):
                redacted[key] = "••••••"
            else:
                redacted[key] = _redact_api_payload(item)
        return redacted
    if isinstance(value, list):
        return [_redact_api_payload(item) for item in value]
    return value


def _load_openapi_catalog(
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, str | None]:
    """Load every executable FastAPI operation from OpenAPI."""
    ok, document, _ = request_api(
        "GET",
        "/openapi.json",
        auth=False,
        timeout=30,
    )
    if not ok:
        return [], None, str(document)
    if not isinstance(document, dict):
        return [], None, "The backend returned an invalid OpenAPI document."

    operations: list[dict[str, Any]] = []
    supported_methods = {
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "head",
        "options",
    }

    for path, path_item in (document.get("paths") or {}).items():
        if not isinstance(path_item, dict):
            continue
        path_parameters = path_item.get("parameters") or []
        for method, raw_operation in path_item.items():
            if method.lower() not in supported_methods:
                continue
            operation = (
                raw_operation if isinstance(raw_operation, dict) else {}
            )
            parameter_map: dict[tuple[str, str], dict[str, Any]] = {}
            for raw_parameter in [
                *path_parameters,
                *(operation.get("parameters") or []),
            ]:
                parameter = _resolve_openapi_node(document, raw_parameter)
                parameter_map[
                    (str(parameter.get("in")), str(parameter.get("name")))
                ] = parameter
            tags = operation.get("tags") or ["Other"]
            security = operation.get("security", document.get("security"))
            operations.append(
                {
                    "path": str(path),
                    "method": method.upper(),
                    "summary": (
                        operation.get("summary")
                        or operation.get("operationId")
                        or "API operation"
                    ),
                    "description": operation.get("description") or "",
                    "operation_id": operation.get("operationId"),
                    "tags": [str(tag) for tag in tags],
                    "requires_auth": bool(security),
                    "parameters": list(parameter_map.values()),
                    "request_body": operation.get("requestBody"),
                    "system_endpoint": False,
                }
            )

    existing = {(item["method"], item["path"]) for item in operations}
    system_endpoints = [
        ("GET", "/openapi.json", "OpenAPI specification"),
        ("GET", "/docs", "Swagger API documentation"),
        ("GET", "/redoc", "ReDoc API documentation"),
        ("GET", "/metrics", "Prometheus service metrics"),
    ]
    for method, path, summary in system_endpoints:
        if (method, path) in existing:
            continue
        operations.append(
            {
                "path": path,
                "method": method,
                "summary": summary,
                "description": "Framework or operational endpoint.",
                "operation_id": None,
                "tags": ["System"],
                "requires_auth": False,
                "parameters": [],
                "request_body": None,
                "system_endpoint": True,
            }
        )

    operations.sort(
        key=lambda item: (
            item["tags"][0].lower(),
            item["path"],
            item["method"],
        )
    )
    return operations, document, None


def _endpoint_app_location(operation: dict[str, Any]) -> str:
    """Show where a live endpoint is available in the user interface."""
    path = str(operation.get("path") or "")
    method = str(operation.get("method") or "GET")

    if operation.get("system_endpoint"):
        return "All Project APIs"
    if path == "/api/v1/welcome":
        return "Overview"
    if path.startswith("/api/v1/auth"):
        if path.endswith("/refresh"):
            return "Automatic session refresh"
        if path.endswith("/me"):
            return "Account"
        return "Sign in / Create workspace"
    if path.startswith("/api/v1/database-connections"):
        if "/permissions" in path:
            return "Database Permissions"
        if path.endswith("/schema/filtered") or path.endswith("/query"):
            return "Database Data"
        return "Database Connections"
    if path.startswith("/api/v1/tasks"):
        return "Tasks"
    if path.startswith("/api/v1/users"):
        return "Users"
    if path.startswith("/api/v1/roles"):
        return "Roles"
    if path.startswith("/api/v1/projects"):
        if "/files" in path:
            return "Documents"
        if path.endswith("/search") or path.endswith("/ask"):
            return "AI Assistant"
        return "Projects"
    if method in {"GET", "POST", "PATCH", "PUT", "DELETE"}:
        return "All Project APIs"
    return "All Project APIs"


def _operation_key(operation: dict[str, Any]) -> str:
    return f"{operation.get('method')} {operation.get('path')}"


def _operation_group_name(operation: dict[str, Any]) -> str:
    tags = [str(tag) for tag in operation.get("tags") or []]
    return next(
        (tag for tag in tags if tag.lower() not in {"api_v1", "api"}),
        tags[0] if tags else "Other",
    )


def api_catalog_page() -> None:
    page_header(
        "All Project APIs",
        "Every FastAPI endpoint is listed below and can be run from the same screen.",
        "Live OpenAPI coverage",
    )

    operations, document, error = _load_openapi_catalog()
    if error or document is None:
        st.error(error or "Unable to load the OpenAPI specification.")
        st.caption(
            "Confirm that FastAPI is running and that /openapi.json is available."
        )
        return
    if not operations:
        st.info("No API operations were found.")
        return

    methods = sorted({item["method"] for item in operations})
    tags = sorted({tag for item in operations for tag in item["tags"]})
    summary_cols = st.columns(3)
    summary_cols[0].metric("Endpoints", len(operations))
    summary_cols[1].metric("API groups", len(tags))
    summary_cols[2].metric(
        "Authenticated",
        sum(1 for item in operations if item["requires_auth"]),
    )

    c1, c2, c3 = st.columns([2, 1, 1])
    search_text = c1.text_input(
        "Search APIs",
        placeholder="Search by path, name, or description",
    ).strip().lower()
    selected_method = c2.selectbox("Method", ["ALL", *methods])
    selected_tag = c3.selectbox("Group", ["ALL", *tags])

    filtered = []
    for item in operations:
        searchable = " ".join(
            [
                item["path"],
                item["method"],
                item["summary"],
                item["description"],
                *item["tags"],
            ]
        ).lower()
        if search_text and search_text not in searchable:
            continue
        if selected_method != "ALL" and item["method"] != selected_method:
            continue
        if selected_tag != "ALL" and selected_tag not in item["tags"]:
            continue
        filtered.append(item)

    st.markdown(
        f'<span class="api-count">{len(filtered)} of {len(operations)} endpoints</span>',
        unsafe_allow_html=True,
    )
    if not filtered:
        st.info("No endpoints match the current filters.")
        return

    st.markdown("### Complete API directory")
    st.caption(
        "This directory is generated live from FastAPI /openapi.json. "
        "It includes every current project API and updates automatically when "
        "a new backend endpoint is added."
    )

    grouped_operations: dict[str, list[dict[str, Any]]] = {}
    for item in filtered:
        group_name = _operation_group_name(item)
        grouped_operations.setdefault(group_name, []).append(item)

    for group_name, group_operations in grouped_operations.items():
        st.markdown(f"#### {escape(str(group_name).replace('_', ' ').title())}")
        for item in group_operations:
            item_key = re.sub(
                r"[^a-zA-Z0-9]+",
                "_",
                _operation_key(item),
            ).strip("_")
            method_class = f"api-{item['method'].lower()}"
            location = _endpoint_app_location(item)
            api_col, select_col = st.columns([6, 1])
            api_col.markdown(
                f'<div class="api-summary">'
                f'<div style="display:flex;gap:.75rem;align-items:flex-start">'
                f'<span class="api-method {method_class}">'
                f'{escape(item["method"])}</span>'
                f'<div><div class="api-path">{escape(item["path"])}</div>'
                f'<div class="api-description">'
                f'{escape(str(item["summary"]))} · App: {escape(location)}'
                f'</div></div></div></div>',
                unsafe_allow_html=True,
            )
            if select_col.button(
                "Run",
                key=f"directory_run_{item_key}",
                use_container_width=True,
            ):
                st.session_state["api_endpoint_selector"] = (
                    f"{item['method']:<7} {item['path']} · {item['summary']}"
                )
                st.toast(
                    f"Selected {item['method']} {item['path']}. "
                    "Use the runner below."
                )

    st.markdown("### Run an endpoint")
    endpoint_labels = [
        f"{item['method']:<7} {item['path']} · {item['summary']}"
        for item in filtered
    ]
    current_endpoint = st.session_state.get("api_endpoint_selector")
    if current_endpoint not in endpoint_labels:
        st.session_state["api_endpoint_selector"] = endpoint_labels[0]
    selected_label = st.selectbox(
        "Endpoint",
        endpoint_labels,
        key="api_endpoint_selector",
    )
    selected = filtered[endpoint_labels.index(selected_label)]
    endpoint_key = re.sub(
        r"[^a-zA-Z0-9]+",
        "_",
        f"{selected['method']}_{selected['path']}",
    ).strip("_")

    method_class = f"api-{selected['method'].lower()}"
    auth_text = (
        "Authentication required"
        if selected["requires_auth"]
        else "Public endpoint"
    )
    st.markdown(
        f'<div class="api-summary">'
        f'<div style="display:flex;gap:.75rem;align-items:flex-start">'
        f'<span class="api-method {method_class}">'
        f'{escape(selected["method"])}</span>'
        f'<div><div class="api-path">{escape(selected["path"])}</div>'
        f'<div class="api-description">'
        f'{escape(str(selected["summary"]))} · {escape(auth_text)}'
        f'</div></div></div></div>',
        unsafe_allow_html=True,
    )
    if selected["description"]:
        st.caption(str(selected["description"]))

    parameter_values: dict[tuple[str, str], str] = {}
    parameters = selected.get("parameters") or []
    if parameters:
        st.markdown("#### Parameters")
    for parameter in parameters:
        location = str(parameter.get("in") or "query")
        name = str(parameter.get("name") or "parameter")
        parameter_schema = _resolve_openapi_node(
            document,
            parameter.get("schema") or {},
        )
        default = parameter.get("example", parameter_schema.get("default", ""))
        required = bool(parameter.get("required")) or location == "path"
        help_text = str(parameter.get("description") or "")
        label = f"{name} · {location}"
        if required:
            label += " · required"
        value = st.text_input(
            label,
            value="" if default is None else str(default),
            help=help_text or None,
            key=f"api_parameter_{endpoint_key}_{location}_{name}",
        )
        parameter_values[(location, name)] = value

    request_body = _resolve_openapi_node(
        document,
        selected.get("request_body") or {},
    )
    content_map = request_body.get("content") or {}
    selected_content_type = None
    json_body_text = ""
    raw_body_text = ""
    multipart_files: list[tuple[str, tuple[str, bytes, str]]] = []
    form_values: dict[str, str] = {}

    if content_map:
        st.markdown("#### Request body")
        content_types = list(content_map)
        selected_content_type = st.selectbox(
            "Content type",
            content_types,
            key=f"api_content_type_{endpoint_key}",
        )
        media_schema = (content_map.get(selected_content_type) or {}).get(
            "schema"
        ) or {}
        resolved_media_schema = _resolve_openapi_node(document, media_schema)

        if selected_content_type == "application/json" or selected_content_type.endswith(
            "+json"
        ):
            example = _openapi_example(document, media_schema)
            json_body_text = st.text_area(
                "JSON body",
                value=json.dumps(
                    {} if example is None else example,
                    ensure_ascii=False,
                    indent=2,
                ),
                height=260,
                key=f"api_json_body_{endpoint_key}",
            )
        elif selected_content_type in {
            "multipart/form-data",
            "application/x-www-form-urlencoded",
        }:
            properties = resolved_media_schema.get("properties") or {}
            required_fields = set(resolved_media_schema.get("required") or [])
            for property_name, raw_property_schema in properties.items():
                property_schema = _resolve_openapi_node(
                    document,
                    raw_property_schema,
                )
                is_file = property_schema.get("format") == "binary"
                is_file_list = (
                    property_schema.get("type") == "array"
                    and _resolve_openapi_node(
                        document,
                        property_schema.get("items") or {},
                    ).get("format")
                    == "binary"
                )
                required_suffix = (
                    " · required" if property_name in required_fields else ""
                )
                if is_file or is_file_list:
                    uploaded = st.file_uploader(
                        property_name + required_suffix,
                        accept_multiple_files=is_file_list,
                        key=f"api_file_{endpoint_key}_{property_name}",
                    )
                    uploaded_files = (
                        uploaded if isinstance(uploaded, list) else [uploaded]
                    )
                    for uploaded_file in uploaded_files:
                        if uploaded_file is not None:
                            multipart_files.append(
                                (
                                    property_name,
                                    (
                                        uploaded_file.name,
                                        uploaded_file.getvalue(),
                                        uploaded_file.type
                                        or "application/octet-stream",
                                    ),
                                )
                            )
                else:
                    example = _openapi_example(document, property_schema)
                    form_values[property_name] = st.text_input(
                        property_name + required_suffix,
                        value="" if example is None else str(example),
                        key=f"api_form_{endpoint_key}_{property_name}",
                    )
        else:
            raw_body_text = st.text_area(
                "Raw request body",
                height=220,
                key=f"api_raw_body_{endpoint_key}",
            )

    option_cols = st.columns([1.2, 1, 1])
    send_auth = option_cols[0].checkbox(
        "Send session token",
        value=bool(selected["requires_auth"]),
        key=f"api_auth_{endpoint_key}",
    )
    timeout_seconds = option_cols[1].number_input(
        "Timeout (seconds)",
        min_value=1,
        max_value=300,
        value=60,
        key=f"api_timeout_{endpoint_key}",
    )
    execute = option_cols[2].button(
        "Run endpoint",
        type="primary",
        use_container_width=True,
        key=f"api_execute_{endpoint_key}",
    )

    if execute:
        final_path = selected["path"]
        query_params: dict[str, str] = {}
        request_headers: dict[str, str] = {}
        request_cookies: dict[str, str] = {}
        validation_error = None

        for parameter in parameters:
            location = str(parameter.get("in") or "query")
            name = str(parameter.get("name") or "parameter")
            value = parameter_values.get((location, name), "").strip()
            required = bool(parameter.get("required")) or location == "path"
            if required and not value:
                validation_error = f"{name} is required."
                break
            if not value:
                continue
            if location == "path":
                final_path = final_path.replace(
                    "{" + name + "}",
                    quote(value, safe=""),
                )
            elif location == "query":
                query_params[name] = value
            elif location == "header":
                request_headers[name] = value
            elif location == "cookie":
                request_cookies[name] = value

        request_kwargs: dict[str, Any] = {}
        if query_params:
            request_kwargs["params"] = query_params
        if request_headers:
            request_kwargs["headers"] = request_headers
        if request_cookies:
            request_kwargs["cookies"] = request_cookies

        if not validation_error and selected_content_type:
            body_required = bool(request_body.get("required"))
            if selected_content_type == "application/json" or selected_content_type.endswith(
                "+json"
            ):
                try:
                    request_kwargs["json"] = json.loads(json_body_text)
                except json.JSONDecodeError as exc:
                    validation_error = f"Invalid JSON body: {exc}"
            elif selected_content_type == "multipart/form-data":
                if body_required and not multipart_files and not any(
                    value for value in form_values.values()
                ):
                    validation_error = "The request body is required."
                request_kwargs["files"] = multipart_files
                request_kwargs["data"] = form_values
            elif selected_content_type == "application/x-www-form-urlencoded":
                request_kwargs["data"] = form_values
            else:
                if body_required and not raw_body_text:
                    validation_error = "The request body is required."
                request_headers.setdefault(
                    "Content-Type",
                    selected_content_type,
                )
                request_kwargs["headers"] = request_headers
                request_kwargs["data"] = raw_body_text

        if validation_error:
            st.error(validation_error)
        else:
            with st.spinner(
                f"Running {selected['method']} {final_path}..."
            ):
                ok, result, status_code = request_api(
                    selected["method"],
                    final_path,
                    auth=send_auth,
                    timeout=int(timeout_seconds),
                    **request_kwargs,
                )
            st.session_state["api_explorer_last_result"] = {
                "endpoint": f"{selected['method']} {final_path}",
                "ok": ok,
                "status_code": status_code,
                "result": result,
            }

    last_result = st.session_state.get("api_explorer_last_result")
    if isinstance(last_result, dict):
        st.markdown("### Latest response")
        message = (
            f"{last_result.get('endpoint')} · HTTP "
            f"{last_result.get('status_code')}"
        )
        if last_result.get("ok"):
            st.success(message)
        else:
            st.error(message)
        result = last_result.get("result")
        if isinstance(result, bytes):
            try:
                decoded = result.decode("utf-8")
            except UnicodeDecodeError:
                decoded = ""
            if decoded and len(decoded) <= 20000:
                st.code(decoded, language=None)
            st.download_button(
                "Download response",
                data=result,
                file_name="api-response.bin",
                use_container_width=True,
            )
        elif isinstance(result, (dict, list)):
            st.json(_redact_api_payload(result), expanded=True)
        elif result is None:
            st.info("The endpoint completed without a response body.")
        else:
            st.code(str(result), language=None)

    st.caption(
        "The explorer is generated from /openapi.json and includes system "
        "endpoints. Restart FastAPI after backend route changes, then refresh "
        "this page; new endpoints appear automatically."
    )


def _friendly_datetime(value: str | None) -> str:
    """Convert API timestamps into a concise user-facing value."""
    if not value:
        return "Not available"

    clean_value = str(value).strip()
    clean_value = clean_value.replace("T", " ")
    clean_value = clean_value.replace("Z", " UTC")

    if "." in clean_value:
        left, right = clean_value.split(".", 1)
        timezone_suffix = " UTC" if "UTC" in right else ""
        clean_value = left + timezone_suffix

    return clean_value


def account_page() -> None:
    page_header(
        "Account",
        "Profile, workspace access, and account information.",
    )

    current = st.session_state.current_user or {}
    user = current.get("user") or {}
    tenant = current.get("tenant") or {}
    roles = current.get("roles") or []

    full_name = (
        user.get("user_full_name")
        or user.get("user_email")
        or "User"
    )
    email = user.get("user_email") or "Email not available"
    initials = "".join(
        part[0].upper()
        for part in str(full_name).split()
        if part
    )[:2] or "U"
    user_status = str(user.get("user_status") or "unknown").title()
    workspace_status = str(
        tenant.get("tenant_status") or "unknown"
    ).title()
    role_values = [
        str(role.get("role_name"))
        for role in roles
        if role.get("role_name")
    ]
    if user.get("is_tenant_admin") and "Tenant Admin" not in role_values:
        role_values.insert(0, "Tenant Admin")

    st.markdown(
        f'<div class="account-profile">'
        f'<div class="account-avatar">{escape(initials)}</div>'
        f'<div><div class="account-name">{escape(str(full_name))}</div>'
        f'<div class="account-email">{escape(str(email))}</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        f'<div class="detail-grid">'
        f'<div class="detail-card"><div class="detail-label">Account status</div>'
        f'<div class="detail-value"><span class="status-pill">{escape(user_status)}</span></div></div>'
        f'<div class="detail-card"><div class="detail-label">Workspace status</div>'
        f'<div class="detail-value"><span class="status-pill">{escape(workspace_status)}</span></div></div>'
        f'<div class="detail-card"><div class="detail-label">Last sign in</div>'
        f'<div class="detail-value">{escape(_friendly_datetime(user.get("last_login_at")))}</div></div>'
        f'<div class="detail-card"><div class="detail-label">Member since</div>'
        f'<div class="detail-value">{escape(_friendly_datetime(user.get("created_at")))}</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown("### Access roles")
    if role_values:
        role_html = "".join(
            f'<span class="role-pill">{escape(role)}</span>'
            for role in dict.fromkeys(role_values)
        )
        st.markdown(role_html, unsafe_allow_html=True)
    else:
        st.info("No roles are assigned to this account.")

    st.markdown("### Session")
    st.caption(
        "Authentication credentials are stored only in the current "
        "Streamlit session. Internal identifiers and raw API payloads "
        "are not displayed."
    )
    if st.button("Sign out of this session", type="primary"):
        logout()


def main() -> None:
    if not st.session_state.access_token:
        auth_page(); return
    if not st.session_state.current_user and not load_me():
        auth_page(); return
    page = sidebar()
    pages = {
        "Overview": overview,
        "Projects": projects_page,
        "Documents": documents_page,
        "AI Assistant": assistant_page,
        "Database Access": database_access_page,
        "Tasks": tasks_page,
        "Account": account_page,
        "Users": users_page,
        "Roles": roles_page,
        "Database Connections": database_connections_page,
        "Database Permissions": database_permissions_page,
        "API Explorer": api_catalog_page,
    }
    pages[page]()


if __name__ == "__main__":
    main()
