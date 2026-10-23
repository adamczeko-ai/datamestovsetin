"""JSONL úložiště s deduplikací (id + sha256), manifest sběru a zápis RUNLOG.

Každý řádek JSONL = jeden záznam s povinnými poli id, source_url, retrieved_at, sha256.
sha256 = SHA-256 kanonického JSON obsahu záznamu bez polí METADATA (obsahový otisk;
změna jen času stažení nebo URL zdroje novou verzi nevytvoří).
Soubor je append-only: shodné (id, sha256) se přeskočí, změněný obsah stejného id se připíše
jako nová verze (platí poslední řádek s daným id). Nic se nemaže.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Prague")
METADATA = ("sha256", "retrieved_at", "puvod", "source_url")  # původ, ne obsah
MAX_CHYB = 20  # kolik posledních chyb na zdroj držet v manifestu


def ted() -> str:
    """Aktuální čas v Europe/Prague, ISO 8601 s posunem."""
    return datetime.now(TZ).isoformat(timespec="seconds")


def otisk(rec: dict) -> str:
    obsah = {k: v for k, v in rec.items() if k not in METADATA}
    s = json.dumps(obsah, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


class Jsonl:
    """Jeden datový soubor data/<nazev>.jsonl."""

    def __init__(self, path: str):
        self.path = path
        self.seen: set[tuple[str, str]] = set()
        self.latest: dict[str, dict] = {}
        self.pending: list[dict] = []
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                for n, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    r = json.loads(line)
                    self.seen.add((r["id"], r["sha256"]))
                    self.latest[r["id"]] = r

    def add(self, rec: dict) -> str:
        """Vrátí 'nove' | 'zmeneno' | 'nezmeneno'. Záznam bez sha256 dostane obsahový otisk."""
        for k in ("id", "source_url", "retrieved_at"):
            if not rec.get(k):
                raise ValueError(f"záznam bez povinného pole {k}: {str(rec)[:200]}")
        rec["sha256"] = otisk(rec)
        key = (rec["id"], rec["sha256"])
        if key in self.seen:
            return "nezmeneno"
        stav = "zmeneno" if rec["id"] in self.latest else "nove"
        self.seen.add(key)
        self.latest[rec["id"]] = rec
        self.pending.append(rec)
        return stav

    def flush(self) -> int:
        if not self.pending:
            return 0
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as f:
            for r in self.pending:
                f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
        n = len(self.pending)
        self.pending = []
        return n

    def souhrn(self) -> dict:
        radku = len(self.seen)
        return {"radku": radku, "unikatnich_id": len(self.latest)}


class Sklad:
    """Sada JSONL souborů v adresáři data/ (otevřené líně, zapisují se najednou)."""

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.files: dict[str, Jsonl] = {}

    def __getitem__(self, nazev: str) -> Jsonl:
        if nazev not in self.files:
            self.files[nazev] = Jsonl(os.path.join(self.data_dir, f"{nazev}.jsonl"))
        return self.files[nazev]

    def flush(self) -> dict[str, int]:
        return {n: f.flush() for n, f in self.files.items()}


# --- manifest ---

def nacti_manifest(path: str) -> dict:
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"schema": "vsetin-osint/manifest@1", "zdroje": {}, "soubory": {}}


def zapis_zdroj(man: dict, zdroj: str, *, zacatek: str, stav: str, pocty: dict | None = None,
                kurzor: dict | None = None, chyba: str | None = None, soubory: list[str] | None = None,
                poznamka: str | None = None):
    """stav: ok | chyba | unreachable (hostitel síťově nedosažitelný – nepočítá se mezi chyby)."""
    z = man.setdefault("zdroje", {}).setdefault(zdroj, {"chyby": []})
    z["posledni_beh"] = zacatek
    z["stav"] = stav
    if stav == "unreachable":
        z["nedosazitelny"] = {"cas": zacatek, "duvod": (poznamka or "")[:500]}
    elif "nedosazitelny" in z:
        z["posledni_nedosazitelnost"] = z.pop("nedosazitelny")
    if stav == "ok":
        z["posledni_uspech"] = zacatek
    if pocty is not None:
        z["pocty_posledniho_behu"] = pocty
    if kurzor is not None:
        z["kurzor"] = kurzor
    if soubory:
        z["soubory"] = sorted(set(z.get("soubory", [])) | set(soubory))
    if chyba:
        z["chyby"] = (z.get("chyby", []) + [{"cas": zacatek, "chyba": chyba[:500]}])[-MAX_CHYB:]


def zapis_manifest(path: str, man: dict, sklad: Sklad | None = None, data_dir: str | None = None):
    man["aktualizovano"] = ted()
    if data_dir:
        souhrn = man.setdefault("soubory", {})
        for fn in sorted(os.listdir(data_dir)):
            if not fn.endswith(".jsonl"):
                continue
            p = os.path.join(data_dir, fn)
            j = sklad[fn[:-6]] if sklad else Jsonl(p)
            with open(p, "rb") as f:
                h = sha256_bytes(f.read())
            souhrn[f"data/{fn}"] = {**j.souhrn(), "sha256_souboru": h}
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=1, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def zapis_runlog(path: str, beh: dict):
    """Připíše sekci běhu do docs/RUNLOG.md."""
    novy = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as f:
        if novy:
            f.write("# RUNLOG – sběr dat (scripts/sber.py)\n\nČasy v Europe/Prague. Každý ostrý běh připisuje jednu sekci; "
                    "dry-run se nezapisuje.\n")
        f.write(f"\n## {beh['zacatek']} – {beh.get('rezim', 'ostry')}\n\n")
        f.write(f"- konec: {beh['konec']}; zdroje: {', '.join(beh['zdroje'])}; limity: {json.dumps(beh.get('limity', {}), ensure_ascii=False)}\n\n")
        f.write("| Zdroj | Stav | Nové | Změněné | Nezměněné | Poznámka |\n|---|---|---|---|---|---|\n")
        for z, v in beh["vysledky"].items():
            p = v.get("pocty") or {}
            pozn = (v.get("chyba") or v.get("poznamka") or "").replace("|", "/").replace("\n", " ")[:300]
            f.write(f"| {z} | {v['stav']} | {p.get('nove', 0)} | {p.get('zmeneno', 0)} | {p.get('nezmeneno', 0)} | {pozn} |\n")
