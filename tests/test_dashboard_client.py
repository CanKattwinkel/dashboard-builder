"""Tests for dashboard_client.py"""

import os
import sys
import json
import tempfile
from pathlib import Path
from unittest import mock
import requests

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock the API key at import time
with mock.patch.dict(os.environ, {"GLASSNODE_API_KEY": "test-key"}):
    from dashboard_client import create_dashboard, update_dashboard


def test_create_dashboard():
    """Test creating a dashboard"""
    # Expected use - successful creation
    with mock.patch("dashboard_client.requests.post") as mock_post:
        mock_response = mock.Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"uuid": "new-uuid-123"}
        mock_response.raise_for_status = mock.Mock()
        mock_post.return_value = mock_response

        dashboard_data = {"configs": [], "layouts": [], "meta": {"name": "Test"}}
        response = create_dashboard(dashboard_data)

        # Verify API was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://api.glassnode.com/v1/dashboards/create"
        assert call_args[1]["json"]["data"] == dashboard_data
        assert call_args[1]["json"]["categoryUuid"] == "My Dashboards"
        assert response.json()["uuid"] == "new-uuid-123"

    # Edge case - dashboard data already wrapped with categoryUuid
    with mock.patch("dashboard_client.requests.post") as mock_post:
        mock_response = mock.Mock()
        mock_response.raise_for_status = mock.Mock()
        mock_post.return_value = mock_response

        wrapped_data = {"categoryUuid": "Custom Category", "data": {"configs": []}}
        create_dashboard(wrapped_data)

        # Should not double-wrap
        call_json = mock_post.call_args[1]["json"]
        assert call_json["categoryUuid"] == "Custom Category"
        assert "data" in call_json

    # Edge case - create from file
    with mock.patch("dashboard_client.requests.post") as mock_post:
        mock_response = mock.Mock()
        mock_response.raise_for_status = mock.Mock()
        mock_post.return_value = mock_response

        test_data = {"configs": [], "meta": {"name": "From File"}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_path = f.name

        try:
            create_dashboard(temp_path)
            call_json = mock_post.call_args[1]["json"]
            assert call_json["data"]["meta"]["name"] == "From File"
        finally:
            os.unlink(temp_path)

    # Failing case - API error
    with mock.patch("dashboard_client.requests.post") as mock_post:
        mock_response = mock.Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("400 Bad Request")
        mock_post.return_value = mock_response

        try:
            create_dashboard({})
            assert False, "Should have raised HTTPError"
        except requests.HTTPError:
            pass


def test_update_dashboard():
    """Test updating a dashboard"""
    # Expected use - successful update
    with (
        mock.patch("dashboard_client.requests.get") as mock_get,
        mock.patch("dashboard_client.requests.put") as mock_put,
    ):
        # Mock GET response
        mock_get_resp = mock.Mock()
        mock_get_resp.json.return_value = {"categoryUuid": "existing-category"}
        mock_get_resp.raise_for_status = mock.Mock()
        mock_get.return_value = mock_get_resp

        # Mock PUT response
        mock_put_resp = mock.Mock()
        mock_put_resp.status_code = 200
        mock_put_resp.raise_for_status = mock.Mock()
        mock_put.return_value = mock_put_resp

        dashboard_data = {"configs": [], "layouts": []}
        update_dashboard("test-uuid", dashboard_data)

        # Verify GET was called to fetch category
        assert "test-uuid" in mock_get.call_args[0][0]

        # Verify PUT was called with wrapped data
        put_json = mock_put.call_args[1]["json"]
        assert put_json["categoryUuid"] == "existing-category"
        assert put_json["data"] == dashboard_data

    # Edge case - update from file path
    with (
        mock.patch("dashboard_client.requests.get") as mock_get,
        mock.patch("dashboard_client.requests.put") as mock_put,
    ):
        mock_get_resp = mock.Mock()
        mock_get_resp.json.return_value = {"categoryUuid": "cat-123"}
        mock_get_resp.raise_for_status = mock.Mock()
        mock_get.return_value = mock_get_resp

        mock_put_resp = mock.Mock()
        mock_put_resp.raise_for_status = mock.Mock()
        mock_put.return_value = mock_put_resp

        test_data = {"configs": [], "meta": {"name": "Update File"}}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            temp_path = f.name

        try:
            update_dashboard("uuid-123", temp_path)
            put_json = mock_put.call_args[1]["json"]
            assert put_json["data"]["meta"]["name"] == "Update File"
        finally:
            os.unlink(temp_path)

    # Edge case - dashboard has no categoryUuid (uses default)
    with (
        mock.patch("dashboard_client.requests.get") as mock_get,
        mock.patch("dashboard_client.requests.put") as mock_put,
    ):
        mock_get_resp = mock.Mock()
        mock_get_resp.json.return_value = {}  # No categoryUuid
        mock_get_resp.raise_for_status = mock.Mock()
        mock_get.return_value = mock_get_resp

        mock_put_resp = mock.Mock()
        mock_put_resp.raise_for_status = mock.Mock()
        mock_put.return_value = mock_put_resp

        update_dashboard("uuid-123", {})
        put_json = mock_put.call_args[1]["json"]
        assert put_json["categoryUuid"] == "My Dashboards"  # Default

    # Failing case - dashboard not found
    with mock.patch("dashboard_client.requests.get") as mock_get:
        mock_get_resp = mock.Mock()
        mock_get_resp.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_get.return_value = mock_get_resp

        try:
            update_dashboard("nonexistent-uuid", {})
            assert False, "Should have raised HTTPError"
        except requests.HTTPError as e:
            assert "404" in str(e)


def test_api_key_handling():
    """Test API key is included in requests"""
    # Test create includes API key
    with mock.patch("dashboard_client.requests.post") as mock_post:
        mock_response = mock.Mock()
        mock_response.raise_for_status = mock.Mock()
        mock_post.return_value = mock_response

        create_dashboard({})

        params = mock_post.call_args[1]["params"]
        assert params["api_key"] == "test-key"

    # Test update includes API key
    with (
        mock.patch("dashboard_client.requests.get") as mock_get,
        mock.patch("dashboard_client.requests.put") as mock_put,
    ):
        mock_get_resp = mock.Mock()
        mock_get_resp.json.return_value = {"categoryUuid": "cat"}
        mock_get_resp.raise_for_status = mock.Mock()
        mock_get.return_value = mock_get_resp

        mock_put_resp = mock.Mock()
        mock_put_resp.raise_for_status = mock.Mock()
        mock_put.return_value = mock_put_resp

        update_dashboard("uuid", {})

        # Check both GET and PUT have API key
        assert mock_get.call_args[1]["params"]["api_key"] == "test-key"
        assert mock_put.call_args[1]["params"]["api_key"] == "test-key"


if __name__ == "__main__":
    test_create_dashboard()
    test_update_dashboard()
    test_api_key_handling()
    print("All dashboard_client tests passed!")
