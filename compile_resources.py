#!/usr/bin/env python3
"""Compile GResource bundle manually (workaround for missing glib-compile-resources)"""

import subprocess
import sys
from pathlib import Path

src_dir = Path('src')
gresource_xml = src_dir / 'assets.gresource.xml'
gresource_output = src_dir / 'assets.gresource'

# Try using glib-compile-resources
try:
    result = subprocess.run([
        'glib-compile-resources',
        str(gresource_xml),
        f'--target={gresource_output}',
        f'--sourcedir={src_dir}'
    ], check=True, capture_output=True, text=True)
    print(f"✓ GResource compiled: {gresource_output}")
    print(result.stdout)
    sys.exit(0)
except FileNotFoundError:
    print("✗ glib-compile-resources not found")
    print("  Install with: sudo apt install libglib2.0-dev-bin")
    print("\n  Alternative: Use meson build system")
    sys.exit(1)
except subprocess.CalledProcessError as e:
    print(f"✗ Compilation failed: {e}")
    print(e.stderr)
    sys.exit(1)
