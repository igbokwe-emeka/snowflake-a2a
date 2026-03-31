import os
import uuid
import json
import requests
import uvicorn
import asyncio
from fastapi import FastAPI, Request, Header, HTTPException
from auth import decode_token_claims, get_snowflake_headers
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Snowflake Cortex Proxy")

def _get_snowflake_urls():
    account = os.getenv("SNOWFLAKE_ACCOUNT", "")
    account_locator = os.getenv("SNOWFLAKE_ACCOUNT_LOCATOR", "")
    db = os.getenv("AGENT_DATABASE", "")
    schema = os.getenv("AGENT_SCHEMA", "")
    cortex_agent = os.getenv("AGENT_NAME", "")

    path = f"/api/v2/databases/{db}/schemas/{schema}/agents/{cortex_agent}:run"

    api_url = f"https://{account}.snowflakecomputing.com{path}" if account else ""
    api_url_locator = f"https://{account_locator}.snowflakecomputing.com{path}" if account_locator else ""
    return api_url, api_url_locator

def _parse_cortex_sse(raw_text: str) -> str:
    """Parse Snowflake Cortex SSE response into plain text.

    Snowflake sends each content block twice: incremental *.delta events
    and a complete *.text event. Collect ONLY response.text.delta to avoid
    duplication.
    """
    answer_parts = []
    current_event = None

    for line in raw_text.splitlines():
        if line.startswith("event:"):
            current_event = line[6:].strip()
            continue

        if not line.startswith("data:"):
            continue
        data_str = line[5:].strip()
        if not data_str or data_str == "[DONE]":
            continue

        if current_event != "response.text.delta":
            continue

        try:
            data = json.loads(data_str)
            text = data.get("text", "")
            if text:
                answer_parts.append(text)
        except json.JSONDecodeError:
            pass

    result = "".join(answer_parts).strip()
    return result if result else "(No text in Cortex response)"

def _call_snowflake(url, headers, payload):
    """Make the actual streaming API call to Snowflake Cortex."""
    return requests.post(url, json=payload, headers=headers, timeout=120, stream=True)

@app.api_route("/", methods=["GET", "POST"])
async def root_handler(request: Request, authorization: str = Header(None)):
    """Handle root health checks and Discovery Engine POSTs."""
    if request.method == "GET":
        return {"status": "ok", "message": "Snowflake Cortex Proxy is running"}
    return await handle_query(request, authorization)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/.well-known/agent.json")
async def agent_card():
    """Serve A2A agent card for discovery."""
    cloud_run_url = os.getenv("AGENT_URL", "").strip() or f"https://{os.getenv('K_SERVICE','snowflakea2a')}-bt24fn2lfa-uc.a.run.app"
    return {
        "name": os.getenv("AGENT_NAME", "snowflake-a2a"),
        "description": os.getenv("AGENT_DESCRIPTION", "Snowflake Cortex Agent"),
        "url": cloud_run_url,
        "version": "1.0.0",
        "capabilities": {"streaming": False, "pushNotifications": False},
        "defaultInputModes": ["text"],
        "defaultOutputModes": ["text"],
        "protocolVersion": "1.0.0"
    }

@app.post("/query")
async def handle_query(request: Request, authorization: str = Header(None)):
    """
    Receives A2A queries, authenticates against Snowflake, and returns results.
    Auth flow: Entra ID Bearer token (OAuth) -> Key-Pair JWT fallback.
    """
    try:
        body = await request.json()

        # 1. Parse JSON-RPC 2.0 envelope (A2A standard)
        text = ""
        is_json_rpc = body.get("jsonrpc") == "2.0"
        params = body.get("params", {})

        if is_json_rpc:
            message = params.get("message", {})
            parts = message.get("parts", [])
            for part in parts:
                if part.get("kind") == "text" or "text" in part:
                    text = part.get("text")
                    break

        # 2. Fallback to standard top-level fields
        if not text:
            text = body.get("text") or body.get("query") or body.get("query_text") or body.get("input", "")

        if not text:
            print(f"ERROR: Could not extract query text from body. Keys: {list(body.keys())}")
            error_msg = "Missing query text in request."
            if is_json_rpc:
                return {
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "error": {"code": -32602, "message": error_msg}
                }
            return {"error": error_msg}

        print(f"INFO: Processing query: {text[:80]}...")

        # Ping test
        if text.lower().strip() == "ping":
            if is_json_rpc:
                return {
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "result": {
                        "id": str(uuid.uuid4()),
                        "contextId": params.get("message", {}).get("messageId", str(uuid.uuid4())),
                        "status": {"state": "completed"},
                        "artifacts": [{"artifactId": str(uuid.uuid4()), "name": "response", "parts": [{"kind": "text", "text": "pong"}]}]
                    }
                }
            return {"text": "pong"}

        payload = {
            "messages": [{"role": "user", "content": [{"type": "text", "text": text}]}]
        }

        api_url, api_url_locator = _get_snowflake_urls()

        # Only accept user OAuth tokens from the Authorization header (set by Gemini Enterprise after Connect flow)
        authorization = request.headers.get("Authorization", "")

        final_answer = ""
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization.split(" ", 1)[1].strip()
            claims = decode_token_claims(token)
            token_email = claims.get("email", "")
            is_service_account = "gserviceaccount.com" in token_email

            if is_service_account:
                # Gemini sent its own service account — user has not completed the OAuth Connect flow
                print("INFO: Service account token received. User has not completed OAuth Connect flow.")
                final_answer = "Please connect your Microsoft account: click the 'Connect' button in Gemini Enterprise to authorise this agent."
            else:
                # Valid Entra ID user token
                email = next(
                    (i for i in [claims.get("upn"), claims.get("preferred_username"), claims.get("unique_name"), token_email]
                     if isinstance(i, str) and i),
                    "Unknown"
                )
                print(f"INFO: User OAuth token received. Calling Snowflake for: {email}.")
                headers = get_snowflake_headers(token=token)
                try:
                    print(f"INFO: Calling Snowflake: {api_url}")
                    response = await asyncio.to_thread(_call_snowflake, api_url, headers, payload)
                    print(f"INFO: Snowflake responded with status {response.status_code}")

                    if response.status_code == 200:
                        try:
                            final_answer = _parse_cortex_sse(response.text)
                            print(f"INFO: Call succeeded. Answer length={len(final_answer)}")
                        except Exception as parse_err:
                            final_answer = f"Error parsing Snowflake response: {response.text[:200]}"
                            print(f"ERROR: Could not parse response: {parse_err}")
                    else:
                        raw = response.text or "(empty body)"
                        print(f"ERROR: Snowflake returned {response.status_code}. Body: {raw[:1000]}")
                        final_answer = f"Snowflake Error {response.status_code}: {raw[:500]}"
                except Exception as e:
                    print(f"ERROR: Call to Snowflake failed: {str(e)}")
                    final_answer = f"Proxy error: {str(e)}"
        else:
            print("INFO: No Authorization header. User has not completed OAuth Connect flow.")
            final_answer = "Please connect your Microsoft account: click the 'Connect' button in Gemini Enterprise to authorise this agent."

        # 3. Format response
        if is_json_rpc:
            context_id = params.get("message", {}).get("messageId", str(uuid.uuid4()))
            return {
                "jsonrpc": "2.0",
                "id": body.get("id"),
                "result": {
                    "id": str(uuid.uuid4()),
                    "contextId": context_id,
                    "status": {"state": "completed"},
                    "artifacts": [
                        {
                            "artifactId": str(uuid.uuid4()),
                            "name": "response",
                            "parts": [{"kind": "text", "text": final_answer}]
                        }
                    ]
                }
            }

        return {
            "query": text,
            "response": final_answer,
            "propagated": bool(authorization and authorization.lower().startswith("bearer "))
        }

    except Exception as e:
        print(f"ERROR: Error handling query: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    print(f"INFO: Starting Snowflake Cortex proxy on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
