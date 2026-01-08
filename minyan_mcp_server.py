import os
from typing import Any, Dict, Optional

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


API_BASE_URL = os.getenv("MINYAN_FINDER_API_BASE_URL", "https://minyan-finder-api.onrender.com")


def _request(
    method: str,
    path: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    json_body: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Helper to call the Minyan Finder API with basic error handling.
    """
    url = f"{API_BASE_URL.rstrip('/')}{path}"
    try:
        resp = requests.request(method, url, params=params, json=json_body, timeout=15)
    except requests.RequestException as exc:
        return {
            "ok": False,
            "error": f"Network error calling Minyan Finder API: {exc}",
        }

    try:
        data = resp.json()
    except ValueError:
        data = {"raw_text": resp.text}

    if not resp.ok:
        return {
            "ok": False,
            "status": resp.status_code,
            "error": "Minyan Finder API returned an error status.",
            "response": data,
        }

    return {
        "ok": True,
        "status": resp.status_code,
        "response": data,
    }


def _validate_lat_lon(lat: float, lon: float) -> None:
    if not (-90.0 <= lat <= 90.0):
        raise ValueError(f"lat must be between -90 and 90, got {lat}")
    if not (-180.0 <= lon <= 180.0):
        raise ValueError(f"lon must be between -180 and 180, got {lon}")


def _validate_radius(radius_km: float) -> None:
    if radius_km <= 0:
        raise ValueError("radius_km must be > 0")


app = FastAPI(title="Minyan Finder MCP Server")


@app.get("/")
async def root():
    """Root endpoint - provides service information."""
    return {
        "service": "Minyan Finder MCP Server",
        "status": "running",
        "endpoints": {
            "mcp_tools": "/mcp",
            "mcp_call": "/mcp/call",
            "docs": "/docs",
        },
        "description": "MCP server for Minyan Finder API",
    }


# MCP Protocol Models
class Tool(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any]


class MCPToolsResponse(BaseModel):
    tools: list[Tool]


class ToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]


# Tool implementations
async def health_check() -> Dict[str, Any]:
    """
    Call GET /health on the Minyan Finder API.
    """
    return _request("GET", "/health")


async def get_nearby_broadcasts(
    lat: float,
    lon: float,
    radius_km: float = 5.0,
) -> Dict[str, Any]:
    """
    Call GET /broadcasts/nearby with latitude/longitude and radius_km.
    """
    _validate_lat_lon(lat, lon)
    _validate_radius(radius_km)

    params = {
        "lat": lat,
        "lon": lon,
        "radius_km": radius_km,
    }
    return _request("GET", "/broadcasts/nearby", params=params)


async def create_broadcast(
    title: str,
    description: str,
    lat: float,
    lon: float,
    start_time_iso: str,
    tz: str,
) -> Dict[str, Any]:
    """
    Call POST /broadcasts to create a new minyan broadcast.
    """
    if not title.strip():
        raise ValueError("title is required")
    if not description.strip():
        raise ValueError("description is required")
    if not start_time_iso.strip():
        raise ValueError("start_time_iso is required (ISO-8601 string)")
    if not tz.strip():
        raise ValueError("tz is required (IANA timezone string)")

    _validate_lat_lon(lat, lon)

    body = {
        "title": title,
        "description": description,
        "lat": lat,
        "lon": lon,
        "start_time_iso": start_time_iso,
        "tz": tz,
    }
    return _request("POST", "/broadcasts", json_body=body)


async def update_broadcast(
    broadcast_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    start_time_iso: Optional[str] = None,
    tz: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Call PUT /broadcasts/{id} to update a broadcast.
    Only provided fields will be updated.
    """
    if not broadcast_id.strip():
        raise ValueError("broadcast_id is required")

    body: Dict[str, Any] = {}
    if title is not None:
        body["title"] = title
    if description is not None:
        body["description"] = description
    if lat is not None:
        _validate_lat_lon(lat, lon if lon is not None else 0.0)
        body["lat"] = lat
    if lon is not None:
        _validate_lat_lon(lat if lat is not None else 0.0, lon)
        body["lon"] = lon
    if start_time_iso is not None:
        body["start_time_iso"] = start_time_iso
    if tz is not None:
        body["tz"] = tz

    if not body:
        raise ValueError("At least one field must be provided to update")

    return _request("PUT", f"/broadcasts/{broadcast_id}", json_body=body)


async def delete_broadcast(broadcast_id: str) -> Dict[str, Any]:
    """
    Call DELETE /broadcasts/{id} to delete a broadcast.
    """
    if not broadcast_id.strip():
        raise ValueError("broadcast_id is required")

    return _request("DELETE", f"/broadcasts/{broadcast_id}")


# Helper function to get tools list
def get_tools_list() -> Dict[str, Any]:
    """Get the list of available tools."""
    return {
        "tools": [
            {
                "name": "health_check",
                "description": "Call GET /health on the Minyan Finder API.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            {
                "name": "get_nearby_broadcasts",
                "description": "Call GET /broadcasts/nearby with latitude/longitude and radius_km.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "lat": {"type": "number", "description": "Latitude (-90 to 90)"},
                        "lon": {"type": "number", "description": "Longitude (-180 to 180)"},
                        "radius_km": {"type": "number", "description": "Radius in kilometers", "default": 5.0},
                    },
                    "required": ["lat", "lon"],
                },
            },
            {
                "name": "create_broadcast",
                "description": "Call POST /broadcasts to create a new minyan broadcast.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "lat": {"type": "number"},
                        "lon": {"type": "number"},
                        "start_time_iso": {"type": "string", "description": "ISO-8601 string"},
                        "tz": {"type": "string", "description": "IANA timezone string"},
                    },
                    "required": ["title", "description", "lat", "lon", "start_time_iso", "tz"],
                },
            },
            {
                "name": "update_broadcast",
                "description": "Call PUT /broadcasts/{id} to update a broadcast. Only provided fields will be updated.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "broadcast_id": {"type": "string"},
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "lat": {"type": "number"},
                        "lon": {"type": "number"},
                        "start_time_iso": {"type": "string"},
                        "tz": {"type": "string"},
                    },
                    "required": ["broadcast_id"],
                },
            },
            {
                "name": "delete_broadcast",
                "description": "Call DELETE /broadcasts/{id} to delete a broadcast.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "broadcast_id": {"type": "string"},
                    },
                    "required": ["broadcast_id"],
                },
            },
        ]
    }


# MCP Endpoints
@app.get("/mcp", response_model=MCPToolsResponse)
async def list_tools_get():
    """List all available MCP tools (GET request)."""
    return get_tools_list()


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    """
    Main MCP endpoint - handles both listing tools and calling tools.
    If request contains 'name' and 'arguments', it calls a tool.
    Otherwise, it returns the list of tools.
    """
    try:
        body = await request.json()
    except:
        # If no body or invalid JSON, return tools list
        return get_tools_list()
    
    # If request has 'name' field, it's a tool call
    if "name" in body:
        tool_map = {
            "health_check": health_check,
            "get_nearby_broadcasts": get_nearby_broadcasts,
            "create_broadcast": create_broadcast,
            "update_broadcast": update_broadcast,
            "delete_broadcast": delete_broadcast,
        }

        tool_name = body.get("name")
        tool_arguments = body.get("arguments", {})

        if tool_name not in tool_map:
            raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

        try:
            result = await tool_map[tool_name](**tool_arguments)
            return {"result": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    # Otherwise, return tools list
    return get_tools_list()


@app.post("/mcp/call")
async def call_tool(request: ToolCallRequest):
    """Call an MCP tool by name with arguments (alternative endpoint)."""
    tool_map = {
        "health_check": health_check,
        "get_nearby_broadcasts": get_nearby_broadcasts,
        "create_broadcast": create_broadcast,
        "update_broadcast": update_broadcast,
        "delete_broadcast": delete_broadcast,
    }

    if request.name not in tool_map:
        raise HTTPException(status_code=404, detail=f"Tool '{request.name}' not found")

    try:
        result = await tool_map[request.name](**request.arguments)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



