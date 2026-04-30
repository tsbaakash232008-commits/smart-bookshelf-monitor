
from flask import Flask, render_template, Response, request, redirect, jsonify
import cv2
import numpy as np
import sqlite3
import serial
import threading
import time
import os
from datetime import datetime
from thumbnail_helper import save_thumb

app = Flask(__name__)

# ─── Config ───────────────────────────────────────────────────────────────────
PORT        = "COM3"
BAUD        = 9600
THRESHOLD   = 500000
SLOT_COUNT  = 11
DIFF_THRESH = 8

BOOK_NAMES = {
    1:  "Intro to Astrophysics",
    2:  "European History Alt 1500-1800",
    3:  "European History 1500-1800",
    4:  "Modern Literature",
    5:  "Global Politics",
    6:  "Psychology",
    7:  "Ancient Greece",
    8:  "Quantum Mechanics",
    9:  "Philosophy & Ethics",
    10: "Medieval Society",
    11: "Art History",
}

# ─── Shared state ─────────────────────────────────────────────────────────────
state = {
    "status":         "BOOTING",
    "pipeline_stage": "booting",
    "trigger_count":  0,
    "removed_books":  [],
    "added_books":    [],
    "motion_events":  0,
    "arduino_ok":     False,
    "camera_ok":      False,
    "log":            [],
}

reference_frame = None
camera          = None
arduino         = None

# ─── Database ─────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("library.db")
    cur  = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            added_at TEXT
        )""")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS missing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            member TEXT,
            timestamp TEXT
        )""")
    cur.execute("PRAGMA table_info(books)")
    cols = [r[1] for r in cur.fetchall()]
    if "added_at" not in cols:
        cur.execute("ALTER TABLE books ADD COLUMN added_at TEXT")
    conn.commit()
    conn.close()

def db_add_book(title):
    conn = sqlite3.connect("library.db")
    conn.execute("INSERT INTO books (title, added_at) VALUES (?, ?)",
                 (title, str(datetime.now())))
    conn.commit(); conn.close()

def db_get_books():
    conn = sqlite3.connect("library.db")
    rows = conn.execute("SELECT id, title, added_at FROM books ORDER BY id DESC").fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "added_at": r[2]} for r in rows]

def db_add_missing(title):
    conn = sqlite3.connect("library.db")
    conn.execute("INSERT INTO missing (title, member, timestamp) VALUES (?, ?, ?)",
                 (title, "Unknown Member", str(datetime.now())))
    conn.commit(); conn.close()

def db_get_missing():
    conn = sqlite3.connect("library.db")
    rows = conn.execute("SELECT id, title, member, timestamp FROM missing ORDER BY id DESC").fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "member": r[2], "timestamp": r[3]} for r in rows]

# ─── Logging ──────────────────────────────────────────────────────────────────
def log(msg, level="info"):
    entry = {"ts": datetime.now().strftime("%H:%M:%S"), "msg": msg, "level": level}
    state["log"].insert(0, entry)
    state["log"] = state["log"][:100]
    print(f"[{entry['ts']}] {msg}")

# ─── Model 2: Slot-level shelf detection ──────────────────────────────────────
def detect_shelf_changes():
    before = cv2.imread("before.png")
    after  = cv2.imread("after.png")
    if before is None or after is None:
        log("Detection failed — image files not found", "error")
        return [], []

    after = cv2.resize(after, (before.shape[1], before.shape[0]))
    h, w, _ = before.shape
    before_crop = before[int(h * 0.35):int(h * 0.65), :]
    after_crop  = after [int(h * 0.35):int(h * 0.65), :]
    gray1 = cv2.cvtColor(before_crop, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(after_crop,  cv2.COLOR_BGR2GRAY)

    slot_w  = w // SLOT_COUNT
    removed = []
    added   = []
    for i in range(SLOT_COUNT):
        x1, x2 = i * slot_w, (i + 1) * slot_w
        r1 = gray1[:, x1:x2]
        r2 = gray2[:, x1:x2]
        diff = np.mean(cv2.absdiff(r1, r2))
        if diff > DIFF_THRESH:
            if np.mean(r1) > np.mean(r2):
                removed.append(i + 1)
            else:
                added.append(i + 1)
    return removed, added

# ─── Model 1: Detection pipeline ──────────────────────────────────────────────
def run_detection_pipeline():
    state["pipeline_stage"] = "detecting"
    log("Running detection (Model 1 + Model 2)...", "info")

    before = cv2.imread("before.png")
    after  = cv2.imread("after.png")
    if before is None or after is None:
        log("Detection aborted — images missing", "error")
        reset_triggers()
        return

    after_r   = cv2.resize(after, (before.shape[1], before.shape[0]))
    diff      = cv2.absdiff(before, after_r)
    gray_diff = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    _, th     = cv2.threshold(gray_diff, 25, 255, cv2.THRESH_BINARY)
    change    = int(np.sum(th))

    log(f"Pixel diff: {change:,}  |  threshold: {THRESHOLD:,}", "info")

    if change > THRESHOLD:
        log("Shelf Change Detected — running slot analysis", "warn")
        removed, added = detect_shelf_changes()
        state["removed_books"]  = [BOOK_NAMES.get(s, f"Slot {s}") for s in removed]
        state["added_books"]    = [BOOK_NAMES.get(s, f"Slot {s}") for s in added]
        state["motion_events"] += 1
        state["status"]         = "SECURITY"
        state["pipeline_stage"] = "done"
        for title in state["removed_books"]:
            db_add_missing(title)
            log(f"Missing flagged: {title}", "error")
        if state["removed_books"]:
            log(f"Removed: {', '.join(state['removed_books'])}", "error")
        if state["added_books"]:
            log(f"Added: {', '.join(state['added_books'])}", "ok")
    else:
        log("No Change Detected", "ok")
        state["removed_books"]  = []
        state["added_books"]    = []
        state["status"]         = "LIBRARIAN"
        state["pipeline_stage"] = "done"

    log("Detection complete — DB updated", "ok")
    time.sleep(5)
    reset_triggers()

def reset_triggers():
    state["trigger_count"]  = 0
    state["pipeline_stage"] = "ready"
    state["status"]         = "INACTIVE"
    log("System ready — waiting for next trigger...", "warn")

# ─── Arduino listener ─────────────────────────────────────────────────────────
def arduino_listener():
    global arduino
    log("Arduino listener active", "ok")
    log("Waiting for ultrasonic trigger...", "warn")
    while True:
        try:
            if arduino and arduino.in_waiting > 0:
                data = arduino.readline().decode(errors="ignore").strip()
                if data:
                    log(f"Serial: {data}", "info")
                    handle_trigger()
        except serial.SerialException as e:
            log(f"Serial disconnected: {e} — retrying in 5s", "error")
            time.sleep(5)
            try_connect_arduino()
        except Exception as e:
            log(f"Serial error: {e}", "error")
        time.sleep(0.05)

def handle_trigger():
    global camera
    if state["pipeline_stage"] not in ("ready", "waiting_before", "waiting_after"):
        return
    ret, frame = camera.read()
    if not ret:
        log("Camera read failed on trigger", "error")
        return

    if state["trigger_count"] == 0:
        cv2.imwrite("before.png", frame)
        save_thumb("before.png", "static/before_thumb.jpg")
        state["trigger_count"]  = 1
        state["pipeline_stage"] = "waiting_after"
        state["status"]         = "INACTIVE"
        log("Trigger 1 — before.png saved", "ok")
        time.sleep(2)

    elif state["trigger_count"] == 1:
        cv2.imwrite("after.png", frame)
        save_thumb("after.png", "static/after_thumb.jpg")
        state["trigger_count"] = 2
        log("Trigger 2 — after.png saved", "ok")
        threading.Thread(target=run_detection_pipeline, daemon=True).start()

# ─── Camera feed ──────────────────────────────────────────────────────────────
def generate_frames():
    global reference_frame, camera
    while True:
        if camera is None or not camera.isOpened():
            time.sleep(0.1)
            continue
        ret, frame = camera.read()
        if not ret:
            time.sleep(0.05)
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if reference_frame is not None:
            diff = cv2.absdiff(reference_frame, gray)
            _, thr = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            thr = cv2.dilate(thr, np.ones((3, 3), np.uint8), iterations=2)
            contours, _ = cv2.findContours(thr, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in contours:
                if cv2.contourArea(c) > 4000:
                    x, y, w, h = cv2.boundingRect(c)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 3)

        ts = datetime.now().strftime("%H:%M:%S")
        cv2.putText(frame, f"CAM_01  {ts}", (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 200, 150), 1)
        ret2, buf = cv2.imencode(".jpg", frame)
        if not ret2:
            continue
        yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")

# ─── Auto-startup ─────────────────────────────────────────────────────────────
def try_connect_arduino():
    global arduino
    try:
        arduino = serial.Serial(PORT, BAUD, timeout=1)
        time.sleep(2)
        state["arduino_ok"] = True
        log(f"Arduino connected on {PORT}", "ok")
    except Exception as e:
        state["arduino_ok"] = False
        log(f"Arduino not found on {PORT}: {e}", "error")

def auto_startup():
    global camera, reference_frame
    log("MODEL 1 : Ultrasonic → Capture → Detection", "info")
    log("Auto-startup sequence...", "info")
    os.makedirs("static", exist_ok=True)

    # 1. Camera
    camera = cv2.VideoCapture(0)
    if camera.isOpened():
        state["camera_ok"] = True
        log("Camera started on index 0", "ok")
    else:
        state["camera_ok"] = False
        log("Camera not detected — check connection", "error")
        state["status"] = "SECURITY"
        return

    time.sleep(1)

    # 2. Reference frame
    ret, frame = camera.read()
    if ret:
        reference_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        log("Reference frame captured", "ok")
    else:
        log("Could not capture reference frame", "error")

    # 3. Arduino
    try_connect_arduino()

    # 4. Ready
    state["status"]         = "INACTIVE"
    state["pipeline_stage"] = "ready"
    state["trigger_count"]  = 0
    log("System fully initialized — waiting for trigger...", "warn")

    # 5. Run listener loop forever
    arduino_listener()

# ─── Routes ───────────────────────────────────────────────────────────────────
@app.route("/")
def dashboard():
    return render_template("dashboard.html",
                           books=db_get_books(),
                           missing=db_get_missing(),
                           state=state,
                           now=int(time.time()),
                           THRESHOLD=THRESHOLD)

@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/api/state")
def api_state():
    return jsonify({
        "status":         state["status"],
        "pipeline_stage": state["pipeline_stage"],
        "trigger_count":  state["trigger_count"],
        "removed_books":  state["removed_books"],
        "added_books":    state["added_books"],
        "motion_events":  state["motion_events"],
        "arduino_ok":     state["arduino_ok"],
        "camera_ok":      state["camera_ok"],
        "log":            state["log"][:30],
        "books":          db_get_books(),
        "missing":        db_get_missing(),
    })

@app.route("/add_book", methods=["POST"])
def add_book():
    title = request.form.get("title", "").strip()
    if title:
        db_add_book(title)
        state["status"] = "LIBRARIAN"
        log(f"Book added: {title}", "ok")
    return redirect("/")

@app.route("/api/add_book", methods=["POST"])
def api_add_book():
    data  = request.get_json(force=True)
    title = (data or {}).get("title", "").strip()
    if title:
        db_add_book(title)
        state["status"] = "LIBRARIAN"
        log(f"Book added: {title}", "ok")
        return jsonify({"ok": True})
    return jsonify({"ok": False}), 400

# ─── Launch ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    log("Sentient Lib — Integrated System online", "ok")
    threading.Thread(target=auto_startup, daemon=True).start()
    app.run(debug=False, threaded=True, host="0.0.0.0", port=5000)
