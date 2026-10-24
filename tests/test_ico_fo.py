"""Testy integrace/sber/ico_fo.py – pseudonymizace IČO OSVČ (syntetická IČO a data)."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from integrace.sber import ico_fo, store  # noqa: E402

FO1, FO2, PO = "11111111", "22222222", "33333333"  # syntetická IČO (kontrolní číslice se tu neřeší)


def zapis(d, nazev, zaznamy):
    j = store.Jsonl(os.path.join(d, nazev + ".jsonl"))
    for r in zaznamy:
        j.add({"source_url": "https://example.org/", "retrieved_at": "2026-10-24T10:00:00+02:00", **r})
    j.flush()


def obsah(d):
    out = ""
    for f in sorted(os.listdir(d)):
        if f.endswith(".jsonl"):
            with open(os.path.join(d, f), encoding="utf-8") as fh:
                out += fh.read()
    return out


class TestIcoFo(unittest.TestCase):
    def data(self):
        d = tempfile.mkdtemp()
        zapis(d, "subjekty_ares", [
            {"id": f"ico:{FO1}", "ico": FO1, "fyzicka_osoba": True, "pravni_forma": "101",
             "source_url": f"{ico_fo.ARES_ZAKLAD}/{FO1}"},
            {"id": f"ico:{FO2}", "ico": FO2, "fyzicka_osoba": False, "pravni_forma": "107"},
            {"id": f"ico:{PO}", "ico": PO, "fyzicka_osoba": False, "pravni_forma": "112"}])
        zapis(d, "graf_uzly", [{"id": f"subjekt:{FO1}", "typ": "subjekt", "ico": FO1, "fo": True},
                               {"id": f"subjekt:{PO}", "typ": "subjekt", "ico": PO}])
        zapis(d, "graf_hrany", [{"id": f"hrana:x:u1>subjekt:{FO1}", "z": "u1", "c": f"subjekt:{FO1}", "typ": "x"}])
        zapis(d, "usneseni", [{"id": "usneseni:1:1/1/RM/2026", "ico": [FO1, PO],
                               "text": "dotace [FO], IČ: 222 22 222, a firmě IČO 33333333"}])
        return d

    def test_bez_klice_nic_neunikne_a_vazby_drzi(self):
        d = self.data()
        souhrn = ico_fo.aplikuj(d, klic="")
        t = obsah(d)
        self.assertNotIn(FO1, t)
        self.assertNotIn("222 22 222", t)
        self.assertNotIn(FO2, t)
        self.assertIn(PO, t)  # právnická osoba zůstává
        self.assertEqual(souhrn["rezim"], "poradi")
        uzly = [json.loads(x) for x in open(os.path.join(d, "graf_uzly.jsonl"))]
        hrany = [json.loads(x) for x in open(os.path.join(d, "graf_hrany.jsonl"))]
        kod = [u["ico"] for u in uzly if u.get("fo")][0]
        self.assertTrue(kod.startswith("FO-"))
        self.assertEqual(hrany[0]["c"], f"subjekt:{kod}")  # hrana míří na stejný kód jako uzel
        sub = [json.loads(x) for x in open(os.path.join(d, "subjekty_ares.jsonl"))]
        self.assertIn(f"ico:{kod}", [s["id"] for s in sub])
        self.assertEqual([s["source_url"] for s in sub if s["id"] == f"ico:{kod}"], [ico_fo.ARES_ZAKLAD])
        for f in os.listdir(d):  # sha256 sedí s obsahem
            for x in open(os.path.join(d, f)):
                r = json.loads(x)
                self.assertEqual(r["sha256"], store.otisk(r))

    def test_s_klicem_stabilni_a_idempotentni(self):
        d1, d2 = self.data(), self.data()
        ico_fo.aplikuj(d1, klic="tajny-testovaci-klic")
        ico_fo.aplikuj(d2, klic="tajny-testovaci-klic")
        self.assertEqual(obsah(d1), obsah(d2))  # stejný klíč -> stejné kódy
        pred = obsah(d1)
        self.assertEqual(ico_fo.aplikuj(d1, klic="tajny-testovaci-klic", fo={FO1, FO2})["zmenenych_radku"], 0)
        self.assertEqual(obsah(d1), pred)
        self.assertNotIn(FO1, pred)

    def test_nova_surova_verze_se_spoji_se_stavajici(self):
        d = self.data()
        ico_fo.aplikuj(d, klic="k")
        zapis(d, "subjekty_ares", [{"id": f"ico:{FO1}", "ico": FO1, "fyzicka_osoba": True, "pravni_forma": "101",
                                    "source_url": f"{ico_fo.ARES_ZAKLAD}/{FO1}"}])  # nový běh přinese surový záznam
        ico_fo.aplikuj(d, klic="k")
        sub = [json.loads(x) for x in open(os.path.join(d, "subjekty_ares.jsonl"))]
        self.assertEqual(len(sub), 3)  # duplicitní (id, sha256) se nezapsal
        self.assertNotIn(FO1, obsah(d))


if __name__ == "__main__":
    unittest.main()
