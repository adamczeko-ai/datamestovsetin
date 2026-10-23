"""Testy balíku integrace/ – offline (lokální HTTP server s Range/ETag) na vzorcích reálných dat.

Spuštění: python3 -m unittest tests.test_integrace -v
Živé testy (ARES, registr smluv) jen s INTEGRACE_LIVE=1.
"""
import hashlib
import http.server
import io
import json
import os
import sqlite3
import sys
import tempfile
import threading
import unittest
import zipfile
from datetime import date

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
FIX = os.path.join(os.path.dirname(__file__), "fixtures")

from integrace import db  # noqa: E402
from integrace.http import Http  # noqa: E402
from integrace.sources import monitor_finm, ruian_vfr, rvz, vr, registr_smluv  # noqa: E402

FILES: dict[str, bytes] = {}


class Srv(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _etag(self, b):
        return '"' + hashlib.md5(b).hexdigest()[:12] + '"'

    def do_HEAD(self):
        b = FILES.get(self.path)
        if b is None:
            self.send_response(404); self.end_headers(); return
        self.send_response(200)
        self.send_header("ETag", self._etag(b)); self.send_header("Content-Length", str(len(b)))
        self.send_header("Accept-Ranges", "bytes"); self.end_headers()

    def do_GET(self):
        b = FILES.get(self.path)
        if b is None:
            self.send_response(404); self.end_headers(); return
        et = self._etag(b)
        if self.headers.get("If-None-Match") == et:
            self.send_response(304); self.end_headers(); return
        rng = self.headers.get("Range")
        if rng:
            s, e = rng.split("=")[1].split("-")
            s, e = int(s), min(int(e), len(b) - 1)
            part = b[s:e + 1]
            self.send_response(206); self.send_header("Content-Range", f"bytes {s}-{e}/{len(b)}")
            self.send_header("Content-Length", str(len(part))); self.end_headers(); self.wfile.write(part); return
        self.send_response(200); self.send_header("ETag", et); self.send_header("Content-Length", str(len(b)))
        self.end_headers(); self.wfile.write(b)


def zipped(name, text):
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(name, text)
    return bio.getvalue()


# --- vzorky reálných řádků (MONITOR 2026_08 FINM01_UJ a 2025_12 FINM202/203) ---
H26 = '"""Výkaz"""ZC_VYKAZ:ZC_VYKAZ;"""Tabulka"""ZC_VTAB:ZC_VTAB\n'
UJ26 = "\n".join([
    "063;000100;2026008;1000017218;00304450;CZ072;CZ0723;2;0000;8115;;;;;;84599000.00 ;118457944.86 ;11594990.50-;",
    "063;000100;2026008;1000017218;00304450;CZ072;CZ0723;2;0000;4134;;;;;;0.00 ;0.00 ;1356607000.00 ;",
    "063;000100;2026008;1000017218;00304450;CZ072;CZ0723;2;0000;1211;;;;;;291000000.00 ;291000000.00 ;194203348.33 ;",
    "063;000100;2026008;1000017218;00304450;CZ072;CZ0723;3;6409;5345;;;;;;0.00 ;0.00 ;1224344457.00 ;",
    "063;000100;2026008;1000017218;00304450;CZ072;CZ0723;3;3412;5213;;;;;28593987;27447000.00 ;27447000.00 ;18298000.00 ;",
    "063;000100;2026008;1000017218;00304450;CZ072;CZ0723;3;2219;6121;;;;;;5000000.00 ;5000000.00 ;1000000.00 ;",
    "063;000100;2026008;1000012299;70891320;CZ072;CZ072;3;4378;5321;13305;;;;00304450;0.00 ;0.00 ;2235000.00 ;",
    "063;000100;2026008;1000099999;12345678;CZ072;CZ072;3;3412;5321;;;;;87654321;1.00 ;1.00 ;1.00 ;",
]) + "\n"
H25 = '"""x"""ZC_VYKAZ;ZC_VTAB;0FISCPER;ZC_UCJED;ZC_ICO;ZC_KRAJ;ZC_NUTS;ZC_POLVYK;ZU_ROZSCH;ZU_ROZPZM;ZU_ROZKZ;copy\n'
T202 = "051;000300;2025012;1000017218;00304450;CZ072;CZ0723;8115;79553052.00 ;207352097.86 ;28581756.03 ;\n"
T203 = ("051;000400;2025012;1000017218;00304450;CZ072;CZ0723;4200;914746594.00 ;941235992.41 ;1003369035.77 ;\n"
        "051;000400;2025012;1000017218;00304450;CZ072;CZ0723;4430;1194299646.00 ;1348588090.27 ;1082275065.54 ;\n"
        "051;000400;2025012;1000000215;00231525;CZ020;CZ0201;4200;1.00 ;1.00 ;1.00 ;\n")

# --- VFR: reálné prvky z 20260930_OB_541630_UKSH (zkrácené geometrie) ---
VFR = """<?xml version="1.0" encoding="UTF-8"?>
<vf:VymennyFormat xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:ami="urn:cz:isvs:ruian:schemas:AdrMistoIntTypy:v1" xmlns:com="urn:cz:isvs:ruian:schemas:CommonTypy:v1" xmlns:coi="urn:cz:isvs:ruian:schemas:CastObceIntTypy:v1" xmlns:kui="urn:cz:isvs:ruian:schemas:KatUzIntTypy:v1" xmlns:obi="urn:cz:isvs:ruian:schemas:ObecIntTypy:v1" xmlns:pai="urn:cz:isvs:ruian:schemas:ParcelaIntTypy:v1" xmlns:soi="urn:cz:isvs:ruian:schemas:StavObjIntTypy:v1" xmlns:uli="urn:cz:isvs:ruian:schemas:UliceIntTypy:v1" xmlns:vf="urn:cz:isvs:ruian:schemas:VymennyFormatTypy:v1">
<vf:Hlavicka><vf:VerzeVFR>3.1</vf:VerzeVFR></vf:Hlavicka><vf:Data>
<vf:Ulice><vf:Ulice gml:id="UL.633593"><uli:Kod>633593</uli:Kod><uli:Nazev>4. května</uli:Nazev><uli:Obec><obi:Kod>541630</obi:Kod></uli:Obec><uli:PlatiOd>2024-07-08T00:00:00</uli:PlatiOd></vf:Ulice></vf:Ulice>
<vf:Parcely><vf:Parcela gml:id="PA.85463398010"><pai:Id>85463398010</pai:Id><pai:KmenoveCislo>553</pai:KmenoveCislo><pai:PododdeleniCisla>3</pai:PododdeleniCisla><pai:VymeraParcely>310</pai:VymeraParcely><pai:DruhCislovaniKod>2</pai:DruhCislovaniKod><pai:DruhPozemkuKod>5</pai:DruhPozemkuKod><pai:KatastralniUzemi><kui:Kod>786764</kui:Kod></pai:KatastralniUzemi><pai:PlatiOd>2024-07-19T00:00:00</pai:PlatiOd><pai:Geometrie><pai:DefinicniBod><gml:Point gml:id="DPA.85463398010" srsName="urn:ogc:def:crs:EPSG::5514" srsDimension="2"><gml:pos>-495506.09 -1155392.65</gml:pos></gml:Point></pai:DefinicniBod></pai:Geometrie></vf:Parcela></vf:Parcely>
<vf:StavebniObjekty><vf:StavebniObjekt gml:id="SO.23879602"><soi:Kod>23879602</soi:Kod><soi:CislaDomovni><com:CisloDomovni>1</com:CisloDomovni></soi:CislaDomovni><soi:IdentifikacniParcela><pai:Id>2556628810</pai:Id></soi:IdentifikacniParcela><soi:TypStavebnihoObjektuKod>1</soi:TypStavebnihoObjektuKod><soi:ZpusobVyuzitiKod>7</soi:ZpusobVyuzitiKod><soi:CastObce><coi:Kod>186953</coi:Kod></soi:CastObce><soi:PlatiOd>2023-12-24T00:00:00</soi:PlatiOd><soi:IsknBudovaId>334560810</soi:IsknBudovaId><soi:Dokonceni>1960-12-31T00:00:00</soi:Dokonceni><soi:PocetBytu>1</soi:PocetBytu><soi:PocetPodlazi>2</soi:PocetPodlazi><soi:ZastavenaPlocha>92</soi:ZastavenaPlocha><soi:Geometrie><soi:DefinicniBod><gml:Point gml:id="DSO.23879602" srsName="urn:ogc:def:crs:EPSG::5514" srsDimension="2"><gml:pos>-497223.42 -1156326.78</gml:pos></gml:Point></soi:DefinicniBod></soi:Geometrie></vf:StavebniObjekt></vf:StavebniObjekty>
<vf:AdresniMista><vf:AdresniMisto gml:id="AD.74904469"><ami:Kod>74904469</ami:Kod><ami:CisloDomovni>470</ami:CisloDomovni><ami:Psc>75501</ami:Psc><ami:StavebniObjekt><soi:Kod>82263639</soi:Kod></ami:StavebniObjekt><ami:Ulice><uli:Kod>634689</uli:Kod></ami:Ulice><ami:PlatiOd>2016-05-31T00:00:00</ami:PlatiOd><ami:Geometrie><ami:DefinicniBod><ami:AdresniBod><gml:Point gml:id="DAM.74904469.1" srsName="urn:ogc:def:crs:EPSG::5514" srsDimension="2"><gml:pos>-497348.12 -1156778.84</gml:pos></gml:Point></ami:AdresniBod></ami:DefinicniBod></ami:Geometrie></vf:AdresniMisto></vf:AdresniMista>
</vf:Data></vf:VymennyFormat>"""


def rvz_doc():
    def rec(nid, zad_ico, dod_ico, ts, nazev):
        return {"verejna_zakazka": {"identifikator_NIPEZ": nid, "casova_znacka": ts, "nazev_verejne_zakazky": nazev,
                                    "druh_verejne_zakazky": "Stavební práce", "rezim_verejne_zakazky": "Podlimitní",
                                    "predpokladana_hodnota_bez_DPH_v_CZK": 12000000,
                                    "zadavaci_postupy": [{"identifikator_NIPEZ": nid + "-ZP", "zadavatel_zadavaciho_postupu": {"zadavatele": [{"subjekt": {"nazev_subjektu": "X {\"[]}", "ico": zad_ico}}]}}],
                                    "casti_verejne_zakazky": [{"identifikator_NIPEZ": nid + "/001", "zadavaci_postup_pro_cast": {"vysledek": {"smlouva": [
                                        {"datum_uzavreni_smlouvy": "2026-06-23", "hodnota_smluvni_ceny_bez_DPH": 9440000, "hodnota_smluvni_ceny_s_DPH": 11422400,
                                         "hodnota_smluvni_ceny_mena": "CZK", "dodavatele_se_kterymi_byla_uzavrena_smlouva": [{"subjekt": {"ico": dod_ico}}]}]}}}]},
                "historie_lhut": [], "zdroj_dat": "Národní elektronický nástroj"}
    return {"obdobi_od": "2026-09-01T00:00:00", "obdobi_do": "2026-09-30T23:59:59", "verze": "2.10.2",
            "data": [rec("RVZ1", "70891320", "11111111", "2026-09-01T10:00:00", "Cizí"),
                     rec("RVZ2", "304450", "26825457", "2026-09-02T10:00:00", "Oprava lávky – „test“ {závorky}"),
                     rec("RVZ3", "99999999", "28593987", "2026-09-03T10:00:00", "Dodavatel je městská firma")]}


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Srv)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.con = db.connect(os.path.join(self.tmp, "t.db"))
        self.http = Http(self.con, os.path.join(self.tmp, "cache"), min_interval=0, sleep=lambda s: None)
        self.http.opener = __import__("urllib.request").request.build_opener(__import__("urllib.request").request.ProxyHandler({}))


class TestMonitor(Base):
    def test_2026_range_rekapitulace_transfery_idempotence(self):
        FILES["/data/extrakty/csv/FinM2026/2026_08_Data_CSUIS_FINM2026.zip"] = zipped("FINM01_UJ_2026008.csv", H26 + UJ26)
        monitor_finm.BASE = self.base
        r = monitor_finm.sync_period(self.con, self.http, 2026, 8, {"00304450"})
        self.assertEqual(r["status"], "importovano")
        self.assertEqual(r["radky"], 7)  # 6 vlastních + 1 kde je město partnerem; cizí řádek vynechán
        tr = dict(((a, b), c) for a, b, c in self.con.execute("SELECT poskytovatel_ico, prijemce_ico, castka FROM observed_transfer"))
        self.assertEqual(tr[("00304450", "28593987")], 18298000.0)
        self.assertEqual(tr[("70891320", "00304450")], 2235000.0)
        rek = dict((k, v) for k, v in self.con.execute("SELECT radek, vysledek FROM monitor_rekapitulace"))
        self.assertAlmostEqual(rek["4060_odv"], 1356607000.0)
        self.assertAlmostEqual(rek["4250_odv"], 1224344457.0)
        self.assertAlmostEqual(rek["4200_odv"], 194203348.33)  # 1211 + 4134 − konsolidace
        r2 = monitor_finm.sync_period(self.con, self.http, 2026, 8, {"00304450"})
        self.assertEqual(r2["status"], "beze_zmeny")
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM monitor_finm_radek").fetchone()[0], 7)

    def test_2025_legacy_tab(self):
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("FINM201_2025012.csv", "x\n" + "nic\n" * 50000)  # velký člen, který se nestahuje
            z.writestr("FINM202_2025012.csv", H25 + T202)
            z.writestr("FINM203_2025012.csv", H25 + T203)
        FILES["/data/extrakty/csv/FinM/2025_12_Data_CSUIS_FINM.zip"] = bio.getvalue()
        monitor_finm.BASE = self.base
        r = monitor_finm.sync_period(self.con, self.http, 2025, 12, {"00304450"})
        self.assertEqual(r["rekapitulace"], 3)
        rek = dict((k, v) for k, v in self.con.execute("SELECT radek, vysledek FROM monitor_rekapitulace"))
        self.assertAlmostEqual(rek["4200"], 1003369035.77)  # = závěrečný účet 2025
        self.assertAlmostEqual(rek["4430"], 1082275065.54)
        self.assertAlmostEqual(rek["8115"], 28581756.03)

    def test_nepublikovane_obdobi(self):
        monitor_finm.BASE = self.base
        r = monitor_finm.sync_period(self.con, self.http, 2025, 7, {"00304450"})
        self.assertEqual(r["status"], "nepublikovano")

    def test_num(self):
        self.assertEqual(monitor_finm.num("12394400.48-"), -12394400.48)
        self.assertTrue(monitor_finm.url_for(2026, 8).endswith("/FinM2026/2026_08_Data_CSUIS_FINM2026.zip"))
        self.assertTrue(monitor_finm.url_for(2025, 12).endswith("/FinM/2025_12_Data_CSUIS_FINM.zip"))


class TestRuian(Base):
    def test_import_a_304(self):
        ruian_vfr.BASE = self.base + "/vfr/"
        FILES["/vfr/20260930_OB_541630_UKSH.xml.zip"] = zipped("20260930_OB_541630_UKSH.xml", VFR)
        r = ruian_vfr.sync(self.con, self.http, 541630, date(2026, 9, 30))
        self.assertEqual((r["ruian_adresni_misto"], r["ruian_stavebni_objekt"], r["ruian_parcela"], r["ruian_ulice"]), (1, 1, 1, 1))
        am = self.con.execute("SELECT cislo_domovni, psc, stavebni_objekt_kod, x FROM ruian_adresni_misto").fetchone()
        self.assertEqual(am, (470, "75501", 82263639, -497348.12))
        so = self.con.execute("SELECT identifikacni_parcela_id, zastavena_plocha, cast_obce_kod FROM ruian_stavebni_objekt").fetchone()
        self.assertEqual(so, (2556628810, 92, 186953))
        self.assertEqual(self.con.execute("SELECT nazev FROM ruian_ulice").fetchone()[0], "4. května")
        self.assertEqual(ruian_vfr.sync(self.con, self.http, 541630, date(2026, 9, 30))["status"], "beze_zmeny")

    def test_datum(self):
        self.assertEqual(ruian_vfr.last_publication(date(2026, 10, 23)), date(2026, 9, 30))
        self.assertEqual(ruian_vfr.last_publication(date(2026, 3, 5)), date(2026, 2, 28))


class TestRvz(Base):
    def test_stream_parser_hranice_bloku(self):
        doc = json.dumps(rvz_doc(), ensure_ascii=False)
        for chunk in (7, 64, 1 << 20):
            recs = list(rvz.iter_records(io.StringIO(doc), chunk=chunk))
            self.assertEqual([r["verejna_zakazka"]["identifikator_NIPEZ"] for r in recs], ["RVZ1", "RVZ2", "RVZ3"], chunk)

    def test_sync_filtr_a_novejsi_verze(self):
        rvz.BASE = self.base + "/rvz/"
        FILES["/rvz/VZ-09-2026.zip"] = zipped("VZ-09-2026.json", json.dumps(rvz_doc(), ensure_ascii=False))
        r = rvz.sync_month(self.con, self.http, 2026, 9, {"00304450", "28593987"})
        self.assertEqual((r["zakazky"], r["smlouvy"]), (2, 2))  # RVZ2 (zadavatel bez nul) + RVZ3 (dodavatel)
        row = self.con.execute("SELECT zadavatele_ico, nazev FROM rvz_zakazka WHERE identifikator_nipez='RVZ2'").fetchone()
        self.assertEqual(row[0], "00304450")
        old = rvz_doc(); old["data"][1]["verejna_zakazka"]["casova_znacka"] = "2026-01-01T00:00:00"
        self.assertEqual(rvz.upsert_newer(self.con, rvz.filter_records(old["data"], {"00304450"}, "x")[0]), [])


class TestVr(unittest.TestCase):
    def test_parse_minimalizace(self):
        doc = json.load(open(os.path.join(FIX, "ares_vr_28593987_anonym.json"), encoding="utf-8"))
        subj, ang = vr.parse(doc)
        self.assertEqual((subj["ico"], subj["nazev"]), ("28593987", "Vsetínská sportovní, s.r.o."))
        akt = [a for a in ang if not a["datum_vymazu"]]
        spol = [a for a in akt if a["funkce"] == "Společník"]
        self.assertEqual(len(spol), 1)
        self.assertEqual((spol[0]["osoba_ico"], spol[0]["podil"].replace(" ", "")), ("00304450", "100,00"))
        self.assertEqual(len([a for a in akt if a["funkce"] != "Společník"]), 7)  # = ARES-VR 23. 10. 2026
        self.assertNotIn("datumNarozeni", json.dumps(ang, ensure_ascii=False))
        self.assertTrue(all(set(a) >= {"jmeno", "funkce", "datum_zapisu"} for a in ang))


class TestRegistrSmluv(unittest.TestCase):
    def test_parse_hodnoty(self):
        a = registr_smluv.parse(open(os.path.join(FIX, "rs_39950637.xml"), "rb").read(), "39950637")
        self.assertEqual((a["value_kind"], a["hodnota_bez_dph"], a["hodnota_s_dph"]), ("s_dph", None, 114804.8))
        b = registr_smluv.parse(open(os.path.join(FIX, "rs_39962817.xml"), "rb").read(), "39962817")
        self.assertEqual((b["value_kind"], b["hodnota_bez_dph"], b["hodnota_s_dph"]), ("bez_dph", 83125.0, 100581.25))


@unittest.skipUnless(os.environ.get("INTEGRACE_LIVE") == "1", "živé testy jen s INTEGRACE_LIVE=1")
class TestLive(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.con = db.connect(os.path.join(self.tmp, "live.db"))
        self.http = Http(self.con, os.path.join(self.tmp, "c"), min_interval=2.0)

    def test_registr_smluv(self):
        r = registr_smluv.sync(self.con, self.http, ["39950637", "38540900"])
        self.assertEqual(r["chyby"], 0)
        v = dict(self.con.execute("SELECT id_verze, hodnota_s_dph FROM rs_verze"))
        self.assertEqual(v["38540900"], 500000000.0)
        self.assertEqual(registr_smluv.sync(self.con, self.http, ["39950637"])["preskoceno_existujici"], 1)

    def test_ares_vr(self):
        r = vr.sync(self.con, self.http, ["28593987", "47972114"])
        self.assertEqual(r["chyby"], 0)
        self.assertEqual(vr.sync(self.con, self.http, ["28593987"])["importovano"], 0)  # beze změny (hash)


if __name__ == "__main__":
    unittest.main(verbosity=2)
