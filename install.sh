#!/bin/bash

echo "🚀 Starting installation for Zero-Touch Scanner..."

# 1. Update Termux and install required packages automatically
echo "📦 Installing dependencies (Python, Termux-API, Wget)..."
pkg update -y && pkg upgrade -y
pkg install python termux-api wget -y

# 2. Download the main Python script from your GitHub
echo "📥 Downloading scanner.py..."
wget -qO ~/scanner.py https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/scanner.py

# 3. Create the widget shortcut directory and the launch script
echo "⚙️ Configuring home screen widget shortcut..."
mkdir -p ~/.shortcuts

cat << 'EOF' > ~/.shortcuts/Start_Scanner.sh
#!/bin/bash
# Prevent CPU sleep
termux-wake-lock

# Give Termux a second to render
sleep 1

# Force open Binary Eye (Continuous Scan compatible)
am start -n de.markusfisch.android.binaryeye/de.markusfisch.android.binaryeye.activity.CameraActivity > /dev/null 2>&1

# Boot the local server
python ~/scanner.py
EOF

# Make the widget script executable
chmod +x ~/.shortcuts/Start_Scanner.sh

echo "✅ Installation Complete!"
echo ""
echo "⚠️ FINAL MANUAL STEPS FOR THE USER:"
echo "1. Ensure 'Termux:Widget' and 'Termux:API' apps are installed."
echo "2. Go to Android Settings -> Apps -> Termux -> Allow 'Display over other apps'."
echo "3. Add the Termux Widget to your home screen."

