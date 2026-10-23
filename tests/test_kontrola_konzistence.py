"""Testy scripts/kontrola_konzistence.py na syntetických datech (dočasný kořen repa)."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import kontrola_konzistence as kk  # noqa: E402


def zapis(root, rel, obsah):
    f = os.path.join(root, rel)
    os.makedirs(os.path.dirname(f), exist_ok=True)
    with open(f, "w", encoding="utf-8") as fh:
        if isinstance(obsah, str):
            fh.write(obsah)
        else:
            json.dump(obsah, fh, ensure_ascii=False)


class TestKontrolaKonzistence(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.puvodni = kk.ROOT
        kk.ROOT = self.root
        self.addCleanup(setattr, kk, "ROOT", self.puvodni)
        radek = {"typ": "V", "odpa": "2212", "pol": "5169", "org": None, "orj": "0004", "pred": 100.0, "zmena": 50.0, "po": 150.0}
        hlavicka = "ro,organ,datum,usneseni,typ,odpa,pol,org,orj,pred,zmena,po,popis\n"
        for rok in kk.ROKY_RO:
            zapis(self.root, f"data/rozpocet/{rok}/rozpoctova_opatreni_{rok}.json", {"opatreni": [
                {"id": f"RO-{rok}-01", "cislo": 1, "datum": f"{rok}-02-03", "usneseni": f"5/17/ZM/{rok}",
                 "bilance": {"prijmy": 0, "vydaje": 50.0, "financovani": 0}, "radky": [radek]}]})
            zapis(self.root, f"data/rozpocet/{rok}/rozpoctova_opatreni_{rok}_radky.csv",
                  hlavicka + "1,ZM,,,V,2212,5169,,0004,100.0,50.0,150.0,x\n")
        zapis(self.root, "data/rozpocet/rozpoctova_opatreni_2023-2026_radky.csv",
              "rok," + hlavicka + "".join(f"{r},1,ZM,,,V,2212,5169,,0004,100.0,50.0,150.0,x\n" for r in kk.ROKY_RO))
        zapis(self.root, "data/entity/ares_overeni.json", {"subjekty": [
            {"ico": "00304450", "obchodni_jmeno": "Město Vsetín", "sidlo": "Svárov 1080", "pravni_forma": "801"},
            {"ico": "11111111", "obchodni_jmeno": "x", "pravni_forma": "101"}]})
        zapis(self.root, "data/entity/subjekty.json", {"subjekty": [
            {"ico": "00304450", "ares": {"obchodni_jmeno": "Město Vsetín", "sidlo": "Svárov 1080"}}]})
        zapis(self.root, "data/usneseni/usneseni_vazby_RO.json",
              {"index_ZM": [{"zasedani": 17, "datum": "2023-02-03"}], "index_RM_2026": []})
        zapis(self.root, "data/zakazky/z.json", {"zakazky": [{"ucastnici": [{"ico": "11111111", "nazev": "Kvido Neznámý"}]}]})

    def run_main(self):
        out = os.path.join(self.root, "data/analyzy/konzistence.json")
        with open(os.devnull, "w") as dn:
            old, sys.stdout = sys.stdout, dn
            try:
                self.assertEqual(kk.main(["--vystup", out]), 0)
            finally:
                sys.stdout = old
        with open(out, encoding="utf-8") as f:
            return json.load(f), out

    def test_konzistentni_data_bez_rozporu_k1_k2_k3_k5(self):
        d, _ = self.run_main()
        pocty = {s["kontrola"]: s["pocet"] for s in d["souhrn"]}
        self.assertEqual([pocty[k] for k in ("K1", "K2", "K3", "K5")], [0, 0, 0, 0])
        self.assertEqual(pocty["K4"], 1)  # 11111111 – chybná kontrolní číslice
        self.assertEqual(pocty["K6"], 1)  # FO (právní forma 101) uvedena jménem
        self.assertNotIn("Kvido", json.dumps(d, ensure_ascii=False))  # jméno se do výstupu nepřenáší

    def test_rozpory_se_zapisi_s_obema_hodnotami(self):
        zapis(self.root, "data/rozpocet/2024/rozpoctova_opatreni_2024_radky.csv",
              "ro,organ,datum,usneseni,typ,odpa,pol,org,orj,pred,zmena,po,popis\n1,ZM,,,V,2212,5169,,0004,100.0,60.0,160.0,x\n")
        zapis(self.root, "data/usneseni/usneseni_vazby_RO.json",
              {"index_ZM": [{"zasedani": 17, "datum": "2023-02-04"}], "index_RM_2026": []})
        d, _ = self.run_main()
        k1 = [r for r in d["rozpory"] if r["kontrola"] == "K1"]
        self.assertTrue(k1 and all(r["a"]["soubor"] != r["b"]["soubor"] for r in k1))
        k5 = [r for r in d["rozpory"] if r["kontrola"] == "K5"]
        self.assertEqual(len(k5), 1)
        self.assertEqual((k5[0]["a"]["hodnota"], k5[0]["b"]["hodnota"], k5[0]["stav"]), ("2023-02-03", "2023-02-04", "ke_kontrole"))

    def test_stav_od_cloveka_se_zachova_a_id_je_stabilni(self):
        d, out = self.run_main()
        d["rozpory"][0]["stav"] = "vysvetleno"
        d["rozpory"][0]["poznamka_cloveka"] = "zástupná hodnota ve zdroji"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        d2, _ = self.run_main()
        r = {x["id"]: x for x in d2["rozpory"]}[d["rozpory"][0]["id"]]
        self.assertEqual((r["stav"], r["poznamka_cloveka"], r["zjisteno"]),
                         ("vysvetleno", "zástupná hodnota ve zdroji", d["rozpory"][0]["zjisteno"]))
        self.assertEqual(d2["zmizele_od_minula"], [])


if __name__ == "__main__":
    unittest.main()
