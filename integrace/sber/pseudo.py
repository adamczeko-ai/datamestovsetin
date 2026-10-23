"""Pseudonymizace fyzických osob v odvozených datech.

Heuristika (není zaručená – výstup před zveřejněním kontroluje člověk):
1. známá jména (např. odvozená z dříve pseudonymizovaného názvu bodu) včetně skloňovaných tvarů,
2. oslovení: pan/paní/panu/manželé … + 1–3 slova s velkým písmenem,
3. akademické tituly (Ing., Mgr., MUDr., …) + jména,
4. řádek se jménem bez titulu před funkcí (starosta, místostarostka, tajemník, vedoucí …),
5. křestní jméno ze slovníku (i skloňované: Pavlem, Janou, Zdeňkovi) + slovo s velkým písmenem, i obráceně,
6. v názvech: úsek za čárkou/pomlčkou ve tvaru „Příjmení Jméno“ bez právní formy a bez slov instituce.
Firmy (s právní formou), instituce a obce se nemění. Zástupný text: FO.
"""
from __future__ import annotations

import re

FO = "[FO]"
FO_ARES = "[FO – pseudonymizováno]"
# kódy právních forem ČSÚ pro fyzické osoby (podnikatelé, zahraniční FO)
FO_PRAVNI_FORMY = {"100", "101", "102", "103", "104", "105", "106", "107", "108", "424", "425"}

V = "A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ"
M = "a-záčďéěíňóřšťúůýž"
SLOVO = rf"[{V}][{M}]+(?:-[{V}][{M}]+)?"
JMENO = rf"{SLOVO}(?:\s+{SLOVO}){{0,2}}"

PRAVNI_FORMA = re.compile(
    r"(s\.\s?r\.\s?o|spol\.|a\.\s?s\.|v\.\s?o\.\s?s|k\.\s?s\.|z\.\s?s\.|z\.\s?ú\.|o\.\s?p\.\s?s|"
    r"družstvo|(?-i:\bSE\b)|GmbH|Ltd|\bInc\b|s\.p\.|státní podnik|příspěvková organizace|p\.\s?o\.|nadace|nadační|ústav|"
    r"spolek|svaz|jednota|klub|sdružení|společenství|církev|farnost|sbor|škola|školka|\bZŠ\b|\bMŠ\b|\bSŠ\b|"
    r"gymnázium|nemocnice|obec|město|městys|kraj|úřad|ministerstvo|republika|policie|hasič|centrum|muzeum|"
    r"knihovna|divadlo|komise|výbor|rada|zastupitelstvo|odbor|fond|agentura|správa|technické služby)",
    re.I)
# jen právní forma (pro kontrolu textu za jménem: „Petr Novák s.r.o.“)
PRAVNI_FORMA_ZA = re.compile(r"(s\.\s?r\.\s?o|spol\.|a\.\s?s\.|v\.\s?o\.\s?s|k\.\s?s\.|z\.\s?s\.|z\.\s?ú\.|o\.\s?p\.\s?s|"
                             r"(?-i:SE\b)|GmbH|Ltd|družstvo)", re.I)
# slova, která nejsou jménem osoby (místa a běžné výrazy v názvech bodů)
NE_JMENO = {
    "Vsetín", "Vsetína", "Vsetíně", "Jasenka", "Rokytnice", "Bobrky", "Ohrada", "Trávníky", "Luh", "Sychrov",
    "Bečva", "Horní", "Dolní", "Nové", "Nový", "Staré", "Starý", "Velké", "Malé", "Malá", "Valašské", "Valašská",
    "Svárov", "Lázky", "Semetín", "Hrbová", "Pržno", "Rybníky", "Ratiboř", "Zlín", "Zlínský", "Praha",
    "Smlouva", "Dodatek", "Žádost", "Dotace", "Prodej", "Nákup", "Pronájem", "Výpůjčka", "Rozpočtové",
    "Opatření", "Program", "Kontrola", "Informace", "Zpráva", "Návrh", "Změna", "Oprava", "Rekonstrukce",
    "Česká", "Český", "Moravská", "Lávka", "Most", "Ulice", "Náměstí", "Zápis", "Dražební", "Oznámení",
}

KRESTNI = """Adam Adéla Adriana Alena Aleš Alexandr Alexandra Alice Alois Alžběta Andrea Aneta Anežka Anna Antonie
Antonín Barbora Blanka Bohdan Bohumil Bohumila Bohuslav Božena Bronislav Dagmar Dalibor Daniel Daniela Darina David
Denisa Dominik Dušan Eduard Edita Eliška Emil Emilie Eva Filip František Františka Gabriela Hana Helena Ilona Irena
Iva Ivan Ivana Iveta Jakub Jan Jana Jarmila Jaromír Jaroslav Jaroslava Jindřich Jindřiška Jiří Jiřina Jitka Josef
Jozef Jana Julie Kamil Kamila Karel Karla Karolína Kateřina Klára Kristýna Kryštof Ladislav Lenka Leoš Libor Libuše
Lubomír Lucie Ludmila Luděk Lukáš Magdalena Marcel Marcela Marek Marie Marián Markéta Marta Martin Martina Matěj
Matyáš Michael Michaela Michal Milada Milan Milena Miloslav Miloš Miluše Miroslav Miroslava Monika Naděžda Natálie
Nikola Nikolas Oldřich Olga Ondřej Otakar Patricie Patrik Pavel Pavla Pavlína Petr Petra Přemysl Radek Radim Radka
Radomír Radoslav Radovan Renata Richard Robert Roman Romana Rostislav Růžena Sabina Simona Soňa Stanislav Stanislava
Stefanie Šárka Šimon Štefan Štěpán Štěpánka Taťána Tereza Tomáš Václav Vanda Vendula Veronika Věra Viktor Viktorie
Vilém Vladimír Vladimíra Vladislav Vlasta Vlastimil Vojtěch Vratislav Zbyněk Zdeněk Zdeňka Zdenka Zuzana Žaneta
Ludvík Noemi Svatopluk Igor Bořivoj Ctirad Čestmír Drahomír Drahomíra Hedvika Hynek Ignác Ivo Jarmil Jindra Kornélie
Judita Jenny Jesika Kevin Leona Linda Lubomíra Ludmila Marcela Margarita Nataša Nela Oskar Otto Rudolf Samantha
Sandra Silvie Sofie Svatava Šimona Tadeáš Tobiáš Valerie Vanesa Vavřinec Vítězslav Vít Zora Zlata Zita Žofie""".split()


def _kmeny(j: str) -> set[str]:
    k = {j[:-1] if j[-1] in "aeiouyáéíý" else j}
    if j.endswith("el"):
        k.add(j[:-2] + "l")  # Pavel -> Pavla, Pavlem
    if j.endswith("ek"):
        k.add(j[:-2] + "k")  # Marek -> Marka
    if j.endswith("ěk"):
        k.add(j[:-2] + "ňk")  # Zdeněk -> Zdeňka
    return {x for x in k if len(x) >= 3}


_KM = sorted({k for j in KRESTNI for k in _kmeny(j)}, key=len, reverse=True)
KRESTNI_RX = rf"(?:{'|'.join(_KM)})[{M}]{{0,4}}"
RE_KRESTNI = (re.compile(rf"\b{KRESTNI_RX}\s+{SLOVO}\b"), re.compile(rf"\b{SLOVO}\s+{KRESTNI_RX}\b"),
              # ženské příjmení na -ová/-ové/-ovou s dalším slovem s velkým písmenem
              re.compile(rf"\b{SLOVO}\s+[{V}][{M}]+ov(?:á|é|ou)\b"),
              re.compile(rf"\b[{V}][{M}]+ov(?:á|é|ou)\s+{SLOVO}\b"),
              # instrumentál po předložce: „s Radomilem Palou“, „se Zdeňkem Novákem“
              re.compile(rf"(?:(?<=\bs )|(?<=\bse ))[{V}][{M}]+(?:em|ou)\s+[{V}][{M}]+(?:em|ou|ým|í)\b"))

TITUL = r"(?:Ing\.\s?arch\.|Ing\.|Mgr\.\s?A\.|Mgr\.|Bc\.\s?A\.|Bc\.|MUDr\.|MDDr\.|MVDr\.|JUDr\.|PhDr\.|RNDr\.|PaedDr\.|PharmDr\.|ThDr\.|ThLic\.|Dr\.|doc\.|prof\.)"
RE_TITUL = re.compile(rf"(?:{TITUL}\s*)+{JMENO}(?:,?\s*(?:Ph\.\s?D\.|CSc\.|MBA|DiS\.|LL\.M\.|MPA|DBA))*")
OSLOVENI = (r"pan|pana|panu|panem|paní|pí\.|manželé|manželů|manželům|manžele|manželi|manž\.|"
            r"žadatel|žadatelka|žadatelce|žadateli|nájemce|nájemkyně|kupující|kupujícímu|prodávající")
RE_OSLOVENI = re.compile(rf"\b({OSLOVENI})\s+({JMENO}(?:\s+a\s+{JMENO})?)")
RE_FUNKCE = re.compile(
    rf"(?m)^({JMENO})[ \t]*\n(?=[ \t]*(?:I+\.\s*)?(?:starost|místostarost|tajemn|vedouc|předsed|ředitel|"
    rf"jednatel|referent|zpracoval|člen))")
RE_ZPRACOVAL = re.compile(rf"((?:Zpracoval(?:/a|a)?|Vypracoval(?:/a|a)?|Předkládá|Předkladatel|Vyřizuje|"
                          rf"Kontaktní osoba)\s*:\s*)((?:{TITUL}\s*)*{JMENO}(?:,?\s*(?:Ph\.\s?D\.|DiS\.|MBA))*)")


def je_pravnicka(nazev: str | None) -> bool:
    return bool(nazev and PRAVNI_FORMA.search(nazev))


def vypada_jako_jmeno(s: str) -> bool:
    """„Příjmení Jméno“ (2–3 slova s velkým písmenem), bez právní formy a slov instituce/místa."""
    s = s.strip().strip(".,;:")
    if not re.fullmatch(rf"(?:{TITUL}\s*)*{SLOVO}(?:\s+{SLOVO}){{1,2}}", s):
        return False
    if je_pravnicka(s):
        return False
    return not any(w in NE_JMENO for w in re.findall(rf"[{V}{M}]+", s))


def nazev_subjektu(nazev: str | None, pravni_forma: str | None = None) -> str | None:
    """Název smluvní strany / účastníka: FO -> FO_ARES, firmy beze změny."""
    if not nazev:
        return nazev
    if pravni_forma is not None:
        return FO_ARES if str(pravni_forma) in FO_PRAVNI_FORMY else nazev
    if je_pravnicka(nazev) or "[FO" in nazev:
        return nazev
    if re.search(r"\d", nazev):
        return nazev
    return FO_ARES if vypada_jako_jmeno(re.sub(rf"^{TITUL}\s*", "", nazev)) else nazev


def _tvary(jmeno: str) -> list[str]:
    """Kmeny slov jména pro skloňované tvary (Mirgová -> Mirgov…, Denisa -> Denis…)."""
    out = []
    for w in re.findall(rf"[{V}][{M}]+", jmeno):
        if len(w) >= 4 and w not in NE_JMENO:
            out.append(w[:-1] if len(w) > 4 else w)
    return out


def _krestni(m: re.Match) -> str:
    s, za = m.group(0), m.string[m.end():m.end() + 25]
    if je_pravnicka(s) or PRAVNI_FORMA_ZA.match(za.lstrip(" ,")) or any(w in NE_JMENO for w in s.split()):
        return s  # firma pojmenovaná po osobě („Petr Novák s.r.o.“) nebo místo
    return FO


def text(t: str | None, znama_jmena: list[str] | tuple = ()) -> str | None:
    if not t:
        return t
    for jm in znama_jmena:
        for kmen in _tvary(jm):
            t = re.sub(rf"\b{re.escape(kmen)}[{M}]{{0,4}}\b", FO, t)
    t = RE_TITUL.sub(FO, t)
    for rx in RE_KRESTNI:  # nejdřív „Jméno Příjmení“, pak „Příjmení Jméno“
        t = rx.sub(_krestni, t)
    t = RE_ZPRACOVAL.sub(lambda m: m.group(1) + FO, t)
    t = RE_OSLOVENI.sub(lambda m: f"{m.group(1)} {FO}" if not je_pravnicka(m.group(2)) else m.group(0), t)
    t = RE_FUNKCE.sub(lambda m: (FO + "\n") if not any(w in NE_JMENO for w in m.group(1).split()) else m.group(0), t)
    t = re.sub(rf"\[FO\](?:\s+\[FO\])+", FO, t)
    return t


def nazev(t: str | None, znama_jmena: list[str] | tuple = ()) -> str | None:
    """Název bodu / dokumentu: navíc úseky za čárkou či pomlčkou ve tvaru jména."""
    if not t:
        return t
    t = text(t, znama_jmena)
    casti = re.split(r"(\s*[,–]\s*|\s+-\s+|(?<=[{M}])-(?=[{V}]))".replace("{M}", M).replace("{V}", V), t)
    return "".join(FO if (i % 2 == 0 and vypada_jako_jmeno(c)) else c for i, c in enumerate(casti))


def jmena_z_pseudonymu(puvodni: str, pseudonym: str) -> list[str]:
    """Z dvojice (původní název, název s [FO]) vrátí nahrazené řetězce."""
    if "[FO]" not in pseudonym or not puvodni:
        return []
    vzor = "^" + "(.+?)".join(re.escape(p) for p in pseudonym.split("[FO]")) + "$"
    m = re.match(vzor, puvodni, re.S)
    return [g.strip() for g in m.groups() if g.strip()] if m else []
