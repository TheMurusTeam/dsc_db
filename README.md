# DSC ships and coast stations list

A list of ship and coast stations for DSC (Digital Selective Calling)
decoders: each line gives the MMSI of a station with its name, and where
known its call sign and type, so a decoder can show who is calling.

Made for the DSC receiver of the OpenX6100 firmware for the Xiegu X6100,
usable by any program.

**For listening only.** This list is not for navigation, nor for distress
and safety watchkeeping. It may be incomplete, out of date or wrong.

## Files

- `lista.csv`: the list, UTF-8, one station per line:

  ```
  mmsi,ship_name,call_sign,ship_type,source
  230123456,FINNLADY,OJKA,Cargo,Fintraffic Digitraffic (CC BY 4.0)
  ```

  - `mmsi`: 9 digits: ship stations (first digit 2 to 7) and coast
    stations (00 and the country's MID).
  - `ship_name`: upper case, at most 56 characters.
  - `call_sign`: empty if unknown.
  - `ship_type`: from the AIS ship type code where the source gives it
    (Cargo, Tanker, Passenger, Fishing, Tug, ...), "Coast station" for a
    coast station, empty if unknown.
  - `source`: where the line comes from (see below).

- `add_ships.py`: the tool that builds the list from the sources below.
- `make_ships_db.py`: turns the list into `ships.bin`, the compact file read
  by the OpenX6100 DSC receiver (format described in the script).
- `extra_stations.csv`: stations added by hand, each with its source.
- `LICENSE`: the GNU Lesser General Public License 2.1 (the tools).
- `COPYING-GPL-3.0`: the GNU General Public License 3 (the list).

## Where the data comes from

Every line comes from one of these sources, named in its `source` column.
A station found in several sources is taken from the first one used and
never changed by the later ones.

| `source` | Source | Licence | Stations |
|---|---|---|---|
| `FCC ULS` | U.S. Federal Communications Commission, Universal Licensing System, ship station licences (records SH: call sign, ship name, MMSI), weekly complete file `l_ship.zip` from https://data.fcc.gov/download/pub/uls/complete/ | U.S. Government Works (https://www.usa.gov/government-works), as listed on https://catalog.data.gov/dataset/fcc-universal-licensing-system-uls | 150,223 |
| `Wikidata (CC0)` | Wikidata, items with an MMSI (property P587) and an English label, https://www.wikidata.org | CC0 1.0 (https://creativecommons.org/publicdomain/zero/1.0/) | 35,672 |
| `Fintraffic Digitraffic (CC BY 4.0)` | Fintraffic Digitraffic, vessel metadata of the AIS received in Finland, https://meri.digitraffic.fi/api/ais/v1/vessels | CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/) | 936 |
| `DEMA Denmark AIS` | Danish Emergency Management Agency (DEMA), historical AIS data of the Danish AIS system, daily files from http://aisdata.ais.dk/: only the static fields MMSI, vessel name, call sign and ship type; pleasure craft, sailing vessels and Class B craft of unknown type left out | Free to use, see "The Danish data" below | (to be filled in) |
| `ITU (via SDRangel)` | The ITU list of coast stations (https://www.itu.int/mmsapp/coaststation/list), as included since 2024 in the DSC decoder of SDRangel: `plugins/channelrx/demoddsc/coaststations.cpp` of https://github.com/f4exb/sdrangel | ITU data, see "The coast stations" below | 676 |
| `FCC ULS` (coast) | FCC ULS coast station licences (`l_coast.zip`): KSM and SailMail, in `extra_stations.csv` | U.S. Government Works | 2 |
| `NOAA AIS` | NOAA Office for Coastal Management and BOEM, MarineCadastre.gov, Nationwide Automatic Identification System, 562 daily files from 2020 to 2026 (`ais-YYYY-MM-DD.csv.zst` from https://noaaocm.blob.core.windows.net/ais/csv2/): only the static fields MMSI, vessel name, call sign and vessel type | U.S. Government work, see "The NOAA data" below | 72,769 |

Counts as of 11 November 2026: 260,278 stations.

### Attribution

The Digitraffic lines are used under CC BY 4.0, which asks for this credit:

> Source: Fintraffic / digitraffic.fi, license CC 4.0 BY

Fintraffic provides its data as is, without warranty. Lines from it keep
their `source` column, which marks them in the list.

The FCC lines contain U.S. Government material, identified by their
`source` column.

### The NOAA data

What NOAA says, in its AIS FAQ (https://coast.noaa.gov/data/marinecadastre/ais/faq.pdf):

- "The historical data are generally considered public domain."
- "Yes, you may release derived products built from these data."
- Recipients "shall not charge a fee for its usage."
- Works using U.S. Government material "must provide notice with such
  work(s) identifying the U.S. Government material incorporated."

On data.gov the dataset's licence reads: "No license information was
provided. If this work was prepared by an officer or employee of the United
States government as part of that person's official duties it is
considered a U.S. Government Work."

Our reading: "generally considered public domain" means public domain
except where a use is specifically not authorized. This list takes only
four static fields per vessel (no position, time or track), it is a derived
product, and it is free of charge. 

Suggested citation: NOAA Office for Coastal Management. (2026). Nationwide
Automatic Identification System 2026. Marine Cadastre. https://marinecadastre.gov.
The NOAA lines are marked by their `source` column.

### The Danish data

DEMA confirmed to us in writing (11 November 2026) that it does not
interfere with what the data is used for, and that it may be cited as:

> Historical AIS data taken from the Danish AIS system under the Danish
> Emergency Management Agency.

Their terms (https://www.brs.dk/da/om-os/organisation/sikre-farvande/ais-data/):
DEMA does not guarantee the accuracy of the AIS data and is not liable for
any damage from its use; the recipient must process the data in accordance
with applicable legislation; and the data may not be combined with other
data in a way that creates personally identifiable information. For this
reason only four static fields per vessel are kept, with no positions,
times or tracks, and pleasure craft, sailing vessels and Class B craft of
unknown type are left out.

### The coast stations

The names of the coast stations are ITU data: SDRangel's `coaststations.cpp`
says "From https://www.itu.int/mmsapp/coaststation/list". The ITU publishes
that list free to consult, and SDRangel (Copyright (C) 2024 Jon Beniston,
M7RCE, GPL-3.0-or-later for its code) has distributed it since 2024; they
are taken here from SDRangel. We have asked the ITU to confirm that they may
be used this way and will report their answer here.

## Licence

The tools (`add_ships.py`, `make_ships_db.py`) are released under the GNU
Lesser General Public License, version 2.1 or later (`LICENSE`), Copyright
(C) 2026 Hany El Imam.

The list (`lista.csv`, and `ships.bin` built from it) is released under the
GNU General Public License, version 3 or later (`COPYING-GPL-3.0`),
Copyright (C) 2026 Hany El Imam for the selection, merging, cleaning and
format. It is a data file: a program that reads it is not bound by its
licence.

The data keeps the terms of its source: the coast stations are ITU data (see
"The coast stations");
the DEMA lines with the credit above; the Digitraffic lines CC BY 4.0, with the credit above wherever the list is
redistributed; the Wikidata lines CC0; the FCC and NOAA lines U.S.
Government material (see "The NOAA data" for NOAA's own words).

## Removal on request

If anyone with a real claim on any part of this data asks for it to be
removed, it will be removed. Write to info@murus.it.

## How to rebuild it

`add_ships.py` adds to the list the stations of one source that are not in it
yet, and writes the source of each one:

```
python3 add_ships.py lista.csv digitraffic                 # downloads it
python3 add_ships.py lista.csv fcc l_ship.zip
python3 add_ships.py lista.csv wikidata wikidata.csv
python3 add_ships.py lista.csv sdrangel                    # downloads it
python3 add_ships.py lista.csv extra extra_stations.csv
python3 add_ships.py lista.csv noaa-net 2020-01-01 2026-06-30 3   # a day in 3
python3 add_ships.py lista.csv dma-net 2024-03-01 2026-06-30 7    # a day a week
```

`noaa-net` and `dma-net` read each day straight from the NOAA and DEMA
servers, nothing is written to disk; the days done are kept in
`lista.csv.noaa-days` and `lista.csv.dma-days`, so they go on from there
when run again. DEMA has daily files from March 2024; the older months come
as one large file each and are left out.

`wikidata.csv` is the result, downloaded as CSV, of this query on
https://query.wikidata.org:

```
SELECT ?mmsi ?name WHERE {
  ?ship wdt:P587 ?mmsi .
  ?ship rdfs:label ?name . FILTER(LANG(?name) = "en")
}
```

For the OpenX6100 DSC receiver:

```
python3 make_ships_db.py lista.csv ships.bin
```

and `ships.bin` goes on the SD card in `/mnt/dsc/`.
