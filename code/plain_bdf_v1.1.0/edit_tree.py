#!/usr/bin/env python3
"""nm000238 v1.1.0 text edits (runs inside a Voyager Job, on the clone's work tree).

Usage:
  edit_tree.py core REPO           .bidsignore, README.md, dataset_description.json (Version + GeneratedBy), CHANGES
  edit_tree.py resting REPO VERIFY_TSV
                                   task-restingState_eeg.json + one CHANGES bullet + one README bullet

Every edit is an exact text replacement asserted to match exactly once in the v1.0.0 file; the rest of
each file stays byte-identical. Exits nonzero (and writes nothing) on any mismatch.
"""
import json
import os
import sys

NEW_VERSION = "1.1.0"
DATE = "2026-10-15"


def rd(p):
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


def wr(p, s):
    tmp = p + ".tmp-edit"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(s)
    os.replace(tmp, p)


def rep1(text, old, new, what):
    n = text.count(old)
    if n != 1:
        sys.exit(f"EDIT_FAIL {what}: expected 1 occurrence, found {n}")
    return text.replace(old, new)


def core(repo):
    out = {}
    # .bidsignore: drop the *.bdf.gz rule and its comment line
    p = os.path.join(repo, ".bidsignore")
    t = rd(p)
    t = rep1(t, "# BDF's were gzipped to save space\n*.bdf.gz\n", "", ".bidsignore")
    out[p] = t

    # README.md: sidecar location bullet + the three recording paths
    p = os.path.join(repo, "README.md")
    t = rd(p)
    old = ("  * `/code/task-listeningActive_eeg.json` — full recording-level EEG metadata (SamplingFrequency, "
           "Manufacturer, EEGChannelCount, EEGReference, PowerLineFrequency, ...). Relocated from the dataset root "
           "because the validator does not match the orphan top-level sidecar against the `.bdf.gz` data files.")
    new = ("  * `/task-listeningActive_eeg.json` — full recording-level EEG metadata (SamplingFrequency, "
           "Manufacturer, EEGChannelCount, EEGReference, PowerLineFrequency, ...). Version 1.0.0 kept it under "
           "`/code/` because the EEG was stored as `.bdf.gz`, which the validator does not match against the "
           "sidecar. Since version 1.1.0 the EEG is plain `.bdf` and the sidecar is back at the dataset root, "
           "where BIDS inheritance applies it to every `task-listeningActive` recording.")
    t = rep1(t, old, new, "README sidecar bullet")
    if t.count("_eeg.bdf.gz") != 3:
        sys.exit(f"EDIT_FAIL README: expected 3 '_eeg.bdf.gz' paths, found {t.count('_eeg.bdf.gz')}")
    t = t.replace("_eeg.bdf.gz", "_eeg.bdf")
    if "_eeg.bdf.gz" in t:
        sys.exit("EDIT_FAIL README: '_eeg.bdf.gz' path still present after the edits")
    out[p] = t

    # dataset_description.json: Version + one GeneratedBy entry, text-level (rest byte-identical)
    p = os.path.join(repo, "dataset_description.json")
    t0 = rd(p)
    d0 = json.loads(t0)
    if d0.get("Version") != "1.0.0":
        sys.exit(f"EDIT_FAIL dataset_description: Version is {d0.get('Version')!r}, expected '1.0.0'")
    t = rep1(t0, '  "Version": "1.0.0"', f'  "Version": "{NEW_VERSION}"', "Version")
    gen = {
        "Name": "nm000238 v1.1.0 plain-BDF rebuild",
        "Description": (
            "Decompressed every sub-*/ses-*/eeg/*_eeg.bdf.gz of version 1.0.0 to *_eeg.bdf: the SHA-256 of each "
            ".bdf.gz was checked against its git-annex key, gzip checked CRC32 and length, and every BDF header "
            "was checked (BIOSEMI magic, 24BIT, header size, file size = header + records x samples x 3 bytes). "
            "Signal and header bytes are unchanged. Moved task-listeningActive_eeg.json from /code/ back to the "
            "dataset root and removed *.bdf.gz from .bidsignore. Scripts and the per-file verification table "
            "are in /code/plain_bdf_v1.1.0/."
        ),
        "CodeURL": "https://github.com/nemarDatasets/nm000238/tree/main/code/plain_bdf_v1.1.0",
    }
    ent = json.dumps(gen, indent=2, ensure_ascii=False)
    ent = "\n".join("    " + line for line in ent.splitlines())
    t = rep1(t, '    }\n  ],\n  "SourceDatasets"', "    },\n" + ent + '\n  ],\n  "SourceDatasets"', "GeneratedBy")
    d1 = json.loads(t)
    chk = dict(d0)
    chk["Version"] = NEW_VERSION
    chk["GeneratedBy"] = d0["GeneratedBy"] + [gen]
    if d1 != chk:
        sys.exit("EDIT_FAIL dataset_description: parsed result differs from the intended change")
    out[p] = t

    # CHANGES (new file)
    p = os.path.join(repo, "CHANGES")
    if os.path.exists(p):
        sys.exit("EDIT_FAIL CHANGES already exists")
    out[p] = (
        f"{NEW_VERSION} {DATE}\n"
        "  - EEG recordings are now plain BDF (sub-*/ses-*/eeg/*_eeg.bdf) instead of\n"
        "    gzip-compressed *_eeg.bdf.gz, so BIDS tools, MNE and EEGDash can read\n"
        "    them. Each .bdf is the exact gunzip output of the version 1.0.0 file\n"
        "    (input SHA-256 = git-annex key, gzip CRC32/length and BDF header\n"
        "    checked); no signal or header byte was changed.\n"
        "  - task-listeningActive_eeg.json moved from code/ back to the dataset root\n"
        "    (BIDS inheritance); *.bdf.gz removed from .bidsignore; README paths\n"
        "    updated.\n"
        "  - All other files (behavioural .apr, events, stimulation tables, stimuli,\n"
        "    derivatives, code) are unchanged.\n"
        "1.0.0 2026-04-29\n"
        "  - Initial NEMAR re-host of SparrKULee (KU Leuven RDR, doi:10.48804/K3VSND):\n"
        "    80 of 85 subjects, EEG stored as *_eeg.bdf.gz.\n"
    )
    for p, t in out.items():
        wr(p, t)
    print("EDIT_CORE_OK " + " ".join(sorted(os.path.relpath(p, repo) for p in out)))


def resting(repo, verify_tsv):
    """task-restingState_eeg.json: TaskName from the filename entity, SamplingFrequency from the BDF headers
    (must be one value over all restingState recordings); EEGReference, PowerLineFrequency and SoftwareFilters
    copied verbatim from the authors' task-listeningActive_eeg.json (same BioSemi ActiveTwo set-up and sessions)."""
    rates = set()
    n = 0
    for i, line in enumerate(open(verify_tsv)):
        f = line.rstrip("\n").split("\t")
        if i == 0:
            cols = f
            continue
        r = dict(zip(cols, f))
        if "_task-restingState_" not in r["bdf_path"]:
            continue
        if r["ok"] != "True":
            sys.exit(f"EDIT_FAIL resting: {r['bdf_path']} not verified")
        n += 1
        rates.add(r["eeg_rate_hz"])
    if n == 0:
        sys.exit("EDIT_FAIL resting: no restingState recordings in the verification table")
    if len(rates) != 1 or "|" in next(iter(rates)) or "/" in next(iter(rates)):
        sys.exit(f"EDIT_FAIL resting: EEG rates not a single integer value over {n} files: {sorted(rates)}")
    sf = int(next(iter(rates)))
    la = json.loads(rd(os.path.join(repo, "task-listeningActive_eeg.json")))
    side = {
        "TaskName": "restingState",
        "SamplingFrequency": sf,
        "EEGReference": la["EEGReference"],
        "PowerLineFrequency": la["PowerLineFrequency"],
        "SoftwareFilters": la["SoftwareFilters"],
    }
    p = os.path.join(repo, "task-restingState_eeg.json")
    if os.path.exists(p):
        sys.exit("EDIT_FAIL task-restingState_eeg.json already exists")
    out = {p: json.dumps(side, indent=2, ensure_ascii=False) + "\n"}
    pc = os.path.join(repo, "CHANGES")
    t = rd(pc)
    bullet = (
        "  - Added task-restingState_eeg.json, required by the validator once the\n"
        "    restingState recordings are visible: TaskName from the file names,\n"
        f"    SamplingFrequency ({sf} Hz) from the BDF headers of all {n} restingState\n"
        "    recordings; EEGReference, PowerLineFrequency and SoftwareFilters copied\n"
        "    from the authors' task-listeningActive_eeg.json (same BioSemi ActiveTwo\n"
        "    set-up and sessions).\n"
    )
    out[pc] = rep1(t, "  - All other files (", bullet + "  - All other files (", "CHANGES resting bullet")
    pr = os.path.join(repo, "README.md")
    t = rd(pr)
    anchor = "  * `/code/remarks/`"
    rb = ("  * `/task-restingState_eeg.json` — added in version 1.1.0 (the validator requires it once the "
          "restingState `.bdf` files are visible): TaskName and SamplingFrequency from the BDF headers; "
          "EEGReference, PowerLineFrequency and SoftwareFilters copied from the authors' "
          "`task-listeningActive_eeg.json` (same BioSemi ActiveTwo set-up).\n")
    out[pr] = rep1(t, anchor, rb + anchor, "README resting bullet")
    for p, t in out.items():
        wr(p, t)
    print(f"EDIT_RESTING_OK n_files={n} SamplingFrequency={sf}")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "core":
        core(sys.argv[2])
    elif len(sys.argv) >= 4 and sys.argv[1] == "resting":
        resting(sys.argv[2], sys.argv[3])
    else:
        sys.exit(__doc__)
