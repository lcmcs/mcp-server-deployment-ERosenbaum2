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
            description="Call GET /broadcasts/nearby with latitude/longitude and radius_km.",
            inputSchema={
                "type": "object",
                "properties": {
                    "lat": {"type": "number", "description": "Latitude (-90 to 90)"},
                    "lon": {"type": "number", "description": "Longitude (-180 to 180)"},
                    "radius_km": {"type": "number", "description": "Radius in kilometers", "default": 5.0},
                },
                "required": ["lat", "lon"],
            },
        ),
        Tool(
            name="create_broadcast",
            description="Call POST /broadcasts to create a new minyan broadcast.",
            inputSchema={
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
        ),
        Tool(
            name="update_broadcast",
            description="Call PUT /broadcasts/{id} to update a broadcast. Only provided fields will be updated.",
            inputSchema={
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
        ),
        Tool(
            name="delete_broadcast",
            description="Call DELETE /broadcasts/{id} to delete a broadcast.",
            inputSchema={
                "type": "object",
                "properties": {
                    "broadcast_id": {"type": "string"},
                },
                "required": ["broadcast_id"],
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
        lat = arguments.get("lat")
        lon = arguments.get("lon")
        radius_km = arguments.get("radius_km", 5.0)
        
        _validate_lat_lon(lat, lon)
        _validate_radius(radius_km)
        
        params = {
            "lat": lat,
            "lon": lon,
            "radius_km": radius_km,
        }
        result = _request("GET", "/broadcasts/nearby", params=params)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "create_broadcast":
        title = arguments.get("title", "").strip()
        description = arguments.get("description", "").strip()
        lat = arguments.get("lat")
        lon = arguments.get("lon")
        start_time_iso = arguments.get("start_time_iso", "").strip()
        tz = arguments.get("tz", "").strip()
        
        if not title:
            raise ValueError("title is required")
        if not description:
            raise ValueError("description is required")
        if not start_time_iso:
            raise ValueError("start_time_iso is required (ISO-8601 string)")
        if not tz:
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
        result = _request("POST", "/broadcasts", json_body=body)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "update_broadcast":
        broadcast_id = arguments.get("broadcast_id", "").strip()
        if not broadcast_id:
            raise ValueError("broadcast_id is required")
        
        body: Dict[str, Any] = {}
        if "title" in arguments:
            body["title"] = arguments["title"]
        if "description" in arguments:
            body["description"] = arguments["description"]
        if "lat" in arguments:
            lat = arguments["lat"]
            lon = arguments.get("lon")
            _validate_lat_lon(lat, lon if lon is not None else 0.0)
            body["lat"] = lat
        if "lon" in arguments:
            lat = arguments.get("lat")
            lon = arguments["lon"]
            _validate_lat_lon(lat if lat is not None else 0.0, lon)
            body["lon"] = lon
        if "start_time_iso" in arguments:
            body["start_time_iso"] = arguments["start_time_iso"]
        if "tz" in arguments:
            body["tz"] = arguments["tz"]
        
        if not body:
            raise ValueError("At least one field must be provided to update")
        
        result = _request("PUT", f"/broadcasts/{broadcast_id}", json_body=body)
        return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    elif name == "delete_broadcast":
        broadcast_id = arguments.get("broadcast_id", "").strip()
        if not broadcast_id:
            raise ValueError("broadcast_id is required")
        
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

