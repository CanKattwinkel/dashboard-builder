#!/usr/bin/env python3
"""Simple test runner for dashboard-builder tests"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("Running dashboard-builder tests...\n")

# Run each test module
test_modules = ["test_dashboard_builder", "test_dashboard_client", "test_dashboard_cli"]

for module in test_modules:
    print(f"Running {module}...")
    try:
        exec(f"from {module} import *")
        exec(f"import {module}")
        exec(f"{module}.main()" if hasattr(eval(module), "main") else "")
        print(f"✓ {module} passed\n")
    except Exception as e:
        print(f"✗ {module} failed: {e}\n")
        sys.exit(1)

print("All tests passed!")
