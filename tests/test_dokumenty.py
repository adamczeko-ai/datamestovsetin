"""Testy integrace/sources/dokumenty.py – text po stranách + SHA-256 (offline, syntetické PDF/HTML/ZIP).

PDF se generuje přímo v testu (minimální platné PDF), extrakce běží přes pdftotext nebo pypdf;
když není k dispozici ani jeden, testy PDF se přeskočí.
"""
import hashlib
import http.server
import io
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import zipfile

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

from integrace import db  # noqa: E402
from integrace.http import Http  # noqa: E402
from integrace.sources import dokumenty as d  # noqa: E402

try:
    import pypdf  # noqa: F401
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False
HAS_EXTRAKTOR = bool(shutil.which("pdftotext")) or HAS_PYPDF


def mini_pdf(stranky):
    """Minimální PDF; stranky = seznam textů (ASCII) nebo None pro stránku bez textu (jen obdélník)."""
    objs = ["<< /Type /Catalog /Pages 2 0 R >>", None, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for s in stranky:
        stream = (f"BT /F1 14 Tf 72 720 Td ({s}) Tj ET" if s is not None else "0 0 1 rg 100 100 200 200 re f").encode()
        objs.append(f"<< /Length {len(stream)} >>\nstream\n{stream.decode()}\nendstream")
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {len(objs)} 0 R >>")
        kids.append(len(objs))
    objs[1] = f"<< /Type /Pages /Kids [{' '.join(f'{k} 0 R' for k in kids)}] /Count {len(kids)} >>"
    out, offs = io.BytesIO(), []
    out.write(b"%PDF-1.4\n")
    for i, o in enumerate(objs, 1):
        offs.append(out.tell())
        out.write(f"{i} 0 obj\n{o}\nendobj\n".encode())
    x = out.tell()
    out.write(f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode())
    for o in offs:
        out.write(f"{o:010d} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n".encode())
    return out.getvalue()


@unittest.skipUnless(HAS_EXTRAKTOR, "chybí pdftotext i pypdf")
class Pdf(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.t)

    def test_strany_a_otisk(self):
        pdf = mini_pdf(["Usneseni 34/18/ZM/2025 kupni cena 33 150 000 Kc", "Strana dva: rozpoctove opatreni c. 4"])
        m = d.uloz(self.t, "https://x/a.pdf", pdf, stazeno_utc="2026-10-23T08:00:00+00:00")[0]
        sha = hashlib.sha256(pdf).hexdigest()
        self.assertEqual(m["sha256"], sha)
        self.assertEqual(m["pocet_stran"], 2)
        self.assertTrue(m["textova_vrstva"])
        self.assertEqual(m["stazeno_praha"], "2026-10-23T10:00:00+02:00")
        with open(os.path.join(self.t, sha, "p1.txt"), encoding="utf-8") as f:
            self.assertIn("33 150 000", f.read())
        with open(os.path.join(self.t, sha, "p2.txt"), encoding="utf-8") as f:
            self.assertIn("Strana dva", f.read())
        self.assertFalse(os.path.exists(os.path.join(self.t, sha + ".part")))

    def test_idempotence_a_dalsi_url(self):
        pdf = mini_pdf(["Text dokumentu pro test idempotence a URL"])
        self.assertTrue(d.uloz(self.t, "https://x/1", pdf)[0]["_nove"])
        m2 = d.uloz(self.t, "https://x/2", pdf)[0]
        self.assertFalse(m2["_nove"])
        self.assertEqual(m2["url"], ["https://x/1", "https://x/2"])

    def test_sken_bez_textove_vrstvy(self):
        m = d.uloz(self.t, "https://x/sken.pdf", mini_pdf([None, None]))[0]
        self.assertEqual(m["pocet_stran"], 2)
        self.assertFalse(m["textova_vrstva"])
        self.assertIn("OCR", m["poznamka"])

    def test_zip_clenove(self):
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as z:
            z.writestr("navrh-usneseni_108136.html", "<html><body><p>kupní cena …………,- Kč</p></body></html>")
            z.writestr("priloha.pdf", mini_pdf(["Priloha s textem pro test ZIP clenu"]))
            z.writestr("obrazek.jpg", b"\xff\xd8\xff")
        ms = d.uloz(self.t, "https://x/balicek.zip", b.getvalue())
        self.assertEqual(sorted(m["url"][0] for m in ms),
                         ["https://x/balicek.zip#navrh-usneseni_108136.html", "https://x/balicek.zip#priloha.pdf"])
        html_m = next(m for m in ms if m["typ"] == "html")
        with open(os.path.join(self.t, html_m["sha256"], "p1.txt"), encoding="utf-8") as f:
            self.assertIn("kupní cena …………,- Kč", f.read())


class Html(unittest.TestCase):
    def test_html_cisty_text(self):
        t = d.text_html("<html><script>x()</script><p>Řádek&nbsp;1</p><br>Řádek 2</html>".encode())[0]
        self.assertNotIn("x()", t)
        self.assertIn("Řádek 1", t)
        self.assertIn("Řádek 2", t)

    def test_seznam(self):
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".txt", encoding="utf-8") as f:
            f.write("# komentář\nhttps://a/1\nzm.balicky\thttps://a/2\n\n")
        try:
            self.assertEqual(d.nacti_seznam(f.name), [(d.SOURCE_ID, "https://a/1"), ("zm.balicky", "https://a/2")])
        finally:
            os.remove(f.name)


FILES = {}


class Srv(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        b = FILES.get(self.path)
        if b is None:
            self.send_response(404); self.end_headers(); return
        etag = '"' + hashlib.md5(b).hexdigest()[:12] + '"'
        if self.headers.get("If-None-Match") == etag:
            self.send_response(304); self.end_headers(); return
        self.send_response(200)
        self.send_header("ETag", etag)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


@unittest.skipUnless(HAS_EXTRAKTOR, "chybí pdftotext i pypdf")
class SyncEndToEnd(unittest.TestCase):
    def test_sync_dvakrat(self):
        FILES["/doc.pdf"] = mini_pdf(["Dokument mesta pro end-to-end test"])
        srv = http.server.HTTPServer(("127.0.0.1", 0), Srv)
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()
        tmp = tempfile.mkdtemp()
        try:
            con = db.connect(os.path.join(tmp, "i.db"))
            h = Http(con, os.path.join(tmp, "cache"), min_interval=0, sleep=lambda s: None)
            url = f"http://127.0.0.1:{srv.server_port}/doc.pdf"
            seznam = [("test", url), ("test", f"http://127.0.0.1:{srv.server_port}/chybi.pdf")]
            r1 = d.sync(con, h, seznam, os.path.join(tmp, "texty"))
            self.assertEqual((r1["nove_texty"], len(r1["chyby"])), (1, 1))
            r2 = d.sync(con, h, seznam[:1], os.path.join(tmp, "texty"))
            self.assertEqual((r2["nove_texty"], r2["beze_zmeny"]), (0, 1))
            row = con.execute("SELECT sha256, pocet_stran, textova_vrstva FROM dokument_text WHERE url=?", (url,)).fetchone()
            self.assertEqual(row, (hashlib.sha256(FILES["/doc.pdf"]).hexdigest(), 1, 1))
            led = con.execute("SELECT status FROM sync_ledger WHERE url=? ORDER BY id", (url,)).fetchall()
            self.assertEqual([x[0] for x in led], ["downloaded", "not_modified"])
        finally:
            srv.shutdown()
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
