[![DOI](https://img.shields.io/badge/DOI-10.82901%2Fnemar.nm000238-blue)](https://doi.org/10.82901/nemar.nm000238)

=============================================================
IMPORTANT — RESTRICTED SUBJECTS EXCLUDED FROM NEMAR RE-HOST
=============================================================

IMPORTANT — 5 of the 85 original subjects (sub-019, sub-020, sub-021, sub-022, sub-026) are EXCLUDED from this NEMAR re-host because their raw EEG files are access-restricted on the KU Leuven Dataverse (HTTP 403 on download without a data-use agreement). Researchers who need these subjects should email sparrkulee@kuleuven.be to request access and download the data directly from https://rdr.kuleuven.be/dataset.xhtml?persistentId=doi:10.48804/K3VSND (DOI 10.48804/K3VSND). The re-host therefore contains 80 of the original 85 subjects, covering all 11 session types (shortstories01, varyingStories01..10).

Excluded subjects: sub-019, sub-020, sub-021, sub-022, sub-026

Cohort demographics
-------------------

Cohort demographics (from Accou et al., Data 2024, 9, 94, Section 2.1): 85 original participants, 74 female / 11 male, aged 21.4 ± 1.9 years (mean ± SD), inclusion window 18-30 years, all normal-hearing (≤30 dB HL, 125-8000 Hz), native Dutch/Flemish speakers. Per-subject numeric ages are not published by the SparrKULee authors for privacy reasons; `participants.tsv` only ships 3-year binned ages in the `age_range` column (see `participants.json` for details).

How to cite
-----------

Please cite the original SparrKULee data descriptor when using this dataset: Accou, B., Bollens, L., Gillis, M., Verheijen, W., Van hamme, H., & Francart, T. (2024). SparrKULee: A Speech-Evoked Auditory Response Repository from KU Leuven, Containing the EEG of 85 Participants. Data, 9(8), 94. https://doi.org/10.3390/data9080094

Where extra metadata lives (after NEMAR preparation)
----------------------------------------------------

  * `/code/task-listeningActive_eeg.json` — full recording-level EEG metadata (SamplingFrequency, Manufacturer, EEGChannelCount, EEGReference, PowerLineFrequency, ...). Relocated from the dataset root because the validator does not match the orphan top-level sidecar against the `.bdf.gz` data files.
  * `/code/remarks/` — per-session free-form recording notes (`.txt` and `.docx`) originally placed under `sub-XX/ses-YY/remarks/`. Relocated so the validator does not see an arbitrary `remarks/` folder inside BIDS session directories.
  * `/code/convert_accou2023.py` — the exact script that was run to produce this NEMAR re-host.

-------------------------------------------------------------

README
======

__SparrKULee__: A Speech-evoked Auditory Response Repository of the KU Leuven, containing EEG of 85 participants

Overview
--------

An overview of the dataset including details about the filetypes, methods and technical validation can be found in [our
paper]()


Notes
-----

Code to download, preprocess and validate the data can be found at https://github.com/exporl/auditory-eeg-dataset.

Due to mistakes during recording, following recordings do not have an adequate number of triggers and can therefore not be accurately aligned with the stimulus:

1. sub-006/ses-shortstories01/eeg/sub-006_ses-shortstories01_task-listeningActive_run-06_eeg.bdf.gz
2. sub-017/ses-shortstories01/eeg/sub-017_ses-shortstories01_task-listeningActive_run-03_eeg.bdf.gz
3. sub-048/ses-varyingStories05/eeg/sub-048_ses-varyingStories05_task-listeningActive_run-04_eeg.bdf.gz
