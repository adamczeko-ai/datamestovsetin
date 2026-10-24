"""Inkrementální sběr veřejných dokumentů do data/*.jsonl (vstupní bod scripts/sber.py).

- store: JSONL s deduplikací podle (id, sha256), append-only verze, manifest a RUNLOG.
- pseudo: pseudonymizace fyzických osob v odvozených datech.
- vismo, zdroje: parsery webu města (CMS vismo), profilu zadavatele, registru smluv, ARES.
Jen standardní knihovna; text z PDF přes `pdftotext`, z .doc přes `antiword` (pokud jsou k dispozici).
"""
