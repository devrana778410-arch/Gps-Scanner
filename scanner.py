import urllib.parse
import subprocess
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

PORT = 8080
scanned_data = []

class ScanHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        # Intercept the webhook from Binary Eye
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if 'data' in query:
            raw_data = query['data'][0]

            # Invisible Data Processing: Replace first hyphen with a tab
            processed_data = raw_data.replace('-', '\t', 1)
            scanned_data.append(processed_data)

            # Print a quick confirmation for the CLI view so you know it worked
            print(f"✅ Logged: {processed_data.replace('\t', '  [TAB]  ')}")

        # Tell Binary Eye the data was received
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"OK")

    # Suppress messy web server logs
    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    print(f"--- Termux Zero-Touch Scanner ---")
    print(f"Listening on http://127.0.0.1:{PORT}/?data=%s")
    print(f"Scan your boxes. Press Ctrl+C when finished to get your copyable block.\n")

    # Utilizing ThreadingHTTPServer for concurrent, rapid-fire webhook processing
    with ThreadingHTTPServer(("127.0.0.1", PORT), ScanHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            # When you hit Ctrl+C, format and print the final clean block
            print("\n" * 2)
            print("=" * 40)
            print(" READY TO COPY ".center(40, "="))
            print("=" * 40 + "\n")

            # --- DEDUPLICATION LOGIC ---
            # Remove duplicates while preserving the original scan order
            unique_data = list(dict.fromkeys(scanned_data))
            final_block = "\n".join(unique_data)

            # Calculate how many duplicates were filtered out for the log
            duplicates_removed = len(scanned_data) - len(unique_data)

            print(final_block)

            print("\n" + "=" * 40)
            if duplicates_removed > 0:
                print(f"🧹 Cleaned up: Removed {duplicates_removed} duplicate scan(s).")

            # Zero-Touch Export: Attempts to push straight to Android Clipboard
            try:
                subprocess.run(['termux-clipboard-set'], input=final_block.encode('utf-8'), check=True, stderr=subprocess.DEVNULL)

                # Triggers a native Android popup to confirm the batch is ready
                subprocess.run(['termux-toast', '-b', 'green', '-c', 'white', '📋 Scans Copied to Clipboard!'], check=True, stderr=subprocess.DEVNULL)

                print("📋 Automatically copied unique scans to your Android clipboard!")
            except FileNotFoundError:
                print("💡 Tip: Install 'termux-api' to auto-copy this directly to your clipboard next time.")

