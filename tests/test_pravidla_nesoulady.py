"""Testy pravidel R13–R16 (syntetické vstupy) + kontrola původu dat v cenove_body.json."""
import json
import os
import re
import sys
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import pravidla_nesoulady as p  # noqa: E402

KONF = p.nacti_konfiguraci(os.path.join(ROOT, "data/analyzy/pravidla_konfigurace.json"))


def smlouva(druh, puv, *zmeny):
    return {"nazev": "X", "druh": druh, "puvodni": puv, "zaklad": "bez_DPH",
            "dodatky": [{"id": str(i), "castka": z} for i, z in enumerate(zmeny)], "odkazy": []}


class R13(unittest.TestCase):
    def test_pod_pasmem_bez_signalu(self):
        self.assertEqual(p.r13_dodatky(smlouva("stavebni_prace", 100, 5, 5), KONF), [])  # 10 % < 12 %

    def test_blizko_limitu_stavby(self):
        f = p.r13_dodatky(smlouva("stavebni_prace", 100, 13), KONF)
        self.assertEqual(f[0]["zavaznost"], "nizka")

    def test_nad_limitem_sluzby(self):
        f = p.r13_dodatky(smlouva("dodavky_sluzby", 100, 6, 6), KONF)  # 12 % > 10 %
        self.assertEqual(f[0]["zavaznost"], "stredni")

    def test_kumulace_absolutni_hodnoty(self):
        # +12 a −12: čistý součet 0, absolutně 24 % > 15 % → signál (výklad MMR)
        f = p.r13_dodatky(smlouva("stavebni_prace", 100, 12, -12), KONF)
        self.assertEqual(f[0]["zavaznost"], "stredni")

    def test_nad_30_procent(self):
        self.assertEqual(p.r13_dodatky(smlouva("stavebni_prace", 100, 31), KONF)[0]["zavaznost"], "vysoka")

    def test_neznamy_druh_prisnejsi_limit(self):
        f = p.r13_dodatky(smlouva(None, 100, 11), KONF)
        self.assertEqual(f[0]["zavaznost"], "stredni")
        self.assertIn("Druh plnění neurčen", f[0]["popis"])

    def test_dodatky_bez_hodnoty(self):
        self.assertEqual(p.r13_dodatky(smlouva("stavebni_prace", 100, None), KONF), [])


class R14(unittest.TestCase):
    def test_limit_podle_data_novely(self):
        self.assertEqual(p.limit_vzmr(p.datum("2025-04-02"), "dodavky_sluzby", KONF), 2000000)
        self.assertEqual(p.limit_vzmr(p.datum("2025-04-03"), "dodavky_sluzby", KONF), 3000000)
        self.assertEqual(p.limit_vzmr(p.datum("2025-04-03"), "stavebni_prace", KONF), 9000000)

    def test_tesne_pod_limitem(self):
        z = {"nazev": "Z", "druh": "stavebni_prace", "predp_hodnota": 8_900_000, "datum": "2026-01-10"}
        self.assertEqual(len(p.r14_pod_limitem(z, KONF)), 1)
        z["predp_hodnota"] = 7_000_000
        self.assertEqual(p.r14_pod_limitem(z, KONF), [])
        z["predp_hodnota"] = 9_000_000  # rovno limitu = už není VZMR
        self.assertEqual(p.r14_pod_limitem(z, KONF), [])

    def test_deleni(self):
        ss = [{"dodavatel_ico": "1", "druh": "dodavky_sluzby", "bez_DPH": 1_900_000, "datum": "2026-01-01", "id": "a"},
              {"dodavatel_ico": "1", "druh": "dodavky_sluzby", "bez_DPH": 1_500_000, "datum": "2026-06-01", "id": "b"},
              {"dodavatel_ico": "2", "druh": "dodavky_sluzby", "bez_DPH": 2_900_000, "datum": "2026-06-01", "id": "c"}]
        f = p.r14_deleni(ss, KONF)
        self.assertEqual(len(f), 1)
        self.assertIn("IČO 1", f[0]["popis"])


class R15(unittest.TestCase):
    ZR = [{"zakazka": "PROVOZOVÁNÍ SLUŽBY SENIOR TAXI", "terminy": ["2026-06-19", "2026-07-02"]}]

    def test_shoda_senior_taxi(self):
        sm = [{"id": "38999306", "predmet": "Dodatek č. 2 ke smlouvě o provozování služby senior taxi", "datum": "31.07.2026"}]
        f = p.r15_zruseni_prodlouzeni(self.ZR, sm, KONF)
        self.assertEqual(len(f), 1)
        self.assertIn("38999306", f[0]["odkazy"][0])

    def test_jiny_predmet(self):
        sm = [{"id": "1", "predmet": "Dodatek č. 1 - změna termínu plnění", "datum": "31.07.2026"}]
        self.assertEqual(p.r15_zruseni_prodlouzeni(self.ZR, sm, KONF), [])

    def test_mimo_okno(self):
        sm = [{"id": "1", "predmet": "Dodatek o prodloužení – senior taxi", "datum": "2027-06-01"}]
        self.assertEqual(p.r15_zruseni_prodlouzeni(self.ZR, sm, KONF), [])

    def test_pred_zrusenim(self):
        sm = [{"id": "1", "predmet": "Dodatek o prodloužení – senior taxi", "datum": "2026-01-01"}]
        self.assertEqual(p.r15_zruseni_prodlouzeni(self.ZR, sm, KONF), [])


class R16(unittest.TestCase):
    def akce(self, *body):
        return {"akce": "A", "body": [dict(b, zdroj="t") for b in body]}

    def test_navrh_vs_schvaleno(self):
        a = self.akce({"typ": "navrh", "castka": 34e6, "zaklad": "neurceno"}, {"typ": "schvaleno", "castka": 33.15e6, "zaklad": "neurceno"})
        self.assertEqual([f["kod"] for f in p.r16_cenovy_rozdil(a, KONF)], ["R16-cena-navrh-vs-schvaleno"])

    def test_tolerance_zaokrouhleni(self):
        a = self.akce({"typ": "schvaleno", "castka": 68983750.54, "zaklad": "bez_DPH"}, {"typ": "smlouva", "castka": 68983751, "zaklad": "bez_DPH"})
        self.assertEqual(p.r16_cenovy_rozdil(a, KONF), [])

    def test_ruzny_zaklad_se_neporovnava(self):
        a = self.akce({"typ": "schvaleno", "castka": 100e6, "zaklad": "bez_DPH"}, {"typ": "smlouva", "castka": 121e6, "zaklad": "s_DPH"})
        self.assertEqual(p.r16_cenovy_rozdil(a, KONF), [])

    def test_smlouva_nad_rozpoctem(self):
        a = self.akce({"typ": "rozpocet", "castka": 23e6, "zaklad": "rozpocet"}, {"typ": "smlouva", "castka": 23574636, "zaklad": "s_DPH"})
        self.assertEqual([f["kod"] for f in p.r16_cenovy_rozdil(a, KONF)], ["R16-smlouva-nad-rozpoctem"])


class PuvodCenovychBodu(unittest.TestCase):
    """Každá hodnota v cenove_body.json musí existovat ve zdrojovém souboru repa (nic nedopočteno)."""

    def test_pointery(self):
        with open(os.path.join(ROOT, "data/analyzy/cenove_body.json"), encoding="utf-8") as fh:
            cb = json.load(fh)
        for a in cb["akce"]:
            for b in a["body"]:
                soubor, ptr = b["zdroj"].split("#")
                with open(os.path.join(ROOT, soubor), encoding="utf-8") as fh:
                    v = json.load(fh)
                for k in ptr.strip("/").split("/"):
                    v = v[int(k)] if isinstance(v, list) else v[k]
                if isinstance(v, (int, float)):
                    self.assertAlmostEqual(v, b["castka"], places=2, msg=b["zdroj"])
                else:
                    cisla = {re.sub(r"\s", "", m) for m in re.findall(r"\d{1,3}(?:[  ]\d{3})+", v)}
                    self.assertIn(f"{b['castka']:.0f}", cisla, msg=b["zdroj"])


if __name__ == "__main__":
    unittest.main()
