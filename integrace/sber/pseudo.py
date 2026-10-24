"""Pseudonymizace fyzických osob v odvozených datech.

Heuristika (není zaručená – výstup před zveřejněním kontroluje člověk):
1. známá jména (např. odvozená z dříve pseudonymizovaného názvu bodu) včetně skloňovaných tvarů,
2. oslovení: pan/paní/panu/manželé … + 1–3 slova s velkým písmenem,
3. akademické tituly (Ing., Mgr., MUDr., …) + jména,
4. řádek se jménem bez titulu před funkcí (starosta, místostarostka, tajemník, vedoucí …),
5. křestní jméno ze slovníku (i skloňované: Pavlem, Janou, Zdeňkovi) + slovo s velkým písmenem, i obráceně,
6. jméno před „bytem“, „nar.“, „r. č.“ (typicky příjemce dotace – fyzická osoba) se nahradí vždy;
   datum narození (i „17. října 1987“) a adresa za „bytem“ se nahradí „…“,
7. dokumenty o volbách (zápis o výsledku voleb, kandidátní listiny): všechna víceslovná jména celoplošně,
8. v názvech: úsek za čárkou/pomlčkou ve tvaru „Příjmení Jméno“ bez právní formy a bez slov instituce.
Ulice (ul., třída, nábřeží, „Tomáše Bati 21, …“), instituce pojmenované po osobě (škola, nadace,
univerzita …) a firmy s právní formou za jménem („Petr Novák s.r.o.“) se nemění.
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

_KONC = r"(?:a|e|i|o|u|y|ou|em|ům|ů|ách|ích|ech|ami|ě|é|í|ský|ská|ské|ského|skému|ském|ským|ní|ního|ním)?"
_INSTITUCE = ("obec|obc|měst|městys|kraj|rad|zastupitelstv|úřad|ministerstv|republik|polici|hasič|centr|muze|"
              "knihovn|divadl|komis|výbor|odbor|fond|agentur|správ|spolek|spolk|svaz|jednot|klub|sdružení|"
              "společenství|církev|církv|farnost|sbor|škol|školk|gymnázi|nemocnic|ústav|nadac|nadač|univerzit|"
              "fakult|institut|akademi|technické služby")
PRAVNI_FORMA = re.compile(
    r"(s\.\s?r\.\s?o|spol\.|a\.\s?s\.|v\.\s?o\.\s?s|k\.\s?s\.|z\.\s?s\.|z\.\s?ú\.|o\.\s?p\.\s?s|"
    r"družstv|(?-i:\bSE\b)|GmbH|Ltd|\bInc\b|s\.p\.|státní podnik|příspěvková organizace|p\.\s?o\.|"
    r"\bZŠ\b|\bMŠ\b|\bSŠ\b|\b(?:" + _INSTITUCE + r")" + _KONC + r"\b)",
    re.I)  # slova institucí jen jako celá slova („Radaně“ ani „Krajíček“ nejsou rada/kraj)
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
    "Hradec", "Králové", "Dvůr", "Labem", "Meziříčí", "Bystřice", "Polanka", "Lhota", "Ústí", "Karolinka",
    "Morava", "Moravy", "Moravu", "Slezsko", "Valašsko", "Valašska", "Škoda", "Grand", "Prix", "Velkou",
    "Dětem", "Domov", "Domova",
}
# kontext před jménem, kdy jde o ulici nebo instituci pojmenovanou po osobě
RE_PRED_ULICE = re.compile(
    r"(?:\bul\.|ulice|ulici|ulicí|třída|třídě|tř\.|nábřeží|náměstí|nám\.|sídliště|park|parku|most|mostu|lávka|"
    r"stadion|stadionu|škola|školy|škole|gymnázium|gymnázia|univerzita|univerzity|univerzitě|fakulta|akademie|nadace|nadaci|"
    r"nadací|nadační|ústav|institut|nemocnice|knihovna|muzeum|domov|centrum|kostel|kaple|pomník|památník|cena|ceny|"
    r"\bsv\.|svatého|svaté|\bZŠ|\bMŠ|\bSOŠ|\bSPŠ|\bSŠ|\bVOŠ|nadační fond)\s*$", re.I)
RE_ADRESA_ZA = re.compile(r"^\s*\d+(?:/\d+)?[a-z]?\s*,")  # „Tomáše Bati 21, Zlín“
RE_VOLBY = re.compile(r"výsledku voleb|kandidátní listin|Volební stran|kandidát|hlasovací líst|zvolen[iíý] členové", re.I)
NE_VOLBY = {"Volební", "Strana", "Kandidáti", "Kandidát", "Počet", "Zápis", "Obec", "Obce", "Město", "Města",
            "Zastupitelstvo", "Zastupitelstva", "Okrsek", "Okrsky", "Hlasy", "Hlasů", "Pořadí", "Celkem", "Seznam",
            "Registrační", "Úřad", "Úřadu", "Komise", "Předseda", "Místopředseda", "Zapisovatel", "Strana", "Hnutí",
            "Sdružení", "Nezávislí", "Nezávislých", "Koalice", "Občanská", "Česká", "Křesťanská", "Komunistická",
            "Svoboda", "Přímá", "Starostové", "Piráti", "Pirátů", "Volby", "Voleb", "Datum", "Platné", "Odevzdané"}

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
Sandra Silvie Sofie Svatava Šimona Tadeáš Tobiáš Valerie Vanesa Vavřinec Vítězslav Vít Zora Zlata Zita Žofie
Albert Alexander Alexej Alfréd Alžbeta Amálie Amelie Anastázie Andrej Anton Antonín Arnošt Augustin Benedikt Benjamin
Bernard Bětka Bohumír Bořek Branislav Bruno Cyril Dalimil Daniel Denis Diana Dita Dobroslav Dorota Edvard Elena Elisa
Elizabeth Elinor Ella Ema Emma Erik Erika Ervín Ester Evelína Evžen Evženie Felix Filoména František Gabriel Gustav
Hedvika Herbert Hubert Hugo Ilja Ingrid Isabela Iveta Ivona Izabela Jáchym Jana Jakub Ján Jindřich Jolana Jonáš
Jonatan Julian Julián Juliana Justýna Karin Karolína Kristián Kristina Kristýna Klaudie Klaudia Laura Lea Leo Leon
Leopold Liliana Lilian Liliana Lívie Lorenzo Lucas Lucián Ľubomír Ľudovít Lumír Luisa Magda Marina Mário Matouš
Matěj Max Maxim Maximilián Melanie Metoděj Mia Michaela Mikuláš Miriam Mojmír Natalie Natalia Naďa Nikol Nikoleta
Norbert Olivie Olivia Oliver Oto Peter Petronela Prokop Rafael Rebeka Robin Rozálie Sára Samuel Sebastián Sebastian
Sergej Silvestr Sofia Stela Šebestián Štefánie Teodor Theodor Timotej Tobias Tomas Tomasz Valentýn Valentina Vasil
Vendelín Viola Vincent Vladan Vojtech Xenie Zbyšek Zikmund Zoe Zoja Adrian Adrián Alan Aleksandr Alex Andrzej Artur
Boris Dmitrij Dennis Eliáš Eric Ewa Fabian Georg George Gregor Henrik Jacob Jacek James Jaroslaw Jessica John Joseph
Julius Kamila Krzysztof Larisa Liam Lukas Marco Marek Maria Mária Mariana Marián Mark Martha Matteo Michal Milo Mykola
Nadia Nathalie Nicole Nina Oksana Olena Olexandr Patrick Paul Pavol Piotr Rostislav Ruslan Sarah Simon Sophie Stefan
Svetlana Taras Thomas Tatiana Valerij Viktoriia Vitalij Volodymyr Wojciech Yuliia Zuzana Ladislava Jozefa Miroslava
Radomil Ludevít Bedřich Kvido Radoš Blahoslav Bohuš Bořislav Břetislav Dobromil Drahoslav Jaromil Kazimír Ladislava
Lubor Luboš Milivoj Miloň Mirek Mstislav Otmar Přemek Radomila Radmila Slavomír Soběslav Spytihněv Svatoslav Věnceslav
Vladimíra Vlastislav Zdislava Zoltán Ľudmila Agáta Alena Anděla Apolena Berta Bohdana Bohuslava Božena Dobromila
Drahuše Eliška Hermína Irma Jindřiška Kamila Ladislava Libuše Lydie Milada Miloslava Otilie Pavlína Romana Růžena
Slavěna Taťána Věroslava Vítězslava Vlasta Zdenka Zbyňka Ingeborg Ruprecht Arnold Leopold Otakar Rudolf Valdemar
Matej Juraj Jozef Ľuboš Ondrej Rastislav Pavol Juraj Dušana Marek Marián Milan Miroslav Mojmír Šimon Štefánia
Anh Minh Thao Thi Ngoc Linh Hoang Huong Tuan Quang Duc Nguyen""".split()


def _kmeny(j: str) -> set[str]:
    k = {j[:-1] if j[-1] in "aeiouyáéíý" else j}
    if j.endswith("el"):
        k.add(j[:-2] + "l")  # Pavel -> Pavla, Pavlem
    if j.endswith("ek"):
        k.add(j[:-2] + "k")  # Marek -> Marka
    if j.endswith("ěk"):
        k.add(j[:-2] + "ňk")  # Zdeněk -> Zdeňka
    return {x for x in k if len(x) >= 3}


KRESTNI_SET = set(KRESTNI)
_KM = sorted({k for j in KRESTNI for k in _kmeny(j)}, key=len, reverse=True)
KRESTNI_RX = rf"(?:{'|'.join(_KM)})[{M}]{{0,4}}"
RE_KRESTNI = (re.compile(rf"\b{KRESTNI_RX}(?:\s+{SLOVO}){{1,2}}\b"), re.compile(rf"\b{SLOVO}\s+{KRESTNI_RX}\b"),
              # ženské příjmení na -ová/-ové/-ovou s dalším slovem s velkým písmenem
              re.compile(rf"\b{SLOVO}\s+[{V}][{M}]+ov(?:á|é|ou)\b"),
              re.compile(rf"\b[{V}][{M}]+ov(?:á|é|ou)\s+{SLOVO}\b"),
              # instrumentál po předložce: „s Radomilem Palou“, „se Zdeňkem Novákem“
              re.compile(rf"(?:(?<=\bs )|(?<=\bse )|(?<=\ba ))[{V}][{M}]+(?:em|ou)\s+[{V}][{M}]+(?:em|ou|ým|í)\b"))

RE_BYTEM = re.compile(rf"\b({SLOVO}(?:\s+{SLOVO}){{1,3}})(?=,?\s*(?:trvale\s+)?(?:bytem|nar\.|narozen|datum narození|r\.\s?č\.))")
# příjemce dotace/daru v dativu: „poskytnutí dotace Ivě Novákové, se sídlem …“ (instituce chrání je_pravnicka)
RE_PRIJEMCE = re.compile(rf"((?:poskytnutí|poskytnout|poskytuje|schvaluje)\s+(?:neinvestiční\s+|investiční\s+|individuální\s+)?"
                         rf"(?:dotace|dotaci|daru|dar|finančního daru|příspěvku|příspěvek|zápůjčky|zápůjčku)\s+)"
                         rf"({SLOVO}(?:\s+{SLOVO}){{1,2}})(?=\s*,)")
RE_FYZ_OSOBA = re.compile(rf"(fyzick\w+\s+osob\w+\s*:?\s*)({SLOVO}(?:\s+{SLOVO}){{1,2}})")

# jméno verzálkami: „VÁCLAV NOVÁK“ / „NOVÁK VÁCLAV“ (jedno slovo = křestní jméno ze slovníku)
RE_VERZALKY = re.compile(rf"\b([{V}]{{2,}})\s+([{V}]{{2,}})(?:\s+([{V}]{{2,}}))?\b")


def _verzalky(m: re.Match) -> str:
    slova = [w for w in m.groups() if w]
    if not any(w.capitalize() in KRESTNI_SET for w in slova[:2]):
        return m.group(0)
    if any(w.capitalize() in NE_JMENO for w in slova) or je_pravnicka(m.group(0)) or _chraneny_kontext(m):
        return m.group(0)
    return FO


TITUL = r"(?:Ing\.\s?arch\.|Ing\.|Mgr\.\s?A\.|Mgr\.|Bc\.\s?A\.|Bc\.|MUDr\.|MDDr\.|MVDr\.|JUDr\.|PhDr\.|RNDr\.|PaedDr\.|PharmDr\.|ThDr\.|ThLic\.|Dr\.|doc\.|prof\.)"
RE_TITUL = re.compile(rf"(?:{TITUL}\s*)+{JMENO}(?:,?\s*(?:Ph\.\s?D\.|CSc\.|MBA|DiS\.|LL\.M\.|MPA|DBA))*")
OSLOVENI = (r"pan|pana|panu|panem|paní|pí\.|manželé|manželů|manželům|manžele|manželi|manž\.|"
            r"žadatel|žadatelka|žadatelce|žadateli|nájemce|nájemci|nájemcem|nájemkyně|nájemkyni|kupující|kupujícímu|"
            r"prodávající|vlastník|vlastníkovi|vlastnice|vlastnici|obdarovaný|obdarované|příjemce|příjemci|příjemkyni")
RE_OSLOVENI = re.compile(rf"\b((?i:{OSLOVENI}))\s+({JMENO}(?:\s+a\s+{JMENO})?)")  # i „Paní Nováková“
# iniciály osoby: „pány R.K (rok nar. 1965)“, „J. N., nar.“
RE_INICIALY = re.compile(rf"(\b(?i:{OSLOVENI}|pány|pánům|pánech|paním)\s+)([{V}]\.\s?[{V}]\.?(?:\s?[{V}]\.?)?)(?![{M}])"
                         rf"|\b([{V}]\.\s?[{V}]\.?)(?=,?\s*\(?(?:rok\s+)?nar)")
# rok/datum narození fyzické osoby se neuvádí (minimalizace): „nar. 1971“, „nar. 17. října 1987“ -> „nar. …“
_MESICE = "ledna|února|března|dubna|května|června|července|srpna|září|října|listopadu|prosince"
RE_NAR = re.compile(rf"((?:rok\s+|dat\.\s*)?(?:nar(?:\.|ozen[aáýé]?)|datum narození:?)\s*(?:dne\s*)?)"
                    rf"(?:\d{{1,2}}\.\s?(?:\d{{1,2}}\.|(?:{_MESICE}))\s?)?\d{{4}}")
# adresa bydliště fyzické osoby se neuvádí: „bytem Na Příkopě 1235, 755 01 Vsetín“ -> „bytem …“
# (ulice s číslem domu, pak nejvýše 3 úseky PSČ / obec; „se sídlem“ právnických osob se nemění)
_OBEC = rf"[{V}][{M}]+(?:\s+(?:pod|nad|u|v)\s+[{V}][{M}]+|-[{V}][{M}]+)?(?![.{M}])"
RE_BYDLISTE = re.compile(
    rf"(\b(?:trvale\s+)?bytem\s+)(?![…░\[])[^,;()\[\]]{{0,40}}?(?:č\.\s?p\.\s?)?\d+(?:/\d+)?[a-zA-Z]?\b"
    rf"(?:\s*,?\s*(?:PSČ:?\s*\d{{3}}\s?\d{{2}}(?:\s+{_OBEC})?|\d{{3}}\s?\d{{2}}(?:\s+{_OBEC})?|{_OBEC})){{0,3}}")
RE_FUNKCE = re.compile(
    rf"(?m)^({JMENO})[ \t]*\n(?=[ \t]*(?:I+\.\s*)?(?:starost|místostarost|tajemn|vedouc|předsed|ředitel|"
    rf"jednatel|referent|zpracoval|člen))")
RE_ZPRACOVAL = re.compile(rf"((?:Zpracoval(?:/a|a)?|Vypracoval(?:/a|a)?|Předkládá|Předkladatel|Vyřizuje|"
                          rf"Kontaktní osoba)\s*:\s*)((?:{TITUL}\s*)*{JMENO}(?:,?\s*(?:Ph\.\s?D\.|DiS\.|MBA))*)")


def je_pravnicka(nazev: str | None) -> bool:
    return bool(nazev and PRAVNI_FORMA.search(nazev))


def vypada_jako_jmeno(s: str) -> bool:
    """„Příjmení Jméno“ (2–3 slova s velkým písmenem), bez právní formy a slov instituce/místa."""
    # název bodu s přilepeným orgánem: „Bedřich Novák I. Rada města Vsetín“
    s = re.sub(r"\s*(?:I+\.\s*)?(?:Rada|Zastupitelstvo) města Vsetín.*$", "", s)
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
    if re.search(r",?\s*(?:\(?rok\s+)?(?:nar\.|narozen|bytem|r\.\s?č\.)", nazev):
        return FO_ARES  # „Jan Novák, nar. 1971“ – vždy fyzická osoba
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


def _chraneny_kontext(m: re.Match) -> bool:
    """Ulice, adresa, instituce pojmenovaná po osobě nebo firma s právní formou za jménem."""
    pred, za = m.string[max(0, m.start() - 40):m.start()], m.string[m.end():m.end() + 40]
    pred = re.sub(rf"(?:{TITUL}\s*)+$", "", pred)  # „ul. MUDr. Františka Sovy“
    if RE_PRED_ULICE.search(pred):
        return True
    # „Tomáše Bati 21, Zlín“ = adresa; ne však „Martin Novák Štěpánská 1822, …“ (nominativ křestního jména)
    if RE_ADRESA_ZA.match(za) and m.group(0).split()[0] not in KRESTNI_SET:
        return True
    usek = re.split(r"[;\n]|\s+a\s+|\s+–\s+", za, maxsplit=1)[0][:30]
    return bool(PRAVNI_FORMA_ZA.search(usek)) if usek.lstrip(" ,").split() and len(usek.split()) <= 4 else False


def _krestni(m: re.Match) -> str:
    s = m.group(0)
    slova = s.split()
    while slova and slova[-1] in NE_JMENO:  # „Jan Novák Vsetín“ -> místo ponechat
        slova.pop()
    if len(slova) < 2 or any(w in NE_JMENO for w in slova) or je_pravnicka(" ".join(slova)) or _chraneny_kontext(m):
        return s
    return FO + s[len(" ".join(slova)):] if s.startswith(" ".join(slova)) else FO


def _titul(m: re.Match) -> str:
    return m.group(0) if _chraneny_kontext(m) else FO


def _bytem(m: re.Match) -> str:
    slova = m.group(1).split()
    while slova and (slova[0] in NE_JMENO or je_pravnicka(slova[0])):
        slova.pop(0)
    if len(slova) < 2:
        return m.group(0)
    return m.group(0)[:len(m.group(0)) - len(" ".join(slova))] + FO


def _volby(t: str) -> str:
    """Dokument o volbách: každá dvojice/trojice slov s velkým písmenem = jméno (kromě slov NE_VOLBY/NE_JMENO)."""
    def r(m):
        slova = m.group(0).split()
        if any(w in NE_VOLBY or w in NE_JMENO for w in slova) or je_pravnicka(m.group(0)):
            return m.group(0)
        return FO
    return re.sub(rf"\b(?:{TITUL}\s*)*{SLOVO}(?:\s+{SLOVO}){{1,2}}\b", r, t)


def text(t: str | None, znama_jmena: list[str] | tuple = ()) -> str | None:
    if not t:
        return t
    for jm in znama_jmena:
        for kmen in _tvary(jm):
            t = re.sub(rf"\b{re.escape(kmen)}[{M}]{{0,4}}\b", FO, t)
    t = RE_TITUL.sub(_titul, t)
    t = RE_BYTEM.sub(_bytem, t)
    t = RE_FYZ_OSOBA.sub(lambda m: m.group(1) + FO, t)
    t = RE_INICIALY.sub(lambda m: (m.group(1) + FO) if m.group(1) else FO, t)
    t = RE_NAR.sub(lambda m: m.group(1) + "…", t)
    t = RE_BYDLISTE.sub(lambda m: m.group(1) + "…", t)
    t = RE_PRIJEMCE.sub(lambda m: m.group(0) if je_pravnicka(m.group(2)) or any(
        w in NE_JMENO for w in m.group(2).split()) else m.group(1) + FO, t)
    if RE_VOLBY.search(t):
        t = _volby(t)
    t = RE_VERZALKY.sub(_verzalky, t)
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
    def nahrad(c):
        konec = re.search(r"\s*(?:I+\.\s*)?(?:Rada|Zastupitelstvo) města Vsetín.*$", c)
        return FO + (konec.group(0) if konec else "")
    return "".join(nahrad(c) if (i % 2 == 0 and vypada_jako_jmeno(c)) else c for i, c in enumerate(casti))


def jmena_z_pseudonymu(puvodni: str, pseudonym: str) -> list[str]:
    """Z dvojice (původní název, název s [FO]) vrátí nahrazené řetězce."""
    if "[FO]" not in pseudonym or not puvodni:
        return []
    vzor = "^" + "(.+?)".join(re.escape(p) for p in pseudonym.split("[FO]")) + "$"
    m = re.match(vzor, puvodni, re.S)
    return [g.strip() for g in m.groups() if g.strip()] if m else []


def info_dokumentu(t: str | None) -> str | None:
    """Popisek souboru „Oznámení …, Příjmení Jméno [PDF, 316 kB]Odbor …“: část před „[“ jako název."""
    if not t:
        return t
    m = re.match(r"^(.*?)(\s*\[.*)$", t, re.S)
    return nazev(m.group(1)) + text(m.group(2)) if m else nazev(t)
