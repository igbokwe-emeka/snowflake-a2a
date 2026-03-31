# Snowflake Cortex A2A Proxy

A lightweight FastAPI proxy that bridges **Google Gemini Enterprise** with **Snowflake Cortex Agents** using the [A2A (Agent-to-Agent)](https://google.github.io/A2A/) protocol.

## Architecture

```
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│  Gemini Enterprise  │────▶│     A2A Proxy         │────▶│  Snowflake Cortex   │
│  (JSON-RPC 2.0)     │     │   (Cloud Run)         │     │      Agent          │
└─────────────────────┘     └──────────────────────┘     └─────────────────────┘
         │                           │
   Entra ID Bearer             OAuth Propagation
   Token (via Connect)         (X-Snowflake-Authorization-Token-Type: OAUTH)
```

**Key Features:**
- Implements the A2A `message/send` JSON-RPC 2.0 protocol for Gemini Enterprise compatibility.
- Propagates user Entra ID (Azure AD) OAuth tokens directly to Snowflake — no service account impersonation.
- Prompts users to complete the OAuth Connect flow if no valid user token is present.
- Parses Snowflake Cortex SSE streaming responses into clean text artifacts.
- Returns A2A-compliant `Task` objects with `artifacts` so Gemini Enterprise renders results correctly.

## Project Structure

```
snowflake-a2a/
├── main.py                # FastAPI server — A2A protocol handler and Snowflake integration
├── auth.py                # Authentication — OAuth token decoding and Snowflake header builder
├── register_a2a_agent.py  # Registers the proxy as an agent in Gemini Enterprise
├── deploy.py              # Full deployment automation (build, deploy, authorization, register)
├── Dockerfile             # Container definition
├── requirements.txt       # Python dependencies
├── env.template           # Environment variable template
└── README.md              # This file
```

## Prerequisites

Before deploying, ensure the following are in place:

- **Python 3.11+** with `pip install -r requirements.txt`
- **Snowflake Cortex Agent** deployed in Snowflake
- **Snowflake External OAuth** integration configured to trust your Entra ID (Azure AD) tenant and accept the token audience (`api://<client-id>/session:role-any`)
- **Entra ID App Registration** with:
  - A client secret
  - Redirect URI: `https://vertexaisearch.cloud.google.com/static/oauth/oauth.html`
  - API permission: `api://<client-id>/session:role-any` (exposed by the app itself)
- **Google Cloud project** with the following enabled:
  - Gemini Enterprise (Agent Builder / Discovery Engine)
  - Cloud Run
  - Cloud Build
  - Artifact Registry
- **`gcloud` CLI** authenticated (`gcloud auth login` and `gcloud auth application-default login`)

## Setup

### 1. Configure Environment

Copy `env.template` to `.env` and fill in your values:

```ini
# Snowflake Connection
SNOWFLAKE_ACCOUNT=YOUR_ORG-YOUR_ACCOUNT
SNOWFLAKE_ACCOUNT_LOCATOR=YOUR_ACCOUNT_LOCATOR
SNOWFLAKE_USER=YOUR_SERVICE_USER

# Cortex Agent
AGENT_DATABASE=YOUR_DATABASE
AGENT_SCHEMA=YOUR_SCHEMA
AGENT_NAME=YOUR_CORTEX_AGENT_NAME
AGENT_DESCRIPTION=Your agent description

# Entra ID (Azure AD) OAuth
OAUTH_TENANT_ID=YOUR_ENTRA_TENANT_ID
OAUTH_CLIENT_ID=YOUR_ENTRA_CLIENT_ID
OAUTH_CLIENT_SECRET=YOUR_ENTRA_CLIENT_SECRET

# Cloud Run Service URL (set after first deploy)
AGENT_URL=https://YOUR_SERVICE-YOUR_HASH-uc.a.run.app
```

### 2. Run Locally

```bash
pip install -r requirements.txt
python main.py
# Proxy starts on http://localhost:8080
```

## Deployment

A single command handles the full end-to-end deployment:

```bash
python deploy.py
```

This runs four steps in order:

#### Step 1 — Build
Builds the container image using Cloud Build and pushes it to Artifact Registry:
```
us-central1-docker.pkg.dev/<PROJECT_ID>/cloud-run-source-deploy/<service-name>:latest
```

#### Step 2 — Deploy to Cloud Run
Deploys the image to Cloud Run with:
- `--allow-unauthenticated` (Gemini Enterprise calls the service directly)
- `--min-instances=1 --max-instances=1` (prevents Gemini from fanning out to multiple instances)

#### Step 3 — Manage Authorization Resource
Creates a `serverSideOauth2` authorization resource in Discovery Engine using your Entra ID credentials. This is the resource that triggers the **Connect** button in Gemini Enterprise.

- If an authorization resource with the same name already exists, it is **deleted first** then recreated fresh.
- The `authorizationUri` includes the required `redirect_uri` and `prompt=consent` parameters.
- The created resource name is automatically passed to the next step.

#### Step 4 — Register Agent
Runs `register_a2a_agent.py` to register (or re-register) the agent in Gemini Enterprise:
- Deletes any existing agent with the same display name.
- Creates a new agent with `a2aAgentDefinition` pointing to your Cloud Run URL.
- Binds the authorization resource created in Step 3.
- Sets sharing to `ALL_USERS`.

### Register Only (after deploy)

If you need to re-register without redeploying:

```bash
python register_a2a_agent.py
```

> Set `AGENT_AUTHORIZATION` in your `.env` to the full resource path
> (`projects/.../locations/us/authorizations/<auth-id>`) before running standalone.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/` | POST | A2A entry point (JSON-RPC 2.0) |
| `/query` | POST | A2A query handler |
| `/health` | GET | Health check |
| `/.well-known/agent.json` | GET | A2A agent card discovery |

### A2A Request (JSON-RPC 2.0)

```json
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "method": "message/send",
  "params": {
    "message": {
      "parts": [{"kind": "text", "text": "What are the latest sales trends?"}],
      "role": "user"
    }
  }
}
```

### A2A Response

```json
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "result": {
    "status": {"state": "completed"},
    "artifacts": [
      {
        "name": "response",
        "parts": [{"kind": "text", "text": "Based on the data..."}]
      }
    ]
  }
}
```

## Authentication Flow

Gemini Enterprise injects the user's Entra ID Bearer token into the `Authorization` header after the user completes the OAuth Connect flow.

1. The proxy decodes the incoming Bearer token (without signature verification) to inspect claims.
2. **No Authorization header** or **GCP service account token** (`gserviceaccount.com` in email claim): user has not completed the Connect flow. The proxy returns a message prompting them to click **Connect** in Gemini Enterprise.
3. **Valid Entra ID user token**: propagated directly to Snowflake with `X-Snowflake-Authorization-Token-Type: OAUTH`.

## Agent Registration Details

The proxy registers in Gemini Enterprise using the Discovery Engine `v1alpha` API:

```python
{
    "displayName": "snowflake-a2a",
    "a2aAgentDefinition": {"jsonAgentCard": "<agent card JSON>"},
    "sharingConfig": {"scope": "ALL_USERS"},
    "authorizationConfig": {
        "agentAuthorization": "projects/.../locations/us/authorizations/..."
    }
}
```

Key points:
- `a2aAgentDefinition` (not `adkAgentDefinition`) is used for direct HTTP A2A endpoints.
- `authorizationConfig.agentAuthorization` (single string) is the correct field for A2A agents.
- The agent card must **not** contain a `clientSecret` — if it does, Gemini performs a server-side `client_credentials` exchange and the user-facing **Connect** button never appears.

---
Built with Snowflake Cortex + Google Gemini Enterprise
