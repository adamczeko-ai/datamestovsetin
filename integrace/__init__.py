"""VSETÍN OSINT – konektory veřejných datových zdrojů.

Balík je samostatný (jen standardní knihovna Pythonu 3.10+), zapisuje do vlastní
SQLite databáze (výchozí `integrace.db`) a evidenci stahování (`sync_ledger`).
Aplikace nasvsetin.cz z ní může číst nebo ji importovat – balík NEMĚNÍ databázi
aplikace.

Použití: viz `python -m integrace --help` a docs/INTEGRACE_NASAZENI.md.
"""

__version__ = "0.1.0"
