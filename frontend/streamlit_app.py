import os
import re
import time
from html import escape
from typing import Any

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

#MainMenu, footer, [data-testid="stToolbar"] {visibility:hidden;}
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


def request_api(method: str, path: str, *, auth: bool = True, timeout: int = REQUEST_TIMEOUT, **kwargs: Any):
    headers = dict(kwargs.pop("headers", {}))
    if auth and st.session_state.access_token:
        headers["Authorization"] = f"Bearer {st.session_state.access_token}"
    try:
        response = requests.request(method, f"{st.session_state.api_url}{path}", headers=headers, timeout=timeout, **kwargs)
    except requests.RequestException as exc:
        return False, f"Backend connection failed: {exc}", 0
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
                ok, data, _ = request_api("POST", "/api/v1/auth/register", auth=False, json={"tenant_name": tenant_name, "tenant_code": tenant_code, "admin_full_name": full_name, "admin_email": email, "password": password, "confirm_password": confirm})
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
            ("Tasks", "◷  Tasks"),
            ("Account", "◎  Account"),
        ]
        if is_admin():
            navigation += [
                ("Users", "♙  Users"),
                ("Roles", "⌘  Roles"),
                ("Database Connections", "◉  Database Connections"),
                ("API Catalog", "⌁  API Catalog"),
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
    page_header("Workspace overview", "Monitor projects, documents, and account access.", "System online")
    projects = fetch_projects()
    full_name = user_data().get("user_full_name") or "there"
    first_name = str(full_name).split()[0]
    workspace_name = tenant_data().get("tenant_name") or "your workspace"
    st.markdown(
        f'<div class="hero"><div class="hero-kicker">Intelligence workspace</div>'
        f'<h2>Good to see you, {escape(first_name)}.</h2>'
        f'<p>{escape(str(workspace_name))} is ready. Organize your knowledge, index new files, and ask evidence-grounded questions from one secure place.</p></div>',
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
    page_header("Projects", "Organize documents into isolated knowledge spaces.")
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
    for p in fetch_projects():
        with st.expander(f"{p['project_name']}  ·  Project #{p['project_id']}"):
            st.write(p.get("project_description") or "No description")
            st.caption(f"Created: {p.get('created_at', '-')}")


def documents_page() -> None:
    page_header("Documents", "Upload, process, download, and re-index project files.")
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
            c1, c2, c3 = st.columns(3)
            c1.metric("Status", asset.get("asset_status", "-"))
            c2.metric("Size", f"{asset.get('asset_size', 0):,} B")
            c3.metric("Chunks", asset.get("asset_indexed_chunks", 0))
            if asset.get("asset_error"):
                st.error(asset["asset_error"])
            d_ok, content, _ = request_api("GET", f"/api/v1/projects/{project_id}/files/{asset['asset_id']}/download", timeout=120)
            if d_ok and isinstance(content, bytes):
                st.download_button("Download", content, file_name=name, mime=cfg.get("content_type") or "application/octet-stream", key=f"dl_{asset['asset_id']}")
            if can_manage_files():
                b1, b2 = st.columns(2)
                if b1.button("Reprocess", key=f"rp_{asset['asset_id']}"):
                    ok, result, _ = request_api("POST", f"/api/v1/projects/{project_id}/files/{asset['asset_id']}/reprocess")
                    if ok:
                        st.session_state.last_task_id = result.get("task_id")
                        st.success("Reprocessing queued.")
                    else:
                        st.error(result)
                if b2.button("Delete", key=f"del_{asset['asset_id']}"):
                    ok, result, _ = request_api("DELETE", f"/api/v1/projects/{project_id}/files/{asset['asset_id']}")
                    if ok:
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
    page_header("AI Assistant", "Ask grounded questions across the selected project's indexed documents.", "RAG enabled")
    project_id, project = project_selector("assistant_project")
    if project_id is None:
        return
    if st.session_state.chat_project_id != project_id:
        st.session_state.chat_project_id = project_id
        st.session_state.chat_messages = []
    st.markdown(f'<div class="hero"><div class="hero-kicker">Grounded AI assistant</div><h2>Chat with {escape(project["project_name"])}</h2><p>Ask in natural language and receive answers grounded in your indexed content. Open Sources under any response to verify the exact supporting file and location.</p></div>', unsafe_allow_html=True)
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
    page_header("Tasks", "Track background document processing jobs.")
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


def database_connections_page() -> None:
    page_header(
        "Database Connections",
        "Securely manage and test workspace PostgreSQL connections.",
        "Encrypted credentials",
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
                    st.success("Database connection deleted.")
                    st.rerun()
                else:
                    st.error(result)


def _load_openapi_catalog() -> tuple[list[dict[str, Any]], str | None]:
    """Load every FastAPI operation from OpenAPI without exposing raw JSON."""
    ok, schema, _ = request_api(
        "GET",
        "/openapi.json",
        auth=False,
        timeout=30,
    )
    if not ok:
        return [], str(schema)
    if not isinstance(schema, dict):
        return [], "The backend returned an invalid OpenAPI document."

    operations: list[dict[str, Any]] = []
    supported_methods = {"get", "post", "put", "patch", "delete"}

    for path, path_item in (schema.get("paths") or {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in supported_methods:
                continue
            operation = operation if isinstance(operation, dict) else {}
            tags = operation.get("tags") or ["Other"]
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
                    "tags": [str(tag) for tag in tags],
                    "requires_auth": bool(operation.get("security")),
                }
            )

    operations.sort(
        key=lambda item: (
            item["tags"][0].lower(),
            item["path"],
            item["method"],
        )
    )
    return operations, None


def api_catalog_page() -> None:
    page_header(
        "API Catalog",
        "A complete live catalog generated from the backend OpenAPI specification.",
        "Auto-synced",
    )

    operations, error = _load_openapi_catalog()
    if error:
        st.error(error)
        st.caption(
            "Confirm that FastAPI is running and that /openapi.json is available."
        )
        return

    if not operations:
        st.info("No API operations were found.")
        return

    methods = sorted({item["method"] for item in operations})
    tags = sorted({tag for item in operations for tag in item["tags"]})

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

    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in filtered:
        group = item["tags"][0] if item["tags"] else "Other"
        grouped.setdefault(group, []).append(item)

    for group, items in grouped.items():
        st.markdown(f"### {escape(group.title())}")
        for item in items:
            method_class = f"api-{item['method'].lower()}"
            auth_text = "Authentication required" if item["requires_auth"] else "Public endpoint"
            st.markdown(
                f'<div class="api-summary">'
                f'<div style="display:flex;gap:.75rem;align-items:flex-start">'
                f'<span class="api-method {method_class}">{escape(item["method"])}</span>'
                f'<div><div class="api-path">{escape(item["path"])}</div>'
                f'<div class="api-description">'
                f'{escape(str(item["summary"]))} · {escape(auth_text)}'
                f'</div></div></div></div>',
                unsafe_allow_html=True,
            )

    st.caption(
        "This page is generated from /openapi.json. New backend endpoints "
        "will appear automatically after the backend restarts."
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
        "Tasks": tasks_page,
        "Account": account_page,
        "Users": users_page,
        "Roles": roles_page,
        "Database Connections": database_connections_page,
        "API Catalog": api_catalog_page,
    }
    pages[page]()


if __name__ == "__main__":
    main()