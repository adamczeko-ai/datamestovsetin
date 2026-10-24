"""Testy scripts/normalizace_dat.py: převod na ISO, idempotence, původní pole beze změny."""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import normalizace_dat as nd  # noqa: E402


class TestNormalizaceDat(unittest.TestCase):
    def test_na_iso(self):
        self.assertEqual(nd.na_iso("12.05.2026"), "2026-05-12")
        self.assertEqual(nd.na_iso("1. 2. 2017"), "2017-02-01")
        self.assertEqual(nd.na_iso("2026-09-21"), "2026-09-21")
        for x in ("neuvedeno (mezi 2023-02-24 a 2026-09)", "31.02.2026", "", None, 2026):
            self.assertIsNone(nd.na_iso(x), x)

    def test_nedestruktivni_a_idempotentni(self):
        data = {"verze": [{"version_id": "1", "datum_uzavreni": "12.05.2026", "predmet": "x"},
                          {"version_id": "2", "datum_uzavreni": "neuvedeno", "predmet": "y"}]}
        puvodni = copy.deepcopy(data)
        self.assertEqual(nd.normalizuj(data, "verze", "datum_uzavreni"), 2)
        self.assertEqual([z["datum_uzavreni_iso"] for z in data["verze"]], ["2026-05-12", None])
        self.assertEqual(list(data["verze"][0]), ["version_id", "datum_uzavreni", "datum_uzavreni_iso", "predmet"])
        bez_iso = [{k: v for k, v in z.items() if k != "datum_uzavreni_iso"} for z in data["verze"]]
        self.assertEqual(bez_iso, puvodni["verze"])
        self.assertEqual(nd.normalizuj(data, "verze", "datum_uzavreni"), 0)

    def test_repo_je_normalizovane(self):
        """Data v repu jsou aktuální (jinak spusť python3 scripts/normalizace_dat.py)."""
        with open(os.devnull, "w") as dn:
            old, sys.stdout = sys.stdout, dn
            try:
                self.assertEqual(nd.main(["--kontrola"]), 0)
            finally:
                sys.stdout = old


if __name__ == "__main__":
    unittest.main()
