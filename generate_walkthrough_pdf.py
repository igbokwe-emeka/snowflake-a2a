"""
generate_walkthrough_pdf.py
Generates a detailed, novice-friendly codebase walkthrough PDF for snowflake-a2a.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import textwrap, os

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "snowflake_a2a_walkthrough.pdf")

# ─── Colour palette ───────────────────────────────────────────────────────────
C_BRAND    = colors.HexColor("#0D2B4E")   # deep navy
C_ACCENT   = colors.HexColor("#29A8E0")   # sky blue
C_CODE_BG  = colors.HexColor("#F4F6F8")   # very light grey
C_CODE_FG  = colors.HexColor("#1A1A2E")   # near-black
C_WARN     = colors.HexColor("#E07B29")   # amber
C_OK       = colors.HexColor("#27AE60")   # green
C_HR       = colors.HexColor("#BDC3C7")   # light grey line

# ─── Styles ───────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

def S(name, **kw):
    """Create a named paragraph style."""
    base = kw.pop("parent", "Normal")
    s = ParagraphStyle(name, parent=styles[base], **kw)
    return s

TITLE      = S("MyTitle",    fontSize=26, textColor=C_BRAND,   spaceAfter=6,  spaceBefore=0,  alignment=TA_CENTER, fontName="Helvetica-Bold")
SUBTITLE   = S("MySub",      fontSize=13, textColor=C_ACCENT,  spaceAfter=20, spaceBefore=0,  alignment=TA_CENTER, fontName="Helvetica")
H1         = S("MyH1",       fontSize=17, textColor=C_BRAND,   spaceAfter=8,  spaceBefore=18, fontName="Helvetica-Bold", borderPad=4)
H2         = S("MyH2",       fontSize=13, textColor=C_ACCENT,  spaceAfter=6,  spaceBefore=14, fontName="Helvetica-Bold")
H3         = S("MyH3",       fontSize=11, textColor=C_BRAND,   spaceAfter=4,  spaceBefore=10, fontName="Helvetica-Bold")
BODY       = S("MyBody",     fontSize=9.5, leading=14,          spaceAfter=5,  spaceBefore=2,  alignment=TA_JUSTIFY, fontName="Helvetica")
BULLET     = S("MyBullet",   fontSize=9.5, leading=14,          spaceAfter=3,  spaceBefore=1,  leftIndent=16, bulletIndent=6, fontName="Helvetica")
CODE       = S("MyCode",     fontSize=8.2, leading=12,          spaceAfter=2,  spaceBefore=2,  fontName="Courier",
               backColor=C_CODE_BG, textColor=C_CODE_FG, leftIndent=10, rightIndent=4, borderPad=4,
               borderWidth=0, borderColor=C_CODE_BG)
LABEL      = S("MyLabel",    fontSize=8,  textColor=colors.white, fontName="Helvetica-Bold", alignment=TA_CENTER)
NOTE       = S("MyNote",     fontSize=8.5, textColor=C_WARN,   fontName="Helvetica-Oblique", spaceAfter=4)

# ─── Helpers ──────────────────────────────────────────────────────────────────
def hr():
    return HRFlowable(width="100%", thickness=0.5, color=C_HR, spaceAfter=6, spaceBefore=6)

def section_badge(text):
    """Coloured banner used as a section header background."""
    data = [[Paragraph(text, LABEL)]]
    t = Table(data, colWidths=["100%"])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), C_BRAND),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
    ]))
    return t

def file_badge(filename):
    data = [[Paragraph(f"  📄  {filename}", LABEL)]]
    t = Table(data, colWidths=["100%"])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), C_ACCENT),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 10),
    ]))
    return t

def code_block(lines_text):
    """Render code lines in a monospaced box."""
    parts = []
    for line in lines_text.splitlines():
        safe = line.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        parts.append(Paragraph(safe if safe.strip() else "&nbsp;", CODE))
    return parts

def annotated_line(lineno, code_text, explanation):
    """A two-column table: line number + code | explanation."""
    code_safe = code_text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
    left  = Paragraph(f'<font name="Courier" size="7.5" color="#555555">{lineno:>4} </font>'
                      f'<font name="Courier" size="8" color="#1A1A2E">{code_safe}</font>', BODY)
    right = Paragraph(f'<font size="8.5">{explanation}</font>', BODY)
    t = Table([[left, right]], colWidths=[8.5*cm, 8.5*cm])
    t.setStyle(TableStyle([
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("BACKGROUND",    (0,0), (0,-1),  C_CODE_BG),
        ("LEFTPADDING",   (0,0), (0,-1),  4),
        ("RIGHTPADDING",  (0,0), (0,-1),  6),
        ("LEFTPADDING",   (1,0), (1,-1),  8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("LINEBELOW",     (0,0), (-1,-1), 0.3, C_HR),
    ]))
    return t

def bullet(text):
    return Paragraph(f"• {text}", BULLET)

def kv_table(rows):
    """Key-value table for env vars / config."""
    data = [[Paragraph(f"<b>{k}</b>", CODE), Paragraph(v, BODY)] for k,v in rows]
    t = Table(data, colWidths=[6*cm, 11*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (0,-1), C_CODE_BG),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
        ("GRID",          (0,0), (-1,-1), 0.3, C_HR),
    ]))
    return t

# ─── Content builder ──────────────────────────────────────────────────────────

def build_story():
    story = []

    # ── Cover ──────────────────────────────────────────────────────────────────
    story += [
        Spacer(1, 2*cm),
        Paragraph("Snowflake Cortex A2A Proxy", TITLE),
        Paragraph("Complete Line-by-Line Codebase Walkthrough", SUBTITLE),
        Paragraph("For Novice Developers", S("CoverNote", parent="Normal",
                  fontSize=11, textColor=colors.grey, alignment=TA_CENTER)),
        Spacer(1, 0.5*cm),
        hr(),
        Spacer(1, 0.3*cm),
        Paragraph(
            "This document walks through every file in the <b>snowflake-a2a</b> project, "
            "explaining each block of code in plain English so that anyone new to Python, "
            "APIs, or cloud deployments can follow along.",
            S("CoverBody", parent="Normal", fontSize=10, leading=15,
              textColor=C_BRAND, alignment=TA_CENTER)),
        Spacer(1, 1*cm),
    ]

    # ── Architecture overview ──────────────────────────────────────────────────
    story += [
        PageBreak(),
        section_badge("ARCHITECTURE OVERVIEW"),
        Spacer(1, 0.4*cm),
        Paragraph("What does this project do?", H1),
        Paragraph(
            "This project is a <b>middleman service</b> (called a <i>proxy</i>) that sits "
            "between two AI platforms: <b>Google Gemini Enterprise</b> and <b>Snowflake Cortex</b>. "
            "When a user types a question into Gemini, Gemini forwards it here. This proxy "
            "then passes the question — along with the user's identity — to Snowflake's AI "
            "agent, which does the heavy thinking and sends back an answer. The proxy relays "
            "that answer back to Gemini.", BODY),
        Paragraph("Why do we need a proxy?", H2),
        Paragraph(
            "Snowflake requires an <b>OAuth token</b> (a digital key that proves who you are) to answer "
            "questions. Gemini does not speak Snowflake's language natively, so this proxy "
            "translates the request format <i>and</i> forwards the user's own identity token — "
            "so Snowflake knows exactly which user is asking.", BODY),
        Paragraph("Protocol: A2A JSON-RPC 2.0", H2),
        Paragraph(
            "The proxy speaks the <b>Agent-to-Agent (A2A)</b> protocol — a standard way for AI "
            "agents to communicate using JSON-RPC 2.0 messages. Think of JSON-RPC like "
            "a phone call format: you send a structured 'request' object and get back a "
            "structured 'response' object.", BODY),
        Spacer(1, 0.3*cm),
        Paragraph("Request / Response flow", H3),
    ]

    flow_data = [
        ["Step", "From", "To", "What happens"],
        ["1", "User", "Gemini", "User types a question"],
        ["2", "Gemini", "A2A Proxy (Cloud Run)", "POST /query + Bearer token"],
        ["3", "A2A Proxy", "Snowflake Cortex", "POST /api/v2/agents/…:run + same token"],
        ["4", "Snowflake", "A2A Proxy", "SSE streaming response"],
        ["5", "A2A Proxy", "Gemini", "JSON-RPC 2.0 result"],
        ["6", "Gemini", "User", "Displays the answer"],
    ]
    ft = Table(flow_data, colWidths=[1.5*cm, 4*cm, 5*cm, 7*cm])
    ft.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  C_BRAND),
        ("TEXTCOLOR",     (0,0), (-1,0),  colors.white),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, C_CODE_BG]),
        ("GRID",          (0,0), (-1,-1), 0.3, C_HR),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
    ]))
    story += [ft, Spacer(1, 0.4*cm)]

    story += [
        Paragraph("File map", H2),
    ]
    file_map = [
        ["File", "Purpose"],
        ["main.py",               "FastAPI server — handles all incoming HTTP requests"],
        ["auth.py",               "JWT decoding & Snowflake header builder"],
        ["deploy.py",             "One-command deployment: build → Cloud Run → OAuth → register"],
        ["register_a2a_agent.py", "Registers this proxy as an agent inside Gemini Enterprise"],
        ["requirements.txt",      "Lists Python packages the project needs"],
        ["env.template",          "Template for the .env configuration file"],
        ["Dockerfile",            "Recipe for building the container image"],
    ]
    fmt = Table(file_map, colWidths=[5*cm, 12*cm])
    fmt.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  C_ACCENT),
        ("TEXTCOLOR",     (0,0), (-1,0),  colors.white),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,-1), 8.5),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, C_CODE_BG]),
        ("GRID",          (0,0), (-1,-1), 0.3, C_HR),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
    ]))
    story += [fmt, PageBreak()]

    # ══════════════════════════════════════════════════════════════════════════
    # FILE 1 — main.py
    # ══════════════════════════════════════════════════════════════════════════
    story += [
        section_badge("FILE 1 OF 4  —  main.py"),
        Spacer(1, 0.3*cm),
        Paragraph("main.py — The Heart of the Application", H1),
        Paragraph(
            "This is the entry point of the whole system. It starts the web server, "
            "defines all the URL routes (the addresses you can send requests to), and "
            "contains the core logic that handles every query from Gemini.", BODY),
        Spacer(1, 0.2*cm),
    ]

    # ── Imports block ─────────────────────────────────────────────────────────
    story += [
        Paragraph("Section 1 — Imports (lines 1–9)", H2),
        Paragraph(
            "Every Python file starts by <b>importing</b> — bringing in tools and libraries "
            "from other files so you do not have to write everything from scratch.", BODY),
    ]
    import_lines = [
        (1,  "import os",         "Lets us read environment variables (settings stored outside the code)."),
        (2,  "import uuid",       "Generates unique random IDs — used to label each response."),
        (3,  "import json",       "Converts Python objects ↔ JSON strings (the data format APIs use)."),
        (4,  "import requests",   "A popular library for making HTTP calls to other APIs."),
        (5,  "import uvicorn",    "The web-server engine that runs our FastAPI app."),
        (6,  "import asyncio",    "Allows code to run tasks concurrently without blocking."),
        (7,  "from fastapi import FastAPI, Request, Header, HTTPException",
                                  "FastAPI framework: builds the API; Request = incoming data; Header = HTTP headers; HTTPException = error responses."),
        (8,  "from auth import decode_token_claims, get_snowflake_headers",
                                  "Imports our own auth.py functions (covered in File 2)."),
        (9,  "from dotenv import load_dotenv",
                                  "Reads the .env file so environment variables are available at runtime."),
    ]
    for ln, code, expl in import_lines:
        story.append(annotated_line(ln, code, expl))
    story.append(Spacer(1, 0.3*cm))

    # ── load_dotenv + app ─────────────────────────────────────────────────────
    story += [
        Paragraph("Section 2 — App Initialisation (lines 11–13)", H2),
        Paragraph("Two things happen here: environment variables are loaded, and the web app is created.", BODY),
    ]
    for ln, code, expl in [
        (11, "load_dotenv()",
             "Reads the .env file (if it exists) and makes all KEY=VALUE pairs available via os.getenv()."),
        (13, 'app = FastAPI(title="Snowflake Cortex Proxy")',
             "Creates the FastAPI application object. 'app' is the central object — every route is attached to it."),
    ]:
        story.append(annotated_line(ln, code, expl))
    story.append(Spacer(1, 0.3*cm))

    # ── _get_snowflake_urls ───────────────────────────────────────────────────
    story += [
        Paragraph("Section 3 — _get_snowflake_urls() (lines 15–26)", H2),
        Paragraph(
            "This function builds the two HTTP URLs we can use to call the Snowflake Cortex Agent. "
            "Snowflake has two addressing schemes — by account name and by account locator — "
            "so we build both as a fallback option.", BODY),
    ]
    for ln, code, expl in [
        (15, "def _get_snowflake_urls():",
             "Defines the function. The leading underscore (_) is a Python convention meaning 'private — only used inside this file'."),
        (16, '    account = os.getenv("SNOWFLAKE_ACCOUNT", "")',
             "Reads SNOWFLAKE_ACCOUNT from environment variables. If not set, defaults to an empty string."),
        (17, '    account_locator = os.getenv("SNOWFLAKE_ACCOUNT_LOCATOR", "")',
             "Same for the alternative account locator identifier."),
        (18, '    db = os.getenv("AGENT_DATABASE", "")',
             "The Snowflake database that contains the agent."),
        (19, '    schema = os.getenv("AGENT_SCHEMA", "")',
             "The schema (sub-namespace) inside that database."),
        (20, '    cortex_agent = os.getenv("AGENT_NAME", "")',
             "The name of the specific Cortex Agent to query."),
        (22, '    path = f"/api/v2/databases/{db}/schemas/{schema}/agents/{cortex_agent}:run"',
             "Constructs the URL path using an f-string — Python's way of embedding variables inside strings."),
        (24, '    api_url = f"https://{account}.snowflakecomputing.com{path}" if account else ""',
             "Builds the primary URL only if account is non-empty; otherwise uses empty string."),
        (25, '    api_url_locator = f"https://{account_locator}.snowflakecomputing.com{path}" if account_locator else ""',
             "Builds the fallback URL using the account locator."),
        (26, "    return api_url, api_url_locator",
             "Returns BOTH URLs as a tuple — the caller decides which to use."),
    ]:
        story.append(annotated_line(ln, code, expl))
    story.append(Spacer(1, 0.3*cm))

    # ── _parse_cortex_sse ─────────────────────────────────────────────────────
    story += [
        Paragraph("Section 4 — _parse_cortex_sse() (lines 28–61)", H2),
        Paragraph(
            "Snowflake streams its answer back as <b>Server-Sent Events (SSE)</b> — a format where "
            "the server sends a series of small text chunks, each prefixed with 'event:' and 'data:'. "
            "This function reads that stream and extracts just the answer text.", BODY),
        Paragraph(
            "<b>Important:</b> Snowflake sends each piece of text TWICE — once as a "
            "<i>delta</i> (incremental chunk) and once as the complete block. We only collect "
            "the delta events to avoid duplicating the answer.", NOTE),
    ]
    for ln, code, expl in [
        (28,  "def _parse_cortex_sse(raw_text: str) -> str:",
              "Function signature. Takes the full raw SSE text string; must return a plain string."),
        (35,  "    answer_parts = []",
              "Empty list — we'll append text pieces here as we find them."),
        (36,  "    current_event = None",
              "Tracks which event type the current 'data:' line belongs to."),
        (38,  "    for line in raw_text.splitlines():",
              "Loops over every line in the SSE response."),
        (39,  '        if line.startswith("event:"):',
              "Detects event type lines like 'event: response.text.delta'."),
        (40,  "            current_event = line[6:].strip()",
              "Strips the 'event:' prefix and surrounding whitespace, stores the event name."),
        (41,  "            continue",
              "Moves to the next line — no data to extract from an event-type line."),
        (43,  '        if not line.startswith("data:"):',
              "Skip any line that isn't a data line (blank lines, comments, etc.)."),
        (45,  "        data_str = line[5:].strip()",
              "Strips the 'data:' prefix (5 characters)."),
        (46,  '        if not data_str or data_str == "[DONE]":',
              "'[DONE]' is the SSE end-of-stream sentinel. Empty strings are also skipped."),
        (49,  '        if current_event != "response.text.delta":',
              "Only process delta events — skip complete-text events to prevent duplication."),
        (52,  "        try:",
              "Start error-safe block in case the JSON is malformed."),
        (53,  "            data = json.loads(data_str)",
              "Parses the JSON payload after 'data:'."),
        (54,  '            text = data.get("text", "")',
              "Reads the 'text' key from the parsed JSON; defaults to empty string if absent."),
        (55,  "            if text:",
              "Only append if there is actual text content."),
        (56,  "                answer_parts.append(text)",
              "Adds this chunk to our growing list of text pieces."),
        (60,  '    result = "".join(answer_parts).strip()',
              "Joins all pieces into one string and removes leading/trailing whitespace."),
        (61,  '    return result if result else "(No text in Cortex response)"',
              "Returns the assembled answer, or a fallback message if nothing was found."),
    ]:
        story.append(annotated_line(ln, code, expl))
    story.append(Spacer(1, 0.3*cm))

    # ── _call_snowflake ───────────────────────────────────────────────────────
    story += [
        Paragraph("Section 5 — _call_snowflake() (lines 63–65)", H2),
        Paragraph(
            "A tiny helper that makes the actual HTTP POST request to Snowflake. "
            "It is separated into its own function so that the main logic is easier to read.", BODY),
    ]
    for ln, code, expl in [
        (63, "def _call_snowflake(url, headers, payload):",
             "Takes the endpoint URL, authentication headers, and the JSON body to send."),
        (65, "    return requests.post(url, json=payload, headers=headers, timeout=120, stream=True)",
             "Makes the POST request. json= auto-serialises the dict. timeout=120 means give up after 2 minutes. stream=True fetches the response in chunks (needed for SSE)."),
    ]:
        story.append(annotated_line(ln, code, expl))
    story.append(Spacer(1, 0.3*cm))

    # ── Routes ────────────────────────────────────────────────────────────────
    story += [
        Paragraph("Section 6 — HTTP Route Handlers (lines 67–91)", H2),
        Paragraph(
            "FastAPI uses <b>decorators</b> (the @app.xxx lines above each function) to map "
            "URL paths to Python functions. When an HTTP request arrives at that path, FastAPI "
            "automatically calls the matching function.", BODY),
    ]
    for ln, code, expl in [
        (67,  '@app.api_route("/", methods=["GET", "POST"])',
              "Register this function for BOTH GET and POST requests to the root URL '/'."),
        (68,  "async def root_handler(request: Request, authorization: str = Header(None)):",
              "'async def' means this function can pause while waiting for I/O. 'authorization' is automatically pulled from the HTTP Authorization header."),
        (70,  '    if request.method == "GET":',
              "If it's a browser checking if the server is alive..."),
        (71,  '        return {"status": "ok", "message": "Snowflake Cortex Proxy is running"}',
              "...return a simple health-check JSON response."),
        (72,  "    return await handle_query(request, authorization)",
              "For POST requests, delegate to the main handler (defined later). 'await' pauses here until handle_query finishes."),
        (74,  '@app.get("/health")',
              "Register a dedicated health check route at /health."),
        (76,  '    return {"status": "ok"}',
              "Returns minimal OK response — used by Cloud Run to verify the service is healthy."),
        (78,  '@app.get("/.well-known/agent.json")',
              "Register route for the A2A 'agent card' — a standardised URL where other agents can discover capabilities."),
        (81,  '    cloud_run_url = os.getenv("AGENT_URL", "").strip() or ...',
              "Reads the service's own public URL from env. Falls back to a constructed URL using the K_SERVICE env var (set automatically by Cloud Run)."),
        (82,  '    return { "name": ..., "capabilities": ... }',
              "Returns a JSON object describing this agent: its name, what it can do, input/output formats, and protocol version."),
    ]:
        story.append(annotated_line(ln, code, expl))
    story.append(Spacer(1, 0.3*cm))

    # ── handle_query ──────────────────────────────────────────────────────────
    story += [
        PageBreak(),
        Paragraph("Section 7 — handle_query() (lines 93–229)", H1),
        Paragraph(
            "This is the most important function in the entire codebase. It receives every query "
            "from Gemini, figures out who is asking, contacts Snowflake, and returns the answer. "
            "Let's walk through it in phases.", BODY),
    ]

    story += [Paragraph("Phase A — Parse the request body (lines 99–128)", H2)]
    for ln, code, expl in [
        (100, "    body = await request.json()",
              "Reads and parses the JSON body of the incoming HTTP request. 'await' pauses until the body is fully received."),
        (104, '    is_json_rpc = body.get("jsonrpc") == "2.0"',
              "Checks if this is a JSON-RPC 2.0 message (the A2A standard format). body.get() safely returns None if the key doesn't exist."),
        (105, '    params = body.get("params", {})',
              "Extracts the 'params' object; defaults to empty dict {} if missing."),
        (107, "    if is_json_rpc:",
              "If the message is in JSON-RPC format..."),
        (108, '        message = params.get("message", {})',
              "...dig into the nested message object."),
        (109, '        parts = message.get("parts", [])',
              "A2A messages contain a 'parts' array — each part can be text, image, etc."),
        (111, '        if part.get("kind") == "text" or "text" in part:',
              "Look for a part that is text (either explicitly labelled 'kind: text' or containing a 'text' key)."),
        (112, "            text = part.get(\"text\")",
              "Extract the actual text string from that part."),
        (113, "            break",
              "Stop after finding the first text part — we don't need to keep looking."),
        (116, "    if not text:",
              "If we didn't find text in the JSON-RPC format, try simpler flat fields."),
        (117, '    text = body.get("text") or body.get("query") or ...',
              "Try common field names. Python's 'or' chain returns the first truthy (non-empty) value."),
        (119, "    if not text:",
              "If still no text was found, the request is malformed."),
        (122, "        if is_json_rpc:",
              "Return an error in the appropriate format depending on how the request came in."),
        (123, '            return {"jsonrpc":"2.0","id":...,"error":{"code":-32602,"message":...}}',
              "JSON-RPC error format: code -32602 means 'Invalid params' per the spec."),
    ]:
        story.append(annotated_line(ln, code, expl))
    story.append(Spacer(1, 0.2*cm))

    story += [Paragraph("Phase B — Ping test (lines 132–145)", H2),
              Paragraph(
                  "A simple liveness test — if anyone sends 'ping', we immediately respond 'pong' "
                  "without calling Snowflake. Useful for verifying connectivity.", BODY)]
    for ln, code, expl in [
        (133, '    if text.lower().strip() == "ping":',
              ".lower() makes it case-insensitive; .strip() removes accidental spaces."),
        (134, "        if is_json_rpc:",
              "Format the 'pong' response in the correct protocol format."),
        (145, '        return {"text": "pong"}',
              "Simple format for legacy/non-JSON-RPC callers."),
    ]:
        story.append(annotated_line(ln, code, expl))
    story.append(Spacer(1, 0.2*cm))

    story += [Paragraph("Phase C — Build Snowflake payload (lines 147–149)", H2),
              Paragraph(
                  "Snowflake Cortex expects the query wrapped in a specific JSON structure "
                  "that mirrors the OpenAI chat format.", BODY)]
    for ln, code, expl in [
        (147, '    payload = {',
              "Start building the JSON body we will send to Snowflake."),
        (148, '        "messages": [{"role": "user", "content": [{"type": "text", "text": text}]}]',
              "Snowflake expects: a messages array where each item has a role ('user' or 'assistant') and a content array with type+text."),
    ]:
        story.append(annotated_line(ln, code, expl))
    story.append(Spacer(1, 0.2*cm))

    story += [Paragraph("Phase D — Authentication & Snowflake call (lines 153–197)", H2),
              Paragraph(
                  "This is the security-critical section. We inspect the Bearer token to decide "
                  "how to proceed. There are three possible paths:", BODY),
              bullet("No token → prompt user to connect their Microsoft account"),
              bullet("GCP service account token → prompt user to connect (Gemini's own token, not the user's)"),
              bullet("Entra ID user token → call Snowflake with the propagated token"),
              Spacer(1, 0.15*cm)]
    for ln, code, expl in [
        (154, '    authorization = request.headers.get("Authorization", "")',
              "Read the Authorization header directly from the request (overrides the function parameter to be safe)."),
        (157, '    if authorization and authorization.lower().startswith("bearer "):',
              "Checks that the header exists AND starts with 'Bearer ' (case-insensitive check via .lower())."),
        (158, '        token = authorization.split(" ", 1)[1].strip()',
              "Splits 'Bearer eyJhbGci...' on the space and takes the part after it (index [1])."),
        (159, '        claims = decode_token_claims(token)',
              "Calls our auth.py function to decode the JWT and get its claims (e.g., email, subject)."),
        (160, '        token_email = claims.get("email", "")',
              "Extracts the email claim from the decoded token."),
        (161, '        is_service_account = "gserviceaccount.com" in token_email',
              "Google service accounts always have 'gserviceaccount.com' in their email — this is how we detect them."),
        (163, '        if is_service_account:',
              "Path 1: Service account detected — this is Gemini's own token, not the user's."),
        (166, '            final_answer = "Please connect your Microsoft account..."',
              "Tell the user they need to do the OAuth 'Connect' flow inside Gemini to link their Microsoft account."),
        (169, '        email = next(',
              "Path 2: User token detected. Find the email using the first of several possible JWT claim names."),
        (175, '        headers = get_snowflake_headers(token=token)',
              "Build the HTTP headers for Snowflake, including the Authorization: Bearer header with the user's token."),
        (178, '        response = await asyncio.to_thread(_call_snowflake, api_url, headers, payload)',
              "Run the blocking _call_snowflake() in a separate thread so the async server isn't blocked while waiting."),
        (181, '        if response.status_code == 200:',
              "HTTP 200 = success. Parse the SSE response."),
        (183, '            final_answer = _parse_cortex_sse(response.text)',
              "Extract the plain-text answer from the SSE stream."),
        (190, '            final_answer = f"Snowflake Error {response.status_code}: {raw[:500]}"',
              "Non-200 status: include the error code and first 500 chars of the error body in the answer."),
        (195, "    else:",
              "Path 3: No Authorization header at all."),
        (197, '        final_answer = "Please connect your Microsoft account..."',
              "Same connect prompt as the service account path."),
    ]:
        story.append(annotated_line(ln, code, expl))
    story.append(Spacer(1, 0.2*cm))

    story += [Paragraph("Phase E — Format and return the response (lines 199–223)", H2),
              Paragraph(
                  "The final answer text is wrapped in the correct response envelope "
                  "depending on whether the original request was JSON-RPC 2.0 or legacy format.", BODY)]
    for ln, code, expl in [
        (200, "    if is_json_rpc:",
              "If the caller used JSON-RPC 2.0 format..."),
        (201, '        context_id = params.get("message", {}).get("messageId", str(uuid.uuid4()))',
              "Read the original message ID to include in the response (allows correlation). Generate a new UUID if not provided."),
        (202, '        return {"jsonrpc": "2.0", "id": body.get("id"), "result": {...}}',
              "Standard JSON-RPC 2.0 success response: version, request ID echo, and result containing the artifacts."),
        (209, '            "artifacts": [{"artifactId": str(uuid.uuid4()), "name": "response", "parts": [...]}]',
              "A2A 'artifacts' wrap the answer. Each artifact has a unique ID, a name, and an array of parts (text)."),
        (219, "    return {",
              "Legacy (non-JSON-RPC) format: simpler flat object."),
        (220, '        "query": text,',
              "Echo back the original query."),
        (221, '        "response": final_answer,',
              "The answer from Snowflake."),
        (222, '        "propagated": bool(...)',
              "True if a Bearer token was successfully propagated to Snowflake; False otherwise."),
    ]:
        story.append(annotated_line(ln, code, expl))
    story.append(Spacer(1, 0.2*cm))

    story += [Paragraph("Section 8 — Entry point (lines 231–234)", H2),
              Paragraph(
                  "When you run 'python main.py' directly, Python sets __name__ to '__main__'. "
                  "This block starts the web server.", BODY)]
    for ln, code, expl in [
        (231, 'if __name__ == "__main__":',
              "Standard Python idiom: this block only runs when the file is executed directly, not when it's imported."),
        (232, '    port = int(os.getenv("PORT", 8080))',
              "Read the port from environment; default to 8080 (the standard Cloud Run port). int() converts the string to a number."),
        (234, '    uvicorn.run(app, host="0.0.0.0", port=port)',
              "Start the ASGI web server. host='0.0.0.0' means accept connections from any network interface (required in containers)."),
    ]:
        story.append(annotated_line(ln, code, expl))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # FILE 2 — auth.py
    # ══════════════════════════════════════════════════════════════════════════
    story += [
        section_badge("FILE 2 OF 4  —  auth.py"),
        Spacer(1, 0.3*cm),
        Paragraph("auth.py — Authentication & Token Helpers", H1),
        Paragraph(
            "This small but important file handles everything related to OAuth tokens. "
            "It provides two utility functions used by main.py: one to read a JWT token "
            "and one to build the correct headers for Snowflake.", BODY),
        Spacer(1, 0.2*cm),
    ]

    story += [Paragraph("Section 1 — Imports (lines 1–9)", H2)]
    for ln, code, expl in [
        (1,  '"""Authentication module..."""',
             "Module docstring — describes the file's purpose. Triple quotes allow multi-line strings."),
        (5,  "import json",
             "JSON parsing utility (imported but not actively used here; present for potential future use)."),
        (6,  "import jwt",
             "PyJWT library — Python's standard library for encoding/decoding JSON Web Tokens."),
        (7,  "from dotenv import load_dotenv",
             "For reading .env files."),
        (9,  "load_dotenv()",
             "Load environment variables from .env file immediately when this module is imported."),
    ]:
        story.append(annotated_line(ln, code, expl))
    story.append(Spacer(1, 0.2*cm))

    story += [Paragraph("Section 2 — decode_token_claims() (lines 12–18)", H2),
              Paragraph(
                  "A JWT (JSON Web Token) is a base64-encoded string with three parts separated by dots: "
                  "<b>header.payload.signature</b>. The payload contains <i>claims</i> — facts "
                  "about the user like their email and username. This function reads those claims.", BODY),
              Paragraph(
                  "<b>Security Note:</b> We decode WITHOUT verifying the signature. This is intentional — "
                  "we trust that Gemini Enterprise has already verified the token before passing it to us. "
                  "Verifying ourselves would require Entra ID's public keys.", NOTE)]
    for ln, code, expl in [
        (12, "def decode_token_claims(token: str) -> dict:",
             "Type hints: token must be a string (str), and the function returns a dictionary (dict)."),
        (13, '    """Decode a JWT token WITHOUT verification..."""',
             "Docstring explaining the function's behaviour — important for security audit purposes."),
        (14, "    try:",
             "Wrap in try/except so a bad token doesn't crash the whole server."),
        (15, '        return jwt.decode(token, options={"verify_signature": False})',
             "PyJWT's decode() reads the payload. The options dict disables signature verification."),
        (17, "    except Exception as e:",
             "Catch ANY exception — malformed tokens, null bytes, etc."),
        (18, "        return {}",
             "Return empty dict on failure — callers use .get() so this is safe."),
    ]:
        story.append(annotated_line(ln, code, expl))
    story.append(Spacer(1, 0.2*cm))

    story += [Paragraph("Section 3 — get_snowflake_headers() (lines 21–28)", H2),
              Paragraph(
                  "Snowflake needs specific HTTP headers to accept an OAuth token instead of "
                  "its default key-pair authentication. This function builds those headers.", BODY)]
    for ln, code, expl in [
        (21, "def get_snowflake_headers(token: str) -> dict:",
             "Takes the raw OAuth token string; returns a dict of HTTP headers."),
        (23, '    "Authorization": f"Bearer {token}"',
             "Standard HTTP Authorization header: the word 'Bearer' followed by the token."),
        (24, '    "Content-Type": "application/json"',
             "Tells Snowflake that the request body is JSON."),
        (25, '    "Accept": "application/json"',
             "Tells Snowflake that we want a JSON response (not XML or plain text)."),
        (27, '    "X-Snowflake-Authorization-Token-Type": "OAUTH"',
             "Snowflake-specific header: instructs Snowflake to treat the Bearer token as OAuth rather than a JWT key-pair."),
    ]:
        story.append(annotated_line(ln, code, expl))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # FILE 3 — deploy.py
    # ══════════════════════════════════════════════════════════════════════════
    story += [
        section_badge("FILE 3 OF 4  —  deploy.py"),
        Spacer(1, 0.3*cm),
        Paragraph("deploy.py — Automated Deployment Orchestrator", H1),
        Paragraph(
            "Run this one file and it handles everything: building the Docker container, "
            "deploying it to Google Cloud Run, creating the OAuth authorization resource, "
            "and registering the agent with Gemini Enterprise.", BODY),
        Spacer(1, 0.2*cm),
    ]

    story += [Paragraph("Section 1 — Imports & global config (lines 1–21)", H2)]
    for ln, code, expl in [
        (7,  "import subprocess",
             "Lets Python run shell commands — used to call the gcloud CLI."),
        (8,  "import urllib.request",
             "Python's built-in HTTP library — used for REST API calls to Google Discovery Engine."),
        (9,  "import urllib.error",
             "Exception types for HTTP errors (404, 403, etc.)."),
        (10, "import urllib.parse",
             "URL encoding/decoding utilities."),
        (15, 'REGION = os.getenv("GCP_REGION", "us-central1")',
             "Read deployment region; default to us-central1 (Iowa, USA)."),
        (19, "if not PROJECT_ID:",
             "Fail early and loudly if a required config value is missing — better than a cryptic error later."),
        (21, "    sys.exit(1)",
             "sys.exit(1) terminates the script with an error code of 1 (non-zero = failure)."),
    ]:
        story.append(annotated_line(ln, code, expl))
    story.append(Spacer(1, 0.2*cm))

    story += [Paragraph("Section 2 — gcloud() helper (lines 24–30)", H2),
              Paragraph(
                  "All Google Cloud operations are done through the 'gcloud' command-line tool. "
                  "This wrapper function makes it easy to call gcloud from Python.", BODY)]
    for ln, code, expl in [
        (24, "def gcloud(*args, check=True):",
             "*args collects any number of arguments into a tuple. check=True means exit if the command fails."),
        (25, '    cmd = "gcloud.cmd" if sys.platform == "win32" else "gcloud"',
             "On Windows, gcloud is installed as 'gcloud.cmd' (a batch file), not just 'gcloud'."),
        (26, '    result = subprocess.run([cmd] + list(args), capture_output=True, text=True)',
             "subprocess.run() runs an external command. capture_output=True captures stdout/stderr. text=True returns strings not bytes."),
        (27, "    if check and result.returncode != 0:",
             "returncode 0 = success, anything else = failure. Exit if check mode is on."),
        (30, "    return result.stdout.strip()",
             "Return the command's output (e.g., the Cloud Run URL) with trailing whitespace removed."),
    ]:
        story.append(annotated_line(ln, code, expl))
    story.append(Spacer(1, 0.2*cm))

    story += [Paragraph("Section 3 — OAuth authorization management (lines 42–181)", H2),
              Paragraph(
                  "Before Gemini can forward user tokens to this proxy, we need to create an "
                  "<b>OAuth authorization resource</b> in Google Discovery Engine. This is the "
                  "plumbing that enables the 'Connect' button users see in Gemini.", BODY)]
    for ln, code, expl in [
        (42, "def _auth_url(auth_id):",
             "Builds the Google API URL for a specific authorization resource by its ID."),
        (49, "def authorization_exists(token, auth_id) -> bool:",
             "Checks if an authorization resource with this ID already exists — returns True/False."),
        (51, "    req = urllib.request.Request(..., method='GET')",
             "urllib.request.Request creates an HTTP request object. method='GET' asks for the resource without modifying it."),
        (57, "    with urllib.request.urlopen(req):",
             "'with' ensures the connection is closed after use. urlopen() sends the request."),
        (58, "        return True",
             "If we got here without an exception, the resource exists."),
        (60, "    except urllib.error.HTTPError as e:",
             "HTTPError is raised for any non-2xx response."),
        (61, "        if e.code == 404:",
             "404 = Not Found — resource doesn't exist yet."),
        (66, "def delete_authorization(token, auth_id):",
             "Sends a DELETE request to remove the authorization resource. Needed before recreating it."),
        (80, "def delete_registered_agents(token, agent_name):",
             "Before deleting the auth resource, we must unlink any agents using it — Google API requires this order."),
        (96, "        agents = json.loads(resp.read().decode()).get('agents', [])",
             "resp.read() reads the raw bytes; .decode() converts to string; json.loads() parses it; .get('agents',[]) extracts the list."),
        (117, "def create_authorization(token, auth_id):",
              "Creates a new OAuth authorization resource for Entra ID (Azure AD)."),
        (122, "    default_scopes = f'api://{client_id}/session:role-any openid offline_access'",
              "The OAuth scopes: api://... is a Snowflake-specific scope; openid gets the user's identity; offline_access enables token refresh."),
        (131, "    base_auth_url = os.getenv('OAUTH_AUTH_URL') or ...",
              "Use custom auth URL if provided, otherwise build the standard Entra ID v2.0 authorize endpoint."),
        (133, "    params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)",
              "parse_qs() turns 'foo=1&bar=2' into {'foo':['1'], 'bar':['2']} — a dict of URL query parameters."),
        (136, "    params['redirect_uri'] = [redirect_uri]",
              "The redirect URI tells Azure where to send the user after they authenticate — must be Google's OAuth handler page."),
        (137, "    params['prompt'] = ['consent']",
              "Forces the Azure consent screen to appear — required to get the offline_access (refresh token) permission."),
        (145, "    payload = {'displayName': auth_id, 'serverSideOauth2': {...}}",
              "The full payload for the Google Discovery Engine API: display name + OAuth2 configuration with client ID, secret, endpoints, and scopes."),
    ]:
        story.append(annotated_line(ln, code, expl))
    story.append(Spacer(1, 0.2*cm))

    story += [Paragraph("Section 4 — main() — The 4-step deployment (lines 200–257)", H2),
              Paragraph("This is the top-level function. Run 'python deploy.py' and this executes.", BODY)]
    steps = [
        ("Step 1: Build (line 216)",
         "gcloud builds submit --tag {image} .",
         "Uploads the source code to Google Cloud Build, which builds the Docker container and pushes it to Artifact Registry. '.' means 'use current directory as context'."),
        ("Step 2: Deploy (lines 221–231)",
         "gcloud run deploy {service_name} ...",
         "Deploys the container to Cloud Run. --allow-unauthenticated: Gemini can call without GCP credentials. --min-instances=1: always keep one instance warm. --set-env-vars: passes config from .env to the running container."),
        ("Step 3: Get URL (lines 234–240)",
         "gcloud run services describe ... --format=value(status.url)",
         "Queries Cloud Run to get the HTTPS URL of the deployed service. Stores it so the registration script can use it."),
        ("Step 4: Register (lines 242–253)",
         "manage_authorization() + register_a2a_agent.py",
         "Creates the OAuth resource in Discovery Engine, then runs register_a2a_agent.py as a subprocess to register the agent with Gemini Enterprise."),
    ]
    for title, cmd, explanation in steps:
        story += [
            Paragraph(title, H3),
            *code_block(f"    {cmd}"),
            Paragraph(explanation, BODY),
            Spacer(1, 0.2*cm),
        ]

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # FILE 4 — register_a2a_agent.py
    # ══════════════════════════════════════════════════════════════════════════
    story += [
        section_badge("FILE 4 OF 4  —  register_a2a_agent.py"),
        Spacer(1, 0.3*cm),
        Paragraph("register_a2a_agent.py — Gemini Enterprise Registration", H1),
        Paragraph(
            "This script tells Gemini Enterprise that our proxy exists and how to use it. "
            "It registers the proxy as an A2A agent in Google Discovery Engine so that "
            "Gemini users can find and invoke it.", BODY),
        Spacer(1, 0.2*cm),
    ]

    story += [Paragraph("Section 1 — Configuration loading (lines 11–28)", H2),
              Paragraph(
                  "Unlike main.py which reads env vars lazily (at request time), "
                  "this script reads everything at module load time and fails immediately if "
                  "required values are missing.", BODY)]
    for ln, code, expl in [
        (11, "def _env(key, default=''):",
             "Custom env reader that also strips surrounding quotes — some .env editors add extra quotes."),
        (13, "    return os.getenv(key, default).strip().strip('\"').strip(\"'\")",
             "Chain of .strip() calls: first removes whitespace, then double quotes, then single quotes."),
        (15, "PROJECT_ID = _env('GCP_PROJECT_ID')",
             "Module-level constant — loaded once and available throughout the file."),
        (18, "AGENT_NAME = 'snowflake-a2a'",
             "Hardcoded — the display name of this agent in Gemini is always 'snowflake-a2a'."),
        (20, "if not PROJECT_ID:",
             "Guard: if GCP_PROJECT_ID is empty, there's no point continuing."),
    ]:
        story.append(annotated_line(ln, code, expl))
    story.append(Spacer(1, 0.2*cm))

    story += [Paragraph("Section 2 — grant_public_access() (lines 64–81)", H2),
              Paragraph(
                  "Gemini Enterprise calls our proxy without a GCP identity — it just sends "
                  "the user's Entra ID token. So the Cloud Run service must be publicly accessible. "
                  "This function grants that permission.", BODY)]
    for ln, code, expl in [
        (64, "def grant_public_access():",
             "Makes the Cloud Run service publicly reachable."),
        (71, '    [cmd, "run", "services", "add-iam-policy-binding", service_name,',
             "The gcloud command to modify IAM (Identity and Access Management) policy."),
        (72, '     "--member=allUsers",',
             "allUsers = anyone on the internet, no GCP account required."),
        (73, '     "--role=roles/run.invoker",',
             "run.invoker = permission to call (invoke) the Cloud Run service."),
    ]:
        story.append(annotated_line(ln, code, expl))
    story.append(Spacer(1, 0.2*cm))

    story += [Paragraph("Section 3 — register_agent() (lines 122–201)", H2),
              Paragraph(
                  "The main registration function. It builds an 'agent card' (a JSON description "
                  "of the agent's capabilities) and submits it to the Discovery Engine API.", BODY)]
    for ln, code, expl in [
        (123, "    token = get_access_token()",
              "Get a GCP access token — needed to authenticate the API call to Google."),
        (124, "    delete_existing_agents(token)",
              "Clean up any previous registration with the same name — you can't have duplicates."),
        (130, "    agent_card = {",
              "Start building the agent card — this is what Gemini reads to understand the agent."),
        (131, '        "name": AGENT_NAME,',
              "The agent's identifier name."),
        (132, '        "description": AGENT_DESCRIPTION,',
              "Human-readable description shown in the Gemini UI."),
        (133, '        "url": cloud_run_url,',
              "The HTTPS URL where Gemini will send requests."),
        (135, '        "skills": [{"id": "query_cortex_agent", ...}]',
              "A skill describes one capability. 'tags' help Gemini discover the agent for relevant queries."),
        (143, '        "capabilities": {"streaming": False, "pushNotifications": False}',
              "Declare what the agent can/cannot do. This proxy does not stream or send push notifications."),
        (152, "    payload = {",
              "The full registration payload for the Discovery Engine API."),
        (153, '        "displayName": AGENT_NAME,',
              "How the agent appears in the Gemini Enterprise UI."),
        (155, '        "a2aAgentDefinition": {"jsonAgentCard": json.dumps(agent_card)}',
              "The agent card is stringified to JSON and nested inside the payload."),
        (158, '        "sharingConfig": {"scope": "ALL_USERS"}',
              "Make this agent available to everyone in the Gemini Enterprise organization."),
        (161, '        "authorizationConfig": {"agentAuthorization": AGENT_AUTHORIZATION}',
              "Links this agent to the OAuth resource created by deploy.py — enables the Connect button."),
        (173, "    req = urllib.request.Request(url, data=..., headers=..., method='POST')",
              "Build the HTTP POST request to the Discovery Engine agents endpoint."),
        (188, '            print(json.dumps(result, indent=2))',
              "Pretty-print the API response with 2-space indentation — helpful for debugging."),
        (199, '        with open("error.log", "w") as f:',
              "On failure, save the full error body to error.log for investigation."),
    ]:
        story.append(annotated_line(ln, code, expl))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # SUPPORTING FILES
    # ══════════════════════════════════════════════════════════════════════════
    story += [
        section_badge("SUPPORTING FILES"),
        Spacer(1, 0.3*cm),
        Paragraph("requirements.txt", H1),
        Paragraph(
            "This file lists all the Python packages the project needs. "
            "Run 'pip install -r requirements.txt' to install them all at once.", BODY),
    ]
    req_rows = [
        ("fastapi",          "The web framework — provides @app.get, @app.post, Request, etc."),
        ("uvicorn>=0.27.0",  "The ASGI web server that runs FastAPI. Must be 0.27.0 or newer."),
        ("requests>=2.31.0", "HTTP client library used to call the Snowflake API. >= means 'minimum version'."),
        ("pyjwt>=2.8.0",     "JSON Web Token library — used by auth.py to decode JWT tokens."),
        ("python-dotenv>=1.0.1", "Reads .env files so environment variables can be set without exporting them in your shell."),
    ]
    story.append(kv_table(req_rows))
    story.append(Spacer(1, 0.4*cm))

    story += [
        Paragraph("env.template — Configuration Reference", H1),
        Paragraph(
            "Copy this file to '.env' and fill in your real values. "
            "The .gitignore prevents .env from being committed to git (it contains secrets).", BODY),
        Spacer(1, 0.2*cm),
    ]
    env_rows = [
        ("SNOWFLAKE_ACCOUNT",        "Your Snowflake organization and account, e.g. 'myorg-myaccount'"),
        ("SNOWFLAKE_ACCOUNT_LOCATOR","Alternate locator ID for constructing the API URL fallback"),
        ("SNOWFLAKE_USER",           "Snowflake username (used for reference — actual auth uses OAuth tokens)"),
        ("AGENT_DATABASE",           "Snowflake database where the Cortex Agent lives"),
        ("AGENT_SCHEMA",             "Schema inside that database"),
        ("AGENT_NAME",               "Name of the Cortex Agent AND the Cloud Run service name"),
        ("AGENT_DESCRIPTION",        "Text shown in Gemini Enterprise's agent discovery UI"),
        ("GCP_PROJECT_ID",           "Your Google Cloud project ID (required by all GCP services)"),
        ("GCP_ENGINE_ID",            "Discovery Engine ID — the Gemini Enterprise app to register in"),
        ("GCP_LOCATION",             "Discovery Engine location, typically 'us'"),
        ("GCP_REGION",               "Cloud Run deployment region, e.g. 'us-central1'"),
        ("OAUTH_TENANT_ID",          "Azure AD / Entra ID tenant ID (the organisation's unique identifier)"),
        ("OAUTH_CLIENT_ID",          "Application (client) ID registered in Entra ID"),
        ("OAUTH_CLIENT_SECRET",      "Client secret from the Entra ID app registration"),
        ("OAUTH_SCOPES",             "(Optional) Space-separated OAuth scopes; defaults to Snowflake + OpenID scopes"),
        ("AGENT_URL",                "The Cloud Run HTTPS URL — set after first deployment, used by registration"),
    ]
    story.append(kv_table(env_rows))
    story.append(Spacer(1, 0.4*cm))

    story += [
        Paragraph("Dockerfile — Container Recipe", H1),
        Paragraph(
            "A Dockerfile is a set of instructions for building a Docker container image. "
            "Think of it like a recipe: start with an ingredient (base image), add more "
            "ingredients (dependencies), and describe how to run the application.", BODY),
        Spacer(1, 0.2*cm),
    ]
    docker_lines = [
        ("FROM python:3.11-slim",
         "Start from the official Python 3.11 slim image — a minimal Linux environment with Python pre-installed."),
        ("WORKDIR /app",
         "Set the working directory inside the container to /app — all subsequent commands run from here."),
        ("COPY requirements.txt .",
         "Copy the requirements file into the container (the '.' means 'current WORKDIR')."),
        ("RUN pip install --no-cache-dir -r requirements.txt",
         "Install all Python dependencies. --no-cache-dir keeps the image smaller."),
        ("COPY . .",
         "Copy ALL project files into the container."),
        ("EXPOSE 8080",
         "Document that the container listens on port 8080 (informational — Cloud Run uses this)."),
        ('CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]',
         "The command to run when the container starts. 'main:app' means the 'app' object in main.py. --host 0.0.0.0 allows external connections."),
    ]
    for code_text, explanation in docker_lines:
        story.append(annotated_line("", code_text, explanation))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # GLOSSARY
    # ══════════════════════════════════════════════════════════════════════════
    story += [
        section_badge("GLOSSARY — KEY TERMS"),
        Spacer(1, 0.3*cm),
        Paragraph("Key Terms Explained", H1),
    ]
    glossary = [
        ("A2A (Agent-to-Agent)",
         "A protocol standard that lets AI agents call each other. Uses JSON-RPC 2.0 as the message format."),
        ("JSON-RPC 2.0",
         "A remote procedure call protocol encoded in JSON. A request has 'jsonrpc', 'method', 'params', and 'id' fields."),
        ("OAuth / OAuth 2.0",
         "An authorization framework that lets users grant applications access to their data without sharing passwords."),
        ("JWT (JSON Web Token)",
         "A compact, URL-safe token format. Contains three base64-encoded parts: header.payload.signature. The payload holds 'claims' about the user."),
        ("Bearer Token",
         "An HTTP authentication scheme where whoever 'bears' the token has access. Format: 'Authorization: Bearer <token>'."),
        ("Entra ID / Azure AD",
         "Microsoft's cloud identity platform. Issues OAuth tokens for users in organizations that use Microsoft 365."),
        ("SSE (Server-Sent Events)",
         "A protocol where a server pushes data to the client as a stream of text events. Each event has 'event:' and 'data:' lines."),
        ("FastAPI",
         "A modern Python web framework for building APIs. Automatically generates documentation and uses Python type hints."),
        ("Cloud Run",
         "Google Cloud's serverless container platform. You provide a Docker container; Google handles scaling and infrastructure."),
        ("Snowflake Cortex",
         "Snowflake's AI/ML layer. Cortex Agents are conversational AI agents that can query data and generate insights."),
        ("Discovery Engine",
         "Google Cloud's AI-powered search and recommendation service. Used here to host Gemini Enterprise agents."),
        ("Artifact Registry",
         "Google Cloud's container image registry — stores Docker images before they are deployed to Cloud Run."),
        ("ASGI",
         "Asynchronous Server Gateway Interface — the Python standard for async web servers. FastAPI and uvicorn both use ASGI."),
        ("IAM (Identity and Access Management)",
         "Google Cloud's permission system. Controls who (or what) can do what with which resources."),
    ]
    gdata = [[Paragraph(f"<b>{term}</b>", BODY), Paragraph(defn, BODY)] for term, defn in glossary]
    gt = Table(gdata, colWidths=[5*cm, 12*cm])
    gt.setStyle(TableStyle([
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 5),
        ("ROWBACKGROUNDS",(0,0), (-1,-1), [colors.white, C_CODE_BG]),
        ("GRID",          (0,0), (-1,-1), 0.3, C_HR),
    ]))
    story.append(gt)
    story.append(Spacer(1, 0.5*cm))

    story += [
        hr(),
        Paragraph(
            "End of Walkthrough  •  snowflake-a2a codebase  •  Generated 2026-04-02",
            S("Footer", parent="Normal", fontSize=8, textColor=colors.grey, alignment=TA_CENTER)),
    ]

    return story


# ─── Build PDF ────────────────────────────────────────────────────────────────
def generate():
    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=2.2*cm,
        bottomMargin=2*cm,
        title="Snowflake A2A Proxy — Codebase Walkthrough",
        author="Claude Code",
        subject="Line-by-line code walkthrough for novice developers",
    )

    story = build_story()
    doc.build(story)
    print(f"[OK] PDF saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    generate()
