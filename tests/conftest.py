"""Pytest-Setup für Packet Clicker.

Muss VOR dem ersten ``import packet_clicker`` laufen: das Modul ruft beim
Import ``pygame.init()`` und ``display.set_mode()`` auf, daher brauchen wir
in CI/headless die Dummy-Treiber für Video und Audio.
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

# Repo-Wurzel auf den Importpfad, damit `import packet_clicker` von überall geht.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import packet_clicker as pc


@pytest.fixture
def game(tmp_path, monkeypatch):
    """Frisches Game mit leerem Zustand und Save-Pfad in einem tmp-Verzeichnis.

    Der Save-Pfad zeigt auf eine (noch) nicht existierende Datei, damit
    ``Game.__init__`` mit Defaults startet statt das echte ``packet_save.json``
    des Spielers zu laden — und ``save()`` nichts Echtes überschreibt.
    """
    monkeypatch.setattr(pc, "SAVE_PATH", str(tmp_path / "packet_save.json"))
    g = pc.Game()
    return g
