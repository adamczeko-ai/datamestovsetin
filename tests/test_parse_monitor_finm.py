"""Test parseru na vzorku skutečných řádků z 2026_08_Data_CSUIS_FINM2026 (FINM01_UJ, FINM02)."""
import os
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "sync"))
import parse_monitor_finm as p  # noqa: E402

HEADER = '"""Výkaz"""ZC_VYKAZ:ZC_VYKAZ;"""Tabulka výkazu"""ZC_VTAB:ZC_VTAB;"""Fiskální období"""0FISCPER:0FISCPER\n'
# řádky převzaté z extraktu (2 partnerské, 1 vlastní syntetický ve stejném formátu)
ROWS = [
    "063;000100;2026008;1000015590;00298212;CZ080;CZ0804;2;2223;2212;;;;;00304450;0.00 ;0.00 ;500.00 ;",
    "063;000100;2026008;1000012299;70891320;CZ072;CZ072;3;4378;5321;13305;;;;00304450;0.00 ;0.00 ;2235000.00 ;",
    "063;000100;2026008;1000017218;00304450;CZ072;CZ0723;2;0000;8115;;;;;;84599000.00 ;118457944.86 ;11594990.50-;",
]


class T(unittest.TestCase):
    def test_extract(self):
        d = tempfile.mkdtemp()
        zp = os.path.join(d, "x.zip")
        with zipfile.ZipFile(zp, "w") as z:
            z.writestr("FINM01_UJ_2026008.csv", HEADER + "\n".join(ROWS) + "\n")
        own, partner = p.extract(zp, "00304450")
        self.assertEqual((len(own), len(partner)), (1, 2))
        self.assertEqual(own[0]["polozka"], "8115")
        self.assertAlmostEqual(own[0]["po_zmenach"], 118457944.86)
        self.assertAlmostEqual(own[0]["vysledek"], -11594990.50)

    def test_num(self):
        self.assertEqual(p.num("12394400.48-"), -12394400.48)
        self.assertEqual(p.num("0.00 "), 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
