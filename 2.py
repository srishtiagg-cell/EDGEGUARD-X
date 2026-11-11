"""
EdgeGuard-X: laptop prototype of the processing pipeline
Webcam/video -> YOLO detection -> (fake radar) distance -> tracking -> TTC -> risk decision

Run:   python edgeforgeinspect.py              (webcam)
       python edgeforgeinspect.py video.mp4    (video file)

Keys (click on the video window first):
  w = fake object comes closer     s = goes away
  x = stop                         r = reset (8 m, speed 0)
  q = quit
"""
import argparse
import time
from pathlib import Path
import cv2
import numpy as np
from ultralytics import YOLO
from edgeguard_core import class_id_map

# ---------------- Config ----------------
MODEL_PATH = Path(__file__).resolve().with_name("yolov8n.pt")
TARGET_CLASSES = {}  # populated from the selected checkpoint's actual class names
REAL_HEIGHT_M = {"person": 1.7, "car": 1.5, "truck": 3.0}
FOCAL_PX = 388.0               # calibrated: 330 px at 2 m  ->  330*2/1.7
CONF_THRESH = 0.5
IMG_SIZE = 320                 # smaller = faster

USE_FAKE_RADAR = True          # False -> camera-only distance

# TTC thresholds in seconds
WARN_TTC = {"person": 4.0, "car": 3.0, "truck": 3.0}
BRAKE_TTC = {"person": 2.0, "car": 1.5, "truck": 1.5}
MIN_SAFE_DIST_M = 1.5          # brake if anything is closer than this

# Alpha-beta filter gains
ALPHA, BETA = 0.5, 0.2
MATCH_PX = 120
MAX_MISSED = 8

FAKE_START_DIST = 8.0          # m
FAKE_APPROACH_SPEED = 1.5      # m/s


# ---------------- Sensor stubs ----------------
def estimate_distance(box_h_px, cls_name):
    """Camera-only distance (pinhole model)."""
    return FOCAL_PX * REAL_HEIGHT_M[cls_name] / max(box_h_px, 1.0)


def send_to_mcu(command):
    """Hook for ESP32 (pyserial) - step 2."""
    pass


# ---------------- Tracker ----------------
class Track:
    _next_id = 0

    def __init__(self, cx, cy, dist, cls_name):
        self.id = Track._next_id
        Track._next_id += 1
        self.cx, self.cy = cx, cy
        self.d = dist
        self.v = 0.0           # m/s, negative = approaching
        self.cls = cls_name
        self.missed = 0

    def update(self, cx, cy, dist, dt):
        self.cx, self.cy = cx, cy
        pred = self.d + self.v * dt
        r = dist - pred
        self.d = pred + ALPHA * r
        self.v = self.v + BETA * r / max(dt, 1e-3)
        self.missed = 0

    def ttc(self):
        closing = -self.v
        if closing < 0.2:
            return float("inf")
        return self.d / closing


def match_tracks(tracks, detections, dt):
    unmatched = list(range(len(detections)))
    for t in tracks:
        best, best_d = None, MATCH_PX
        for i in unmatched:
            cx, cy, dist, cls = detections[i]
            if cls != t.cls:
                continue
            dpx = np.hypot(cx - t.cx, cy - t.cy)
            if dpx < best_d:
                best, best_d = i, dpx
        if best is not None:
            cx, cy, dist, _ = detections[best]
            t.update(cx, cy, dist, dt)
            unmatched.remove(best)
        else:
            t.missed += 1
    for i in unmatched:
        cx, cy, dist, cls = detections[i]
        tracks.append(Track(cx, cy, dist, cls))
    return [t for t in tracks if t.missed <= MAX_MISSED]


# ---------------- Risk decision ----------------
def decide(tracks):
    state = "SAFE"
    for t in tracks:
        if t.missed > 0:
            continue
        ttc = t.ttc()
        if t.d < MIN_SAFE_DIST_M or ttc < BRAKE_TTC[t.cls]:
            return "BRAKE"
        if ttc < WARN_TTC[t.cls]:
            state = "WARNING"
    return state


COLORS = {"SAFE": (0, 200, 0), "WARNING": (0, 200, 255), "BRAKE": (0, 0, 255)}


def main():
    parser = argparse.ArgumentParser(description="EDGEGUARD-X live/video inference prototype")
    parser.add_argument("source", nargs="?", default="0", help="Camera index or video path (default: 0)")
    parser.add_argument("--model", default=str(MODEL_PATH), help="YOLO .pt checkpoint path")
    args = parser.parse_args()
    src = int(args.source) if args.source.isdigit() else args.source
    try:
        model = YOLO(args.model)
    except Exception as exc:
        raise SystemExit(f"Could not load YOLO checkpoint '{args.model}': {exc}") from exc
    global TARGET_CLASSES
    TARGET_CLASSES = class_id_map(model.names)
    if not TARGET_CLASSES:
        raise SystemExit(f"Checkpoint has no supported person/car/truck classes. Model classes: {model.names!r}")
    missing = {"person", "car", "truck"} - set(TARGET_CLASSES.values())
    if missing:
        print("Checkpoint does not contain these supported classes: " + ", ".join(sorted(missing)))

    cap = None
    if isinstance(src, int):
        attempts = []
        for backend, label in [(cv2.CAP_DSHOW, "DirectShow"), (cv2.CAP_MSMF, "Media Foundation"), (cv2.CAP_ANY, "OpenCV auto")]:
            candidate = cv2.VideoCapture(src, backend)
            if candidate.isOpened():
                candidate.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                candidate.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                ok, first_frame = candidate.read()
                if ok and first_frame is not None:
                    cap = candidate
                    print(f"Camera index {src} opened using {label}.")
                    break
                attempts.append(f"{label}: opened but returned no frame")
            else:
                attempts.append(f"{label}: could not open")
            candidate.release()
        if cap is None:
            raise SystemExit(f"Cannot open camera index {src}. Tried: {'; '.join(attempts)}. Check Windows camera permission and close other camera apps.")
        prefetched = first_frame
    else:
        cap = cv2.VideoCapture(str(src))
        prefetched = None
        if not cap.isOpened():
            cap.release()
            raise SystemExit(f"Cannot open video source '{src}'. Check that the path exists and the codec is supported.")
    tracks = []
    prev_t = time.time()
    last_state = None

    fake_dist = FAKE_START_DIST   # meters
    fake_speed = 0.0              # m/s, positive = coming closer

    while True:
        if prefetched is not None:
            frame, prefetched = prefetched, None
            ok = True
        else:
            ok, frame = cap.read()
        if not ok:
            break

        now = time.time()
        dt = now - prev_t
        prev_t = now

        # fake radar update
        fake_dist = max(0.3, fake_dist - fake_speed * dt)
        fake_dist = min(fake_dist, 30.0)

        # 1) Detection
        res = model(frame, conf=CONF_THRESH, imgsz=IMG_SIZE,
                    classes=list(TARGET_CLASSES.keys()), verbose=False)[0]
        dets = []
        for b in res.boxes:
            c = int(b.cls[0])
            if c not in TARGET_CLASSES:
                continue
            x1, y1, x2, y2 = b.xyxy[0].tolist()
            name = TARGET_CLASSES[c]
            if USE_FAKE_RADAR:
                dist = fake_dist
            else:
                dist = estimate_distance(y2 - y1, name)
            dets.append(((x1 + x2) / 2, (y1 + y2) / 2, dist, name))

        # 2) Tracking + 3) TTC + 4) Decision
        tracks = match_tracks(tracks, dets, dt)
        state = decide(tracks)

        if state != last_state:
            send_to_mcu(state)
            last_state = state

        # Visualisation
        frame = res.plot(labels=False)          # draws bounding boxes
        for t in tracks:
            if t.missed > 0:
                continue
            ttc = t.ttc()
            ttc_txt = "inf" if ttc == float("inf") else f"{ttc:.1f}s"
            label = f"#{t.id} {t.cls} {t.d:.1f}m TTC {ttc_txt}"
            cv2.putText(frame, label, (int(t.cx) - 60, int(t.cy)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, COLORS[state], 2)
            cv2.circle(frame, (int(t.cx), int(t.cy)), 5, COLORS[state], -1)

        cv2.rectangle(frame, (0, 0), (frame.shape[1], 40), COLORS[state], -1)
        cv2.putText(frame, f"{state}   FPS {1/max(dt,1e-3):.0f}", (10, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
        if USE_FAKE_RADAR:
            cv2.putText(frame, f"FAKE RADAR: {fake_dist:.1f} m  speed {fake_speed:.1f} m/s",
                        (10, frame.shape[0] - 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.imshow("EdgeGuard-X sim", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("w"):
            fake_speed = FAKE_APPROACH_SPEED     # come closer
        elif key == ord("s"):
            fake_speed = -FAKE_APPROACH_SPEED    # go away
        elif key == ord("x"):
            fake_speed = 0.0                     # stop
        elif key == ord("r"):
            fake_dist, fake_speed = FAKE_START_DIST, 0.0   # reset

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
