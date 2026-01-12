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
    # Disable SSL verification to handle certificate issues with Render.com
    # In production, you may want to set this via environment variable
    verify_ssl = os.getenv("VERIFY_SSL", "false").lower() == "true"
    try:
        resp = requests.request(
            method, 
            url, 
            params=params, 
            json=json_body, 
            timeout=15,
            verify=verify_ssl
        )
    except requests.exceptions.SSLError as exc:
        return {
            "ok": False,
            "error": f"SSL certificate verification error: {exc}. Try setting VERIFY_SSL=false environment variable.",
        }
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


def _validate_latitude_longitude(latitude: float, longitude: float) -> None:
    if not (-90.0 <= latitude <= 90.0):
        raise ValueError(f"latitude must be between -90 and 90, got {latitude}")
    if not (-180.0 <= longitude <= 180.0):
        raise ValueError(f"longitude must be between -180 and 180, got {longitude}")


def _validate_radius(radius: float) -> None:
    if radius <= 0:
        raise ValueError("radius must be > 0")


def _validate_minyan_type(minyan_type: str) -> None:
    valid_types = ["shacharit", "mincha", "maariv"]
    if minyan_type not in valid_types:
        raise ValueError(f"minyanType must be one of {valid_types}, got {minyan_type}")


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
    latitude: float,
    longitude: float,
    radius: float = 2.0,
    minyanType: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Call GET /broadcasts/nearby with latitude/longitude and radius (in miles).
    """
    _validate_latitude_longitude(latitude, longitude)
    _validate_radius(radius)

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "radius": radius,
    }
    if minyanType:
        _validate_minyan_type(minyanType)
        params["minyanType"] = minyanType
    
    return _request("GET", "/broadcasts/nearby", params=params)


async def create_broadcast(
    latitude: float,
    longitude: float,
    minyanType: str,
    earliestTime: str,
    latestTime: str,
) -> Dict[str, Any]:
    """
    Call POST /broadcasts to create a new minyan broadcast.
    """
    _validate_latitude_longitude(latitude, longitude)
    _validate_minyan_type(minyanType)
    
    if not earliestTime.strip():
        raise ValueError("earliestTime is required (ISO 8601 UTC format, e.g., 2025-03-26T13:00:00Z)")
    if not latestTime.strip():
        raise ValueError("latestTime is required (ISO 8601 UTC format, e.g., 2025-03-26T14:00:00Z)")

    body = {
        "latitude": latitude,
        "longitude": longitude,
        "minyanType": minyanType,
        "earliestTime": earliestTime,
        "latestTime": latestTime,
    }
    return _request("POST", "/broadcasts", json_body=body)


async def update_broadcast(
    id: str,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    minyanType: Optional[str] = None,
    earliestTime: Optional[str] = None,
    latestTime: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Call PUT /broadcasts/{id} to update a broadcast.
    Only provided fields will be updated.
    """
    if not id.strip():
        raise ValueError("id is required")

    body: Dict[str, Any] = {}
    if latitude is not None:
        _validate_latitude_longitude(latitude, longitude if longitude is not None else 0.0)
        body["latitude"] = latitude
    if longitude is not None:
        _validate_latitude_longitude(latitude if latitude is not None else 0.0, longitude)
        body["longitude"] = longitude
    if minyanType is not None:
        _validate_minyan_type(minyanType)
        body["minyanType"] = minyanType
    if earliestTime is not None:
        body["earliestTime"] = earliestTime
    if latestTime is not None:
        body["latestTime"] = latestTime

    if not body:
        raise ValueError("At least one field must be provided to update")

    return _request("PUT", f"/broadcasts/{id}", json_body=body)


async def delete_broadcast(id: str) -> Dict[str, Any]:
    """
    Call DELETE /broadcasts/{id} to delete a broadcast.
    """
    if not id.strip():
        raise ValueError("id is required")

    return _request("DELETE", f"/broadcasts/{id}")


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
                "description": "Call GET /broadcasts/nearby with latitude/longitude and radius (in miles).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number", "description": "Latitude (-90 to 90)"},
                        "longitude": {"type": "number", "description": "Longitude (-180 to 180)"},
                        "radius": {"type": "number", "description": "Search radius in miles", "default": 2.0},
                        "minyanType": {"type": "string", "description": "Filter by minyan type: shacharit, mincha, or maariv", "enum": ["shacharit", "mincha", "maariv"]},
                    },
                    "required": ["latitude", "longitude", "radius"],
                },
            },
            {
                "name": "create_broadcast",
                "description": "Call POST /broadcasts to create a new minyan broadcast.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number", "description": "Latitude (-90 to 90)"},
                        "longitude": {"type": "number", "description": "Longitude (-180 to 180)"},
                        "minyanType": {"type": "string", "description": "Type of minyan: shacharit, mincha, or maariv", "enum": ["shacharit", "mincha", "maariv"]},
                        "earliestTime": {"type": "string", "description": "Earliest time for the minyan (ISO 8601 UTC format, e.g., 2025-03-26T13:00:00Z)"},
                        "latestTime": {"type": "string", "description": "Latest time for the minyan (ISO 8601 UTC format, e.g., 2025-03-26T14:00:00Z)"},
                    },
                    "required": ["latitude", "longitude", "minyanType", "earliestTime", "latestTime"],
                },
            },
            {
                "name": "update_broadcast",
                "description": "Call PUT /broadcasts/{id} to update a broadcast. Only provided fields will be updated.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Broadcast ID (UUID)"},
                        "latitude": {"type": "number", "description": "Latitude (-90 to 90)"},
                        "longitude": {"type": "number", "description": "Longitude (-180 to 180)"},
                        "minyanType": {"type": "string", "description": "Type of minyan: shacharit, mincha, or maariv", "enum": ["shacharit", "mincha", "maariv"]},
                        "earliestTime": {"type": "string", "description": "Earliest time for the minyan (ISO 8601 UTC format)"},
                        "latestTime": {"type": "string", "description": "Latest time for the minyan (ISO 8601 UTC format)"},
                    },
                    "required": ["id"],
                },
            },
            {
                "name": "delete_broadcast",
                "description": "Call DELETE /broadcasts/{id} to delete a broadcast.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Broadcast ID (UUID)"},
                    },
                    "required": ["id"],
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



