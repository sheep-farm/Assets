#!/usr/bin/env python3
"""
__main__.py - Permite executar o CLI como módulo

Uso:
    python -m src add-deps project.assets pandas numpy
    python -m src list-deps project.assets
    python -m src migrate old.assets new.assets
    python -m src create new.assets
"""

from .cli import main
import sys

if __name__ == '__main__':
    sys.exit(main())
