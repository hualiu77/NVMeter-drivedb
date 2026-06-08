# Contributing to NVMeter-drivedb

Thanks for helping grow the database!

## TL;DR

- **No CLA required.** All contributions are released under [CC0 1.0](LICENSE) (public domain).
- One enclosure / bridge chip = one YAML file under `bridges/`.
- CI validates schema + duplicate USB IDs on every PR.
- Merging is fast — accuracy matters more than process.

## Why no CLA?

This repository is **pure data**: USB IDs, smartctl invocation arguments, and
human-readable notes. We do not consider these copyrightable expression, and we
explicitly release everything to the public domain so the data can flow back
into smartmontools' upstream `drivedb.h`, Linux's `udev` rules, competing
tools, or anywhere else it is useful. There is nothing to license.

The companion application repository ([NVMeter](https://github.com/hualiu77/NVMeter))
does require a CLA, because it contains copyrightable code and we maintain an
open-core commercial path. That CLA does **not** apply here.

## I have a new enclosure to add

### Step 1 — Get the USB IDs

```bash
ioreg -r -c IOUSBHostDevice -d 1 | grep -E '"(USB Product Name|idVendor|idProduct)" =' | grep -B 2 "<your-enclosure-name>"
```

Convert decimal `idVendor` and `idProduct` to 4-digit lowercase hex
(`printf '%04x' 4184` → `1058`).

### Step 2 — Probe smartctl

```bash
diskutil list external
# Note the /dev/diskN of your enclosure, then:

for args in "" "-d sat" "-d sat,16" "-d sat,12" "-d jmb39x,0" \
            "-d usbjmicron" "-d usbsunplus" "-d usbcypress" "-d usbprolific"; do
    echo "=== smartctl $args -i /dev/diskN ===" 
    smartctl $args -i /dev/diskN 2>&1 | head -8
done
```

Whichever combination prints a real Model / Serial works. **Often nothing
works on macOS** — that's fine, document it (see "macOS blocked" below).

### Step 3 — Write the YAML

Copy [`bridges/wero-tbt5-1m2-dock.yaml`](bridges/wero-tbt5-1m2-dock.yaml) as
a template. Filename: short, kebab-case, descriptive.

```yaml
bridge: "Vendor Chip-name (Marketing description)"
vendor: "ChipMaker Inc."
usb_ids:
  - "1058:25a3"
smartctl_args: ["-d", "sat,16"]
verified_by:
  - "@your-github-handle"
notes: |
  Optional context: enclosure brand/model where this chip ships, firmware
  quirks, known caveats, the OS where you tested, etc.
```

### Step 4 — Open a PR

CI runs `scripts/validate.py` to check schema + USB-ID uniqueness. If green,
a maintainer merges within a couple of days.

## Special cases

### "macOS blocks SAT pass-through entirely" entries

Many USB-SATA enclosures cannot speak SMART on macOS at all, because macOS
ships no equivalent of Linux's `sd_mod` SAT translation for arbitrary USB
bridges. We still want these documented — both to save the next user the
probe-loop, and so we can detect "known macOS-blocked device" in the app and
show a friendly message rather than an error.

Format:

```yaml
bridge: "Western Digital internal bridge (Elements 25A3 family)"
vendor: "Western Digital"
usb_ids: ["1058:25a3"]
smartctl_args: []       # nothing works on macOS
verified_by: ["@your-handle"]
notes: |
  macOS: smartctl returns "Operation not supported by device" for all -d
  variants. Verified on macOS 14+/Apple Silicon. SMART is reportedly
  readable on Linux with the kernel `sd_mod` SAT layer — Linux probe data
  welcome.
```

### Thunderbolt-native enclosures

Thunderbolt enclosures expose NVMe via PCIe directly — no quirk is needed
and `smartctl_args` should be `[]`. Keep an entry anyway so the catalog is
useful for shopping recommendations and so the app can identify the device.

### One chip in many enclosures

A single chip ID often ships in dozens of enclosures (Orico, Sabrent,
Yottamaster, Vantec, ...). Use one YAML file per **chip**, list all known
enclosure brands in `notes:`, and put **every** observed USB ID in
`usb_ids:`. Don't create separate files per enclosure-brand.

## I don't know how to write YAML

Open an [issue](https://github.com/hualiu77/NVMeter-drivedb/issues/new/choose)
using the **"New enclosure data"** template and paste your probe outputs.
Someone else will convert it to YAML and credit you in `verified_by`.

## Style

- USB IDs are **lowercase hex**, four digits each, separated by `:` —
  `1058:25a3`, not `1058:25A3` or `4184:9635`.
- One YAML file per chip; filename matches the chip slug.
- Keep `notes:` factual. Save opinions for issues / discussions.
- Don't list `verified_by` handles you haven't been authorized to add.
