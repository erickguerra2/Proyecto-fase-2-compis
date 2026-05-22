#!/usr/bin/env python3
"""Interfaz grafica del generador de analizadores sintacticos."""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from src.gui.app import App

if __name__ == "__main__":
    App().mainloop()
