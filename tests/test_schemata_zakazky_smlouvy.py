"""Schémata data/zakazky, data/smlouvy a usneseni_vazby_RO: skutečná data projdou, poškozená ne."""
import copy
import json
import os
import unittest

from jsonschema import Draft202012Validator

ROOT = os.path.join(os.path.dirname(__file__), "..")


def nacti(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def chyby(schema, data):
    return list(Draft202012Validator(nacti(f"data/schema/{schema}.schema.json")).iter_errors(data))


class TestSchemataZakazkySmlouvy(unittest.TestCase):
    PARY = {"nipez-vz-okruh-mesta": "data/zakazky/nipez_vz_okruh_mesta_2024_2026.json",
            "zakazka-senior-taxi": "data/zakazky/sluzba_senior_taxi.json",
            "verejne-zakazky-zrusene": "data/zakazky/verejne_zakazky_zrusene.json",
            "parovani-akci": "data/smlouvy/parovani_akci.json",
            "uver-retezec": "data/smlouvy/uver_CSOB_2026.json",
            "usneseni-vazby-ro": "data/usneseni/usneseni_vazby_RO.json"}

    def test_skutecna_data_projdou(self):
        for sch, f in self.PARY.items():
            self.assertEqual(chyby(sch, nacti(f)), [], f)

    def test_poskozene_ico(self):
        d = copy.deepcopy(nacti(self.PARY["nipez-vz-okruh-mesta"]))
        d["zakazky"][0]["zadavatele"][0]["ico"] = "1234567"
        self.assertTrue(chyby("nipez-vz-okruh-mesta", d))

    def test_datum_neni_iso(self):
        d = copy.deepcopy(nacti(self.PARY["usneseni-vazby-ro"]))
        d["index_ZM"][0]["datum"] = "21.9.2026"
        self.assertTrue(chyby("usneseni-vazby-ro", d))
        d = copy.deepcopy(nacti(self.PARY["verejne-zakazky-zrusene"]))
        d["zakazky"][0]["uverejneno"] = "2026/05/11"
        self.assertTrue(chyby("verejne-zakazky-zrusene", d))

    def test_chybi_povinne_pole(self):
        d = copy.deepcopy(nacti(self.PARY["zakazka-senior-taxi"]))
        del d["smlouvy"][0]["hs"]
        self.assertTrue(chyby("zakazka-senior-taxi", d))
        d = copy.deepcopy(nacti(self.PARY["uver-retezec"]))
        del d["retezec"][0]["zdroj"]
        self.assertTrue(chyby("uver-retezec", d))


if __name__ == "__main__":
    unittest.main()
