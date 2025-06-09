"""Tests for dashboard_client.py"""

import os
import sys
import json
import tempfile
from pathlib import Path
from unittest import mock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import after setting env var
from dashboard_client import (
    create_dashboard,
    update_dashboard,
    create_dashboards,
    update_dashboards,
    create_or_update_dashboard,
    API_KEY,
    load_mappings,
    save_mapping,
)
import requests
import io
import contextlib


def test_create_dashboard():
    """Test creating a dashboard"""
    # Expected use - successful creation
    with mock.patch("requests.post") as mock_post:
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
    with mock.patch("requests.post") as mock_post:
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
    with mock.patch("requests.post") as mock_post:
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
    with mock.patch("requests.post") as mock_post:
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
        mock.patch("requests.get") as mock_get,
        mock.patch("requests.put") as mock_put,
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
        mock.patch("requests.get") as mock_get,
        mock.patch("requests.put") as mock_put,
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
        mock.patch("requests.get") as mock_get,
        mock.patch("requests.put") as mock_put,
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
    with mock.patch("requests.post") as mock_post:
        mock_response = mock.Mock()
        mock_response.raise_for_status = mock.Mock()
        mock_post.return_value = mock_response

        create_dashboard({})

        params = mock_post.call_args[1]["params"]
        assert params["api_key"] == API_KEY

    # Test update includes API key
    with (
        mock.patch("requests.get") as mock_get,
        mock.patch("requests.put") as mock_put,
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
        assert mock_get.call_args[1]["params"]["api_key"] == API_KEY
        assert mock_put.call_args[1]["params"]["api_key"] == API_KEY


def test_create_or_update_dashboard():
    """Test create_or_update_dashboard function"""
    # Test create case - no existing mapping
    with (
        mock.patch("dashboard_client.create_dashboard") as mock_create,
        mock.patch("dashboard_client.update_dashboard") as mock_update,
        mock.patch("dashboard_client.load_mappings", return_value={})
    ):
        mock_create.return_value = mock.Mock(status_code=201, json=lambda: {"uuid": "new-uuid"})
        
        response = create_or_update_dashboard("dashboards/test_dashboard.json")
        
        assert response.status_code == 201
        mock_create.assert_called_once()
        mock_update.assert_not_called()
    
    # Test update case - existing mapping
    with (
        mock.patch("dashboard_client.create_dashboard") as mock_create,
        mock.patch("dashboard_client.update_dashboard") as mock_update,
        mock.patch("dashboard_client.load_mappings", return_value={"configs/test.json": "existing-uuid"})
    ):
        mock_update.return_value = mock.Mock(status_code=200, json=lambda: {"uuid": "existing-uuid"})
        
        response = create_or_update_dashboard("dashboards/test_dashboard.json")
        
        assert response.status_code == 200
        mock_update.assert_called_once_with("existing-uuid", Path("dashboards/test_dashboard.json"))
        mock_create.assert_not_called()


def test_create_dashboards():
    """Test creating multiple dashboards"""
    # Suppress print statements during test
    f = io.StringIO()

    # Expected use - successful batch creation from list
    with (
        mock.patch("dashboard_client.create_dashboard") as mock_create,
        mock.patch("dashboard_client.load_mappings", return_value={})  # No existing dashboards
    ):
        # Mock successful responses
        mock_create.side_effect = [
            mock.Mock(status_code=200, json=lambda: {"uuid": "uuid-1"}),
            mock.Mock(status_code=200, json=lambda: {"uuid": "uuid-2"}),
            mock.Mock(status_code=200, json=lambda: {"uuid": "uuid-3"}),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test files
            (temp_path / "dash1.json").write_text('{"name": "Dashboard 1"}')
            (temp_path / "dash2.json").write_text('{"name": "Dashboard 2"}')
            (temp_path / "dash3.json").write_text('{"name": "Dashboard 3"}')

            file_list = list(temp_path.glob("*.json"))

            with contextlib.redirect_stdout(f):
                responses = create_dashboards(file_list)

            assert len(responses) == 3
            assert all(r.status_code == 200 for r in responses.values())
            assert mock_create.call_count == 3

    # Expected use - from directory
    with (
        mock.patch("dashboard_client.create_dashboard") as mock_create,
        mock.patch("dashboard_client.load_mappings", return_value={})
    ):
        mock_create.return_value = mock.Mock(status_code=201, json=lambda: {"uuid": "new-uuid"})

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            (temp_path / "dash1.json").write_text('{"name": "Dashboard 1"}')
            (temp_path / "dash2.json").write_text('{"name": "Dashboard 2"}')

            with contextlib.redirect_stdout(f):
                responses = create_dashboards(temp_dir)

            assert len(responses) == 2
            assert mock_create.call_count == 2

    # Edge case - single file path (not a list or directory)
    with (
        mock.patch("dashboard_client.create_dashboard") as mock_create,
        mock.patch("dashboard_client.load_mappings", return_value={})
    ):
        mock_create.return_value = mock.Mock(status_code=201)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            f.write(b'{"name": "Single"}')
            temp_file = f.name

        try:
            responses = create_dashboards(temp_file)
            assert len(responses) == 1
            assert Path(temp_file) in responses
        finally:
            os.unlink(temp_file)

    # Edge case - mix of successful and failed creations
    with (
        mock.patch("dashboard_client.create_dashboard") as mock_create,
        mock.patch("dashboard_client.load_mappings", return_value={})
    ):
        # First succeeds, second fails, third succeeds
        mock_create.side_effect = [mock.Mock(status_code=201), Exception("API Error"), mock.Mock(status_code=201)]

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            (temp_path / "good1.json").write_text('{"name": "Good 1"}')
            (temp_path / "bad.json").write_text('{"name": "Bad"}')
            (temp_path / "good2.json").write_text('{"name": "Good 2"}')

            responses = create_dashboards(temp_dir)

            assert len(responses) == 3

            # Check that we have 2 successes and 1 failure
            success_count = sum(1 for r in responses.values() if r.status_code == 201)
            error_count = sum(1 for r in responses.values() if r.status_code == 500)

            assert success_count == 2
            assert error_count == 1

    # Failing case - empty directory
    with mock.patch("dashboard_client.load_mappings", return_value={}):
        with tempfile.TemporaryDirectory() as temp_dir:
            responses = create_dashboards(temp_dir)
            assert len(responses) == 0  # Empty dict, not an error

    # Edge case - directory doesn't exist but treated as file path
    # When a non-existent path is provided, it's treated as a single file
    with mock.patch("dashboard_client.load_mappings", return_value={}):
        responses = create_dashboards("/nonexistent/directory")
        assert len(responses) == 1  # One failed response
        assert Path("/nonexistent/directory") in responses
        assert responses[Path("/nonexistent/directory")].status_code == 500
    
    # Test with create_or_update_dashboard mock
    with mock.patch("dashboard_client.create_or_update_dashboard") as mock_create_or_update:
        mock_create_or_update.side_effect = [
            mock.Mock(status_code=201, json=lambda: {"uuid": "uuid-1"}),
            mock.Mock(status_code=200, json=lambda: {"uuid": "uuid-2"}),
        ]
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test dashboard files
            (temp_path / "dash1.json").write_text('{"name": "Dashboard 1"}')
            (temp_path / "dash2.json").write_text('{"name": "Dashboard 2"}')
            
            responses = create_dashboards(temp_dir)
            
            assert len(responses) == 2
            assert mock_create_or_update.call_count == 2


def test_update_dashboards():
    """Test updating multiple dashboards"""
    # Expected use - from dict mapping
    with mock.patch("dashboard_client.update_dashboard") as mock_update:
        mock_update.side_effect = [mock.Mock(status_code=200), mock.Mock(status_code=200)]

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            file1 = temp_path / "dash1.json"
            file2 = temp_path / "dash2.json"
            file1.write_text('{"name": "Dashboard 1"}')
            file2.write_text('{"name": "Dashboard 2"}')

            mapping = {"uuid-1": str(file1), "uuid-2": str(file2)}

            responses = update_dashboards(mapping)

            assert len(responses) == 2
            assert all(r.status_code == 200 for r in responses.values())
            assert mock_update.call_count == 2

    # Expected use - from list of tuples
    with mock.patch("dashboard_client.update_dashboard") as mock_update:
        mock_update.return_value = mock.Mock(status_code=200)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            f.write(b'{"name": "Test"}')
            temp_file = f.name

        try:
            mapping = [("uuid-1", temp_file), ("uuid-2", temp_file)]
            responses = update_dashboards(mapping)

            assert len(responses) == 2
            assert "uuid-1" in responses
            assert "uuid-2" in responses
        finally:
            os.unlink(temp_file)

    # Expected use - from directory with mappings
    with mock.patch("dashboard_client.update_dashboard") as mock_update:
        mock_update.return_value = mock.Mock(status_code=200)

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create dashboard files WITH the expected path structure
            dashboards_dir = temp_path / "dashboards" / "examples"
            dashboards_dir.mkdir(parents=True)

            dash1 = dashboards_dir / "test1_dashboard.json"
            dash2 = dashboards_dir / "test2_dashboard.json"
            dash1.write_text('{"name": "Test 1"}')
            dash2.write_text('{"name": "Test 2"}')

            # Create configs directory to match the mappings
            configs_dir = temp_path / "configs" / "examples"
            configs_dir.mkdir(parents=True)

            # Create mappings file with paths relative to temp_dir
            mappings = {
                str(configs_dir / "test1.json"): "uuid-1",
                str(configs_dir / "test2.json"): "uuid-2",
                str(temp_path / "configs" / "other" / "test3.json"): "uuid-3",  # Different directory
            }

            mappings_file = temp_path / ".dashboard_mappings.json"
            mappings_file.write_text(json.dumps(mappings))

            # Change to temp directory for the test
            original_cwd = os.getcwd()
            os.chdir(temp_path)

            try:
                # Mock Path.exists to return True for our test files
                with mock.patch("pathlib.Path.exists") as mock_exists:
                    # The mock needs to handle being called as a method
                    mock_exists.return_value = True

                    responses = update_dashboards(dashboards_dir)

                    assert len(responses) == 2  # Only files in examples directory
                    assert "uuid-1" in responses
                    assert "uuid-2" in responses
                    assert "uuid-3" not in responses  # Different directory
            finally:
                os.chdir(original_cwd)

    # Edge case - some updates succeed, some fail
    with mock.patch("dashboard_client.update_dashboard") as mock_update:
        mock_update.side_effect = [mock.Mock(status_code=200), Exception("Network error"), mock.Mock(status_code=200)]

        mapping = {"uuid-1": "file1.json", "uuid-2": "file2.json", "uuid-3": "file3.json"}

        responses = update_dashboards(mapping)

        assert len(responses) == 3
        success_count = sum(1 for r in responses.values() if r.status_code == 200)
        error_count = sum(1 for r in responses.values() if r.status_code == 500)

        assert success_count == 2
        assert error_count == 1

    # Failing case - directory with no mappings file
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            update_dashboards(temp_dir)
            assert False, "Should raise ValueError for missing mappings"
        except ValueError as e:
            # The error message depends on whether file exists but is empty vs doesn't exist
            assert "No" in str(e) and "found" in str(e)

    # Failing case - directory with no matching dashboards
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create mappings file with non-matching paths
        mappings = {"configs/other/test.json": "uuid-1"}
        (temp_path / ".dashboard_mappings.json").write_text(json.dumps(mappings))

        # Create dashboard directory but no matching files
        (temp_path / "dashboards" / "examples").mkdir(parents=True)

        original_cwd = os.getcwd()
        os.chdir(temp_path)

        try:
            update_dashboards("dashboards/examples")
            assert False, "Should raise ValueError for no matching dashboards"
        except ValueError as e:
            assert "No mapped dashboards found" in str(e)
        finally:
            os.chdir(original_cwd)


def test_mappings():
    """Test UUID mapping functions"""
    import dashboard_client

    # Save original MAPPINGS_FILE value
    original_mappings_file = dashboard_client.MAPPINGS_FILE

    # Expected use - save and load mappings
    temp_path = tempfile.mktemp(suffix=".json")

    try:
        dashboard_client.MAPPINGS_FILE = temp_path

        # Test loading empty file
        mappings = load_mappings()
        assert mappings == {}

        # Test saving mapping
        save_mapping("configs/test.json", "uuid-123")

        # Test loading saved mapping
        mappings = load_mappings()
        assert mappings["configs/test.json"] == "uuid-123"

        # Test updating existing mapping
        save_mapping("configs/test.json", "new-uuid")
        mappings = load_mappings()
        assert mappings["configs/test.json"] == "new-uuid"

        # Test adding another mapping
        save_mapping("configs/other.json", "uuid-456")
        mappings = load_mappings()
        assert len(mappings) == 2
        assert mappings["configs/test.json"] == "new-uuid"
        assert mappings["configs/other.json"] == "uuid-456"

    finally:
        os.unlink(temp_path)
        dashboard_client.MAPPINGS_FILE = original_mappings_file


if __name__ == "__main__":
    test_create_dashboard()
    test_update_dashboard()
    test_api_key_handling()
    test_create_dashboards()
    test_update_dashboards()
    test_mappings()
    print("All dashboard_client tests passed!")
