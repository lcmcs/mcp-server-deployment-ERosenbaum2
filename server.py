#!/usr/bin/env python3
"""
MCP Server for Minyan Finder API using stdio protocol.
This server works with Claude Desktop.
"""
import asyncio
import json
import os
import sys
from typing import Any, Dict, Optional

import requests
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent


API_BASE_URL = os.getenv("MINYAN_FINDER_API_BASE_URL", "https://minyan-finder-api.onrender.com")

# Create the MCP server instance
server = Server("minyan-finder-mcp-server")


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


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available MCP tools."""
    return [
        Tool(
            name="health_check",
            description="Call GET /health on the Minyan Finder API.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="get_nearby_broadcasts",
            description="Call GET /broadcasts/nearby with latitude/longitude and radius (in miles).",
            inputSchema={
                "type": "object",
                "properties": {
                    "latitude": {"type": "number", "description": "Latitude (-90 to 90)"},
                    "longitude": {"type": "number", "description": "Longitude (-180 to 180)"},
                    "radius": {"type": "number", "description": "Search radius in miles", "default": 2.0},
                    "minyanType": {"type": "string", "description": "Filter by minyan type: shacharit, mincha, or maariv", "enum": ["shacharit", "mincha", "maariv"]},
                },
                "required": ["latitude", "longitude", "radius"],
            },
        ),
        Tool(
            name="create_broadcast",
            description="Call POST /broadcasts to create a new minyan broadcast.",
            inputSchema={
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
        ),
        Tool(
            name="update_broadcast",
            description="Call PUT /broadcasts/{id} to update a broadcast. Only provided fields will be updated.",
            inputSchema={
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
        ),
        Tool(
            name="delete_broadcast",
            description="Call DELETE /broadcasts/{id} to delete a broadcast.",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Broadcast ID (UUID)"},
                },
                "required": ["id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    
    # Tool implementations
    if name == "health_check":
        result = _request("GET", "/health")
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "get_nearby_broadcasts":
        latitude = arguments.get("latitude")
        longitude = arguments.get("longitude")
        radius = arguments.get("radius", 2.0)
        minyan_type = arguments.get("minyanType")
        
        _validate_latitude_longitude(latitude, longitude)
        _validate_radius(radius)
        
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "radius": radius,
        }
        if minyan_type:
            _validate_minyan_type(minyan_type)
            params["minyanType"] = minyan_type
        
        result = _request("GET", "/broadcasts/nearby", params=params)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "create_broadcast":
        latitude = arguments.get("latitude")
        longitude = arguments.get("longitude")
        minyan_type = arguments.get("minyanType", "").strip()
        earliest_time = arguments.get("earliestTime", "").strip()
        latest_time = arguments.get("latestTime", "").strip()
        
        _validate_latitude_longitude(latitude, longitude)
        _validate_minyan_type(minyan_type)
        
        if not earliest_time:
            raise ValueError("earliestTime is required (ISO 8601 UTC format, e.g., 2025-03-26T13:00:00Z)")
        if not latest_time:
            raise ValueError("latestTime is required (ISO 8601 UTC format, e.g., 2025-03-26T14:00:00Z)")
        
        body = {
            "latitude": latitude,
            "longitude": longitude,
            "minyanType": minyan_type,
            "earliestTime": earliest_time,
            "latestTime": latest_time,
        }
        result = _request("POST", "/broadcasts", json_body=body)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "update_broadcast":
        broadcast_id = arguments.get("id", "").strip()
        if not broadcast_id:
            raise ValueError("id is required")
        
        body: Dict[str, Any] = {}
        if "latitude" in arguments:
            latitude = arguments["latitude"]
            longitude = arguments.get("longitude")
            _validate_latitude_longitude(latitude, longitude if longitude is not None else 0.0)
            body["latitude"] = latitude
        if "longitude" in arguments:
            latitude = arguments.get("latitude")
            longitude = arguments["longitude"]
            _validate_latitude_longitude(latitude if latitude is not None else 0.0, longitude)
            body["longitude"] = longitude
        if "minyanType" in arguments:
            _validate_minyan_type(arguments["minyanType"])
            body["minyanType"] = arguments["minyanType"]
        if "earliestTime" in arguments:
            body["earliestTime"] = arguments["earliestTime"]
        if "latestTime" in arguments:
            body["latestTime"] = arguments["latestTime"]
        
        if not body:
            raise ValueError("At least one field must be provided to update")
        
        result = _request("PUT", f"/broadcasts/{broadcast_id}", json_body=body)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "delete_broadcast":
        broadcast_id = arguments.get("id", "").strip()
        if not broadcast_id:
            raise ValueError("id is required")
        
        result = _request("DELETE", f"/broadcasts/{broadcast_id}")
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    """Run the MCP server using stdio."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

