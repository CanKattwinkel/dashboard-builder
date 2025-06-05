import os
import json
import requests
from dotenv import load_dotenv
from typing import Dict, Any, Union
from pathlib import Path

load_dotenv()

API_KEY = os.getenv("GLASSNODE_API_KEY")
if not API_KEY:
    raise ValueError("GLASSNODE_API_KEY not found in environment variables")


def update_dashboard(dashboard_uuid: str, dashboard_data: Union[Dict[str, Any], str, Path]) -> requests.Response:
    """
    Update a Glassnode dashboard via their API.
    
    Args:
        dashboard_uuid: The UUID of the dashboard to update
        dashboard_data: Either a dict with dashboard config or path to JSON file
    
    Returns:
        Response object from the API call
    """
    # Load from file if path provided
    if isinstance(dashboard_data, (str, Path)):
        with open(dashboard_data, 'r') as f:
            dashboard_data = json.load(f)

    # First, get the current dashboard to retrieve its category UUID
    params = {"api_key": API_KEY}
    response = requests.get(f"https://api.glassnode.com/v1/dashboards/{dashboard_uuid}", params=params)
    response.raise_for_status()
    
    current_dashboard = response.json()
    category_uuid = current_dashboard.get("categoryUuid", "My Dashboards")
    
    # Wrap dashboard data with category UUID
    dashboard_data = {
        "categoryUuid": category_uuid,
        "data": dashboard_data
    }
    
    # Update the dashboard
    url = f"https://api.glassnode.com/v1/dashboards/{dashboard_uuid}"
    
    headers = {
        "content-type": "application/json"
    }
    
    response = requests.put(url, json=dashboard_data, headers=headers, params=params)
    response.raise_for_status()
    
    return response


def create_dashboard(dashboard_data: Union[Dict[str, Any], str, Path], 
                    category_uuid: str = "My Dashboards") -> requests.Response:
    """
    Create a new Glassnode dashboard via their API.
    
    Args:
        dashboard_data: Either a dict with dashboard config or path to JSON file
        category_uuid: Category for the dashboard (default matches update_dashboard)
    
    Returns:
        Response object from the API call
    """
    # Load from file if path provided
    if isinstance(dashboard_data, (str, Path)):
        with open(dashboard_data, 'r') as f:
            dashboard_data = json.load(f)
    
    # Wrap in expected format if not already wrapped
    if "categoryUuid" not in dashboard_data:
        dashboard_data = {
            "categoryUuid": category_uuid,
            "data": dashboard_data
        }
    
    url = "https://api.glassnode.com/v1/dashboards/create"
    
    headers = {
        "content-type": "application/json"
    }
    
    params = {"api_key": API_KEY}
    
    response = requests.post(url, json=dashboard_data, headers=headers, params=params)
    response.raise_for_status()
    
    return response


