# 📱 Android Zero-Touch Edge Scanner

An offline, zero-latency barcode and QR code scanning pipeline built natively for Android. 

This architecture bridges physical optical sensors (Binary Eye) to a local, sandboxed Linux userland (Termux) via a loopback network. It aggregates rapid-fire continuous scans, deduplicates them, and pushes a clean, tab-separated block directly to your Android clipboard—completely bypassing cloud dependencies and external APIs.

## ✨ Features
* **Zero Latency:** Processes scans instantly over `127.0.0.1`, decoupled from Wi-Fi or cellular networks.
* **Continuous Scanning:** Leverages phase-detection autofocus to continuously read symbologies without freezing the UI.
* **Auto-Deduplication:** Automatically removes duplicate scans while preserving original scanning order.
* **Hardware Integrated:** Utilizes native Android `am` intents and Termux API to execute zero-touch clipboard pasting and haptic toast notifications.

---

## 📦 Prerequisites

To ensure background stability and pipeline functionality, you must install the following open-source applications. 
> **⚠️ Important:** Download these from **F-Droid** or GitHub. The Google Play Store versions of Termux are deprecated and will not work correctly.

1. **[Termux](https://f-droid.org/en/packages/com.termux/)** - The core terminal emulator.
2. **[Termux:API](https://f-droid.org/en/packages/com.termux.api/)** - Bridges terminal commands to device hardware.
3. **[Termux:Widget](https://f-droid.org/en/packages/com.termux.widget/)** - Allows executing scripts from the home screen.
4. **[Binary Eye](https://f-droid.org/en/packages/de.markusfisch.android.binaryeye/)** - The optical frontend scanner.

---

## 🚀 Installation

You

