"""CI kontrola repozitáře (GitHub Actions i lokálně): python3 scripts/ci_validate.py

1) každý *.json v repu je validní JSON,
2) data odpovídají JSON Schema (scripts/validate_schemas.py),
3) všechny testy tests/test_*.py procházejí (offline; živé testy jen s INTEGRACE_LIVE=1).
Návratový kód 0 = vše v pořádku.
"""
import glob
import json
import subprocess
import sys

bad = []
for f in sorted(glob.glob("**/*.json", recursive=True)):
    if f.startswith((".git/", "node_modules/")):
        continue
    try:
        with open(f, encoding="utf-8") as fh:
            json.load(fh)
    except Exception as e:  # noqa: BLE001
        bad.append(f"{f}: {e}")
print(f"JSON: {len(bad)} chyb")
for b in bad:
    print("  ", b)

rc_schema = subprocess.call([sys.executable, "scripts/validate_schemas.py"])
print(f"Schémata: {'OK' if rc_schema == 0 else 'CHYBA'}")

mods = [f[:-3].replace("/", ".") for f in sorted(glob.glob("tests/test_*.py"))]
rc_tests = subprocess.call([sys.executable, "-W", "ignore", "-m", "unittest", *mods])
print(f"Testy ({len(mods)} modulů): {'OK' if rc_tests == 0 else 'CHYBA'}")

sys.exit(1 if bad or rc_schema or rc_tests else 0)
