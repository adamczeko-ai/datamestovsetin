"""Testy generátoru signaly@2: stabilní ID, migrace red_flags@1 bez ztráty dat, připojení stavů, osiřelé stavy, schéma."""
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import signaly_v2 as s  # noqa: E402


class StabilniId(unittest.TestCase):
    def test_deterministicke(self):
        a = s.stabilni_id("R1", ["RO-2026-12", "24,38/26/ZM/2026"], 47e6)
        self.assertEqual(a, s.stabilni_id("R1", ["RO-2026-12", "24,38/26/ZM/2026"], 47e6))
        self.assertNotEqual(a, s.stabilni_id("R1", ["RO-2026-12", "24,38/26/ZM/2026"], 46e6))
        self.assertRegex(a, r"^S-[0-9a-f]{10}$")

    def test_duplicita_dostane_priponu(self):
        f = {"kod": "R1", "zavaznost": "nizka", "popis": "x", "castka_Kc": 1, "odkazy": ["RO-2026-1"]}
        out = s.z_flagu([f, dict(f)], "pravidlo")
        self.assertEqual(out[1]["id"], out[0]["id"] + "-2")

    def test_klasifikace_dukazu(self):
        self.assertEqual(s.klasifikuj("RO-2025-04")["typ"], "rozpoctove_opatreni")
        self.assertEqual(s.klasifikuj("35/18/ZM/2025")["typ"], "usneseni")
        self.assertEqual(s.klasifikuj("https://www.hlidacstatu.cz/Detail/34141081")["typ"], "smlouva")
        self.assertIsNone(s.klasifikuj(None))


class NadRepem(unittest.TestCase):
    """Běží nad kopií repa v dočasné složce – nesahá na pracovní data."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        shutil.copytree(os.path.join(ROOT, "data"), os.path.join(self.d, "data"))
        self.cwd = os.getcwd()
        os.chdir(self.d)

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.d)

    def test_migrace_bez_ztraty(self):
        with open("data/analyzy/red_flags.json", encoding="utf-8") as fh:
            rf = json.load(fh)["signaly"]
        out = s.sestav()
        puvodni = [x["puvodni"] for x in out["signaly"] if x["zdroj_signalu"] == "pravidlo" and not x["kod"].startswith(("R13", "R14", "R15", "R16"))]
        self.assertEqual(len(puvodni), len(rf))
        key = lambda f: json.dumps(f, sort_keys=True, ensure_ascii=False)  # noqa: E731
        self.assertEqual(sorted(map(key, puvodni)), sorted(map(key, rf)))

    def test_stav_a_osirely_stav(self):
        out = s.sestav()
        sid = next(x["id"] for x in out["signaly"] if x["kod"] == "R6-soudni-spory")
        with open("data/analyzy/signaly_stavy.json", encoding="utf-8") as fh:
            st = json.load(fh)
        st["stavy"][sid] = {"stav": "vysvetleno", "overil": "test", "datum": "2026-10-23", "oduvodneni": "testovací"}
        st["stavy"]["S-0000000000"] = {"stav": "zamitnuto", "overil": "test", "datum": "2026-10-23", "oduvodneni": "osiřelý"}
        with open("data/analyzy/signaly_stavy.json", "w", encoding="utf-8") as fh:
            json.dump(st, fh, ensure_ascii=False)
        out = s.sestav()
        self.assertEqual(next(x for x in out["signaly"] if x["id"] == sid)["stav"], "vysvetleno")
        self.assertEqual(out["osirele_stavy"], ["S-0000000000"])

    def test_schema(self):
        from jsonschema import Draft202012Validator
        with open("data/schema/signaly.schema.json", encoding="utf-8") as fh:
            v = Draft202012Validator(json.load(fh))
        errs = list(v.iter_errors(json.loads(json.dumps(s.sestav(), ensure_ascii=False))))
        self.assertEqual(errs, [], [e.message for e in errs[:3]])


if __name__ == "__main__":
    unittest.main()
