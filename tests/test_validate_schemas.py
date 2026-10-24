"""Testy registrace schémat (x-data-files): žádné schéma ani datový soubor nezůstane nevalidovaný."""
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import validate_schemas as vs  # noqa: E402


def zapis(root, rel, obsah):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(obsah if isinstance(obsah, str) else json.dumps(obsah, ensure_ascii=False))


class TestRepo(unittest.TestCase):
    def test_kazde_schema_ma_soubory(self):
        for s, (obsah, soubory) in vs.schemata().items():
            with self.subTest(schema=s):
                self.assertTrue(obsah.get(vs.KLIC), f"{s}: chybí {vs.KLIC}")
                self.assertTrue(soubory, f"{s}: {vs.KLIC} neodpovídá žádný soubor")

    def test_kazdy_datovy_soubor_ma_schema(self):
        self.assertEqual(vs.pokryti(), [])

    def test_centralni_slovnik_neexistuje(self):
        with open(os.path.join(ROOT, "scripts", "validate_schemas.py"), encoding="utf-8") as f:
            self.assertNotRegex(f.read(), r"(?m)^M\s*=")

    def test_vyjimky_se_jen_zmensuji(self):
        """Výjimky = soubory bez schématu ke dni zavedení (37). Nový soubor bez schématu do nich nepatří."""
        pokryto = {f for _, s in vs.schemata().values() for f in s}
        nepokryte = vs.vyjimky() - pokryto
        self.assertTrue(all(f.startswith("data/") for f in vs.vyjimky()))
        self.assertLessEqual(len(nepokryte), 37, sorted(nepokryte))


class TestMechanismus(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        zapis(self.root, "data/schema/a.schema.json",
              {"$schema": "https://json-schema.org/draft/2020-12/schema", "x-data-files": ["data/a/*.json"],
               "type": "object", "required": ["x"]})
        zapis(self.root, "data/a/1.json", {"x": 1})

    def tearDown(self):
        self.tmp.cleanup()

    def test_objeveni(self):
        self.assertEqual(vs.schemata(self.root)["data/schema/a.schema.json"][1], ["data/a/1.json"])
        self.assertEqual(vs.pokryti(self.root), [])
        self.assertEqual(vs.main(self.root), 0)

    def test_nevalidni_data(self):
        zapis(self.root, "data/a/2.json", {"y": 1})
        self.assertEqual(vs.main(self.root), 1)

    def test_soubor_bez_schematu(self):
        zapis(self.root, "data/b.json", {})
        self.assertEqual(len(vs.pokryti(self.root)), 1)
        zapis(self.root, vs.VYJIMKY, "# komentář\ndata/b.json\n")
        self.assertEqual(vs.pokryti(self.root), [])

    def test_jsonl_bez_schematu(self):
        zapis(self.root, "data/c.jsonl", "")
        self.assertIn("data/c.jsonl", vs.pokryti(self.root)[0])

    def test_schema_bez_souboru_a_bez_klice(self):
        zapis(self.root, "data/schema/b.schema.json", {"x-data-files": ["data/nic/*.json"]})
        zapis(self.root, "data/schema/c.schema.json", {"type": "object"})
        self.assertEqual(len(vs.pokryti(self.root)), 2)

    def test_stara_vyjimka(self):
        zapis(self.root, vs.VYJIMKY, "data/neexistuje.json\n")
        self.assertIn("neexistuje", vs.pokryti(self.root)[0])


if __name__ == "__main__":
    unittest.main()
