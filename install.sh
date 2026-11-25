#!/bin/bash
set -e

REPO_RAW="https://raw.githubusercontent.com/devrana778410-arch/Gps-Scanner/main"
CACHE_BUST="$(date +%s)"
TARGET_PY="$HOME/scanner.py"
TMP_PY="$HOME/.scanner.py.tmp"
BIN_DIR="${PREFIX:-$HOME/.local}/bin"

download_file() {
    local url="$1"
    local dest="$2"
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "$url" -o "$dest"
    elif command -v wget >/dev/null 2>&1; then
        wget -qO "$dest" "$url"
    else
        return 1
    fi
}

echo "🚀 GPS Scanner — Install / Update"

# 1. Install dependencies only if missing (keeps updates under 2 seconds)
MISSING_PKGS=""
command -v python >/dev/null 2>&1 || MISSING_PKGS="$MISSING_PKGS python"
command -v termux-clipboard-set >/dev/null 2>&1 || MISSING_PKGS="$MISSING_PKGS termux-api"
if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
    MISSING_PKGS="$MISSING_PKGS curl"
fi

if [ -n "$MISSING_PKGS" ]; then
    echo "📦 Installing missing packages:$MISSING_PKGS..."
    pkg update -y
    DEBIAN_FRONTEND=noninteractive pkg install -y -o Dpkg::Options::="--force-confold" $MISSING_PKGS
else
    echo "✅ Dependencies already installed — skipping pkg install."
fi

# 2. Download scanner.py safely (atomic replace + Python syntax validation)
echo "📥 Downloading latest scanner.py..."
if download_file "$REPO_RAW/scanner.py?t=$CACHE_BUST" "$TMP_PY" && python -c "import ast, sys; ast.parse(open(sys.argv[1], encoding='utf-8').read())" "$TMP_PY" 2>/dev/null; then
    mv "$TMP_PY" "$TARGET_PY"
    echo "✅ Updated $TARGET_PY"
else
    rm -f "$TMP_PY"
    echo "❌ Download or validation failed. Existing scanner.py was kept untouched."
    exit 1
fi

# 3. Sync ~/Gps-Scanner if cloned via git
if [ -d "$HOME/Gps-Scanner/.git" ] && command -v git >/dev/null 2>&1; then
    echo "🔄 Syncing ~/Gps-Scanner git repo..."
    git -C "$HOME/Gps-Scanner" pull --ff-only >/dev/null 2>&1 || true
fi

# 4. Configure home screen widget shortcuts (~/.shortcuts/)
echo "⚙️ Configuring Termux:Widget shortcuts..."
mkdir -p "$HOME/.shortcuts"

cat << 'EOF' > "$HOME/.shortcuts/Start_Scanner.sh"
#!/bin/bash
# Prevent CPU sleep
termux-wake-lock 2>/dev/null || true

# Give Termux a second to render
sleep 1

# Open Binary Eye (Continuous Scan compatible)
am start -n de.markusfisch.android.binaryeye/de.markusfisch.android.binaryeye.activity.CameraActivity > /dev/null 2>&1 || true

# Boot the local server + Live Web UI on http://127.0.0.1:8080
python "$HOME/scanner.py"
EOF

cat << 'EOF' > "$HOME/.shortcuts/Update_Scanner.sh"
#!/bin/bash
echo "🔄 Updating GPS Scanner..."
TMP_INST="$HOME/.install_gps_scanner.sh.tmp"
URL="https://raw.githubusercontent.com/devrana778410-arch/Gps-Scanner/main/install.sh?t=$(date +%s)"

OK=0
if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$URL" -o "$TMP_INST" && OK=1
elif command -v wget >/dev/null 2>&1; then
    wget -qO "$TMP_INST" "$URL" && OK=1
fi

if [ "$OK" -eq 1 ] && bash "$TMP_INST"; then
    rm -f "$TMP_INST"
    termux-toast -b green -c white "✅ GPS Scanner Updated!" 2>/dev/null || true
else
    rm -f "$TMP_INST"
    termux-toast -b red -c white "❌ Update Failed (Check Internet)" 2>/dev/null || true
    echo "❌ Update failed. Press Enter to close..."
    read -r _
fi
EOF

chmod +x "$HOME/.shortcuts/Start_Scanner.sh" "$HOME/.shortcuts/Update_Scanner.sh"

# 5. Install short CLI command: `update-scanner`
if [ -d "$BIN_DIR" ] || mkdir -p "$BIN_DIR" 2>/dev/null; then
    cat << 'EOF' > "$BIN_DIR/update-scanner"
#!/bin/bash
exec bash "$HOME/.shortcuts/Update_Scanner.sh"
EOF
    chmod +x "$BIN_DIR/update-scanner"
fi

echo ""
echo "✅ Setup / Update Complete!"
echo "   • Start scanner:  python ~/scanner.py  (or tap 'Start_Scanner' widget)"
echo "   • Live dashboard: http://127.0.0.1:8080  (open in Chrome)"
echo "   • Easy update:    run 'update-scanner' or tap 'Update_Scanner' widget"
