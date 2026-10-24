"""Testy kontrol K7–K13 (scripts/kontrola_konzistence_krizova.py).

Běží nad kopií repa v dočasné složce: čistá kopie nesmí dát nález K7, K8, K9, K10, K11, K13;
kopie s podvrženými vadami musí dát nález u každé z kontrol K7–K13.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NOVE = ("K7", "K8", "K9", "K10", "K11", "K12", "K13")


def spust(koren):
    vystup = os.path.join(koren, "vystup.json")
    r = subprocess.run([sys.executable, "scripts/kontrola_konzistence.py", "--vystup", vystup],
                       cwd=koren, capture_output=True, text=True)
    if r.returncode:
        raise AssertionError(r.stderr[-500:])
    with open(vystup, encoding="utf-8") as f:
        return {s["kontrola"]: s["pocet"] for s in json.load(f)["souhrn"]}


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = tempfile.mkdtemp()
        cls.cisty, cls.vadny = os.path.join(cls.t, "cisty"), os.path.join(cls.t, "vadny")
        for k in (cls.cisty, cls.vadny):
            for d in ("data", "scripts"):
                shutil.copytree(os.path.join(ROOT, d), os.path.join(k, d), ignore=shutil.ignore_patterns("__pycache__"))

        def ed(rel, fn):
            p = os.path.join(cls.vadny, rel)
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            fn(d)
            with open(p, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=1)

        ed("data/analyzy/red_flags.json", lambda d: d["signaly"].pop())                                              # K7
        ed("data/smlouvy/parovani_akci.json", lambda d: d["akce"][0]["klicove"][0].__setitem__("bez_DPH", 9440001))  # K8
        ed("data/analyzy/signaly_stavy.json", lambda d: d["stavy"]["A-2025-01"]["dukazy_overeni"].append("data/neexistuje.json"))  # K9
        ed("data/analyzy/signaly_stavy.json", lambda d: d["stavy"].__setitem__(
            "S-0000000000", {"stav": "zamitnuto", "overil": "t", "datum": "2026-10-23", "oduvodneni": "xxx"}))       # K10
        ed("data/kauzy/K-003_lavka_Vs-04-Bel.json", lambda d: d["casova_osa"].insert(0, {"datum": "2099-01-01", "popis": "x"}))  # K11
        ed("data/zaverecny_ucet/zaverecny_ucet_2023_2025.json",
           lambda d: d["roky"]["2025"]["rozpocet"]["prijmy"].__setitem__("upraveny", 1.0))                          # K12
        ed("data/kauzy/K-004_AERV_zruseni.json", lambda d: d.__setitem__("x", [{"id": "Q1", "a": 1}, {"id": "Q1", "a": 2}]))  # K13
        cls.c, cls.v = spust(cls.cisty), spust(cls.vadny)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.t)

    def test_cista_kopie(self):
        for k in ("K7", "K8", "K9", "K10", "K11", "K13"):
            self.assertEqual(self.c[k], 0, k)

    def test_vady_zachyceny(self):
        for k in NOVE:
            self.assertGreater(self.v[k], self.c[k], k)


if __name__ == "__main__":
    unittest.main()
