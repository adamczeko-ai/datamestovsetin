"""Akceptační kontroly integrační DB po živém běhu (jen čtení).

Očekávané hodnoty pocházejí z ověření 22.–23. 10. 2026 (docs/INTEGRACE_NASAZENI.md, tabulka Akceptace)
a ze zdrojových souborů s konkrétním ETagem. Pokud zdroj vydá novou verzi téhož období, může se
hodnota legitimně změnit – proto výsledek obsahuje i ETag importu.

Stavy: ok | selhalo | nespusteno (tabulka/období v DB chybí – zdroj ještě neběžel) | info (bez pevné hodnoty).
"""
from __future__ import annotations

import sqlite3

TOL = 0.005  # Kč – haléřová shoda
MESTO = "00304450"

# (id, popis, SQL, parametry, očekávaná hodnota | None = info)
KONTROLY = [
    ("monitor.rek.2025.4200", "MONITOR 2025-12 ř. 4200 příjmy po konsolidaci (= ZÚ 2025)",
     "SELECT vysledek FROM monitor_rekapitulace WHERE obdobi='2025-12' AND ico=? AND radek='4200'", (MESTO,), 1003369035.77),
    ("monitor.rek.2025.4430", "MONITOR 2025-12 ř. 4430 výdaje po konsolidaci (= ZÚ 2025)",
     "SELECT vysledek FROM monitor_rekapitulace WHERE obdobi='2025-12' AND ico=? AND radek='4430'", (MESTO,), 1082275065.54),
    ("monitor.rek.2024.4200", "MONITOR 2024-12 ř. 4200",
     "SELECT vysledek FROM monitor_rekapitulace WHERE obdobi='2024-12' AND ico=? AND radek='4200'", (MESTO,), 954467444.47),
    ("monitor.rek.2024.4430", "MONITOR 2024-12 ř. 4430",
     "SELECT vysledek FROM monitor_rekapitulace WHERE obdobi='2024-12' AND ico=? AND radek='4430'", (MESTO,), 933707707.92),
    ("monitor.radky.2026-08", "MONITOR 2026-08 vlastní řádky města",
     "SELECT NULLIF(COUNT(*),0) FROM monitor_finm_radek WHERE obdobi='2026-08' AND ico=?", (MESTO,), 1745),
    ("monitor.8115.2026-08", "MONITOR 2026-08 pol. 8115 po změnách (= RO 14/2026)",
     "SELECT SUM(po_zmenach) FROM monitor_finm_radek WHERE obdobi='2026-08' AND ico=? AND polozka='8115'", (MESTO,), 118457944.86),
    ("monitor.8123.2026-08", "MONITOR 2026-08 pol. 8123 po změnách (= RO 12/2026)",
     "SELECT SUM(po_zmenach) FROM monitor_finm_radek WHERE obdobi='2026-08' AND ico=? AND polozka='8123'", (MESTO,), 107500000.00),
    ("monitor.tr.28593987", "Transfer Město → 28593987 (2026-08, kumulativně)",
     "SELECT SUM(castka) FROM observed_transfer WHERE obdobi='2026-08' AND poskytovatel_ico=? AND prijemce_ico='28593987'", (MESTO,), 18298000.00),
    ("monitor.tr.47972114", "Transfer Město → 47972114 (2026-08)",
     "SELECT SUM(castka) FROM observed_transfer WHERE obdobi='2026-08' AND poskytovatel_ico=? AND prijemce_ico='47972114'", (MESTO,), 12400000.00),
    ("monitor.tr.75063468", "Transfer Město → 75063468 (2026-08)",
     "SELECT SUM(castka) FROM observed_transfer WHERE obdobi='2026-08' AND poskytovatel_ico=? AND prijemce_ico='75063468'", (MESTO,), 90006566.86),
    ("monitor.tr.soucet", "Součet transferů od Města 2026-08 (všechny položky)",
     "SELECT SUM(castka) FROM observed_transfer WHERE obdobi='2026-08' AND poskytovatel_ico=?", (MESTO,), 352871840.46),
    ("monitor.tr.prijemci", "Počet příjemců transferů od Města 2026-08",
     "SELECT NULLIF(COUNT(DISTINCT prijemce_ico),0) FROM observed_transfer WHERE obdobi='2026-08' AND poskytovatel_ico=?", (MESTO,), 111),
    ("ruian.am", "RÚIAN adresní místa (VFR 20260930)",
     "SELECT NULLIF(COUNT(*),0) FROM ruian_adresni_misto", (), 3778),
    ("ruian.so", "RÚIAN stavební objekty", "SELECT NULLIF(COUNT(*),0) FROM ruian_stavebni_objekt", (), 6739),
    ("ruian.parcely", "RÚIAN parcely", "SELECT NULLIF(COUNT(*),0) FROM ruian_parcela", (), 26965),
    ("ruian.ulice", "RÚIAN ulice", "SELECT NULLIF(COUNT(*),0) FROM ruian_ulice", (), 144),
    ("vr.subjekty", "ARES-VR subjekty", "SELECT NULLIF(COUNT(*),0) FROM vr_subjekt", (), 9),
    ("vr.soud", "ARES-VR subjekty mimo KS Ostrava (spisová značka bez kódu KSOS)",
     "SELECT CASE WHEN (SELECT COUNT(*) FROM vr_subjekt)=0 THEN NULL ELSE "
     "(SELECT COUNT(*) FROM vr_subjekt WHERE spisova_znacka NOT LIKE '%KSOS%') END", (), 0),
    ("rs.38540900", "Registr smluv verze 38540900 hodnota s DPH",
     "SELECT hodnota_s_dph FROM rs_verze WHERE id_verze='38540900'", (), 500000000.00),
    # RVZ: referenční průchod v prohlížeči 23. 10. 2026 našel 83 unikátních zakázek (IČO kdekoli v záznamu).
    # Konektor hledá IČO v rolích zadavatel/dodavatel/účastník → menší odchylka je možná, proto jen info.
    ("rvz.zakazky", "RVZ unikátní zakázky okruhu města (reference prohlížeč: 83)",
     "SELECT NULLIF(COUNT(*),0) FROM rvz_zakazka", (), None),
    ("rvz.mesto_zadavatel", "RVZ zakázky, kde zadavatelem je okruh města (reference: 53)",
     "SELECT NULLIF(COUNT(*),0) FROM rvz_zakazka WHERE role_okruhu LIKE '%zadavatel%'", (), None),
]

IDEMPOTENCE = {"monitor.finm": "monitor", "ruian.vfr": "ruian", "nipez.rvz": "rvz", "ares.vr": "vr"}  # ledger → sync_run


def _val(con, sql, params):
    try:
        row = con.execute(sql, params).fetchone()
    except sqlite3.OperationalError as e:  # tabulka/sloupec chybí
        return None, str(e)
    return (row[0] if row else None), None


def _idempotence(con, source_id: str, zdroj: str) -> dict:
    """Poslední běh zdroje nesmí nic stahovat znovu, pokud předchozí běh daný soubor už zpracoval."""
    runs = con.execute("SELECT id, started_at, finished_at FROM sync_run WHERE source_id=? AND finished_at IS NOT NULL "
                       "ORDER BY id DESC LIMIT 2", (zdroj,)).fetchall()
    if len(runs) < 2:
        return {"id": f"idempotence.{source_id}", "vysledek": "nespusteno", "pozn": "méně než 2 dokončené běhy"}
    start, end = runs[0][1], runs[0][2]
    rows = con.execute("SELECT status, COUNT(*) FROM sync_ledger WHERE source_id=? AND checked_at>=? AND checked_at<=? "
                       "GROUP BY status", (source_id, start, end)).fetchall()
    st = dict(rows)
    uspech = sum(st.get(k, 0) for k in ("not_modified", "unchanged_hash", "skipped"))
    if not st:
        res = "nespusteno"
    elif st.get("downloaded", 0) == 0 and st.get("error", 0) == 0 and uspech:
        res = "ok"
    else:  # znovu staženo, nebo chyba spojení – idempotence nedoložena
        res = "selhalo"
    return {"id": f"idempotence.{source_id}", "popis": "2. běh nic nestáhl znovu (304 / unchanged_hash / skipped) a bez chyb",
            "zjisteno": st, "vysledek": res}


def run(con) -> dict:
    out = []
    for kid, popis, sql, params, exp in KONTROLY:
        got, err = _val(con, sql, params)
        if got is None:
            res = "nespusteno"
        elif exp is None:
            res = "info"
        elif isinstance(exp, int):
            res = "ok" if int(got) == exp else "selhalo"
        else:
            res = "ok" if abs(float(got) - exp) <= TOL else "selhalo"
        r = {"id": kid, "popis": popis, "ocekavano": exp, "zjisteno": got, "vysledek": res}
        if err:
            r["chyba_sql"] = err
        out.append(r)
    out += [_idempotence(con, s, z) for s, z in IDEMPOTENCE.items()]
    etagy = {r[0]: r[1] for r in con.execute(
        "SELECT url, etag FROM sync_ledger WHERE status='downloaded' AND etag IS NOT NULL GROUP BY url HAVING id=MAX(id)")}
    souhrn = {k: sum(1 for r in out if r["vysledek"] == k) for k in ("ok", "selhalo", "nespusteno", "info")}
    return {"schema": "vsetin-osint/akceptace@1", "kontroly": out, "etagy_importu": etagy, **souhrn}
