#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
# Copyright (C) 2026 Hany El Imam
"""
Adds to a DSC ships list (CSV) the ships of an open data source that are
not in it yet.  The ships already in the list are never changed: run the
sources you trust most first.

  python3 add_ships.py LIST.csv noaa        AIS_2025_06_30.csv[.zst]
  python3 add_ships.py LIST.csv noaa-net    2026-01-01 2026-06-30 [every N days, 7]
  python3 add_ships.py LIST.csv fcc         l_ship.zip | folder with SH.dat, HD.dat
  python3 add_ships.py LIST.csv digitraffic [vessels.json]     (no file: download it)
  python3 add_ships.py LIST.csv wikidata    query.csv
  python3 add_ships.py LIST.csv sdrangel    [coaststations.cpp]  (no file: download it)
  python3 add_ships.py LIST.csv extra       my_stations.csv

LIST.csv: mmsi,ship_name,call_sign,ship_type,source  (created if missing).
Every added ship gets its source in the "source" column, so the list can
always say where each line comes from.  The list is rewritten sorted by
MMSI; the previous one is kept as LIST.csv.bak.

The sources (check their terms again before you publish):

  noaa         NOAA / BOEM MarineCadastre, Nationwide AIS, one CSV per day
               https://marinecadastre.gov/ais/  (U.S. Government work; terms
               to be confirmed, see their AIS FAQ)
  noaa-net     the same, read straight from NOAA's server, one day every N
               from the first date to the last, nothing written to disk:
               https://noaaocm.blob.core.windows.net/ais/csv2/csvYYYY/
               ais-YYYY-MM-DD.csv.zst.  The days done are written in
               LIST.csv.noaa-days: run it again and it goes on from there.
  fcc          FCC ULS, ship station licences (SH records: call sign, ship
               name, MMSI), weekly complete file of the ship services
               https://www.fcc.gov/uls/transactions/daily-weekly
               (data.gov: "U.S. Government Works")
  digitraffic  Fintraffic Digitraffic, vessel metadata of the AIS seen in
               Finland, https://meri.digitraffic.fi/api/ais/v1/vessels
               Licence CC BY 4.0, credit: "Source: Fintraffic /
               digitraffic.fi, license CC 4.0 BY".  The API gives the
               vessels seen lately: run it now and then to collect more.
  wikidata     Wikidata, items with an MMSI (P587), CC0.  Run this query
               on https://query.wikidata.org and download the result as CSV:

                 SELECT ?mmsi ?name WHERE {
                   ?ship wdt:P587 ?mmsi .
                   ?ship rdfs:label ?name . FILTER(LANG(?name) = "en")
                 }

  sdrangel     the ITU coast station list (MMSI 00xxxxxxx and name), as
               included in SDRangel's DSC decoder: plugins/channelrx/
               demoddsc/coaststations.cpp of https://github.com/f4exb/sdrangel
               ("From https://www.itu.int/mmsapp/coaststation/list").
               Type "Coast station".
  extra        a CSV of your own, same columns as LIST.csv (mmsi,
               ship_name, call_sign, ship_type, source): ships or coast
               stations, each with its own source.

A .zst file is read with Python 3.14 or the "zstandard" package
(pip3 install zstandard); otherwise decompress it first with unzstd.
"""

import csv
import datetime
import gzip
import io
import json
import os
import sys
import urllib.request
import zipfile

HEADER = ["mmsi", "ship_name", "call_sign", "ship_type", "source"]
SOURCES = {
    "noaa": "NOAA AIS",
    "noaa-net": "NOAA AIS",
    "fcc": "FCC ULS",
    "digitraffic": "Fintraffic Digitraffic (CC BY 4.0)",
    "wikidata": "Wikidata (CC0)",
    "sdrangel": "ITU (via SDRangel)",
    "extra": None,                    # the file's own source column
}
SDRANGEL_URL = ("https://raw.githubusercontent.com/f4exb/sdrangel/master/"
                "plugins/channelrx/demoddsc/coaststations.cpp")

# AIS ship type codes, with the words of the usual DSC lists
_FIXED = {30: "Fishing", 31: "Towing", 32: "Towing(long)", 33: "Dredging", 34: "Diving",
          35: "Military", 36: "Sailing", 37: "Pleasure", 50: "Pilot", 51: "SAR", 52: "Tug",
          53: "Port Tender", 54: "Anti Pollution", 55: "Law Enforcement", 56: "Local Type",
          57: "Local Type", 58: "Medical Transport", 59: "Not Conflict"}
_RANGES = ((20, 29, "WIG"), (40, 49, "HSC"), (60, 69, "Passenger"), (70, 79, "Cargo"),
           (80, 89, "Tanker"), (90, 99, "Other"), (1, 19, "Reserved"))


def ais_type(code):
    try:
        c = int(float(code))
    except (TypeError, ValueError):
        return ""
    if c in _FIXED:
        return _FIXED[c]
    for lo, hi, name in _RANGES:
        if lo <= c <= hi:
            return name
    return ""


def clean(s, n):
    s = " ".join(str(s or "").replace(",", " ").split()).upper()
    return s[:n]


def ship_mmsi(m):
    """a ship station: 9 digits, MID first (2..7)"""
    m = str(m or "").strip()
    return m if len(m) == 9 and m.isdigit() and m[0] in "234567" else None


def station_mmsi(m):
    """a ship or a coast station (00 + MID)"""
    m = str(m or "").strip()
    return m if len(m) == 9 and m.isdigit() and (m[0] in "234567" or m[:2] == "00") else None


def good_name(name):
    return bool(name) and name not in ("UNKNOWN", "NONE", "NO NAME", "N/A", "TEST")


# ---- readers: each yields (mmsi, name, call sign, type) ---------------------------

def open_text(path):
    if path.endswith(".zst"):
        try:
            from compression import zstd             # Python 3.14
            raw = zstd.open(path, "rb")
        except ImportError:
            try:
                import zstandard
                raw = zstandard.ZstdDecompressor().stream_reader(open(path, "rb"))
            except ImportError:
                sys.exit("Cannot read .zst here: run  unzstd %s  and give the .csv" % path)
        return io.TextIOWrapper(raw, encoding="utf-8", errors="replace", newline="")
    if path.endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8", errors="replace", newline="")
    return open(path, newline="", encoding="utf-8", errors="replace")


def _zstd_stream(raw):
    try:
        from compression import zstd             # Python 3.14
        return zstd.ZstdFile(raw, "rb")
    except ImportError:
        try:
            import zstandard
            return zstandard.ZstdDecompressor().stream_reader(raw)
        except ImportError:
            sys.exit("Reading .zst needs Python 3.14 or: pip3 install zstandard")


def read_noaa_url(url):
    """one NOAA day, downloaded and decompressed as it arrives: nothing on disk"""
    req = urllib.request.Request(url, headers={"User-Agent": "x6100-dsc-shiplist"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        with io.TextIOWrapper(_zstd_stream(resp), encoding="utf-8", errors="replace",
                              newline="") as f:
            for row in csv.reader(f):
                if len(row) >= 11 and row[0].isdigit():
                    yield row[0], row[7], row[9], ais_type(row[10])


def read_noaa(path):
    """MMSI,BaseDateTime,LON,LAT,SOG,COG,Heading,VesselName,IMO,CallSign,VesselType,..."""
    with open_text(path) as f:
        for row in csv.reader(f):
            if len(row) >= 11 and row[0].isdigit():
                yield row[0], row[7], row[9], ais_type(row[10])


def _uls_lines(path, name):
    """the lines of SH.dat / HD.dat, from a ULS zip or a folder"""
    if os.path.isdir(path):
        p = os.path.join(path, name)
        if not os.path.exists(p):
            return
        with open(p, encoding="latin-1", newline="") as f:
            for line in f:
                yield line.rstrip("\r\n").split("|")
    else:
        with zipfile.ZipFile(path) as z:
            if name not in z.namelist():
                return
            with z.open(name) as raw:
                for line in io.TextIOWrapper(raw, encoding="latin-1", newline=""):
                    yield line.rstrip("\r\n").split("|")


def read_fcc(path):
    """SH: 2 unique id, 5 call sign, 10 ship name, 22 MMSI; HD: 2 unique id, 6 status"""
    status = {}
    for r in _uls_lines(path, "HD.dat"):
        if len(r) > 5 and r[0] == "HD":
            status[r[1]] = r[5]
    found = 0
    ships = []
    for r in _uls_lines(path, "SH.dat"):
        if len(r) > 21 and r[0] == "SH":
            found += 1
            # active licences first, so they win over expired ones for the same MMSI
            ships.append((0 if status.get(r[1]) == "A" else 1, r[21], r[9], r[4]))
    if not found:
        sys.exit("No SH.dat ship records in %s" % path)
    for _, m, name, call in sorted(ships, key=lambda s: s[0]):
        yield m, name, call, ""


def read_digitraffic(path):
    if path:
        with open_text(path) as f:
            data = json.load(f)
    else:
        url = "https://meri.digitraffic.fi/api/ais/v1/vessels"
        req = urllib.request.Request(url, headers={"Accept-Encoding": "gzip",
                                                   "Digitraffic-User": "x6100-dsc-shiplist"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
        data = json.loads(body)
        with open("digitraffic_vessels.json", "wb") as f:      # what was used, kept
            f.write(json.dumps(data).encode())
    for v in data if isinstance(data, list) else data.get("features", []):
        v = v.get("properties", v)
        yield str(v.get("mmsi", "")), v.get("name"), v.get("callSign"), ais_type(v.get("shipType"))


def read_wikidata(path):
    with open_text(path) as f:
        for row in csv.DictReader(f):
            yield row.get("mmsi"), row.get("name"), "", ""


def read_sdrangel(path):
    """{"003311000", "AASIAAT RADIO"}, ...; for an MMSI listed twice the last name,
    as SDRangel's own map keeps it"""
    import re
    if path:
        with open(path, "rb") as f:
            raw = f.read()
    else:
        req = urllib.request.Request(SDRANGEL_URL, headers={"User-Agent": "x6100-dsc-shiplist"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    names = {}
    for m, n in re.findall(r'\{"(\d{9})",\s*"((?:[^"\\]|\\.)*)"\}', text):
        names[m] = n
    if not names:
        sys.exit("No coast stations found in " + (path or SDRANGEL_URL))
    for m, n in names.items():
        yield m, n, "", "Coast station"


def read_extra(path):
    with open_text(path) as f:
        for row in csv.DictReader(f):
            yield (row.get("mmsi"), row.get("ship_name"), row.get("call_sign"),
                   row.get("ship_type"), row.get("source"))


READERS = {"noaa": read_noaa, "noaa-net": None, "fcc": read_fcc, "digitraffic": read_digitraffic,
           "wikidata": read_wikidata, "sdrangel": read_sdrangel, "extra": read_extra}


# ---- the list -------------------------------------------------------------------

def load_list(path):
    if not os.path.exists(path):
        return [], HEADER
    with open(path, newline="", encoding="utf-8") as f:
        r = csv.reader(f)
        header = next(r, HEADER)
        rows = [row for row in r if row]
    if len(header) < 5:                                   # an old list without "source"
        header = HEADER
        rows = [row + [""] * (5 - len(row)) for row in rows]
    return rows, header


def save_list(path, rows, header):
    rows.sort(key=lambda r: r[0])
    if os.path.exists(path):
        os.replace(path, path + ".bak")
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    os.replace(tmp, path)


def add_from(rows, known, records, source, coast=False):
    """adds the stations of records missing from the list; returns (read, added).
    A record may carry its own source as a fifth field (extra)."""
    new = {}                                              # mmsi -> [name, call, type, source]
    read = 0
    for rec in records:
        m, name, call, typ = rec[:4]
        src = (rec[4] if len(rec) > 4 and rec[4] else None) or source
        read += 1
        m = station_mmsi(m) if coast else ship_mmsi(m)
        if not m or m in known:
            continue
        name = clean(name, 56)
        if not good_name(name):
            continue
        call = clean(call, 11)
        old = new.get(m)
        if old is None:
            new[m] = [name, call, typ or "", src]
        else:                                             # fill what was missing
            if not old[1] and call:
                old[1] = call
            if not old[2] and typ:
                old[2] = typ
    for m, (name, call, typ, src) in new.items():
        rows.append([m, name, call, typ, src])
        known.add(m)
    return read, len(new)


def noaa_net(lst, rows, header, known, first, last, step):
    done_path = lst + ".noaa-days"
    done = set()
    if os.path.exists(done_path):
        with open(done_path) as f:
            done = {l.strip() for l in f if l.strip()}
    d = datetime.date.fromisoformat(first)
    end = datetime.date.fromisoformat(last)
    days = []
    while d <= end:
        days.append(d.isoformat())
        d += datetime.timedelta(days=step)
    todo = [x for x in days if x not in done]
    print("NOAA: %d days from %s to %s every %d, %d already done, %d to do."
          % (len(days), first, last, step, len(days) - len(todo), len(todo)))
    for day in todo:
        url = ("https://noaaocm.blob.core.windows.net/ais/csv2/csv%s/ais-%s.csv.zst"
               % (day[:4], day))
        before = len(rows)
        try:
            read, added = add_from(rows, known, read_noaa_url(url), SOURCES["noaa-net"])
        except Exception as e:                            # a missing day, a network error
            print("%s: skipped (%s)" % (day, e))
            continue
        save_list(lst, rows, header)                      # after every day: safe to stop
        with open(done_path, "a") as f:
            f.write(day + "\n")
        print("%s: %d positions, %d new ships. List: %d -> %d ships."
              % (day, read, added, before, len(rows)), flush=True)


def main():
    if len(sys.argv) < 3 or sys.argv[2] not in READERS:
        sys.exit(__doc__)
    lst, kind = sys.argv[1], sys.argv[2]
    rows, header = load_list(lst)
    known = {r[0] for r in rows}

    if kind == "noaa-net":
        if len(sys.argv) < 5:
            sys.exit("usage: python3 add_ships.py LIST.csv noaa-net FIRST LAST [every N days]")
        step = int(sys.argv[5]) if len(sys.argv) > 5 else 7
        noaa_net(lst, rows, header, known, sys.argv[3], sys.argv[4], step)
        return

    src = sys.argv[3] if len(sys.argv) > 3 else None
    if src is None and kind not in ("digitraffic", "sdrangel"):
        sys.exit("give the %s file" % kind)
    before = len(rows)
    read, added = add_from(rows, known, READERS[kind](src), SOURCES[kind] or "",
                           coast=kind in ("sdrangel", "extra"))
    save_list(lst, rows, header)
    print("%s (%s): %d records read, %d new stations added. List: %d -> %d stations."
          % (kind, os.path.basename(src) if src else "download", read, added, before, len(rows)))


if __name__ == "__main__":
    main()
