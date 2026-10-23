"""Čtení vybraných členů vzdáleného ZIP přes HTTP Range (bez stažení celého archivu).

Ověřeno na MONITOR extraktech (nginx podporuje Range): pro roční FIN 2-12 M stačí ~4 MB místo ~24 MB.
Podporuje metody stored (0) a deflate (8); ZIP64 neřeší (extrakty < 4 GB).
"""
from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass


@dataclass
class Member:
    name: str
    method: int
    csize: int
    usize: int
    offset: int


def list_members(http, url: str, size: int, tail: int = 65536) -> list[Member]:
    start = max(0, size - tail)
    buf = http.get_range(url, start, size - 1)
    e = buf.rfind(b"PK\x05\x06")
    if e < 0:
        raise ValueError("EOCD nenalezen – zvětšit tail")
    n, cd_size, cd_off = struct.unpack("<HII", buf[e + 10:e + 20])
    if cd_off < start:  # adresář je delší než tail
        buf = http.get_range(url, cd_off, size - 1)
        start = cd_off
    p = cd_off - start
    out = []
    for _ in range(n):
        if buf[p:p + 4] != b"PK\x01\x02":
            raise ValueError("poškozený central directory")
        method, = struct.unpack("<H", buf[p + 10:p + 12])
        csize, usize = struct.unpack("<II", buf[p + 20:p + 28])
        fl, xl, cl = struct.unpack("<HHH", buf[p + 28:p + 34])
        off, = struct.unpack("<I", buf[p + 42:p + 46])
        name = buf[p + 46:p + 46 + fl].decode("utf-8", "replace")
        out.append(Member(name, method, csize, usize, off))
        p += 46 + fl + xl + cl
    return out


def read_member(http, url: str, m: Member) -> bytes:
    head = http.get_range(url, m.offset, m.offset + 29)
    fl, xl = struct.unpack("<HH", head[26:30])
    data_start = m.offset + 30 + fl + xl
    raw = http.get_range(url, data_start, data_start + m.csize - 1)
    if m.method == 0:
        return raw
    if m.method == 8:
        return zlib.decompress(raw, -15)
    raise ValueError(f"nepodporovaná komprese {m.method}")


def read_members_local(path: str, predicate) -> dict[str, bytes]:
    import zipfile
    with zipfile.ZipFile(path) as z:
        return {n: z.read(n) for n in z.namelist() if predicate(n)}
