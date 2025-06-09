"""Tests for dashboard CLI with focus on UUID mapping edge cases"""

import os
import sys
import json
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the functions we'll test by mocking dependencies first
from unittest.mock import MagicMock, Mock, patch, mock_open

# Create mock modules for the dashboard script
mock_dashboard_client = MagicMock()
mock_dashboard_builder = MagicMock()

# Execute the dashboard file with mocked dependencies
dashboard_globals = {
    "__name__": "dashboard",
    "dashboard_client": mock_dashboard_client,
    "dashboard_builder": mock_dashboard_builder,
    "create_dashboard": mock_dashboard_client.create_dashboard,
    "update_dashboard": mock_dashboard_client.update_dashboard,
    "create_dashboards": mock_dashboard_client.create_dashboards,
    "update_dashboards": mock_dashboard_client.update_dashboards,
    "build_dashboard_from_file": mock_dashboard_builder.build_dashboard_from_file,
    "build_dashboards_from_directory": mock_dashboard_builder.build_dashboards_from_directory,
}

dashboard_path = Path(__file__).parent.parent / "dashboard"
with open(dashboard_path, "r") as f:
    dashboard_code = f.read()
    # Prevent main from running and adjust imports
    dashboard_code = dashboard_code.replace('if __name__ == "__main__":', "if False:")
    dashboard_code = dashboard_code.replace(
        "from dashboard_builder import build_dashboard_from_file, build_dashboards_from_directory", ""
    )
    dashboard_code = dashboard_code.replace(
        "from dashboard_client import create_dashboard, update_dashboard, create_dashboards, update_dashboards", ""
    )
    exec(dashboard_code, dashboard_globals)

# Extract functions we need to test
load_mappings_orig = dashboard_globals["load_mappings"]
save_mapping_orig = dashboard_globals["save_mapping"]
cmd_build = dashboard_globals["cmd_build"]
cmd_create = dashboard_globals["cmd_create"]
cmd_update = dashboard_globals["cmd_update"]


def test_load_mappings():
    """Test loading UUID mappings"""
    # Expected use - file exists
    mappings_data = {"configs/test.json": "uuid-123", "configs/other.json": "uuid-456"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(mappings_data, f)
        temp_path = f.name

    try:
        # Monkey patch the MAPPINGS_FILE for this test
        dashboard_globals["MAPPINGS_FILE"] = temp_path
        mappings = load_mappings_orig()
        assert mappings == mappings_data
    finally:
        os.unlink(temp_path)
        dashboard_globals["MAPPINGS_FILE"] = ".dashboard_mappings.json"

    # Edge case - empty file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{}")
        temp_path = f.name

    try:
        dashboard_globals["MAPPINGS_FILE"] = temp_path
        mappings = load_mappings_orig()
        assert mappings == {}
    finally:
        os.unlink(temp_path)
        dashboard_globals["MAPPINGS_FILE"] = ".dashboard_mappings.json"

    # Edge case - file doesn't exist
    dashboard_globals["MAPPINGS_FILE"] = "nonexistent.json"
    mappings = load_mappings_orig()
    assert mappings == {}
    dashboard_globals["MAPPINGS_FILE"] = ".dashboard_mappings.json"

    # Failing case - corrupted JSON
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{invalid json}")
        temp_path = f.name

    try:
        dashboard_globals["MAPPINGS_FILE"] = temp_path
        try:
            load_mappings_orig()
            assert False, "Should have raised JSONDecodeError"
        except json.JSONDecodeError:
            pass
    finally:
        os.unlink(temp_path)
        dashboard_globals["MAPPINGS_FILE"] = ".dashboard_mappings.json"


def test_save_mapping():
    """Test saving UUID mappings"""
    # Expected use - add new mapping
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"existing.json": "old-uuid"}, f)
        temp_path = f.name

    try:
        dashboard_globals["MAPPINGS_FILE"] = temp_path
        save_mapping_orig("new.json", "new-uuid")

        with open(temp_path) as f:
            mappings = json.load(f)
        assert mappings["existing.json"] == "old-uuid"
        assert mappings["new.json"] == "new-uuid"
    finally:
        os.unlink(temp_path)
        dashboard_globals["MAPPINGS_FILE"] = ".dashboard_mappings.json"

    # Edge case - overwrite existing mapping
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"config.json": "old-uuid"}, f)
        temp_path = f.name

    try:
        dashboard_globals["MAPPINGS_FILE"] = temp_path
        save_mapping_orig("config.json", "new-uuid")

        with open(temp_path) as f:
            mappings = json.load(f)
        assert mappings["config.json"] == "new-uuid"  # Overwritten
    finally:
        os.unlink(temp_path)
        dashboard_globals["MAPPINGS_FILE"] = ".dashboard_mappings.json"

    # Edge case - first mapping (file doesn't exist)
    temp_path = tempfile.mktemp(suffix=".json")
    try:
        dashboard_globals["MAPPINGS_FILE"] = temp_path
        save_mapping_orig("first.json", "first-uuid")

        with open(temp_path) as f:
            mappings = json.load(f)
        assert mappings == {"first.json": "first-uuid"}
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        dashboard_globals["MAPPINGS_FILE"] = ".dashboard_mappings.json"


def test_cmd_create():
    """Test create command with UUID mapping"""
    # Expected use - successful create with mapping
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"uuid": "created-uuid-123"}

    dashboard_globals["create_dashboard"].return_value = mock_response

    # Mock save_mapping
    saved_mappings = []

    def mock_save(config, uuid):
        saved_mappings.append((config, uuid))

    original_save = dashboard_globals["save_mapping"]
    dashboard_globals["save_mapping"] = mock_save

    try:
        args = Mock()
        args.file = "dashboards/test_dashboard.json"

        cmd_create(args)

        # Verify mapping was saved
        assert len(saved_mappings) == 1
        assert saved_mappings[0] == ("configs/test.json", "created-uuid-123")
    finally:
        dashboard_globals["save_mapping"] = original_save

    # Edge case - no UUID in response
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {}  # No UUID

    dashboard_globals["create_dashboard"].return_value = mock_response
    saved_mappings = []

    dashboard_globals["save_mapping"] = mock_save
    try:
        args = Mock()
        args.file = "dashboards/test_dashboard.json"

        cmd_create(args)

        # Mapping should NOT be saved
        assert len(saved_mappings) == 0
    finally:
        dashboard_globals["save_mapping"] = original_save

    # Failing case - API error
    dashboard_globals["create_dashboard"].side_effect = Exception("API Error")

    args = Mock()
    args.file = "dashboard.json"

    try:
        cmd_create(args)
        assert False, "Should have raised SystemExit"
    except SystemExit:
        pass
    finally:
        dashboard_globals["create_dashboard"].side_effect = None


def test_cmd_update_with_uuid():
    """Test update command with explicit UUID"""
    # Expected use - update with UUID and save mapping
    mock_response = Mock()
    mock_response.status_code = 200
    dashboard_globals["update_dashboard"].return_value = mock_response

    saved_mappings = []

    def mock_save(config, uuid):
        saved_mappings.append((config, uuid))

    original_save = dashboard_globals["save_mapping"]
    dashboard_globals["save_mapping"] = mock_save

    try:
        args = Mock()
        args.uuid = "explicit-uuid-123"
        args.file = "dashboards/test_dashboard.json"

        cmd_update(args)

        assert dashboard_globals["update_dashboard"].called
        assert saved_mappings[0] == ("configs/test.json", "explicit-uuid-123")
    finally:
        dashboard_globals["save_mapping"] = original_save


def test_cmd_update_with_config():
    """Test update command with config path (UUID lookup)"""
    # Set up test mappings file
    mappings_data = {"configs/test.json": "mapped-uuid-123"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(mappings_data, f)
        temp_path = f.name

    # Create a temporary directory for dashboard output
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            dashboard_globals["MAPPINGS_FILE"] = temp_path

            # Mock dashboard build
            mock_dashboard = Mock()
            mock_dashboard.model_dump.return_value = {"test": "data"}
            dashboard_globals["build_dashboard_from_file"].return_value = mock_dashboard

            # Mock update response
            mock_response = Mock()
            mock_response.status_code = 200
            dashboard_globals["update_dashboard"].return_value = mock_response

            args = Mock()
            args.uuid = "configs/test.json"  # Config path instead of UUID
            args.file = None

            # Ensure dashboards directory exists
            os.makedirs("dashboards", exist_ok=True)

            cmd_update(args)

            # Verify it used the mapped UUID
            call_args = dashboard_globals["update_dashboard"].call_args[0]
            assert call_args[0] == "mapped-uuid-123"

            # Clean up the created dashboard file
            dashboard_file = Path("dashboards/test_dashboard.json")
            if dashboard_file.exists():
                dashboard_file.unlink()

        finally:
            os.unlink(temp_path)
            dashboard_globals["MAPPINGS_FILE"] = ".dashboard_mappings.json"

    # Edge case - config not in mappings
    empty_mapping = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump({}, empty_mapping)
    empty_mapping.close()

    try:
        dashboard_globals["MAPPINGS_FILE"] = empty_mapping.name

        args = Mock()
        args.uuid = "configs/unmapped.json"
        args.file = None

        try:
            cmd_update(args)
            assert False, "Should have raised SystemExit"
        except SystemExit:
            pass
    finally:
        os.unlink(empty_mapping.name)
        dashboard_globals["MAPPINGS_FILE"] = ".dashboard_mappings.json"


def test_cmd_build():
    """Test build command"""
    # Expected use
    mock_dashboard = Mock()
    mock_dashboard.meta.name = "Test Dashboard"
    mock_dashboard.configs = [Mock(), Mock()]
    mock_dashboard.model_dump.return_value = {"test": "data"}
    dashboard_globals["build_dashboard_from_file"].return_value = mock_dashboard

    args = Mock()
    args.config = "configs/test.json"

    with patch("builtins.open", mock_open()) as mock_file, patch("pathlib.Path.mkdir"):
        cmd_build(args)

        # Verify file was written
        mock_file.assert_called()
        write_calls = mock_file().write.call_args_list
        written_data = "".join(str(call[0][0]) for call in write_calls)
        assert "test" in written_data

    # Failing case - build error
    dashboard_globals["build_dashboard_from_file"].side_effect = FileNotFoundError("Config not found")

    args = Mock()
    args.config = "missing.json"

    try:
        cmd_build(args)
        assert False, "Should have raised SystemExit"
    except SystemExit:
        pass
    finally:
        dashboard_globals["build_dashboard_from_file"].side_effect = None


def test_mapping_edge_cases():
    """Test specific edge cases from our discussion"""
    # Test 1: Multiple creates with same config updates mapping
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"configs/test.json": "old-uuid"}, f)
        temp_path = f.name

    try:
        dashboard_globals["MAPPINGS_FILE"] = temp_path

        # Create new dashboard with same config
        mock_response = Mock()
        mock_response.json.return_value = {"uuid": "new-uuid"}
        dashboard_globals["create_dashboard"].return_value = mock_response

        args = Mock()
        args.file = "dashboards/test_dashboard.json"

        cmd_create(args)

        # Check mapping was updated
        with open(temp_path) as f:
            mappings = json.load(f)
        assert mappings["configs/test.json"] == "new-uuid"

    finally:
        os.unlink(temp_path)
        dashboard_globals["MAPPINGS_FILE"] = ".dashboard_mappings.json"

    # Test 2: Update with different UUID updates mapping
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"configs/test.json": "uuid-1"}, f)
        temp_path = f.name

    try:
        dashboard_globals["MAPPINGS_FILE"] = temp_path

        mock_response = Mock()
        mock_response.status_code = 200
        dashboard_globals["update_dashboard"].return_value = mock_response

        args = Mock()
        args.uuid = "uuid-2"  # Different UUID
        args.file = "dashboards/test_dashboard.json"

        cmd_update(args)

        # Check mapping was updated to new UUID
        with open(temp_path) as f:
            mappings = json.load(f)
        assert mappings["configs/test.json"] == "uuid-2"

    finally:
        os.unlink(temp_path)
        dashboard_globals["MAPPINGS_FILE"] = ".dashboard_mappings.json"


def test_cmd_build_batch():
    """Test batch build command for directories"""
    # Expected use - build multiple dashboards from directory
    mock_dashboards = {
        Path("configs/examples/dash1.json"): Mock(
            meta=Mock(name="Dashboard 1"), configs=[Mock()], model_dump=Mock(return_value={"name": "Dashboard 1"})
        ),
        Path("configs/examples/dash2.json"): Mock(
            meta=Mock(name="Dashboard 2"),
            configs=[Mock(), Mock()],
            model_dump=Mock(return_value={"name": "Dashboard 2"}),
        ),
    }

    dashboard_globals["build_dashboards_from_directory"].return_value = mock_dashboards

    args = Mock()
    args.config = "configs/examples"

    # Mock Path.is_dir to return True
    with (
        patch("pathlib.Path.is_dir", return_value=True),
        patch("pathlib.Path.mkdir"),
        patch("builtins.open", mock_open()),
    ):
        cmd_build(args)

        # Verify build_dashboards_from_directory was called
        dashboard_globals["build_dashboards_from_directory"].assert_called_once_with(Path("configs/examples"))

    # Edge case - empty directory (no dashboards built)
    dashboard_globals["build_dashboards_from_directory"].return_value = {}

    with patch("pathlib.Path.is_dir", return_value=True):
        cmd_build(args)
        # Should complete without error, print 0 dashboards built

    # Failing case - directory doesn't exist
    dashboard_globals["build_dashboards_from_directory"].side_effect = ValueError("Not a directory")

    with patch("pathlib.Path.is_dir", return_value=True):
        try:
            cmd_build(args)
            assert False, "Should have raised SystemExit"
        except SystemExit:
            pass

    dashboard_globals["build_dashboards_from_directory"].side_effect = None


def test_cmd_create_batch():
    """Test batch create command for directories"""
    # Expected use - create multiple dashboards
    mock_responses = {
        Path("dashboards/examples/dash1.json"): Mock(status_code=200, json=Mock(return_value={"uuid": "uuid-1"})),
        Path("dashboards/examples/dash2.json"): Mock(status_code=200, json=Mock(return_value={"uuid": "uuid-2"})),
    }

    dashboard_globals["create_dashboards"].return_value = mock_responses
    dashboard_globals["load_mappings"].return_value = {}

    args = Mock()
    args.file = "dashboards/examples"

    with patch("pathlib.Path.is_dir", return_value=True), patch("builtins.open", mock_open(read_data="{}")):
        cmd_create(args)

        # Verify create_dashboards was called
        dashboard_globals["create_dashboards"].assert_called_once_with(Path("dashboards/examples"))

    # Edge case - some creates fail
    mock_responses_with_failures = {
        Path("dashboards/dash1.json"): Mock(status_code=201, json=Mock(return_value={"uuid": "uuid-1"})),
        Path("dashboards/dash2.json"): Mock(status_code=500, json=Mock(return_value={"error": "Server error"})),
        Path("dashboards/dash3.json"): Mock(status_code=201, json=Mock(return_value={"uuid": "uuid-3"})),
    }

    dashboard_globals["create_dashboards"].return_value = mock_responses_with_failures

    with patch("pathlib.Path.is_dir", return_value=True), patch("builtins.open", mock_open(read_data="{}")):
        cmd_create(args)
        # Should handle partial failures gracefully

    # Failing case - API error
    dashboard_globals["create_dashboards"].side_effect = Exception("Network error")

    with patch("pathlib.Path.is_dir", return_value=True):
        try:
            cmd_create(args)
            assert False, "Should have raised SystemExit"
        except SystemExit:
            pass

    dashboard_globals["create_dashboards"].side_effect = None


def test_cmd_update_batch():
    """Test batch update command for directories"""
    # Expected use - update from configs directory
    mock_dashboards = {
        Path("configs/examples/dash1.json"): Mock(model_dump=Mock(return_value={"name": "Dashboard 1"})),
        Path("configs/examples/dash2.json"): Mock(model_dump=Mock(return_value={"name": "Dashboard 2"})),
    }

    mock_update_responses = {
        "uuid-1": Mock(status_code=200),
        "uuid-2": Mock(status_code=200),
    }

    dashboard_globals["build_dashboards_from_directory"].return_value = mock_dashboards
    dashboard_globals["update_dashboards"].return_value = mock_update_responses

    args = Mock()
    args.uuid = "configs/examples"
    args.file = None

    with (
        patch("pathlib.Path.is_dir", return_value=True),
        patch("pathlib.Path.mkdir"),
        patch("builtins.open", mock_open(read_data="{}")),
    ):
        cmd_update(args)

        # Verify both build and update were called
        # Reset call count since this is not the first test
        assert dashboard_globals["build_dashboards_from_directory"].called
        assert dashboard_globals["update_dashboards"].called

    # Expected use - update from dashboards directory
    dashboard_globals["build_dashboards_from_directory"].reset_mock()
    dashboard_globals["update_dashboards"].reset_mock()

    args.uuid = "dashboards/examples"

    with patch("pathlib.Path.is_dir", return_value=True):
        cmd_update(args)

        # Should not build, just update
        dashboard_globals["build_dashboards_from_directory"].assert_not_called()
        dashboard_globals["update_dashboards"].assert_called_once_with(Path("dashboards/examples"))

    # Edge case - some updates fail
    mock_update_responses_with_failures = {
        "uuid-1": Mock(status_code=200),
        "uuid-2": Mock(status_code=500),
        "uuid-3": Mock(status_code=200),
    }

    dashboard_globals["update_dashboards"].return_value = mock_update_responses_with_failures

    with patch("pathlib.Path.is_dir", return_value=True):
        cmd_update(args)
        # Should handle partial failures

    # Failing case - no mappings found
    dashboard_globals["update_dashboards"].side_effect = ValueError("No mapped dashboards found")

    with patch("pathlib.Path.is_dir", return_value=True):
        try:
            cmd_update(args)
            assert False, "Should have raised SystemExit"
        except SystemExit:
            pass

    dashboard_globals["update_dashboards"].side_effect = None


def test_directory_mirroring():
    """Test that directory structure is preserved configs/ -> dashboards/"""
    # Test build preserves structure
    mock_dashboard = Mock(
        meta=Mock(name="Test Dashboard"), configs=[Mock()], model_dump=Mock(return_value={"test": "data"})
    )
    dashboard_globals["build_dashboard_from_file"].return_value = mock_dashboard

    args = Mock()
    args.config = "configs/examples/subdirectory/test.json"

    with (
        patch("pathlib.Path.is_dir", return_value=False),
        patch("pathlib.Path.mkdir") as mock_mkdir,
        patch("builtins.open", mock_open()) as mock_file,
    ):
        cmd_build(args)

        # Verify correct output path
        expected_path = "dashboards/examples/subdirectory/test_dashboard.json"
        calls = [str(call[0][0]) for call in mock_file.call_args_list if call[0]]
        assert any(expected_path in call for call in calls)

        # Verify directories were created with parents=True
        mock_mkdir.assert_called_with(parents=True, exist_ok=True)


if __name__ == "__main__":
    test_load_mappings()
    test_save_mapping()
    test_cmd_create()
    test_cmd_update_with_uuid()
    test_cmd_update_with_config()
    test_cmd_build()
    test_mapping_edge_cases()
    test_cmd_build_batch()
    test_cmd_create_batch()
    test_cmd_update_batch()
    test_directory_mirroring()
    print("All dashboard CLI tests passed!")
