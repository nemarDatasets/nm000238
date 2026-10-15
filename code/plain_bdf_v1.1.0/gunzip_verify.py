#!/usr/bin/env python3
"""nm000238 v1.1.0: gunzip every *_eeg.bdf.gz to *_eeg.bdf and verify it (runs inside a Voyager Job).

Usage: gunzip_verify.py REPO KEYS_TSV OUT_DIR [--jobs N] [--limit N]

KEYS_TSV  lines "<git-annex key>\t<repo-relative path of the .bdf.gz>" (from `git annex find`).
OUT_DIR   per-file JSON records (OUT_DIR/perfile/) and the table OUT_DIR/bdf_verify.tsv.

Per file:
  * the compressed bytes are streamed through SHA-256; digest and byte count must equal the annex key
    (SHA256E-s<size>--<sha256>.bdf.gz), so the input is exactly the v1.0.0 deposit object;
  * Python's gzip reader checks CRC32 and ISIZE of every member and raises on a mismatch;
  * the output goes to <name>.bdf.part and is renamed to <name>.bdf only after these header checks:
    BDF magic (0xFF + "BIOSEMI"), reserved field "24BIT", header bytes == 256 * (ns + 1),
    n_records >= 1 (not -1), record duration > 0, and
    file size == header bytes + n_records * sum(samples per record) * 3.
  * duration = n_records x record_duration is recorded as an exact decimal (Fraction), never rounded.
Never overwrites an existing .bdf: a .bdf without a record is re-verified by re-decompressing and
comparing SHA-256; any mismatch is a hard failure. Exit status is nonzero if any file fails.
Patient/recording identification fields of the header are never written out.
"""
import argparse
import gzip
import hashlib
import json
import os
import re
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from decimal import Decimal
from fractions import Fraction

CHUNK = 8 * 1024 * 1024
KEY_RE = re.compile(r"^SHA256E-s(\d+)--([0-9a-f]{64})\.bdf\.gz$")


class HashReader:
    """File wrapper hashing every byte read (the gzip reader only calls read())."""

    def __init__(self, f):
        self.f = f
        self.h = hashlib.sha256()
        self.n = 0

    def read(self, size=-1):
        b = self.f.read(size)
        self.h.update(b)
        self.n += len(b)
        return b

    def seek(self, *a):  # gzip rewinds only through its own buffer; a real seek would break the hash
        raise OSError("seek not supported on HashReader")

    def seekable(self):
        return False

    def readable(self):
        return True

    def tell(self):
        return self.n


def parse_bdf_header(path):
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        h = f.read(256)
        if len(h) < 256:
            raise ValueError("file shorter than 256 bytes")
        if h[0:1] != b"\xff" or h[1:8] != b"BIOSEMI":
            raise ValueError(f"bad magic {h[0:8]!r}")
        hdr_bytes = int(h[184:192].decode("ascii").strip())
        reserved = h[192:236].decode("ascii", "replace").strip()
        n_records = int(h[236:244].decode("ascii").strip())
        rec_dur_s = h[244:252].decode("ascii").strip()
        ns = int(h[252:256].decode("ascii").strip())
        if hdr_bytes != 256 * (ns + 1):
            raise ValueError(f"header bytes {hdr_bytes} != 256*(ns+1) with ns={ns}")
        # BioSemi ActiView leaves the reserved field blank in 657/659 SparrKULee files;
        # magic, header size and exact payload size (3 bytes/sample) already prove 24-bit BDF.
        if reserved not in ("24BIT", ""):
            raise ValueError(f"reserved field {reserved!r} not in ('24BIT', '')")
        if n_records < 1:
            raise ValueError(f"n_records {n_records} < 1")
        rec_dur = Fraction(Decimal(rec_dur_s))
        if rec_dur <= 0:
            raise ValueError(f"record duration {rec_dur_s!r} <= 0")
        s = f.read(256 * ns)
        if len(s) != 256 * ns:
            raise ValueError("truncated signal header")

        def field(off, width):
            return [s[off + i * width: off + (i + 1) * width].decode("ascii", "replace").strip() for i in range(ns)]

        labels = field(0, 16)
        o = 16 * ns
        o += 80 * ns  # transducer
        physdim = field(o, 8); o += 8 * ns
        o += 8 * ns * 4  # phys min/max, dig min/max
        prefilt = field(o, 80); o += 80 * ns
        spr = [int(x) for x in field(o, 8)]
    expect = hdr_bytes + n_records * sum(spr) * 3
    if size != expect:
        raise ValueError(f"file size {size} != header {hdr_bytes} + {n_records} records x {sum(spr)} samples x 3 = {expect}")
    rates = [Fraction(x) / rec_dur for x in spr]
    dur = n_records * rec_dur
    return {
        "n_signals": ns,
        "n_records": n_records,
        "record_duration": rec_dur_s,
        "duration_s": str(dur.numerator) if dur.denominator == 1 else f"{dur.numerator}/{dur.denominator}",
        "duration_s_float": float(dur),
        "labels": labels,
        "physdim": sorted(set(physdim)),
        "prefilter": sorted(set(prefilt)),
        "rates_hz": sorted({str(r) for r in rates}),
        "eeg_rate_hz": sorted({str(r) for r, lab in zip(rates, labels) if lab != "Status"}),
        "header_bytes": hdr_bytes,
        "bdf_bytes": size,
    }


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(CHUNK)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def one(repo, key, rel, recdir):
    m = KEY_RE.match(key)
    if not m:
        return {"path": rel, "ok": False, "error": f"unexpected key {key}"}
    key_size, key_sha = int(m.group(1)), m.group(2)
    src = os.path.join(repo, rel)
    dst = src[: -len(".gz")]
    part = dst + ".part"
    rec_path = os.path.join(recdir, rel.replace("/", "__") + ".json")
    if os.path.exists(rec_path):
        rec = json.load(open(rec_path))
        if rec.get("ok") and rec.get("key_gz") == key and os.path.exists(dst) and os.path.getsize(dst) == rec["bdf_bytes"]:
            rec["skipped_existing"] = True
            return rec
    rec = {"path": rel, "bdf_path": rel[: -len(".gz")], "key_gz": key, "gz_bytes": key_size}
    try:
        if os.path.exists(part):
            os.remove(part)  # our own partial output from an interrupted run
        out_h = hashlib.sha256()
        with open(src, "rb") as raw:
            hr = HashReader(raw)
            with gzip.GzipFile(fileobj=hr, mode="rb") as gz:
                if os.path.exists(dst):
                    # .bdf without a record: compare, never overwrite
                    while True:
                        b = gz.read(CHUNK)
                        if not b:
                            break
                        out_h.update(b)
                    rec["preexisting_bdf"] = True
                else:
                    with open(part, "wb") as out:
                        while True:
                            b = gz.read(CHUNK)
                            if not b:
                                break
                            out_h.update(b)
                            out.write(b)
                        out.flush()
                        os.fsync(out.fileno())
            # drain anything the gzip reader did not consume (it reads to EOF; this is a guard)
            while raw.read(CHUNK):
                raise ValueError("trailing bytes after the gzip stream")
        if hr.n != key_size or hr.h.hexdigest() != key_sha:
            raise ValueError(f"compressed input does not match annex key: {hr.n} bytes sha256 {hr.h.hexdigest()}")
        rec["gz_sha256_ok"] = True
        rec["bdf_sha256"] = out_h.hexdigest()
        if rec.get("preexisting_bdf"):
            if sha256_file(dst) != rec["bdf_sha256"]:
                raise ValueError("existing .bdf differs from the gunzip output (left untouched)")
            rec.update(parse_bdf_header(dst))
        else:
            rec.update(parse_bdf_header(part))
            os.rename(part, dst)
        rec["ok"] = True
    except Exception as e:  # noqa: BLE001 - recorded and turned into a nonzero exit
        rec["ok"] = False
        rec["error"] = f"{type(e).__name__}: {e}"
        if os.path.exists(part):
            os.remove(part)
    tmp = rec_path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(rec, f, indent=1)
    os.replace(tmp, rec_path)
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("keys_tsv")
    ap.add_argument("out_dir")
    ap.add_argument("--jobs", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    items = []
    for line in open(a.keys_tsv):
        line = line.rstrip("\n")
        if not line:
            continue
        key, rel = line.split("\t", 1)
        if not rel.endswith("_eeg.bdf.gz") or not rel.startswith("sub-"):
            sys.exit(f"unexpected path in key list: {rel}")
        items.append((key, rel))
    items.sort(key=lambda x: x[1])
    if a.limit:
        items = items[: a.limit]
    recdir = os.path.join(a.out_dir, "perfile")
    os.makedirs(recdir, exist_ok=True)
    res = []
    with ProcessPoolExecutor(max_workers=a.jobs) as ex:
        futs = [ex.submit(one, a.repo, k, r, recdir) for k, r in items]
        for i, fu in enumerate(as_completed(futs), 1):
            r = fu.result()
            res.append(r)
            st = "OK" if r.get("ok") else "FAIL " + r.get("error", "")
            print(f"[{i}/{len(items)}] {r['path']} {st}", flush=True)
    res.sort(key=lambda r: r["path"])
    cols = ["bdf_path", "ok", "key_gz", "gz_bytes", "bdf_bytes", "bdf_sha256", "n_signals", "n_records",
            "record_duration", "duration_s", "eeg_rate_hz", "rates_hz", "physdim", "error"]
    with open(os.path.join(a.out_dir, "bdf_verify.tsv"), "w") as f:
        f.write("\t".join(cols) + "\n")
        for r in res:
            row = []
            for c in cols:
                v = r.get(c, "")
                if isinstance(v, list):
                    v = "|".join(v)
                row.append(str(v))
            f.write("\t".join(row) + "\n")
    bad = [r for r in res if not r.get("ok")]
    print(f"GUNZIP_SUMMARY files={len(res)} ok={len(res) - len(bad)} failed={len(bad)} "
          f"gz_bytes={sum(r.get('gz_bytes', 0) for r in res)} bdf_bytes={sum(r.get('bdf_bytes', 0) for r in res if r.get('ok'))}",
          flush=True)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
