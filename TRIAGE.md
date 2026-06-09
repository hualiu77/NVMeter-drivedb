# Triage guide

How to turn an incoming `bridge-data` issue — especially the auto-generated
`from-app` ones from NVMeter — into a merged YAML PR.

## The TL;DR workflow

```
issue arrives    →    extract USB IDs from ioreg    →
draft YAML       →    open PR    →    close issue with link to PR
```

About 3 minutes for a clean `from-app` report. Slower for hand-written
issues that need follow-up questions.

## Step-by-step

### 1 · Identify the bridge chip

`from-app` reports include an ioreg dump with every USB device on the
sender's host. Scan it for the one that matches the reported `BSD path`
context. Look for:

- **`USB Product Name`** — usually contains the chip family
  (`RTL9210B-CG`, `JMS583`, `ASM2362`, `Elements 25A3`, ...). This becomes
  your YAML `bridge:` description.
- **`idVendor` + `idProduct`** — convert from decimal to 4-digit hex.
  `idVendor = 3034` → `0x0bda`. Concatenate as `vendor:product`
  (lowercase, colon-separated, no `0x`): `0bda:9210`.

If multiple USB-storage devices are listed and the report doesn't make
it obvious which one is the subject, look for the highest UsbLinkSpeed
(NVMe enclosures are typically USB 3.x = 5–10 Gbps).

### 2 · Decide which `smartctl_args` to record

Read the smartctl probe transcript at the bottom of the report:

- **Some `-d` flag returned a real model+serial** → that's the working
  flag. Record it as `smartctl_args: ["-d", "..."]`.
- **All flags errored with `Not a device of type 'scsi'`** → macOS-blocked
  bridge. Record `smartctl_args: []` and document in notes that the chip
  is recognized on Linux but the macOS SCSI stack refuses pass-through.
- **All flags errored with `Unknown device type`** → smartmontools doesn't
  know this bridge yet. Probably worth filing upstream at smartmontools
  too. For our purposes, `smartctl_args: []` with notes.

### 3 · Pick a filename

`bridges/<vendor>-<chip>.yaml`, kebab-case, lowercase, ASCII-only:
- `bridges/realtek-rtl9210b.yaml`
- `bridges/jmicron-jms583.yaml`
- `bridges/wd-elements-25a3.yaml`

If the chip already has an entry in `bridges/imported/` (the
auto-imported pile), the hand-written top-level entry **wins** at runtime.
You can either:
- Keep both (top-level overrides; imported stays as history), or
- Delete the imported one and consolidate.

Top-level entries always carry `verified_by: ["@reporter-handle"]`.

### 4 · Validate locally

```bash
python3 scripts/validate.py
```

CI runs the same check on every PR. Failures are usually:
- USB ID format wrong (need lowercase 4-hex-digit colon hex)
- Duplicate USB ID with another entry (intentional — fix or de-dupe)

### 5 · Open the PR + close the issue

```bash
git checkout -b add-<chip-name>
git add bridges/<file>.yaml
git commit -m "Add <chip name> (issue #N)"
gh pr create --fill
```

Then on the issue: `Closes via #<PR>` and tag with `merged`.

## Common chips & their flags

A cheat sheet so you don't have to look up the same thing twice:

| Chip family | Linux `-d` flag | Common products |
|---|---|---|
| JMicron JMS56x | `-d sat` | Sabrent EC-NVME, many cheap NVMe enclosures |
| JMicron JMS578/583 | `-d sat` | Orico M2PVC, Acasis NVMe |
| ASMedia ASM235CM | `-d sat` | Many SATA enclosures |
| ASMedia ASM2362/2364 | `-d sntasmedia` | Premium NVMe (OWC Envoy Pro, etc.) |
| Realtek RTL9210 (B/-CG) | `-d sntrealtek` | Aliexpress generics, ORICO, OWC Express 4M2 |
| WD/Elements internal | (blocked on macOS) | All WD My Passport / Elements line |
| Apple Fabric (internal) | (uses NVMe driver directly) | Built-in Apple SSDs |

Note: on **macOS** all `-d snt*` flags fail with "Not a device of type
'scsi'" because Apple doesn't expose SCSI generic to userspace. They
DO work on Linux. Record the Linux-working flag anyway; future NVMeter
versions may consume this when a macOS kext or workaround appears.

## Spam / noise

`from-app` issues are signed by the act of running NVMeter, but malicious
data is still possible. Sanity checks before merging:

- The reported BSD path matches `/dev/disk\d+` (not `/dev/null` etc.)
- USB IDs are real hex, not all zeros or `ffff:ffff`
- The ioreg block looks like genuine ioreg output (Apple-formatted)

Decline anything that looks fabricated; the project lead can ban
spammers via GitHub's normal block mechanism.
