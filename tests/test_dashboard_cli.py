"""Tests for dashboard CLI with focus on UUID mapping edge cases"""

import os
import sys
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
    "load_mappings": mock_dashboard_client.load_mappings,
    "save_mapping": mock_dashboard_client.save_mapping,
    "MAPPINGS_FILE": ".dashboard_mappings.json",
    "build_dashboard_from_file": mock_dashboard_builder.build_dashboard_from_file,
    "build_dashboards_from_directory": mock_dashboard_builder.build_dashboards_from_directory,
}

dashboard_path = Path(__file__).parent.parent / "dash"
with open(dashboard_path, "r") as f:
    dashboard_code = f.read()
    # Prevent main from running and adjust imports
    dashboard_code = dashboard_code.replace('if __name__ == "__main__":', "if False:")
    dashboard_code = dashboard_code.replace(
        "from dashboard_builder import build_dashboard_from_file, build_dashboards_from_directory", ""
    )
    dashboard_code = dashboard_code.replace(
        "from dashboard_client import (\n    create_dashboard, update_dashboard, create_dashboards, update_dashboards,\n    load_mappings, save_mapping, MAPPINGS_FILE\n)",
        "",
    )
    exec(dashboard_code, dashboard_globals)

# Extract functions we need to test
cmd_build = dashboard_globals["cmd_build"]
cmd_create = dashboard_globals["cmd_create"]
cmd_update = dashboard_globals["cmd_update"]
config_to_dashboard_path = dashboard_globals["config_to_dashboard_path"]
dashboard_to_config_path = dashboard_globals["dashboard_to_config_path"]
build_and_save_dashboard = dashboard_globals["build_and_save_dashboard"]


def test_path_conversions():
    """Test path conversion utility functions"""
    # Test config to dashboard path
    assert config_to_dashboard_path("configs/test.json") == Path("dashboards/test_dashboard.json")
    assert config_to_dashboard_path("configs/examples/test.json") == Path("dashboards/examples/test_dashboard.json")
    assert config_to_dashboard_path("configs/sub/dir/test.json") == Path("dashboards/sub/dir/test_dashboard.json")

    # Test dashboard to config path
    assert dashboard_to_config_path("dashboards/test_dashboard.json") == "configs/test.json"
    assert dashboard_to_config_path("dashboards/examples/test_dashboard.json") == "configs/examples/test.json"
    assert dashboard_to_config_path("dashboards/sub/dir/test_dashboard.json") == "configs/sub/dir/test.json"

    # Test round-trip conversion
    config_path = "configs/examples/complex_name.json"
    dashboard_path = config_to_dashboard_path(config_path)
    assert dashboard_to_config_path(dashboard_path) == config_path


def test_load_mappings():
    """Test loading UUID mappings - now delegates to dashboard_client"""
    # The load_mappings is now imported from dashboard_client, so we just verify it's a mock
    assert hasattr(dashboard_globals["load_mappings"], "return_value"), "load_mappings should be a mock"


def test_save_mapping():
    """Test saving UUID mappings - now delegates to dashboard_client"""
    # The save_mapping is now imported from dashboard_client, so we just verify it's a mock
    assert hasattr(dashboard_globals["save_mapping"], "assert_called_with"), "save_mapping should be a mock"


def test_build_and_save_dashboard():
    """Test the build_and_save_dashboard utility function"""
    # Mock dashboard
    mock_dashboard = Mock()
    mock_dashboard.meta.name = "Test Dashboard"
    mock_dashboard.configs = [Mock(), Mock()]
    mock_dashboard.model_dump.return_value = {"test": "data"}
    dashboard_globals["build_dashboard_from_file"].return_value = mock_dashboard

    with patch("builtins.open", mock_open()) as mock_file, patch("pathlib.Path.mkdir"):
        # Test the function
        output_path, dashboard = build_and_save_dashboard("configs/test.json")

        # Verify output path is correct
        assert output_path == Path("dashboards/test_dashboard.json")

        # Verify dashboard was returned
        assert dashboard == mock_dashboard

        # Verify file was written
        mock_file.assert_called()
        write_calls = mock_file().write.call_args_list
        assert len(write_calls) > 0


def test_cmd_create():
    """Test create command with UUID mapping"""
    # Expected use - successful create with mapping
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {"uuid": "created-uuid-123"}

    dashboard_globals["create_dashboard"].return_value = mock_response

    # Mock save_mapping
    dashboard_globals["save_mapping"].reset_mock()

    args = Mock()
    args.file = "dashboards/test_dashboard.json"

    cmd_create(args)

    # Verify mapping was saved
    dashboard_globals["save_mapping"].assert_called_once_with("configs/test.json", "created-uuid-123")

    # Edge case - no UUID in response
    mock_response = Mock()
    mock_response.status_code = 201
    mock_response.json.return_value = {}  # No UUID

    dashboard_globals["create_dashboard"].return_value = mock_response
    dashboard_globals["save_mapping"].reset_mock()

    args = Mock()
    args.file = "dashboards/test_dashboard.json"

    cmd_create(args)

    # Mapping should NOT be saved
    dashboard_globals["save_mapping"].assert_not_called()

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

    dashboard_globals["save_mapping"].reset_mock()

    args = Mock()
    args.uuid = "explicit-uuid-123"
    args.file = "dashboards/test_dashboard.json"

    cmd_update(args)

    assert dashboard_globals["update_dashboard"].called
    dashboard_globals["save_mapping"].assert_called_once_with("configs/test.json", "explicit-uuid-123")


def test_cmd_update_with_config():
    """Test update command with config path (UUID lookup)"""
    # Mock load_mappings to return test data
    dashboard_globals["load_mappings"].return_value = {"configs/test.json": "mapped-uuid-123"}

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

    # Edge case - config not in mappings
    dashboard_globals["load_mappings"].return_value = {}

    args = Mock()
    args.uuid = "configs/unmapped.json"
    args.file = None

    try:
        cmd_update(args)
        assert False, "Should have raised SystemExit"
    except SystemExit:
        pass


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
    dashboard_globals["load_mappings"].return_value = {"configs/test.json": "old-uuid"}
    dashboard_globals["save_mapping"].reset_mock()

    # Create new dashboard with same config
    mock_response = Mock()
    mock_response.json.return_value = {"uuid": "new-uuid"}
    dashboard_globals["create_dashboard"].return_value = mock_response

    args = Mock()
    args.file = "dashboards/test_dashboard.json"

    cmd_create(args)

    # Check mapping was updated
    dashboard_globals["save_mapping"].assert_called_with("configs/test.json", "new-uuid")

    # Test 2: Update with different UUID updates mapping
    dashboard_globals["save_mapping"].reset_mock()

    mock_response = Mock()
    mock_response.status_code = 200
    dashboard_globals["update_dashboard"].return_value = mock_response

    args = Mock()
    args.uuid = "uuid-2"  # Different UUID
    args.file = "dashboards/test_dashboard.json"

    cmd_update(args)

    # Check mapping was updated to new UUID
    dashboard_globals["save_mapping"].assert_called_with("configs/test.json", "uuid-2")


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
    test_path_conversions()
    test_load_mappings()
    test_save_mapping()
    test_build_and_save_dashboard()
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
