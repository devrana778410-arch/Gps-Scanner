import re
import urllib.parse
import subprocess
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

PORT = 8080

def haptic_feedback(duration_ms=60):
    """Triggers subtle haptic feedback on Android via Termux API if available."""
    try:
        subprocess.run(['termux-vibrate', '-d', str(duration_ms)], stderr=subprocess.DEVNULL, timeout=0.5)
    except Exception:
        pass

def is_url(text: str) -> bool:
    """Checks if text is a web link (e.g., GPS Bull website QR code)."""
    t = text.strip().lower()
    return bool(re.search(r'^(?:https?://|www\.)', t) or re.search(r'\.(?:com|in|org|net|io|gov)/?', t))

def is_iccid(text: str) -> bool:
    """Checks if text is a SIM ICCID (19-20 digits starting with 89)."""
    clean = re.sub(r'^(?:ICCID[:\s-]*)', '', text.strip(), flags=re.IGNORECASE)
    return bool(re.fullmatch(r'89\d{17,18}', clean))

def get_iccid(text: str) -> str:
    clean = re.sub(r'^(?:ICCID[:\s-]*)', '', text.strip(), flags=re.IGNORECASE)
    m = re.search(r'\b(89\d{17,18})\b', clean)
    return m.group(1) if m else clean

def is_imei(text: str) -> bool:
    """Checks if text is a cellular IMEI (15 digits, not UID)."""
    clean = re.sub(r'^(?:IMEI[:\s-]*)', '', text.strip(), flags=re.IGNORECASE)
    if re.fullmatch(r'\d{15}', clean):
        # Exclude 15-digit proprietary UID serials (such as 2609...)
        if clean.startswith('26'):
            return False
        return True
    return False

def get_imei(text: str) -> str:
    clean = re.sub(r'^(?:IMEI[:\s-]*)', '', text.strip(), flags=re.IGNORECASE)
    m = re.search(r'\b(\d{15})\b', clean)
    return m.group(1) if m else clean

def is_uid(text: str) -> bool:
    """Checks if text is a device UID / Serial barcode."""
    clean = text.strip()
    if re.search(r'^UID[:\s-]*', clean, re.IGNORECASE):
        return True
    if re.fullmatch(r'26\d{13}', clean):
        return True
    return False

def parse_scan(raw: str):
    """
    Parses incoming raw scan data into categorized token:
    Returns (type, value)
    """
    raw = raw.strip()
    if not raw:
        return ("IGNORE", "")

    # 1. Ignore web URLs (e.g. https://www.gpsbull.com/)
    if is_url(raw):
        return ("URL_IGNORE", raw)

    # 2. Check for combined QR codes (e.g. Traxsmart: IMEI-ICCID)
    imei_match = re.search(r'\b(\d{15})\b', raw)
    iccid_match = re.search(r'\b(89\d{17,18})\b', raw)
    if imei_match and iccid_match and imei_match.group(1) != iccid_match.group(1):
        found_imei = imei_match.group(1)
        found_iccid = iccid_match.group(1)
        if found_imei not in found_iccid and not found_imei.startswith('26'):
            return ("COMBINED_PAIR", (found_imei, found_iccid))

    # Fallback for hyphen-separated scans
    if '-' in raw:
        parts = [p.strip() for p in raw.split('-') if p.strip()]
        if len(parts) >= 2:
            p0, p1 = parts[0], parts[1]
            if is_imei(p0) and is_iccid(p1):
                return ("COMBINED_PAIR", (get_imei(p0), get_iccid(p1)))
            elif is_iccid(p0) and is_imei(p1):
                return ("COMBINED_PAIR", (get_imei(p1), get_iccid(p0)))

    # 3. UID barcode
    if is_uid(raw):
        return ("UID_IGNORE", raw)

    # 4. ICCID barcode (19 or 20 digits starting with 89)
    if is_iccid(raw):
        return ("ICCID", get_iccid(raw))

    # 5. IMEI barcode (15 digits)
    if is_imei(raw):
        return ("IMEI", get_imei(raw))

    return ("UNKNOWN", raw)

class DeviceAggregator:
    def __init__(self):
        self.lock = threading.Lock()
        self.buffer_imei = None
        self.buffer_iccid = None
        self.scanned_pairs = []

    def process(self, raw_data: str):
        with self.lock:
            res_type, val = parse_scan(raw_data)

            if res_type in ("IGNORE", "URL_IGNORE"):
                print(f"⚠️  Ignored web link: {val}")
                return

            if res_type == "UID_IGNORE":
                print(f"⚠️  Ignored UID: {val}")
                return

            if res_type == "UNKNOWN":
                print(f"❓ Unrecognized scan: {val}")
                return

            if res_type == "COMBINED_PAIR":
                imei, iccid = val
                pair = f"{imei}\t{iccid}"
                self.scanned_pairs.append(pair)
                haptic_feedback(150)
                print(f"✅ Logged [Combined QR]: {imei}  [TAB]  {iccid}  (Total: {len(self.scanned_pairs)})")
                return

            if res_type == "IMEI":
                imei = val
                if self.buffer_iccid is not None:
                    # Pair completed!
                    pair = f"{imei}\t{self.buffer_iccid}"
                    self.scanned_pairs.append(pair)
                    haptic_feedback(180)
                    print(f"✅ Logged Pair [Device #{len(self.scanned_pairs)}]: {imei}  [TAB]  {self.buffer_iccid}")
                    self.buffer_imei = None
                    self.buffer_iccid = None
                elif self.buffer_imei == imei:
                    # Duplicate rapid continuous scan
                    pass
                elif self.buffer_imei is not None:
                    self.buffer_imei = imei
                    haptic_feedback(50)
                    print(f"🔄 Updated IMEI to: {imei} (Waiting for ICCID...)")
                else:
                    self.buffer_imei = imei
                    haptic_feedback(50)
                    print(f"⏳ [1/2] Buffered IMEI: {imei} (Waiting for ICCID...)")

            elif res_type == "ICCID":
                iccid = val
                if self.buffer_imei is not None:
                    # Pair completed!
                    pair = f"{self.buffer_imei}\t{iccid}"
                    self.scanned_pairs.append(pair)
                    haptic_feedback(180)
                    print(f"✅ Logged Pair [Device #{len(self.scanned_pairs)}]: {self.buffer_imei}  [TAB]  {iccid}")
                    self.buffer_imei = None
                    self.buffer_iccid = None
                elif self.buffer_iccid == iccid:
                    # Duplicate rapid continuous scan
                    pass
                elif self.buffer_iccid is not None:
                    self.buffer_iccid = iccid
                    haptic_feedback(50)
                    print(f"🔄 Updated ICCID to: {iccid} (Waiting for IMEI...)")
                else:
                    self.buffer_iccid = iccid
                    haptic_feedback(50)
                    print(f"⏳ [1/2] Buffered ICCID: {iccid} (Waiting for IMEI...)")

aggregator = DeviceAggregator()

class ScanHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # Intercept the webhook from Binary Eye
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if 'data' in query:
            raw_data = query['data'][0]
            aggregator.process(raw_data)

        # Acknowledge receipt to Binary Eye
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, format, *args):
        # Suppress standard HTTP access logs
        pass

if __name__ == "__main__":
    print("=" * 50)
    print("--- Termux Zero-Touch GPS Scanner ---".center(50))
    print("=" * 50)
    print(f"Listening on http://127.0.0.1:{PORT}/?data=%s\n")
    print("Device Support:")
    print("  • Combined QR (Traxsmart): Auto-extracts IMEI & ICCID")
    print("  • Multi-Barcode (GPS Bull): Pairs IMEI & ICCID in any order")
    print("  • Filters: Automatically ignores web URLs and UID barcodes")
    print("  • Output Format: IMEI [TAB] ICCID\n")
    print("Scan your devices. Press Ctrl+C when finished.\n")

    ThreadingHTTPServer.allow_reuse_address = True
    with ThreadingHTTPServer(("127.0.0.1", PORT), ScanHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n" * 2)
            print("=" * 45)
            print(" READY TO COPY ".center(45, "="))
            print("=" * 45 + "\n")

            with aggregator.lock:
                if aggregator.buffer_imei or aggregator.buffer_iccid:
                    incomplete = aggregator.buffer_imei or aggregator.buffer_iccid
                    print(f"⚠️ Warning: 1 incomplete scan was discarded ({incomplete} had no matching pair).\n")

                # Deduplicate while preserving scan order
                unique_data = list(dict.fromkeys(aggregator.scanned_pairs))
                duplicates_removed = len(aggregator.scanned_pairs) - len(unique_data)

            final_block = "\n".join(unique_data)
            print(final_block)

            print("\n" + "=" * 45)
            if duplicates_removed > 0:
                print(f"🧹 Cleaned up: Removed {duplicates_removed} duplicate pair(s).")
            print(f"📊 Total unique devices captured: {len(unique_data)}")

            # Export to Android Clipboard
            try:
                subprocess.run(['termux-clipboard-set'], input=final_block.encode('utf-8'), check=True, stderr=subprocess.DEVNULL)
                subprocess.run(['termux-toast', '-b', 'green', '-c', 'white', f'📋 {len(unique_data)} Devices Copied to Clipboard!'], check=True, stderr=subprocess.DEVNULL)
                print("📋 Automatically copied unique scans to your Android clipboard!")
            except FileNotFoundError:
                print("💡 Tip: Install 'termux-api' to auto-copy directly to your clipboard.")
