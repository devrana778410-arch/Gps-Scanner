import json
import queue
import re
import subprocess
import threading
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8080

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>GPS Scanner Live</title>
<style>
  :root {
    --bg: #0b0f17;
    --card: #131a26;
    --card-border: #232e42;
    --text: #e6edf7;
    --muted: #8b9bb4;
    --yellow-bg: rgba(245, 158, 11, 0.14);
    --yellow-border: #f59e0b;
    --yellow-text: #fcd34d;
    --green-bg: rgba(16, 185, 129, 0.15);
    --green-border: #10b981;
    --green-text: #6ee7b7;
    --red-bg: rgba(239, 68, 68, 0.18);
    --red-border: #ef4444;
    --red-text: #fca5a5;
    --btn-bg: #1e293b;
    --btn-border: #334155;
  }
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; }
  html, body {
    margin: 0;
    padding: 0;
    background: var(--bg);
    color: var(--text);
    font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    min-height: 100vh;
  }
  .app {
    max-width: 640px;
    margin: 0 auto;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px;
    background: var(--card);
    border: 1px solid var(--card-border);
    border-radius: 14px;
  }
  .title-wrap {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .title {
    font-size: 17px;
    font-weight: 700;
    letter-spacing: -0.01em;
  }
  .conn-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: #ef4444;
    box-shadow: 0 0 8px rgba(239, 68, 68, 0.6);
    flex-shrink: 0;
  }
  .conn-dot.online {
    background: #10b981;
    box-shadow: 0 0 8px rgba(16, 185, 129, 0.7);
  }
  .count-badge {
    background: #1e293b;
    border: 1px solid #334155;
    color: var(--text);
    padding: 5px 11px;
    border-radius: 999px;
    font-size: 13px;
    font-weight: 600;
    white-space: nowrap;
  }
  .card {
    background: var(--card);
    border: 1px solid var(--card-border);
    border-radius: 14px;
    padding: 14px;
    transition: background-color 0.2s ease, border-color 0.2s ease;
  }
  .buffer-card.state-yellow {
    background: var(--yellow-bg);
    border-color: var(--yellow-border);
  }
  .buffer-card.state-green {
    background: var(--green-bg);
    border-color: var(--green-border);
  }
  .buffer-card.state-red {
    background: var(--red-bg);
    border-color: var(--red-border);
  }
  .card-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 10px;
  }
  .card-label {
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    color: var(--muted);
  }
  .state-yellow .card-label { color: var(--yellow-text); }
  .state-green .card-label { color: var(--green-text); }
  .state-red .card-label { color: var(--red-text); }
  .field-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    padding: 9px 12px;
    background: rgba(0, 0, 0, 0.28);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 10px;
    margin-bottom: 8px;
  }
  .field-name {
    font-size: 12px;
    font-weight: 700;
    color: var(--muted);
    width: 48px;
    flex-shrink: 0;
  }
  .field-val {
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 16px;
    font-weight: 600;
    color: var(--text);
    word-break: break-all;
    flex: 1;
  }
  .field-val.empty {
    color: #4b5a73;
  }
  .field-clear {
    min-width: 36px;
    min-height: 36px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.14);
    background: rgba(255, 255, 255, 0.06);
    color: var(--muted);
    font-size: 16px;
    font-weight: 700;
    cursor: pointer;
    display: none;
    align-items: center;
    justify-content: center;
    touch-action: manipulation;
  }
  .field-clear.visible {
    display: inline-flex;
  }
  .status-line {
    font-size: 12px;
    color: var(--muted);
    min-height: 18px;
    margin: 4px 0 12px;
    word-break: break-word;
  }
  .status-line.ignored { color: #fbbf24; }
  .status-line.committed { color: var(--green-text); }
  .status-line.discarded { color: var(--red-text); }
  .btn-row {
    display: flex;
    gap: 10px;
  }
  button.action-btn {
    flex: 1;
    min-height: 48px;
    padding: 10px 14px;
    border-radius: 12px;
    border: 1px solid var(--btn-border);
    background: var(--btn-bg);
    color: var(--text);
    font-size: 15px;
    font-weight: 600;
    cursor: pointer;
    touch-action: manipulation;
    transition: opacity 0.15s ease, transform 0.08s ease;
  }
  button.action-btn:active:not(:disabled) {
    transform: scale(0.98);
  }
  button.action-btn:disabled {
    opacity: 0.38;
    cursor: not-allowed;
  }
  button.btn-danger {
    background: rgba(239, 68, 68, 0.18);
    border-color: rgba(239, 68, 68, 0.55);
    color: #fecaca;
  }
  button.btn-success {
    background: rgba(16, 185, 129, 0.22);
    border-color: rgba(16, 185, 129, 0.65);
    color: #a7f3d0;
    display: none;
  }
  button.btn-success.visible {
    display: block;
  }
  button.btn-undo {
    flex: 0 0 auto;
    min-height: 48px;
    padding: 8px 16px;
    background: rgba(245, 158, 11, 0.16);
    border-color: rgba(245, 158, 11, 0.5);
    color: #fde68a;
  }
  .pairs-list {
    max-height: 46vh;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .empty-list {
    text-align: center;
    color: var(--muted);
    font-size: 13px;
    padding: 20px 8px;
  }
  .pair-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 9px 10px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 10px;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: 13px;
  }
  .pair-row.latest {
    border-color: rgba(16, 185, 129, 0.45);
    background: rgba(16, 185, 129, 0.08);
  }
  .pair-idx {
    color: var(--muted);
    font-weight: 700;
    min-width: 28px;
  }
  .pair-cols {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    flex: 1;
    word-break: break-all;
  }
  .pair-sep {
    color: #4b5a73;
  }
  .dup-tag {
    font-family: system-ui, sans-serif;
    font-size: 10px;
    font-weight: 700;
    padding: 2px 6px;
    border-radius: 6px;
    background: rgba(245, 158, 11, 0.2);
    color: var(--yellow-text);
    text-transform: uppercase;
  }
</style>
</head>
<body>
<div class="app">
  <div class="header">
    <div class="title-wrap">
      <div id="connDot" class="conn-dot" title="Connection status"></div>
      <div class="title">📡 GPS Scanner Live</div>
    </div>
    <div id="countBadge" class="count-badge">0 pairs</div>
  </div>

  <div id="bufferCard" class="card buffer-card">
    <div class="card-head">
      <div id="bufferLabel" class="card-label">⚪ Buffer (ready for scan)</div>
    </div>
    <div class="field-row">
      <div class="field-name">IMEI</div>
      <div id="imeiVal" class="field-val empty">—</div>
      <button id="clearImeiBtn" class="field-clear" type="button" aria-label="Clear IMEI">×</button>
    </div>
    <div class="field-row">
      <div class="field-name">ICCID</div>
      <div id="iccidVal" class="field-val empty">—</div>
      <button id="clearIccidBtn" class="field-clear" type="button" aria-label="Clear ICCID">×</button>
    </div>
    <div id="statusLine" class="status-line">Waiting for Binary Eye scans…</div>
    <div class="btn-row">
      <button id="discardBtn" class="action-btn btn-danger" type="button" disabled>Discard Buffer</button>
      <button id="commitBtn" class="action-btn btn-success" type="button">Commit Pair</button>
    </div>
  </div>

  <div class="card">
    <div class="card-head">
      <div class="card-label">✅ Committed Pairs</div>
      <button id="undoBtn" class="action-btn btn-undo" type="button" disabled>Undo Last ↩</button>
    </div>
    <div id="pairsList" class="pairs-list">
      <div class="empty-list">No pairs committed yet. Scan a combined QR or IMEI + ICCID barcodes in Binary Eye.</div>
    </div>
  </div>
</div>

<script>
(function() {
  const connDot = document.getElementById('connDot');
  const countBadge = document.getElementById('countBadge');
  const bufferCard = document.getElementById('bufferCard');
  const bufferLabel = document.getElementById('bufferLabel');
  const imeiVal = document.getElementById('imeiVal');
  const iccidVal = document.getElementById('iccidVal');
  const clearImeiBtn = document.getElementById('clearImeiBtn');
  const clearIccidBtn = document.getElementById('clearIccidBtn');
  const statusLine = document.getElementById('statusLine');
  const discardBtn = document.getElementById('discardBtn');
  const commitBtn = document.getElementById('commitBtn');
  const undoBtn = document.getElementById('undoBtn');
  const pairsList = document.getElementById('pairsList');

  let currentSessionId = null;
  let lastSeq = -1;
  let latestState = null;
  let flashTimer = null;
  let flashKind = null;
  let flashPair = null;

  function applyState(state) {
    if (!state || typeof state.seq !== 'number') return;
    if (state.session_id && state.session_id !== currentSessionId) {
      currentSessionId = state.session_id;
      lastSeq = -1;
      clearTimeout(flashTimer);
      flashKind = null;
      flashPair = null;
    }
    if (state.seq < lastSeq) return;

    const isInitial = lastSeq === -1;
    const seqChanged = state.seq !== lastSeq;
    lastSeq = state.seq;
    latestState = state;

    const ev = state.last_event || {};
    if (seqChanged && !isInitial) {
      clearTimeout(flashTimer);
      if (ev.kind === 'committed' || ev.kind === 'discarded') {
        flashKind = ev.kind;
        flashPair = ev.pair || null;
        flashTimer = setTimeout(() => {
          flashKind = null;
          flashPair = null;
          if (latestState) renderBuffer(latestState);
        }, 750);
      } else {
        flashKind = null;
        flashPair = null;
      }
    }

    renderHeader(state);
    renderBuffer(state);
    renderPairs(state);
  }

  function renderHeader(state) {
    const total = state.pairs.length;
    const unique = state.unique_count;
    const label = total === 1 ? '1 pair' : `${total} pairs`;
    countBadge.textContent = (total !== unique) ? `${label} (${unique} unique)` : label;
  }

  function renderBuffer(state) {
    let imei = state.buffer_imei;
    let iccid = state.buffer_iccid;
    const ev = state.last_event || {};

    bufferCard.classList.remove('state-yellow', 'state-green', 'state-red');

    if (flashKind === 'discarded' && !imei && !iccid) {
      bufferCard.classList.add('state-red');
      bufferLabel.textContent = '🔴 Buffer Discarded';
    } else if (flashKind === 'committed' && !imei && !iccid && flashPair) {
      bufferCard.classList.add('state-green');
      bufferLabel.textContent = '🟢 Paired & Committed!';
      imei = flashPair.imei;
      iccid = flashPair.iccid;
    } else if (state.buffer_imei && state.buffer_iccid) {
      bufferCard.classList.add('state-green');
      bufferLabel.textContent = '🟢 Buffer (both fields ready)';
    } else if (state.buffer_imei || state.buffer_iccid) {
      bufferCard.classList.add('state-yellow');
      bufferLabel.textContent = state.buffer_imei
        ? '🟡 Buffer (waiting for ICCID)'
        : '🟡 Buffer (waiting for IMEI)';
    } else {
      bufferLabel.textContent = '⚪ Buffer (ready for scan)';
    }

    imeiVal.textContent = imei || '—';
    imeiVal.classList.toggle('empty', !imei);
    iccidVal.textContent = iccid || '—';
    iccidVal.classList.toggle('empty', !iccid);

    clearImeiBtn.classList.toggle('visible', Boolean(state.buffer_imei));
    clearIccidBtn.classList.toggle('visible', Boolean(state.buffer_iccid));

    discardBtn.disabled = !(state.buffer_imei || state.buffer_iccid);
    commitBtn.classList.toggle('visible', Boolean(state.buffer_imei && state.buffer_iccid));

    statusLine.className = 'status-line';
    if (ev.kind === 'ignored' || ev.kind === 'unknown') statusLine.classList.add('ignored');
    else if (ev.kind === 'committed') statusLine.classList.add('committed');
    else if (ev.kind === 'discarded') statusLine.classList.add('discarded');
    statusLine.textContent = ev.message || 'Ready to scan';
  }

  function renderPairs(state) {
    undoBtn.disabled = state.pairs.length === 0;
    pairsList.textContent = '';

    if (state.pairs.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'empty-list';
      empty.textContent = 'No pairs committed yet. Scan a combined QR or IMEI + ICCID barcodes in Binary Eye.';
      pairsList.appendChild(empty);
      return;
    }

    state.pairs.forEach((p, idx) => {
      const row = document.createElement('div');
      row.className = 'pair-row' + (idx === state.pairs.length - 1 ? ' latest' : '');

      const idxEl = document.createElement('span');
      idxEl.className = 'pair-idx';
      idxEl.textContent = '#' + (idx + 1);

      const colsEl = document.createElement('div');
      colsEl.className = 'pair-cols';

      const imeiEl = document.createElement('span');
      imeiEl.textContent = p.imei;

      const sepEl = document.createElement('span');
      sepEl.className = 'pair-sep';
      sepEl.textContent = '|';

      const iccidEl = document.createElement('span');
      iccidEl.textContent = p.iccid;

      colsEl.appendChild(imeiEl);
      colsEl.appendChild(sepEl);
      colsEl.appendChild(iccidEl);

      if (p.duplicate) {
        const dupEl = document.createElement('span');
        dupEl.className = 'dup-tag';
        dupEl.textContent = 'dup';
        colsEl.appendChild(dupEl);
      }

      row.appendChild(idxEl);
      row.appendChild(colsEl);
      pairsList.appendChild(row);
    });

    pairsList.scrollTop = pairsList.scrollHeight;
  }

  async function postAction(url) {
    try {
      const res = await fetch(url, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        if (data && data.state) applyState(data.state);
      }
    } catch (err) {
      console.error('Action failed:', err);
    }
  }

  discardBtn.addEventListener('click', () => postAction('/discard'));
  clearImeiBtn.addEventListener('click', () => postAction('/discard?field=imei'));
  clearIccidBtn.addEventListener('click', () => postAction('/discard?field=iccid'));
  commitBtn.addEventListener('click', () => postAction('/commit'));
  undoBtn.addEventListener('click', () => postAction('/undo'));

  function connectSSE() {
    const es = new EventSource('/stream');
    es.onopen = () => {
      connDot.classList.add('online');
    };
    es.onmessage = (event) => {
      connDot.classList.add('online');
      try {
        applyState(JSON.parse(event.data));
      } catch (e) {}
    };
    es.onerror = () => {
      connDot.classList.remove('online');
    };
  }

  connectSSE();
})();
</script>
</body>
</html>
"""


def haptic_feedback(duration_ms=60):
    """Triggers subtle haptic feedback asynchronously on Android via Termux API."""
    def _vibrate():
        try:
            subprocess.run(
                ['termux-vibrate', '-d', str(duration_ms)],
                stderr=subprocess.DEVNULL,
                timeout=0.5,
            )
        except Exception:
            pass

    threading.Thread(target=_vibrate, daemon=True).start()


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
    """Thread-safe scan state manager with live SSE broadcast support."""

    def __init__(self):
        self.lock = threading.RLock()
        self.session_id = uuid.uuid4().hex[:8]
        self.buffer_imei = None
        self.buffer_iccid = None
        self.scanned_pairs = []
        self.sse_clients = []
        self._seq = 0
        self.last_event = {"kind": "ready", "message": "Ready to scan"}

    def _snapshot_locked(self) -> dict:
        pairs_list = []
        seen = set()
        for item in self.scanned_pairs:
            parts = item.split('\t', 1)
            imei = parts[0]
            iccid = parts[1] if len(parts) > 1 else ""
            is_dup = item in seen
            seen.add(item)
            pairs_list.append({"imei": imei, "iccid": iccid, "duplicate": is_dup})
        return {
            "session_id": self.session_id,
            "seq": self._seq,
            "buffer_imei": self.buffer_imei,
            "buffer_iccid": self.buffer_iccid,
            "pairs": pairs_list,
            "unique_count": len(seen),
            "last_event": dict(self.last_event),
        }

    def get_state(self) -> dict:
        with self.lock:
            return self._snapshot_locked()

    def register_sse_client(self) -> queue.Queue:
        q = queue.Queue(maxsize=64)
        with self.lock:
            self.sse_clients.append(q)
            q.put_nowait(json.dumps(self._snapshot_locked()))
        return q

    def unregister_sse_client(self, q: queue.Queue):
        with self.lock:
            if q in self.sse_clients:
                self.sse_clients.remove(q)

    def push_state(self):
        """Broadcast current state to all connected browsers via SSE."""
        with self.lock:
            self._push_state_locked()

    def _push_state_locked(self):
        if not self.sse_clients:
            return
        payload = json.dumps(self._snapshot_locked())
        dead = []
        for q in self.sse_clients:
            try:
                q.put_nowait(payload)
            except queue.Full:
                dead.append(q)
        for q in dead:
            self.sse_clients.remove(q)

    def notify_shutdown(self):
        """Wake up all SSE listeners so server shuts down cleanly on Ctrl+C."""
        with self.lock:
            for q in self.sse_clients:
                try:
                    q.put_nowait(None)
                except queue.Full:
                    pass

    def _handle_single_field_locked(self, kind: str, val: str):
        own_attr = "buffer_imei" if kind == "IMEI" else "buffer_iccid"
        other_attr = "buffer_iccid" if kind == "IMEI" else "buffer_imei"
        other_label = "ICCID" if kind == "IMEI" else "IMEI"

        current_own = getattr(self, own_attr)
        current_other = getattr(self, other_attr)

        if current_own == val:
            return None

        if current_other is not None:
            imei = val if kind == "IMEI" else current_other
            iccid = current_other if kind == "IMEI" else val
            self.scanned_pairs.append(f"{imei}\t{iccid}")
            self.buffer_imei = None
            self.buffer_iccid = None
            self._seq += 1
            self.last_event = {
                "kind": "committed",
                "message": f"Paired #{len(self.scanned_pairs)}: {imei} / {iccid}",
                "pair": {"imei": imei, "iccid": iccid},
            }
            print(f"✅ Logged Pair [Device #{len(self.scanned_pairs)}]: {imei}  [TAB]  {iccid}")
            self._push_state_locked()
            return 180

        if current_own is not None:
            setattr(self, own_attr, val)
            self._seq += 1
            self.last_event = {"kind": "buffered", "message": f"Replaced {kind}: {val}"}
            print(f"🔄 Updated {kind} to: {val} (Waiting for {other_label}...)")
            self._push_state_locked()
            return 50

        setattr(self, own_attr, val)
        self._seq += 1
        self.last_event = {"kind": "buffered", "message": f"Buffered {kind}: {val}"}
        print(f"⏳ [1/2] Buffered {kind}: {val} (Waiting for {other_label}...)")
        self._push_state_locked()
        return 50

    def process(self, raw_data: str):
        vibrate_ms = None
        with self.lock:
            res_type, val = parse_scan(raw_data)

            if res_type in ("IGNORE", "URL_IGNORE"):
                if res_type == "URL_IGNORE":
                    print(f"⚠️  Ignored web link: {val}")
                    self.last_event = {"kind": "ignored", "message": f"Ignored link: {val}"}
                    self._seq += 1
                    self._push_state_locked()
                return

            if res_type == "UID_IGNORE":
                print(f"⚠️  Ignored UID: {val}")
                self.last_event = {"kind": "ignored", "message": f"Ignored UID: {val}"}
                self._seq += 1
                self._push_state_locked()
                return

            if res_type == "UNKNOWN":
                print(f"❓ Unrecognized scan: {val}")
                self.last_event = {"kind": "unknown", "message": f"Unrecognized: {val}"}
                self._seq += 1
                self._push_state_locked()
                return

            if res_type == "COMBINED_PAIR":
                imei, iccid = val
                self.scanned_pairs.append(f"{imei}\t{iccid}")
                self._seq += 1
                self.last_event = {
                    "kind": "committed",
                    "message": f"Paired #{len(self.scanned_pairs)} (QR): {imei} / {iccid}",
                    "pair": {"imei": imei, "iccid": iccid},
                }
                print(f"✅ Logged [Combined QR]: {imei}  [TAB]  {iccid}  (Total: {len(self.scanned_pairs)})")
                self._push_state_locked()
                vibrate_ms = 150
            elif res_type in ("IMEI", "ICCID"):
                vibrate_ms = self._handle_single_field_locked(res_type, val)

        if vibrate_ms:
            haptic_feedback(vibrate_ms)

    def undo_last(self) -> bool:
        """Move the last committed pair back into the buffer."""
        with self.lock:
            if not self.scanned_pairs:
                return False
            last = self.scanned_pairs.pop()
            parts = last.split('\t', 1)
            self.buffer_imei = parts[0]
            self.buffer_iccid = parts[1] if len(parts) > 1 else None
            self._seq += 1
            self.last_event = {
                "kind": "undone",
                "message": f"Undid pair: {self.buffer_imei} / {self.buffer_iccid}",
            }
            print(f"↩️  Undid pair: {self.buffer_imei}  [TAB]  {self.buffer_iccid} (Moved to buffer)")
            self._push_state_locked()
            return True

    def discard_buffer(self, field=None) -> bool:
        """Clear the pending buffer (or a single field) without committing."""
        with self.lock:
            if field == "imei":
                if self.buffer_imei is None:
                    return False
                old = self.buffer_imei
                self.buffer_imei = None
                self.last_event = {"kind": "discarded", "message": f"Cleared IMEI: {old}"}
                print(f"🗑️  Cleared buffered IMEI: {old}")
            elif field == "iccid":
                if self.buffer_iccid is None:
                    return False
                old = self.buffer_iccid
                self.buffer_iccid = None
                self.last_event = {"kind": "discarded", "message": f"Cleared ICCID: {old}"}
                print(f"🗑️  Cleared buffered ICCID: {old}")
            else:
                if self.buffer_imei is None and self.buffer_iccid is None:
                    return False
                self.buffer_imei = None
                self.buffer_iccid = None
                self.last_event = {"kind": "discarded", "message": "Buffer discarded"}
                print("🗑️  Discarded buffer")

            self._seq += 1
            self._push_state_locked()
            return True

    def commit_buffer(self) -> bool:
        """Commit when both IMEI and ICCID are present in buffer (e.g. after Undo)."""
        with self.lock:
            if not (self.buffer_imei and self.buffer_iccid):
                return False
            imei, iccid = self.buffer_imei, self.buffer_iccid
            self.scanned_pairs.append(f"{imei}\t{iccid}")
            self.buffer_imei = None
            self.buffer_iccid = None
            self._seq += 1
            self.last_event = {
                "kind": "committed",
                "message": f"Committed #{len(self.scanned_pairs)}: {imei} / {iccid}",
                "pair": {"imei": imei, "iccid": iccid},
            }
            print(f"✅ Re-committed Pair [Device #{len(self.scanned_pairs)}]: {imei}  [TAB]  {iccid}")
            self._push_state_locked()
            return True


aggregator = DeviceAggregator()
shutdown_event = threading.Event()


class ScanHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send_bytes(self, status: int, content_type: str, body: bytes):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if body:
            self.wfile.write(body)

    def _send_json(self, status: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        self._send_bytes(status, "application/json; charset=utf-8", body)

    def _drain_body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if length > 0:
            self.rfile.read(length)

    def _handle_sse(self):
        self.close_connection = True
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-transform")
        self.send_header("Connection", "close")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        client_q = aggregator.register_sse_client()
        idle_ticks = 0
        try:
            while not shutdown_event.is_set():
                try:
                    payload = client_q.get(timeout=1.0)
                    idle_ticks = 0
                    if payload is None:
                        break
                    msg = f"data: {payload}\n\n".encode("utf-8")
                    self.wfile.write(msg)
                    self.wfile.flush()
                except queue.Empty:
                    idle_ticks += 1
                    if idle_ticks >= 15:
                        idle_ticks = 0
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass
        finally:
            aggregator.unregister_sse_client(client_q)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        # Binary Eye webhook endpoint
        if parsed.path == "/" and "data" in query:
            raw_data = query["data"][0]
            aggregator.process(raw_data)
            self._send_bytes(200, "text/plain; charset=utf-8", b"OK")
            return

        if parsed.path == "/":
            self._send_bytes(200, "text/html; charset=utf-8", DASHBOARD_HTML.encode("utf-8"))
            return

        if parsed.path == "/stream":
            self._handle_sse()
            return

        if parsed.path == "/state":
            self._send_json(200, aggregator.get_state())
            return

        if parsed.path == "/favicon.ico":
            self._send_bytes(204, "text/plain", b"")
            return

        self._send_bytes(404, "text/plain; charset=utf-8", b"Not Found")

    def do_POST(self):
        self._drain_body()
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/undo":
            ok = aggregator.undo_last()
            self._send_json(200, {"ok": ok, "state": aggregator.get_state()})
            return

        if parsed.path == "/discard":
            field = query.get("field", [None])[0]
            ok = aggregator.discard_buffer(field=field)
            self._send_json(200, {"ok": ok, "state": aggregator.get_state()})
            return

        if parsed.path == "/commit":
            ok = aggregator.commit_buffer()
            self._send_json(200, {"ok": ok, "state": aggregator.get_state()})
            return

        self._send_json(404, {"ok": False, "error": "Not Found"})

    def log_message(self, format, *args):
        # Suppress standard HTTP access logs
        pass


class ScannerServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    print("=" * 50)
    print("--- Termux Zero-Touch GPS Scanner ---".center(50))
    print("=" * 50)
    print(f"Webhook URL:  http://127.0.0.1:{PORT}/?data=%s")
    print(f"Dashboard UI: http://127.0.0.1:{PORT}/\n")
    print("Device Support:")
    print("  • Combined QR (Traxsmart): Auto-extracts IMEI & ICCID")
    print("  • Multi-Barcode (GPS Bull): Pairs IMEI & ICCID in any order")
    print("  • Filters: Automatically ignores web URLs and UID barcodes")
    print("  • Output Format: IMEI [TAB] ICCID\n")
    print("Open the Dashboard UI in Chrome alongside Binary Eye.")
    print("Press Ctrl+C when finished.\n")

    with ScannerServer(("127.0.0.1", PORT), ScanHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            shutdown_event.set()
            aggregator.notify_shutdown()

            print("\n" * 2)
            print("=" * 45)
            print(" READY TO COPY ".center(45, "="))
            print("=" * 45 + "\n")

            with aggregator.lock:
                if aggregator.buffer_imei or aggregator.buffer_iccid:
                    parts = [p for p in (aggregator.buffer_imei, aggregator.buffer_iccid) if p]
                    print(f"⚠️ Warning: Uncommitted buffer was discarded ({' / '.join(parts)}).\n")

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
