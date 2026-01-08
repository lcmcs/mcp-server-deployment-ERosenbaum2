# Minyan Finder MCP Server

This project is an MCP (Model Context Protocol) server that wraps the **Minyan Finder API** hosted at:

- `https://minyan-finder-api.onrender.com/`

The server exposes the API endpoints as MCP tools so that clients like the ChatGPT desktop app or Claude desktop app can discover and call them.

## Features

- `health_check` → `GET /health`
- `get_nearby_broadcasts` → `GET /broadcasts/nearby`
- `create_broadcast` → `POST /broadcasts`
- `update_broadcast` → `PUT /broadcasts/{id}`
- `delete_broadcast` → `DELETE /broadcasts/{id}`

## Local Development

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the MCP HTTP server locally with Uvicorn:

```bash
uvicorn minyan_mcp_server:app --host 0.0.0.0 --port 10000
```

The FastAPI app exposes an MCP-compatible HTTP endpoint which tools clients like ChatGPT can call, following the pattern described in OpenAI’s MCP server docs ([developers.openai.com](https://developers.openai.com/apps-sdk/build/mcp-server?utm_source=openai)).

## Using with ChatGPT Desktop

1. Enable developer mode and connectors as described in the OpenAI docs ([developers.openai.com](https://developers.openai.com/apps-sdk/deploy/connect-chatgpt?utm_source=openai)).
2. In **Settings → Connectors**, create a new connector:
   - **Name**: `Minyan Finder`
   - **Description**: `Find and manage nearby minyan broadcasts.`
   - **Connector URL**: `http://localhost:10000/mcp` (for local testing)
3. Start a new chat, click the **+** near the composer → **More** → select **Minyan Finder**, and issue prompts like:
   - “Check the Minyan Finder health.”
   - “Find minyan broadcasts within 5km of 40.7128, -74.0060.”

For production use, point the connector URL at your deployed Render URL instead of `localhost` (see Deployment below).

## Using with Claude Desktop (optional)

Claude desktop also supports MCP servers. Follow its MCP configuration instructions (Settings → Developer → Edit config file) and add an HTTP server entry that points to your local or deployed URL for `minyan_mcp_server`. The tools will appear under the MCP integrations section once recognized.

## Deployment on Render

To deploy the MCP server on Render as a web service (so ChatGPT can reach it over HTTPS):

1. Push this repo to GitHub.
2. In Render, create a new **Web Service**:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn minyan_mcp_server:app --host 0.0.0.0 --port 10000`
3. Ensure the `PORT` environment variable is set to `10000` (or adjust the start command accordingly).
4. Optionally set `MINYAN_FINDER_API_BASE_URL` (defaults to `https://minyan-finder-api.onrender.com`).
5. After deploy, you’ll have a public URL like:
   - `https://your-mcp-service.onrender.com/mcp`

Use that URL as the **Connector URL** in ChatGPT desktop.

## Demo Video Ideas

In your 3–5 minute video, you can show:

- Configuring the connector in ChatGPT using your Render URL.
- Running `health_check` to show the API is up.
- Calling `get_nearby_broadcasts` with some sample coordinates.
- Creating, updating, and deleting a broadcast via the MCP tools.


