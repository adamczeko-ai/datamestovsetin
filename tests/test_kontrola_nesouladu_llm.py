"""Testy kontroly výstupu LLM: citace musí být doslova ve zdroji, min. 2 zdroje, zakázané výrazy, cesty mimo repo."""
import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import kontrola_nesouladu_llm as k  # noqa: E402

K2 = "data/kauzy/K-002_tribuna_ohrada_TJ_MEZ.json"


def nes(**kw):
    n = {"id": "x", "akce": "K-002", "typ": "cena", "popis": "Cena v návrhu se liší od schválené.",
         "citace": [{"zdroj": f"{K2}#/penize/navrh_cena", "text": "34000000"},
                    {"zdroj": f"{K2}#/penize/schvalena_cena", "text": "33 150 000"}],
         "jistota": "vysoka", "otazka_k_vysvetleni": "Jaký doklad zdůvodňuje snížení ceny?"}
    n.update(kw)
    return n


class T(unittest.TestCase):
    def run_one(self, n):
        return k.zkontroluj({"beh": {}, "nesoulady": [n]}, ROOT)

    def test_projde(self):
        out = self.run_one(nes())
        self.assertEqual(len(out["nesoulady"]), 1, out["zahozeno"])
        self.assertRegex(out["nesoulady"][0]["id"], r"^N-\d{8}-001$")

    def test_vymyslena_citace(self):
        n = nes(citace=[{"zdroj": f"{K2}#/penize/navrh_cena", "text": "35000000"},
                        {"zdroj": f"{K2}#/penize/schvalena_cena", "text": "33150000"}])
        self.assertEqual(len(self.run_one(n)["zahozeno"]), 1)

    def test_jedna_citace(self):
        n = nes(citace=[{"zdroj": f"{K2}#/penize/navrh_cena", "text": "34000000"}])
        self.assertEqual(len(self.run_one(n)["zahozeno"]), 1)

    def test_zakazany_vyraz(self):
        out = self.run_one(nes(popis="Jde o zjevné pochybení vedení."))
        self.assertIn("zakázaný výraz", out["zahozeno"][0]["duvody"][0])

    def test_cesta_mimo_repo_a_url(self):
        n = nes(citace=[{"zdroj": "../etc/passwd", "text": "root"},
                        {"zdroj": "https://example.com", "text": "abc"}])
        d = " ".join(self.run_one(n)["zahozeno"][0]["duvody"])
        self.assertIn("mimo repo", d)
        self.assertIn("URL", d)

    def test_textova_citace_z_casove_osy(self):
        n = nes(citace=[{"zdroj": f"{K2}#/pozorovani/0", "text": "materiál s nevyplněnou cenou"},
                        {"zdroj": f"{K2}#/penize/schvalena_cena", "text": "33150000"}], typ="chybejici_udaj")
        self.assertEqual(len(self.run_one(n)["nesoulady"]), 1)


if __name__ == "__main__":
    unittest.main()
