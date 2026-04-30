# Sentient Lib — Integrated System

Combines **Model 1** (Arduino ultrasonic trigger + camera capture) and
**Model 2** (slot-level shelf detection) into the **Sentient Lib** Flask dashboard.

## Folder Structure

```
sentient_integrated/
├── app.py                  ← main Flask app (run this)
├── requirements.txt
├── library.db              ← auto-created on first run
├── before.png              ← auto-saved by trigger 1
├── after.png               ← auto-saved by trigger 2
├── static/
│   ├── before_thumb.jpg    ← thumbnail shown in UI
│   └── after_thumb.jpg
└── templates/
    └── dashboard.html      ← Sentient UI
```

## Setup

```bash
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000

## Usage

### With Arduino connected (COM3)
1. Click **[ INITIALIZE ]** — captures reference frame, starts Arduino listener
2. Wave hand in front of ultrasonic sensor → **Trigger 1** → `before.png` saved
3. Remove/add a book → **Trigger 2** → `after.png` saved → detection runs automatically

### Without Arduino (testing)
1. Click **[ INITIALIZE ]**
2. Click **[ TRIGGER ]** once → before.png saved
3. Click **[ TRIGGER ]** again → after.png saved → detection runs
4. Or click **[ DETECT ]** to run Sentient's coarse motion check

## Routes

| Route         | Method | Description                          |
|---------------|--------|--------------------------------------|
| `/`           | GET    | Main dashboard                       |
| `/initialize` | GET    | Capture reference frame + start Arduino |
| `/trigger`    | GET    | Manual trigger (simulate Arduino)    |
| `/detect`     | GET    | Run Sentient coarse detection        |
| `/add_book`   | POST   | Add book to registry (form)          |
| `/api/add_book`| POST  | Add book (JSON, used by UI polling)  |
| `/api/state`  | GET    | JSON state (polled every 2s by UI)   |
| `/video_feed` | GET    | MJPEG camera stream                  |

## Changing COM Port

Edit `app.py` line 21:
```python
PORT = "COM3"   # change to your port, e.g. "/dev/ttyUSB0" on Linux
```

## How Detection Works

1. **Trigger 1** → frame saved as `before.png`
2. **Trigger 2** → frame saved as `after.png`
3. **Model 1 coarse check**: `np.sum(absdiff) > 500000` → shelf changed?
4. **Model 2 slot check**: divide shelf into 11 slots, compare mean brightness per slot
5. Results pushed to **Sentient UI**: status pill, missing table, shelf change panel, log
