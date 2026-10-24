"""Testy sběru scripts/sber.py a integrace/sber/ – offline (uložené vzorky, podvržený HTTP opener).

Spuštění: python3 -m unittest tests.test_sber -v
Vzorky: tests/fixtures/sber/ (XMLdataVZ z profilu zadavatele 23. 10. 2026 s anonymizovanými FO,
text výpisů usnesení z předávky P1 – pseudonymizovaný); registr smluv: tests/fixtures/rs_*.xml.
Výpis složky vismo a balíček materiálů ZM jsou syntetické (živý web z cloudu nedostupný).
"""
import email.message
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error
import zipfile
from datetime import date

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
FIX = os.path.join(os.path.dirname(__file__), "fixtures")

from jsonschema import Draft202012Validator  # noqa: E402

from integrace.http import Http, RobotsDenied  # noqa: E402
from integrace.sber import profil, pseudo, registr, store, vismo, zdroje  # noqa: E402
import sber  # noqa: E402


def fix(name, mode="rb"):
    with open(os.path.join(FIX, name), mode) as f:
        return f.read()


def schema(nazev):
    with open(os.path.join(ROOT, "data", "schema", nazev), encoding="utf-8") as f:
        return Draft202012Validator(json.load(f))


# --- podvržený HTTP opener ---

class _Resp(io.BytesIO):
    def __init__(self, body, status=200, ctype="text/html; charset=utf-8"):
        super().__init__(body)
        self.status = status
        self.headers = email.message.Message()
        self.headers["Content-Type"] = ctype


class FakeOpener:
    """URL -> bytes | (status, bytes, content_type) | Exception. Neznámá URL = 404."""

    def __init__(self, routes):
        self.routes = routes
        self.log = []

    def open(self, req, timeout=None):
        url = req.full_url
        self.log.append((url, req.get_header("User-agent")))
        r = self.routes.get(url)
        if isinstance(r, Exception):
            raise r
        if r is None:
            raise urllib.error.HTTPError(url, 404, "Not Found", email.message.Message(), io.BytesIO(b""))
        st, body, ct = r if isinstance(r, tuple) else (200, r, "text/html; charset=utf-8")
        if st != 200:
            raise urllib.error.HTTPError(url, st, "err", email.message.Message(), io.BytesIO(b""))
        return _Resp(body, st, ct)


def http_klient(routes):
    return Http(None, tempfile.mkdtemp(), min_interval=1.0, max_attempts=1, sleep=lambda s: None,
                opener=FakeOpener(routes), user_agent=zdroje.UA, robots=True)


VU_ROBOTS = b"User-Agent: *\nCrawl-Delay: 30\nDisallow: /*?c=1\n"
SITE_DOWN = urllib.error.URLError("Connection reset by peer")


class TestParserUsneseni(unittest.TestCase):
    def setUp(self):
        self.v = json.loads(fix("sber/usneseni_vzorky.json", "r"))["vzorky"]

    def test_cisla_a_vyroky_jako_predavka(self):
        for idd in ("526552", "525823", "566849"):
            s = self.v[idd]
            out = vismo.parse_usneseni(s["raw"], int(idd))
            self.assertEqual([u["cislo"] for u in out], s["ocekavana_cisla"], idd)
            shoda = sum(u["vyroky"] == e for u, e in zip(out, s["ocekavane_vyroky"]))
            self.assertGreaterEqual(shoda / len(out), 0.95, idd)

    def test_preklep_org_ve_zdroji_a_ico_s_mezerami(self):
        out = vismo.parse_usneseni(self.v["541566_vyrez"]["raw"], 541566)
        self.assertIn("32/41/ZM/2020", [u["cislo"] for u in out])  # zdroj: „ZM“ v dokumentu RM
        self.assertEqual(vismo.ico_z_textu("IČ: 661 84 606, IČO 00304450"), ["66184606", "00304450"])

    def test_castky_a_datum(self):
        self.assertEqual(vismo.castky("ve výši 21.457 Kč a 1 999 900,00 Kč"), ["21457 Kč", "1999900 Kč"])
        self.assertEqual(vismo.datum_iso("47. schůze rady města 30.3.2017"), "2017-03-30")
        self.assertEqual(vismo.datum_iso("konané dne 30. března 2017"), "2017-03-30")
        self.assertIsNone(vismo.datum_iso("bez data"))


class TestVismo(unittest.TestCase):
    LISTING = """<html><body><ul class="ui">
      <li><strong><a href="/assets/File.ashx?id_org=18676&amp;id_dokumenty=570510">Rozpočtové opatření č. 18 - RM</a></strong>
          <span>[PDF, 422 kB]</span> <span>Zveřejněno: 16.10.2026</span></li>
      <li><strong><a href="https://www.mestovsetin.cz/assets/File.ashx?id_org=18676&id_dokumenty=570507">Rozpočtové opatření č. 17 - ZM</a></strong>
          <span>[PDF, 388 kB]</span></li>
      <li><a href="/2025%2Drozpoctova%2Dopatreni/ds-19876/archiv=0&amp;p1=72083">2025 - Rozpočtová opatření</a></li>
      </ul><a href="/rozpoctova%2Dopatreni/ds-19317/p1=72083&amp;stranka=2">2</a></body></html>"""

    def test_parse_listing(self):
        v = vismo.parse_listing(self.LISTING, "https://www.mestovsetin.cz/rozpoctova%2Dopatreni/ds-19317/p1=72083")
        self.assertEqual([s["id_dokumenty"] for s in v["soubory"]], [570510, 570507])
        self.assertEqual(v["soubory"][0]["url"], "https://www.mestovsetin.cz/assets/File.ashx?id_org=18676&id_dokumenty=570510")
        self.assertIn("[PDF, 422 kB]", v["soubory"][0]["info"])
        self.assertEqual([p["ds"] for p in v["podslozky"]], [19876])
        self.assertEqual(len(v["stranky"]), 1)

    def test_ro_titul(self):
        self.assertEqual(vismo.parse_ro_titul("Rozpočtové opatření č. 18 - RM"), {"cislo": 18, "schvaluje": "RM"})
        self.assertEqual(vismo.parse_ro_titul("1/2017 - Rozpočtové opatření RM"), {"cislo": 1, "schvaluje": "RM"})

    def test_balicek_zm(self):
        html = ("<html><body><p>ZASTUPITELSTVO MĚSTA VSETÍN</p><p>Pro zasedání dne 21.9.2026</p>"
                "<p>Předkládá: Mgr. Jan Vzorový</p><p>Věc: Prodej pozemku p. č. 123</p><p>Návrh na usnesení:</p>"
                "<p>Zastupitelstvo města Vsetín schvaluje prodej za 150 000 Kč</p><h3>Důvodová zpráva</h3></body></html>")
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, "w") as z:
            z.writestr("navrhy-usneseni/navrh-usneseni_1.html", html.encode("utf-8"))
            z.writestr("pevne-body/x.html", "<p>x</p>")
        out = vismo.parse_balicek_zm(bio.getvalue())
        self.assertEqual(len(out), 1)
        m = out[0]
        self.assertEqual((m["vec"], m["datum_zasedani"], m["castky"], m["ma_duvodovou_zpravu"]),
                         ("Prodej pozemku p. č. 123", "2026-09-21", ["150000 Kč"], True))

    def test_typ_souboru(self):
        self.assertEqual(vismo.typ_souboru(b"%PDF-1.7"), "pdf")
        self.assertEqual(vismo.typ_souboru(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1xx"), "doc")
        self.assertEqual(vismo.typ_souboru(b"PK\x03\x04"), "zip")


class TestProfil(unittest.TestCase):
    def test_parse_v100(self):
        z = {x["kod"]: x for x in profil.parse(fix("sber/xmldatavz_2025q1_anonym.xml"))}
        self.assertEqual(len(z), 15)
        x = z["P25V00000422"]
        self.assertEqual(x["dodavatele"][0]["ico"], "27642411")
        self.assertEqual(x["dodavatele"][0]["cena_smlouva_bez_dph"], 420000)
        self.assertEqual((x["pocet_nabidek"], x["stav"], x["datum_uzavreni_smlouvy"][:10]), (1, "dokončen", "2025-02-11"))
        plneni = z["P25V00002449"]["dodavatele"][0]["plneni_po_letech"]
        self.assertEqual(plneni[0], {"rok": "2025", "cena_bez_dph": 621485.67, "cena_s_dph": 751997.66})

    def test_stara_struktura_vz(self):
        z = {x["kod"]: x for x in profil.parse(fix("sber/xmldatavz_2023q4_stara_struktura_anonym.xml"))}
        self.assertEqual(len(z), 29)
        x = z["P24V00000416"]  # STAVEBNÍ ÚPRAVY LÁVKY EV. Č. VS-02-BEL
        self.assertEqual((x["struktura"], x["stav"], x["druh_rizeni"]), ("VZ", "zakázka byla zadána", "zjednodušené podlimitní řízení"))
        self.assertEqual(x["dodavatele"][0]["ico"], "48399477")
        self.assertEqual(x["dodavatele"][0]["plneni_po_letech"][0]["cena_bez_dph"], 7478610)
        self.assertEqual(x["pocet_nabidek"], len(x["ucastnici"]))
        self.assertEqual(z["P23V00007760"]["datum_zruseni"][:10], "2023-12-06")
        nazvy = {u["nazev"] for x in z.values() for u in x["ucastnici"] + x["dodavatele"]}
        self.assertFalse(nazvy & {"Adam Vzorový", "Petr Zkušební", "Václav Fiktivní"})

    def test_fo_pseudonymizace(self):
        nazvy = {u["nazev"] for x in profil.parse(fix("sber/xmldatavz_2025q1_anonym.xml")) for u in x["ucastnici"]}
        self.assertNotIn("Jan Testovací", nazvy)
        self.assertIn(pseudo.FO_ARES, nazvy)
        self.assertIn("Vlastimil Stupka s.r.o.", {d["nazev"] for x in profil.parse(fix("sber/xmldatavz_2025q1_anonym.xml"))
                                                  for d in x["dodavatele"]})

    def test_intervaly_a_url(self):
        iv = list(profil.intervaly(date(2024, 1, 1), date(2024, 12, 31), 180))
        self.assertEqual(iv[0], (date(2024, 1, 1), date(2024, 6, 28)))
        self.assertEqual(iv[-1][1], date(2024, 12, 31))
        iv = list(profil.intervaly(date(2024, 5, 1), date(2024, 9, 1), 180))  # hranice portálu 1. 7. 2024
        self.assertEqual(iv, [(date(2024, 5, 1), date(2024, 6, 30)), (date(2024, 7, 1), date(2024, 9, 1))])
        self.assertEqual(profil.url_interval(date(2026, 9, 1), date(2026, 10, 22)),
                         "https://www.vhodne-uverejneni.cz/profil/00304450/XMLdataVZ?od=01092026&do=22102026")


class TestRegistr(unittest.TestCase):
    def test_detail(self):
        d = registr.parse_detail(fix("rs_39950637.xml"), "39950637")
        self.assertTrue(d["strany"])
        self.assertIn(d["value_kind"], ("bez_dph", "s_dph", "cizi_mena", "nezjisteno"))
        self.assertEqual(d["xml_url"], "https://smlouvy.gov.cz/smlouva/39950637/xml/registr_smluv_smlouva_39950637.xml")

    def test_hledani(self):
        page = '<a href="/smlouva/40061385">x</a><a href="https://smlouvy.gov.cz/smlouva/285">y</a><a href="/smlouva/40061385">z</a>'
        self.assertEqual(registr.parse_hledani(page), ["40061385", "285"])


class TestPseudo(unittest.TestCase):
    def test_text(self):
        t = ("na základě žádosti paní Ukázkové Denisy\nnájemní smlouvu s Pavlem Valigurou, se sídlem …\n"
             "Bc. Iveta Táborská\nstarostka města Vsetín\nZpracoval/a: Klára Pokusová, DiS.\nkupující ABC s.r.o.")
        out = pseudo.text(t)
        for jm in ("Ukázkov", "Valigur", "Táborsk", "Pokusov"):
            self.assertNotIn(jm, out)
        self.assertIn("ABC s.r.o.", out)
        self.assertIn("se sídlem", out)

    def test_firmy_a_mista_zustavaji(self):
        for s in ("Petr Novák s.r.o.", "Tělocvičná jednota Sokol Vsetín", "smlouva s Českou spořitelnou",
                  "Valašská Bystřice", "Rada města Vsetín schvaluje"):
            self.assertEqual(pseudo.text(s), s)

    def test_nazev_a_subjekt(self):
        self.assertEqual(pseudo.nazev("Dražební vyhláška, Pokusný Tomáš"), "Dražební vyhláška, [FO]")
        self.assertEqual(pseudo.nazev_subjektu("Jan Novák"), pseudo.FO_ARES)
        self.assertEqual(pseudo.nazev_subjektu("Firma X", pravni_forma="101"), pseudo.FO_ARES)
        self.assertEqual(pseudo.nazev_subjektu("SMO a.s."), "SMO a.s.")

    def test_jmena_z_pseudonymu(self):
        self.assertEqual(pseudo.jmena_z_pseudonymu("Žádost o splátkový kalendář-Ukázková Denisa",
                                                   "Žádost o splátkový kalendář-[FO]"), ["Ukázková Denisa"])
        self.assertIn("Ukázkov", pseudo.text("paní Ukázkové", []) + "Ukázkov")  # sanity
        self.assertNotIn("Ukázkov", pseudo.text("dluh Ukázkové", ["Ukázková Denisa"]))


class TestPseudoZnameUniky(unittest.TestCase):
    """Typy úniků nalezené kontrolou 23. 10. 2026 – se syntetickými jmény (žádná skutečná osoba)."""

    def assertBezJmena(self, vstup, *casti):
        out = pseudo.text(vstup)
        for c in casti:
            self.assertNotIn(c, out, f"{vstup!r} -> {out!r}")
        self.assertIn(pseudo.FO, out)
        return out

    def test_cizi_a_mene_casta_krestni_jmena(self):
        self.assertBezJmena("ve výši 15.000 Kč na účast Natalie Zkouškový Testerová na soustředění", "Natalie", "Zkouškový", "Tester")
        for jm in ("Erik", "Jonáš", "Bořek", "Lumír", "Evžen", "Alexander"):
            self.assertBezJmena(f"smlouva, kterou uzavřel {jm} Fiktivní", jm, "Fiktivní")

    def test_datum_narozeni_a_bydliste(self):
        """Datum narození (i slovní měsíc) a adresa za „bytem“ se neuvádějí; sídlo právnické osoby zůstává."""
        out = pseudo.text("prominutí dluhu [FO], nar. 17. října 1987, bytem Na Vzorku 1235, 755 01\nVsetín.")
        self.assertNotIn("1987", out)
        self.assertNotIn("1235", out)
        self.assertIn("nar. …, bytem …", out)
        out = pseudo.text("proti povinnému: [FO]\nbytem Lhota č.p. 655, Lhota, dat. nar. 22.03.1980\nt a k o")
        self.assertNotIn("655", out)
        self.assertNotIn("1980", out)
        out = pseudo.text("[FO], nar. …, a [FO], nar. …, oba trvale bytem Vzorová 1484/25,\n755 01 Vsetín, dle podmínek")
        self.assertNotIn("1484", out)
        self.assertIn("dle podmínek", out)
        s = "Město Vsetín, se sídlem Svárov 1080, 755 01 Vsetín, IČ: 003 04 450"
        self.assertEqual(pseudo.text(s), s)
        self.assertIn("celoročním pobytem občana", pseudo.text("s celoročním pobytem občana města"))

    def test_prijemce_dotace_bytem_nar(self):
        self.assertBezJmena("Žadatel/investor: Erik Zkušební, nar. ░░░░ , bytem ░░░░", "Zkušební")
        self.assertBezJmena("poskytnutí dotace Kvido Neznámý, bytem ………, ve výši 5.000 Kč", "Kvido", "Neznámý")
        self.assertBezJmena("dotace fyzické osobě Radoš Vymyšlený na akci", "Radoš", "Vymyšlený")
        self.assertBezJmena("Rada města Vsetín schvaluje poskytnutí dotace Ivě Vymyšlené, se sídlem Vsetín", "Vymyšlen")
        self.assertEqual(pseudo.text("poskytnutí dotace Centru Áčko, p.o., se sídlem"), "poskytnutí dotace Centru Áčko, p.o., se sídlem")
        self.assertBezJmena("dohoda o uznání dluhu s [FO] a Ruprechtem Vymyšleným", "Ruprecht", "Vymyšlen")
        self.assertBezJmena("sleva z nájemného nájemci Thi Vzorkový Vymyšlená, Jasenická 1, Vsetín", "Vzorkový", "Vymyšlen")
        self.assertBezJmena("Paní Vymyšlená se zněním materiálů souhlasí", "Vymyšlen")
        # nález z kontroly PR #8 (syntetická data): strana smlouvy „jméno, nar. rok“, iniciály s rokem narození
        self.assertEqual(pseudo.nazev_subjektu("Kvido Neznámý, nar. 1971"), pseudo.FO_ARES)
        self.assertEqual(pseudo.nazev_subjektu("ABC s.r.o."), "ABC s.r.o.")
        out = pseudo.text("smlouvy uzavřené mezi městem a pány Q.Z (rok nar. 1965) a Q.Z (rok nar. 1966), a to")
        self.assertNotIn("Q.Z", out)
        self.assertNotIn("1965", out)
        self.assertIn("k.ú. Vsetín", pseudo.text("pozemek p.č. 12, k.ú. Vsetín"))
        self.assertBezJmena("dlužník KVIDO NEZNÁMÝ, Testovací 298, 75604 Testov, nar. 1960", "KVIDO", "NEZNÁMÝ")
        for s in ("ZÁKLADNÍ ŠKOLA JANA PIVEČKY", "ROZŠÍŘENÍ HŘBITOVA VE VSETÍNĚ", "LÁVKA PŘES BEČVU", "TM STAV SPOL. S R.O."):
            self.assertEqual(pseudo.text(s), s)
        out = pseudo.info_dokumentu("Oznámení o místě uložení písemnosti, Kvido Neznámý [PDF, 316 kB]Odbor správních agend")
        self.assertEqual(out, "Oznámení o místě uložení písemnosti, [FO] [PDF, 316 kB]Odbor správních agend")
        self.assertEqual(pseudo.nazev("údržba trailů BAV 1, BAV 2. - Kvido Neznámý"), "údržba trailů BAV 1, BAV 2. - [FO]")
        self.assertEqual(pseudo.nazev("Žádost o prominutí poplatků – Kvido Neznámý I. Rada města Vsetín"),
                         "Žádost o prominutí poplatků – [FO] I. Rada města Vsetín")

    def test_volebni_tabulka_celoplosne(self):
        t = ("Zápis o výsledku voleb do zastupitelstva obce Testov\nVolební strana č. 1\n"
             "1. Kvido Neznámý 41 2. Ruprecht Vymyšlený 55 3. Ingeborg Fiktivní 30")
        out = self.assertBezJmena(t, "Kvido", "Ruprecht", "Ingeborg", "Neznámý", "Vymyšlený", "Fiktivní")
        self.assertIn("Volební strana", out)

    def test_ulice_instituce_firmy_zustavaji(self):
        for s in ("třída Tomáše Bati 21, 76001 Zlín", "Univerzita Tomáše Bati ve Zlíně",
                  "Střední odborná škola Josefa Sousedíka Vsetín", "Nadaci Jana Pivečky, o.p.s.",
                  "Michala Urbánka 436, Rokytnice", "nábřeží Ludvíka Svobody 1222/12", "Hradec Králové",
                  "Petr Novák s.r.o.", "ul. MUDr. Františka Sovy 97, Vsetín"):
            self.assertEqual(pseudo.text(s), s)


class TestStore(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.p = os.path.join(self.d, "x.jsonl")

    def rec(self, **kw):
        return {"id": "x:1", "source_url": "https://example.org/1", "retrieved_at": "2026-10-23T10:00:00+02:00", "a": 1, **kw}

    def test_deduplikace_id_sha256(self):
        j = store.Jsonl(self.p)
        self.assertEqual(j.add(self.rec()), "nove")
        self.assertEqual(j.add(self.rec(retrieved_at="2026-10-24T10:00:00+02:00")), "nezmeneno")  # čas není obsah
        self.assertEqual(j.add(self.rec(a=2)), "zmeneno")
        self.assertEqual(j.flush(), 2)
        j2 = store.Jsonl(self.p)  # po načtení ze souboru
        self.assertEqual(j2.add(self.rec(a=2)), "nezmeneno")
        self.assertEqual(j2.add(self.rec(a=1)), "nezmeneno")  # starší verze je také známá
        self.assertEqual(j2.latest["x:1"]["a"], 2)
        with open(self.p) as f:
            self.assertEqual(len(f.readlines()), 2)  # append-only, nic nepřepsáno

    def test_otisk_stabilni(self):
        a = store.otisk({"id": "1", "b": [1, 2], "a": "č"})
        self.assertEqual(a, store.otisk({"a": "č", "b": [1, 2], "id": "1", "puvod": {"x": 1}}))

    def test_povinna_pole(self):
        with self.assertRaises(ValueError):
            store.Jsonl(self.p).add({"id": "x", "source_url": "https://e"})

    def test_manifest(self):
        man = store.nacti_manifest(os.path.join(self.d, "manifest.json"))
        for i in range(25):
            store.zapis_zdroj(man, "z", zacatek=f"2026-10-23T10:{i:02d}:00+02:00", stav="chyba", chyba=f"e{i}")
        z = man["zdroje"]["z"]
        self.assertEqual(len(z["chyby"]), store.MAX_CHYB)
        self.assertEqual(z["chyby"][-1]["chyba"], "e24")
        self.assertNotIn("posledni_uspech", z)
        store.zapis_zdroj(man, "z", zacatek="2026-10-23T11:00:00+02:00", stav="ok", kurzor={"k": 1}, pocty={"nove": 1})
        self.assertEqual(z["posledni_uspech"], "2026-10-23T11:00:00+02:00")
        j = store.Jsonl(os.path.join(self.d, "x.jsonl"))
        j.add(self.rec())
        j.flush()
        mp = os.path.join(self.d, "manifest.json")
        store.zapis_manifest(mp, man, data_dir=self.d)
        with open(mp) as f:
            m = json.load(f)
        self.assertEqual(m["soubory"]["data/x.jsonl"]["radku"], 1)
        errs = list(schema("manifest.schema.json").iter_errors(m))
        self.assertEqual(errs, [])


class TestSchemataDat(unittest.TestCase):
    def test_vzorek_kazdeho_jsonl(self):
        """Prvních 200 řádků každého data/*.jsonl odpovídá schématu a sha256 sedí."""
        import glob
        soubory = sorted(glob.glob(os.path.join(ROOT, "data", "*.jsonl")))
        self.assertTrue(soubory)
        for f in soubory:
            v = schema(f"jsonl-{os.path.basename(f)[:-6].replace('_', '-')}.schema.json")
            with open(f, encoding="utf-8") as fh:
                for i, line in zip(range(200), fh):
                    r = json.loads(line)
                    self.assertEqual(list(v.iter_errors(r)), [], f"{f}:{i + 1}")
                    self.assertEqual(r["sha256"], store.otisk(r), f"{f}:{i + 1}")


class TestHttpRobots(unittest.TestCase):
    def test_crawl_delay_a_ua(self):
        h = http_klient({"https://www.vhodne-uverejneni.cz/robots.txt": VU_ROBOTS,
                         "https://www.vhodne-uverejneni.cz/a": b"ok"})
        self.assertEqual(h.get_bytes("https://www.vhodne-uverejneni.cz/a"), b"ok")
        self.assertEqual(h._interval["www.vhodne-uverejneni.cz"], 30.0)
        self.assertTrue(all(ua == zdroje.UA for _, ua in h.opener.log))
        with self.assertRaises(RobotsDenied):
            h.get_bytes("https://www.vhodne-uverejneni.cz/x?c=1")

    def test_robots_zastupne_znaky(self):
        from integrace.http import robots_pravidla, robots_povoleno
        pr = robots_pravidla(["User-agent: *", "Crawl-Delay: 30", "Disallow: /*?c=1", "Disallow: /tajne$",
                              "Allow: /verejne/", "Disallow: /verejne/x", "", "User-agent: JinyBot", "Disallow: /"],
                             zdroje.UA)
        self.assertFalse(robots_povoleno(pr, "https://h/profil/1?c=1"))
        self.assertTrue(robots_povoleno(pr, "https://h/profil/1?c=2"))
        self.assertFalse(robots_povoleno(pr, "https://h/tajne"))
        self.assertTrue(robots_povoleno(pr, "https://h/tajne/dalsi"))
        self.assertFalse(robots_povoleno(pr, "https://h/verejne/x1"))
        self.assertTrue(robots_povoleno(pr, "https://h/verejne/y"))
        self.assertTrue(robots_povoleno(pr, "https://h/"))  # skupina JinyBot se nás netýká

    def test_nedostupny_robots_zakazuje(self):
        h = http_klient({"https://www.mestovsetin.cz/robots.txt": SITE_DOWN})
        with self.assertRaises(RobotsDenied):
            h.get_bytes("https://www.mestovsetin.cz/assets/File.ashx?id_org=18676&id_dokumenty=1")
        self.assertEqual(len(h.opener.log), 1)  # jen pokus o robots.txt, dokument se nestahoval

    def test_robots_404_povoluje(self):
        h = http_klient({"https://ares.gov.cz/x": b"{}"})
        self.assertEqual(h.get_bytes("https://ares.gov.cz/x"), b"{}")


class TestSberEndToEnd(unittest.TestCase):
    """scripts/sber.py: izolace selhání zdrojů, manifest, RUNLOG, dry-run, deduplikace."""

    def routes(self):
        url = profil.url_interval(date(2026, 9, 1), date(2026, 10, 23))
        ares = json.dumps({"ico": "27642411", "obchodniJmeno": "DEKPROJEKT s.r.o.", "pravniForma": "112",
                           "sidlo": {"textovaAdresa": "Tiskařská 10/257, Praha"}}).encode()
        url2 = profil.url_interval(date(2026, 8, 24), date(2026, 10, 23))  # 2. běh: kurzor − 60 dní překryv
        return {"https://www.vhodne-uverejneni.cz/robots.txt": VU_ROBOTS,
                url: (200, fix("sber/xmldatavz_2026_09_10.xml"), "text/xml"),
                url2: (200, fix("sber/xmldatavz_2026_09_10.xml"), "text/xml"),
                "https://www.mestovsetin.cz/robots.txt": SITE_DOWN,
                "https://ares.gov.cz/robots.txt": b"User-agent: *\nDisallow: /cms/\n",
                zdroje.ARES_URL.format("27642411"): (200, ares, "application/json")}

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.data = os.path.join(self.d, "data")
        os.makedirs(self.data)
        # výchozí stav: kurzor profilu a jedno IČO v datech k ověření
        with open(os.path.join(self.data, "manifest.json"), "w") as f:
            json.dump({"schema": "vsetin-osint/manifest@1", "soubory": {},
                       "zdroje": {"profil_zadavatele": {"chyby": [], "kurzor": {"stazeno_do": "2026-10-31"}}}}, f)
        j = store.Jsonl(os.path.join(self.data, "vyber_dodavatele.jsonl"))
        j.add({"id": "vd:1/1/RM/2026", "source_url": "https://www.mestovsetin.cz/x", "retrieved_at": store.ted(),
               "cislo_usneseni": "1/1/RM/2026", "vitez_ico": "27642411"})
        j.flush()

    def run_sber(self, *args):
        argv = ["--data-dir", self.data, "--runlog", os.path.join(self.d, "RUNLOG.md"), *args]
        with open(os.devnull, "w") as dn:
            old, sys.stdout, sys.stderr = (sys.stdout, sys.stderr), dn, dn
            try:
                return sber.main(argv, http=http_klient(self.routes()), dnes=date(2026, 10, 23))
            finally:
                sys.stdout, sys.stderr = old

    def test_beh(self):
        # profil: kurzor 31. 10. - 60 dní = 1. 9. 2026 → jeden interval do 23. 10.
        src = ["--source", "usneseni", "--source", "profil_zadavatele", "--source", "ares"]
        self.assertEqual(self.run_sber("--dry-run", *src), 0)  # nedosažitelný web města není chyba běhu
        self.assertFalse(os.path.exists(os.path.join(self.data, "verejne_zakazky.jsonl")))  # dry-run nic nezapsal
        self.assertFalse(os.path.exists(os.path.join(self.d, "RUNLOG.md")))

        self.assertEqual(self.run_sber(*src), 0)  # usnesení: web nedosažitelný -> unreachable, ostatní proběhnou
        with open(os.path.join(self.data, "manifest.json")) as f:
            man = json.load(f)
        z = man["zdroje"]
        self.assertEqual(z["usneseni"]["stav"], "unreachable")
        self.assertIn("robots.txt", z["usneseni"]["nedosazitelny"]["duvod"])
        self.assertEqual(z["usneseni"]["chyby"], [])  # nedosažitelnost se nepočítá mezi chyby
        self.assertEqual(z["profil_zadavatele"]["stav"], "ok")
        self.assertEqual(z["profil_zadavatele"]["pocty_posledniho_behu"]["nove"], 2)
        self.assertEqual(z["profil_zadavatele"]["kurzor"]["stazeno_do"], "2026-10-31")  # kurzor necouvá
        self.assertEqual(z["ares"]["stav"], "ok")
        self.assertEqual(man["posledni_beh"]["stav"], {"usneseni": "unreachable", "profil_zadavatele": "ok", "ares": "ok"})
        self.assertEqual(list(schema("manifest.schema.json").iter_errors(man)), [])
        with open(os.path.join(self.data, "subjekty_ares.jsonl")) as f:
            a = [json.loads(x) for x in f]
        self.assertEqual((a[0]["id"], a[0]["obchodni_jmeno"], a[0]["fyzicka_osoba"]), ("ico:27642411", "DEKPROJEKT s.r.o.", False))
        with open(os.path.join(self.d, "RUNLOG.md")) as f:
            log = f.read()
        self.assertIn("| profil_zadavatele | ok | 2 |", log)
        self.assertIn("| usneseni | unreachable |", log)

        # chyba ve 2. intervalu: počty a kurzor 1. intervalu se uloží, stav = chyba
        b = zdroje.Beh(http=http_klient(self.routes()), sklad=store.Sklad(self.data),
                       kurzor={"stazeno_do": "2026-04-01"}, limit=5, dnes=date(2026, 10, 23))
        b.http.opener.routes[profil.url_interval(date(2026, 1, 31), date(2026, 7, 29))] = (
            200, fix("sber/xmldatavz_2026_09_10.xml"), "text/xml")
        with self.assertRaises(zdroje.CastecnaChyba) as cm:
            zdroje.profil_zadavatele(b)
        self.assertEqual(cm.exception.kurzor["stazeno_do"], "2026-07-29")
        self.assertIn("HTTP 404", str(cm.exception))

        # 2. běh: nic nového (deduplikace podle id + sha256), kurzory drží
        self.assertEqual(self.run_sber("--source", "profil_zadavatele", "--source", "ares"), 0)
        with open(os.path.join(self.data, "manifest.json")) as f:
            z = json.load(f)["zdroje"]
        self.assertEqual(z["profil_zadavatele"]["pocty_posledniho_behu"]["nove"], 0)
        self.assertEqual(z["profil_zadavatele"]["pocty_posledniho_behu"]["nezmeneno"], 2)
        with open(os.path.join(self.data, "verejne_zakazky.jsonl")) as f:
            self.assertEqual(len(f.readlines()), 2)


if __name__ == "__main__":
    unittest.main()
