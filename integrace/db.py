"""SQLite schéma integrační databáze. Všechny zápisy jsou idempotentní (UPSERT podle přirozeného klíče)."""
from __future__ import annotations

import sqlite3

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS sync_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id TEXT NOT NULL, url TEXT NOT NULL, checked_at TEXT NOT NULL,
  http_status INTEGER, etag TEXT, last_modified TEXT, size_bytes INTEGER, sha256 TEXT,
  status TEXT NOT NULL CHECK (status IN ('downloaded','not_modified','unchanged_hash','error','skipped')),
  local_path TEXT, attempts INTEGER NOT NULL DEFAULT 1, error TEXT
);
CREATE INDEX IF NOT EXISTS ix_ledger ON sync_ledger(source_id, url, id);

CREATE TABLE IF NOT EXISTS sync_run (
  id INTEGER PRIMARY KEY AUTOINCREMENT, source_id TEXT NOT NULL,
  started_at TEXT NOT NULL, finished_at TEXT, status TEXT, records_upserted INTEGER DEFAULT 0,
  detail TEXT
);

-- MONITOR FIN 2-12 M: řádky výkazu pro sledovaná IČO (vlastní rozpočet i role partnera)
CREATE TABLE IF NOT EXISTS monitor_finm_radek (
  obdobi TEXT NOT NULL,            -- RRRR-MM
  vykaz_tab TEXT NOT NULL,         -- např. 000100
  ico TEXT NOT NULL, ucjed TEXT,
  typ TEXT, paragraf TEXT, polozka TEXT NOT NULL, uz TEXT, zdroj TEXT, nastroj TEXT, mimud TEXT,
  partner_ico TEXT,
  schvaleny REAL, po_zmenach REAL, vysledek REAL,
  source_url TEXT NOT NULL, etag TEXT, imported_at TEXT NOT NULL,
  PRIMARY KEY (obdobi, vykaz_tab, ico, typ, paragraf, polozka, uz, zdroj, nastroj, mimud, partner_ico)
);
CREATE INDEX IF NOT EXISTS ix_finm_partner ON monitor_finm_radek(partner_ico, obdobi);

-- MONITOR tab. IV rekapitulace (do 2025) / odvozená (od 2026)
CREATE TABLE IF NOT EXISTS monitor_rekapitulace (
  obdobi TEXT NOT NULL, ico TEXT NOT NULL, radek TEXT NOT NULL,
  schvaleny REAL, po_zmenach REAL, vysledek REAL,
  odvozeno INTEGER NOT NULL DEFAULT 0, source_url TEXT, etag TEXT, imported_at TEXT NOT NULL,
  PRIMARY KEY (obdobi, ico, radek)
);

-- Zjištěné transfery (Partner Fin) – indicie, ne úhrada konkrétní smlouvy
CREATE TABLE IF NOT EXISTS observed_transfer (
  obdobi TEXT NOT NULL, poskytovatel_ico TEXT NOT NULL, prijemce_ico TEXT NOT NULL,
  polozka TEXT NOT NULL, castka REAL NOT NULL,
  evidence_level TEXT NOT NULL DEFAULT 'secondary_aggregate', source_url TEXT, imported_at TEXT NOT NULL,
  PRIMARY KEY (obdobi, poskytovatel_ico, prijemce_ico, polozka)
);

-- RÚIAN
CREATE TABLE IF NOT EXISTS ruian_adresni_misto (
  kod INTEGER PRIMARY KEY, cislo_domovni INTEGER, cislo_orientacni INTEGER, cislo_orientacni_pismeno TEXT,
  psc TEXT, ulice_kod INTEGER, stavebni_objekt_kod INTEGER, x REAL, y REAL, plati_od TEXT,
  source_file TEXT, imported_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ruian_stavebni_objekt (
  kod INTEGER PRIMARY KEY, cast_obce_kod INTEGER, identifikacni_parcela_id INTEGER, typ_kod INTEGER,
  zpusob_vyuziti_kod INTEGER, pocet_bytu INTEGER, pocet_podlazi INTEGER, zastavena_plocha INTEGER,
  isknbudova_id INTEGER, dokonceni TEXT, x REAL, y REAL, plati_od TEXT, source_file TEXT, imported_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ruian_parcela (
  id INTEGER PRIMARY KEY, kmenove_cislo INTEGER, pododdeleni INTEGER, vymera INTEGER, druh_pozemku_kod INTEGER,
  druh_cislovani_kod INTEGER, katastralni_uzemi_kod INTEGER, x REAL, y REAL, plati_od TEXT,
  source_file TEXT, imported_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ruian_ulice (
  kod INTEGER PRIMARY KEY, nazev TEXT, obec_kod INTEGER, plati_od TEXT, source_file TEXT, imported_at TEXT NOT NULL
);

-- RVZ (NIPEZ open data)
CREATE TABLE IF NOT EXISTS rvz_zakazka (
  identifikator_nipez TEXT PRIMARY KEY, nazev TEXT, druh TEXT, rezim TEXT,
  predpokladana_hodnota_czk REAL, casova_znacka TEXT, zdroj_dat TEXT,
  zadavatele_ico TEXT, raw_json TEXT, source_file TEXT, imported_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rvz_smlouva (
  identifikator_nipez TEXT NOT NULL, cast_nipez TEXT NOT NULL, poradi INTEGER NOT NULL,
  datum_uzavreni TEXT, cena_bez_dph REAL, cena_s_dph REAL, mena TEXT, dodavatele_ico TEXT,
  PRIMARY KEY (identifikator_nipez, cast_nipez, poradi)
);

-- Veřejný rejstřík (ARES-VR): orgány a společníci – BEZ dat narození a adres FO
CREATE TABLE IF NOT EXISTS vr_subjekt (
  ico TEXT PRIMARY KEY, nazev TEXT, predchozi_nazvy TEXT, spisova_znacka TEXT, pravni_forma TEXT,
  datum_zapisu TEXT, datum_vymazu TEXT, sidlo_adm_kod INTEGER, source_url TEXT, sha256 TEXT, imported_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS vr_angazma (
  ico TEXT NOT NULL, organ TEXT NOT NULL, typ_osoby TEXT NOT NULL,
  jmeno TEXT, osoba_ico TEXT, funkce TEXT, podil TEXT,
  vznik_funkce TEXT, zanik_funkce TEXT, datum_zapisu TEXT NOT NULL, datum_vymazu TEXT,
  imported_at TEXT NOT NULL,
  PRIMARY KEY (ico, organ, typ_osoby, jmeno, osoba_ico, funkce, datum_zapisu)
);

-- Registr smluv: hodnoty verzí (oprava value_kind)
CREATE TABLE IF NOT EXISTS rs_verze (
  id_verze TEXT PRIMARY KEY, id_smlouvy TEXT, predmet TEXT, datum_uzavreni TEXT, cas_zverejneni TEXT,
  hodnota_bez_dph REAL, hodnota_s_dph REAL, cizi_hodnota REAL, cizi_mena TEXT, value_kind TEXT NOT NULL,
  publikujici_ico TEXT, strany_ico TEXT, platny INTEGER, source_url TEXT, imported_at TEXT NOT NULL
);

-- MONITOR Registr dotací (nedokumentované API – jen s explicitním povolením)
CREATE TABLE IF NOT EXISTS dotace_uzemni (
  rok INTEGER NOT NULL, load_id INTEGER NOT NULL, poskytovatel_ico TEXT NOT NULL, prijemce_ico TEXT NOT NULL,
  prijemce_nazev TEXT, prijemce_forma TEXT, druh TEXT NOT NULL, poskytnuto REAL, vraceno REAL, imported_at TEXT NOT NULL,
  PRIMARY KEY (rok, load_id, poskytovatel_ico, prijemce_ico, druh)
);
CREATE TABLE IF NOT EXISTS dotace_statni (
  rok INTEGER NOT NULL, id_dotace TEXT NOT NULL, poskytovatel_ico TEXT, prijemce_ico TEXT NOT NULL,
  nazev TEXT, program TEXT, datum_zdroj TEXT, castka REAL, imported_at TEXT NOT NULL,
  PRIMARY KEY (rok, id_dotace, prijemce_ico)
);
"""


def connect(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    return con


def upsert(con: sqlite3.Connection, table: str, rows: list[dict]) -> int:
    if not rows:
        return 0
    cols = list(rows[0])
    sql = f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})"
    con.executemany(sql, [[r.get(c) for c in cols] for r in rows])
    return len(rows)
