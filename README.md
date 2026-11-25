# 📱 Android Zero-Touch Edge Scanner

An offline, zero-latency barcode and QR code scanning pipeline built natively for Android (Termux + Binary Eye).

This architecture bridges physical optical sensors (Binary Eye) to a local, sandboxed Linux userland (Termux) via a loopback network (`127.0.0.1:8080`). It aggregates rapid-fire continuous scans, pairs barcodes for multi-barcode devices, filters noise, deduplicates entries, and pushes a clean, tab-separated block (`IMEI [TAB] ICCID`) directly to your Android clipboard ready for Google Sheets or Excel.

---

## ✨ Features

* **Multi-Device Support:**
  * **Combined QR Devices (e.g., Traxsmart):** Automatically extracts the 15-digit IMEI and 19/20-digit ICCID from a single QR code scan.
  * **Multi-Barcode Devices (e.g., GPS Bull):** Automatically pairs individual IMEI and ICCID barcodes in any scan order.
* **Smart Noise Filtering:** Automatically discards useless website QR links (e.g. `https://www.gpsbull.com/`) and proprietary UID/serial barcodes.
* **Live Web UI Dashboard (`http://127.0.0.1:8080`):** Real-time browser status view over Server-Sent Events (SSE) while Binary Eye remains your fast hardware camera. Inspect buffered scans, undo mistaken pairs with **Undo Last**, or clear stray half-scans with **Discard Buffer**.
* **Haptic Feedback:** Vibrates subtly on scan and provides a distinct buzz when a device pair is completed.
* **Zero Latency:** Processes scans instantly over loopback (`127.0.0.1`), fully offline without cloud dependencies.
* **Continuous Scanning:** Leverages Binary Eye's continuous autofocus to scan non-stop.
* **Auto-Deduplication:** Removes duplicate scans while preserving original scanning order.
* **One-Tap Export:** Pushes clean TSV data straight to Android Clipboard via Termux API on finish.

---

## 📦 Prerequisites

Install the following open-source applications (recommended via **F-Droid**):

1. **[Termux](https://f-droid.org/en/packages/com.termux/)** — Terminal emulator environment.
2. **[Termux:API](https://f-droid.org/en/packages/com.termux.api/)** — Bridges terminal commands to device clipboard and vibrations.
3. **[Termux:Widget](https://f-droid.org/en/packages/com.termux.widget/)** — Home screen widget launcher.
4. **[Binary Eye](https://f-droid.org/en/packages/de.markusfisch.android.binaryeye/)** — Camera barcode scanner frontend.

---

## ⚙️ Binary Eye Configuration

Open **Binary Eye** -> **Settings**:
1. Enable **Continuous scanning**.
2. Under **Actions** / **Custom URL / Webhook**, configure:
   ```text
   http://127.0.0.1:8080/?data=%s
   ```
3. Set action to trigger automatically on scan.

### Live Dashboard (Optional Safety Net)
While scanning with Binary Eye, you can open Chrome on the same phone to **`http://127.0.0.1:8080`** to view the live buffer and committed pairs:
* **Yellow buffer:** Waiting for the second barcode (IMEI or ICCID).
* **Green flash / ready:** Pair completed (or returned to buffer via Undo).
* **Discard Buffer:** Clear a stray half-scan (or tap `×` on an individual field).
* **Undo Last:** Pop the most recent committed pair back into the buffer to fix a mismatch.

---

## 🚀 Install or Update (Inside Termux)

Run this **one-liner** in Termux to install on a new phone or update an existing phone in ~2 seconds:

```bash
curl -fsSL https://raw.githubusercontent.com/devrana778410-arch/Gps-Scanner/main/install.sh | bash
```

Once installed, future updates are even simpler:
* **1-Tap Home Screen Widget:** Tap **`Update_Scanner.sh`** via Termux:Widget.
* **1-Word Command:** Run `update-scanner` anywhere in Termux.

Or clone the repo directly:
```bash
pkg install git python termux-api -y
git clone https://github.com/devrana778410-arch/Gps-Scanner.git ~/Gps-Scanner
python ~/Gps-Scanner/scanner.py
```

---

## 📋 Output Format

When you finish scanning by pressing `Ctrl + C` in Termux, the script formats your data into standard TSV:

```text
866334071999821	8991102606622830118
864000080679280	89914909100030283911
```

* **Column 1:** IMEI (15 digits)
* **Column 2:** ICCID (19-20 digits)

Directly copy-pasted into Google Sheets or Microsoft Excel!
