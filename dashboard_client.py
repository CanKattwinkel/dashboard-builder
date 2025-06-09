import os
import json
import requests
from dotenv import load_dotenv
from typing import Dict, Any, Union, List
from pathlib import Path

load_dotenv()

API_KEY = os.getenv("GLASSNODE_API_KEY")
if not API_KEY:
    raise ValueError("GLASSNODE_API_KEY not found in environment variables")

MAPPINGS_FILE = ".dashboard_mappings.json"


def load_mappings():
    """Load UUID mappings from file, return empty dict if not found"""
    try:
        with open(MAPPINGS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_mapping(config_path, dashboard_uuid):
    """Save config path to UUID mapping"""
    mappings = load_mappings()
    mappings[config_path] = dashboard_uuid
    with open(MAPPINGS_FILE, "w") as f:
        json.dump(mappings, f, indent=2)


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
        with open(dashboard_data, "r") as f:
            dashboard_data = json.load(f)

    # First, get the current dashboard to retrieve its category UUID
    params = {"api_key": API_KEY}
    response = requests.get(f"https://api.glassnode.com/v1/dashboards/{dashboard_uuid}", params=params)
    response.raise_for_status()

    current_dashboard = response.json()
    category_uuid = current_dashboard.get("categoryUuid", "My Dashboards")

    # Wrap dashboard data with category UUID
    dashboard_data = {"categoryUuid": category_uuid, "data": dashboard_data}

    # Update the dashboard
    url = f"https://api.glassnode.com/v1/dashboards/{dashboard_uuid}"

    headers = {"content-type": "application/json"}

    response = requests.put(url, json=dashboard_data, headers=headers, params=params)
    response.raise_for_status()

    return response


def create_dashboard(
    dashboard_data: Union[Dict[str, Any], str, Path], category_uuid: str = "My Dashboards"
) -> requests.Response:
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
        with open(dashboard_data, "r") as f:
            dashboard_data = json.load(f)

    # Wrap in expected format if not already wrapped
    if "categoryUuid" not in dashboard_data:
        dashboard_data = {"categoryUuid": category_uuid, "data": dashboard_data}

    url = "https://api.glassnode.com/v1/dashboards/create"

    headers = {"content-type": "application/json"}

    params = {"api_key": API_KEY}

    response = requests.post(url, json=dashboard_data, headers=headers, params=params)
    response.raise_for_status()

    return response


def create_dashboards(
    dashboard_files: Union[List[Union[str, Path]], str, Path], category_uuid: str = "My Dashboards"
) -> Dict[Path, requests.Response]:
    """
    Create multiple Glassnode dashboards via their API.

    Args:
        dashboard_files: Either a list of dashboard file paths or a directory path
        category_uuid: Category for the dashboards (default: "My Dashboards")

    Returns:
        Dictionary mapping file paths to Response objects

    Example:
        # From list of files
        responses = create_dashboards(["dashboards/btc.json", "dashboards/eth.json"])

        # From directory
        responses = create_dashboards("dashboards/examples")
        for file_path, response in responses.items():
            if response.status_code == 200:
                print(f"Created dashboard from {file_path}: {response.json()['uuid']}")
    """
    # Handle directory input
    if isinstance(dashboard_files, (str, Path)):
        directory = Path(dashboard_files)
        if directory.is_dir():
            dashboard_files = list(directory.glob("*.json"))
        else:
            dashboard_files = [dashboard_files]

    responses = {}

    for file_path in dashboard_files:
        file_path = Path(file_path)
        try:
            response = create_dashboard(file_path, category_uuid)
            responses[file_path] = response
            print(f"✓ Created dashboard from {file_path}")
        except Exception as e:
            print(f"✗ Failed to create dashboard from {file_path}: {e}")

            # Store the exception as a mock response for consistency
            class ErrorResponse:
                def __init__(self, error):
                    self.error = error
                    self.status_code = 500

                def json(self):
                    return {"error": str(self.error)}

            responses[file_path] = ErrorResponse(e)

    return responses


def update_dashboards(
    dashboard_mapping: Union[Dict[str, Union[str, Path]], List[tuple], str, Path],
) -> Dict[str, requests.Response]:
    """
    Update multiple Glassnode dashboards via their API.

    Args:
        dashboard_mapping: Can be one of:
            - Dict mapping UUIDs to dashboard file paths
            - List of (uuid, file_path) tuples
            - Directory path (will use .dashboard_mappings.json for UUID lookup)

    Returns:
        Dictionary mapping UUIDs to Response objects

    Example:
        # From dict
        responses = update_dashboards({
            "uuid-1": "dashboards/btc.json",
            "uuid-2": "dashboards/eth.json"
        })

        # From list of tuples
        responses = update_dashboards([
            ("uuid-1", "dashboards/btc.json"),
            ("uuid-2", "dashboards/eth.json")
        ])

        # From directory (uses .dashboard_mappings.json)
        responses = update_dashboards("dashboards/examples")
    """
    # Handle directory input - load mappings from .dashboard_mappings.json
    if isinstance(dashboard_mapping, (str, Path)):
        directory = Path(dashboard_mapping)
        if directory.is_dir():
            mappings_file = Path(".dashboard_mappings.json")
            if not mappings_file.exists():
                raise ValueError("No .dashboard_mappings.json file found for UUID lookups")

            with open(mappings_file, "r") as f:
                all_mappings = json.load(f)

            # Filter mappings for dashboards in this directory
            dashboard_mapping = {}
            for config_path, uuid in all_mappings.items():
                # Convert config path to dashboard path
                dashboard_path = Path(str(Path(config_path).parent).replace("configs", "dashboards", 1)) / (
                    Path(config_path).stem + "_dashboard.json"
                )
                if str(directory) in str(dashboard_path) and dashboard_path.exists():
                    dashboard_mapping[uuid] = dashboard_path

            if not dashboard_mapping:
                raise ValueError(f"No mapped dashboards found in {directory}")

    # Convert list of tuples to dict
    elif isinstance(dashboard_mapping, list):
        dashboard_mapping = dict(dashboard_mapping)

    responses = {}

    for uuid, file_path in dashboard_mapping.items():
        file_path = Path(file_path)
        try:
            response = update_dashboard(uuid, file_path)
            responses[uuid] = response
            print(f"✓ Updated dashboard {uuid} from {file_path}")
        except Exception as e:
            print(f"✗ Failed to update dashboard {uuid} from {file_path}: {e}")

            # Store the exception as a mock response
            class ErrorResponse:
                def __init__(self, error):
                    self.error = error
                    self.status_code = 500

                def json(self):
                    return {"error": str(self.error)}

            responses[uuid] = ErrorResponse(e)

    return responses
