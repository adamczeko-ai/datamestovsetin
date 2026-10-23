"""Test exportu zveřejnitelných signálů: projde jen potvrzeno/vysvětleno s druhým ověřením, nikdy LLM ani nový stav."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import export_verejne_signaly as e  # noqa: E402


def sig(id_, stav, druhe=None, zdroj="pravidlo"):
    det = None if stav == "novy" else {"stav": stav, "overil": "x", "datum": "2026-10-23", "oduvodneni": "o", "druhe_overeni": druhe}
    return {"id": id_, "kod": "R1", "zdroj_signalu": zdroj, "zavaznost": "nizka", "popis": "p", "castka_Kc": 1,
            "dukazy": [{"typ": "url", "ref": "https://x", "url": "https://x", "strana": None, "sha256": None}],
            "stav": stav, "stav_detail": det, "puvodni": {"interni": "ne"}}


class T(unittest.TestCase):
    def test_filtr(self):
        vstup = [sig("A-2025-01", "potvrzeno", "Jan Kontrolor"), sig("S-1", "potvrzeno"), sig("S-2", "vysvetleno", "Y"),
                 sig("S-3", "novy"), sig("S-4", "zamitnuto", "Y"), sig("S-5", "overuje_se", "Y"),
                 sig("N-1", "potvrzeno", "Y", zdroj="llm")]
        self.assertEqual([s["id"] for s in e.vyber(vstup)], ["A-2025-01", "S-2"])

    def test_bez_internich_poli(self):
        s = e.vyber([sig("S-2", "vysvetleno", "Y")])[0]
        self.assertNotIn("puvodni", s)
        self.assertNotIn("sha256", s["dukazy"][0])


if __name__ == "__main__":
    unittest.main()
