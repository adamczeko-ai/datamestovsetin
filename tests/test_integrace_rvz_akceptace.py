"""Testy: RVZ zpětné doplnění (roční soubor 2024, role účastník), migrace DB a akceptační kontroly. Offline."""
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from integrace import akceptace, db  # noqa: E402
from integrace.sources import rvz  # noqa: E402
from test_integrace import FILES, Base, rvz_doc, zipped  # noqa: E402


def doc_ucastnik():
    d = rvz_doc()
    vz = d["data"][0]["verejna_zakazka"]  # RVZ1: cizí zadavatel i dodavatel
    vz["casti_verejne_zakazky"][0]["zadavaci_postup_pro_cast"]["ucastnici"] = [
        {"dodavatele": [{"subjekt": {"ico": "26782596"}}]}]  # Technické služby jen podaly nabídku
    return d


class TestRvzObdobi(unittest.TestCase):
    def test_url_rocni_2024(self):
        self.assertTrue(rvz.url_for("VZ", 2024, 0).endswith("/VZ-2024_rocni.zip"))
        self.assertTrue(rvz.url_for("VZ", 2025, 3).endswith("/VZ-03-2025.zip"))

    def test_periods(self):
        p = rvz.periods(2024, date(2026, 10, 23))
        self.assertEqual(p[0], (2024, 0))
        self.assertEqual(p[-1], (2026, 9))
        self.assertEqual(len(p), 22)  # = počet souborů referenčního průchodu v prohlížeči 23. 10. 2026
        self.assertEqual(rvz.periods(2024, date(2026, 10, 3))[-1], (2026, 8))  # před 5. dnem ještě ne září
        self.assertEqual(rvz.periods(2026, date(2026, 1, 3))[-1:], [])  # leden před 5. dnem → nic z roku 2026
        self.assertEqual(rvz.periods(2025, date(2026, 1, 3))[-1], (2025, 11))


class TestRvzRole(unittest.TestCase):
    def test_ucastnik(self):
        zak, _ = rvz.filter_records(doc_ucastnik()["data"], {"26782596", "00304450", "28593987"}, "x")
        role = {z["identifikator_nipez"]: z["role_okruhu"] for z in zak}
        self.assertEqual(role, {"RVZ1": "ucastnik", "RVZ2": "zadavatel", "RVZ3": "dodavatel"})


class TestRvzRange(Base):
    def test_sync_range_a_idempotence(self):
        rvz.BASE = self.base + "/rvzr/"
        FILES["/rvzr/VZ-2024_rocni.zip"] = zipped("VZ-2024.json", json.dumps(doc_ucastnik(), ensure_ascii=False))
        FILES["/rvzr/VZ-01-2025.zip"] = zipped("VZ-01-2025.json", json.dumps(rvz_doc(), ensure_ascii=False))
        icos = {"00304450", "28593987", "26782596"}
        r = rvz.sync_range(self.con, self.http, icos, 2024, date(2025, 2, 10))
        self.assertEqual([x["obdobi"] for x in r], ["2024", "2025-01"])
        self.assertEqual([x["status"] for x in r], ["importovano", "importovano"])
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM rvz_zakazka").fetchone()[0], 3)
        r2 = rvz.sync_range(self.con, self.http, icos, 2024, date(2025, 2, 10))
        self.assertEqual([x["status"] for x in r2], ["beze_zmeny", "beze_zmeny"])
        r3 = rvz.sync_range(self.con, self.http, icos, 2024, date(2025, 3, 10))  # 02/2025 neexistuje
        self.assertEqual(r3[-1]["obdobi"], "2025-02")
        self.assertEqual(r3[-1]["status"], "chyba")
        self.assertEqual(r3[0]["status"], "beze_zmeny")


class TestMigrace(unittest.TestCase):
    def test_doplneni_sloupce(self):
        p = os.path.join(tempfile.mkdtemp(), "old.db")
        c = sqlite3.connect(p)
        c.execute("CREATE TABLE rvz_zakazka (identifikator_nipez TEXT PRIMARY KEY, nazev TEXT, druh TEXT, rezim TEXT, "
                  "predpokladana_hodnota_czk REAL, casova_znacka TEXT, zdroj_dat TEXT, zadavatele_ico TEXT, raw_json TEXT, "
                  "source_file TEXT, imported_at TEXT NOT NULL)")
        c.commit(); c.close()
        con = db.connect(p)
        self.assertIn("role_okruhu", {r[1] for r in con.execute("PRAGMA table_info(rvz_zakazka)")})
        db.connect(p)  # podruhé bez chyby


class TestAkceptace(unittest.TestCase):
    def setUp(self):
        self.con = db.connect(os.path.join(tempfile.mkdtemp(), "a.db"))

    def test_prazdna_db_nic_neselze(self):
        rep = akceptace.run(self.con)
        self.assertEqual(rep["selhalo"], 0)
        self.assertEqual(rep["ok"], 0)
        self.assertTrue(all(k["vysledek"] == "nespusteno" for k in rep["kontroly"]))

    def test_shoda_a_neshoda(self):
        ts = "2026-10-23T00:00:00Z"
        self.con.execute("INSERT INTO monitor_rekapitulace (obdobi, ico, radek, vysledek, imported_at) VALUES "
                         "('2025-12','00304450','4200',1003369035.77,?), ('2025-12','00304450','4430',1.0,?)", (ts, ts))
        self.con.execute("INSERT INTO rs_verze (id_verze, hodnota_s_dph, value_kind, imported_at) VALUES ('38540900', 500000000, 'x', ?)", (ts,))
        k = {x["id"]: x["vysledek"] for x in akceptace.run(self.con)["kontroly"]}
        self.assertEqual(k["monitor.rek.2025.4200"], "ok")
        self.assertEqual(k["monitor.rek.2025.4430"], "selhalo")
        self.assertEqual(k["rs.38540900"], "ok")
        self.assertEqual(k["ruian.am"], "nespusteno")

    def test_idempotence(self):
        c = self.con
        for i, (s, e, st) in enumerate([("2026-10-23T05:00:00+00:00", "2026-10-23T05:01:00+00:00", "downloaded"),
                                         ("2026-10-23T06:00:00+00:00", "2026-10-23T06:00:05+00:00", "not_modified")]):
            c.execute("INSERT INTO sync_run (source_id, started_at, finished_at, status) VALUES ('ruian',?,?,'ok')", (s, e))
            c.execute("INSERT INTO sync_ledger (source_id, url, checked_at, status) VALUES ('ruian.vfr','u',?,?)",
                      (s.replace(":00+", ":02+"), st))
        k = {x["id"]: x for x in akceptace.run(c)["kontroly"]}
        self.assertEqual(k["idempotence.ruian.vfr"]["vysledek"], "ok")
        c.execute("INSERT INTO sync_run (source_id, started_at, finished_at, status) VALUES ('ruian','2026-10-23T07:00:00+00:00','2026-10-23T07:01:00+00:00','ok')")
        c.execute("INSERT INTO sync_ledger (source_id, url, checked_at, status) VALUES ('ruian.vfr','u','2026-10-23T07:00:30+00:00','downloaded')")
        k = {x["id"]: x for x in akceptace.run(c)["kontroly"]}
        self.assertEqual(k["idempotence.ruian.vfr"]["vysledek"], "selhalo")
        # jen chyby spojení (zdroj nedostupný) → idempotence NENÍ doložena
        c.execute("INSERT INTO sync_run (source_id, started_at, finished_at, status) VALUES ('ruian','2026-10-23T08:00:00+00:00','2026-10-23T08:01:00+00:00','chyba')")
        c.execute("INSERT INTO sync_ledger (source_id, url, checked_at, status) VALUES ('ruian.vfr','u','2026-10-23T08:00:30+00:00','error')")
        k = {x["id"]: x for x in akceptace.run(c)["kontroly"]}
        self.assertEqual(k["idempotence.ruian.vfr"]["vysledek"], "selhalo")


class TestCliStav(unittest.TestCase):
    def test_chyba_konektoru_neni_ok(self):
        """RÚIAN bez spojení vrací {"status": "chyba"} – sync_run i návratový kód musí chybu nést."""
        import io
        from contextlib import redirect_stdout
        from integrace import __main__ as cli
        from integrace.sources import ruian_vfr
        p = os.path.join(tempfile.mkdtemp(), "c.db")
        puvodni = ruian_vfr.sync
        ruian_vfr.sync = lambda *a, **k: {"status": "chyba", "http": None, "url": "x"}
        try:
            with redirect_stdout(io.StringIO()):
                rc = cli.main(["ruian", "--db", p, "--cache", os.path.dirname(p)])
        finally:
            ruian_vfr.sync = puvodni
        self.assertEqual(rc, 1)
        self.assertEqual(sqlite3.connect(p).execute("SELECT status FROM sync_run").fetchone()[0], "chyba")


if __name__ == "__main__":
    unittest.main()
