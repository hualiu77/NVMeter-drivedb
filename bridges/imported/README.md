# Imported bridges

YAML files in this directory were **automatically generated** from
smartmontools' upstream [`drivedb.h`](https://github.com/smartmontools/smartmontools/blob/main/src/drivedb.h)
by [`scripts/import-smartmontools.py`](../../scripts/import-smartmontools.py).
They cover ~120 USB-SATA / USB-NVMe bridge chip variants that Linux
smartmontools knows about.

**They are NOT yet verified on macOS.** Most USB-SATA bridges are
silently blocked by macOS's user-space SCSI stack regardless of the
`-d` flag (see the project README for the technical background), so a
non-trivial fraction of these entries will simply not work. That's
fine — knowing "this chip is recognised but blocked" is itself useful
metadata.

## How to upgrade an entry from "imported" to "verified"

1. Plug in the matching enclosure.
2. Run the `smartctl_args` from the YAML against the device:
   ```bash
   smartctl <smartctl_args> -i /dev/diskN
   ```
3. If it returns a real model name + serial: success. Edit the YAML —
   move `verified_by: []` → `verified_by: ["@your-handle"]`, add a
   note about your test environment, and move the file out of
   `imported/` into the top-level `bridges/` so future re-imports
   don't overwrite your manual work.
4. Open a PR.

## Re-running the importer

A fresh `drivedb.h` ships in every smartmontools release. To pick up
new bridge entries:

```bash
brew upgrade smartmontools     # or otherwise update smartmontools
python3 scripts/import-smartmontools.py \
    --source /opt/homebrew/Cellar/smartmontools/<latest>/share/smartmontools/drivedb.h \
    --out bridges/imported/
python3 scripts/validate.py
```

The importer is idempotent at the file level — re-running with a newer
source rewrites every file based on the latest drivedb. Files moved
out of `imported/` to the top-level `bridges/` directory are NOT touched.

## Legal note

USB vendor/product IDs and `smartctl` command-line flags are facts;
they are not copyrightable expression. The output of this importer is
released into the public domain alongside the rest of the repository
(see `LICENSE`). smartmontools is GPL-2.0 source code; no GPL'd code
is copied, only the underlying data is extracted and re-expressed.
The `bridge:` description in each file credits the chip vendor where
the original drivedb.h supplied it.
