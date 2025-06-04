#!/usr/bin/env python3
"""
Generate dashboards from configuration files in the configs/ directory.

Usage:
    python generate_dashboards.py                    # Process all config files
    python generate_dashboards.py sol_basic.json     # Process specific file
    python generate_dashboards.py sol_basic multi_asset_futures  # Process multiple files
"""

import json
import sys
from pathlib import Path
from dashboard_builder import create_dashboard_from_file


def main():
    # Setup directories
    configs_dir = Path("configs")
    dashboards_dir = Path("dashboards")
    dashboards_dir.mkdir(exist_ok=True)

    # Determine which config files to process
    if len(sys.argv) > 1:
        # Process specific files from command line arguments
        config_files = []
        for arg in sys.argv[1:]:
            # Add .json extension if not present
            filename = arg if arg.endswith(".json") else f"{arg}.json"
            config_path = configs_dir / filename
            if config_path.exists():
                config_files.append(config_path)
            else:
                print(f"Warning: Config file not found: {config_path}")
    else:
        # Process all JSON files in configs directory
        config_files = sorted(configs_dir.glob("*.json"))
        # Exclude sol_futures.json as it's just a metrics list, not a dashboard config
        config_files = [f for f in config_files if f.name != "sol_futures.json"]

    if not config_files:
        print("No configuration files found to process.")
        return

    print(f"Processing {len(config_files)} dashboard configuration(s)...\n")

    # Process each config file
    for config_path in config_files:
        try:
            print(f"Processing: {config_path.name}")

            # Create dashboard from config file
            dashboard = create_dashboard_from_file(config_path)

            # Generate output filename based on config filename
            output_name = config_path.stem + "_dashboard.json"
            output_path = dashboards_dir / output_name

            # Save dashboard
            with open(output_path, "w") as f:
                json.dump(dashboard.model_dump(exclude_none=True), f, indent=2)

            print(f"  ✓ Created: {output_path}")
            print(f"  ✓ Name: {dashboard.meta.name}")
            print(f"  ✓ Metrics: {len(dashboard.configs)}")
            print()

        except Exception as e:
            print(f"  ✗ Error processing {config_path.name}: {e}")
            print()

    print(f"\nDashboards saved to: {dashboards_dir.absolute()}")


if __name__ == "__main__":
    main()
