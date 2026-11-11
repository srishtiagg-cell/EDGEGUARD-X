"""
compare_models.py: kaunsa model PERSON ko sabse achha pakadta hai? Sab models ek hi test images par.

Colab / laptop dono par chalta hai (pip install ultralytics opencv-python numpy).

Example:
  python compare_models.py \
      --images /content/edgeguard_stage2/images/val \
      --labels /content/edgeguard_stage2/labels/val \
      --models yolov8s.pt /content/drive/MyDrive/edgeguard_best_v2.pt /content/drive/MyDrive/edgeguard_best_stage2.pt

Labels: YOLO txt (class cx cy w h, normalized). Sirf person class (--person-label-id, default 0) gini jaati hai.
Models mein person ki class unke apne names se dhoondhi jaati hai (COCO ka 'person' ho ya aapka), isliye
COCO-pretrained aur aapke fine-tuned models seedha compare ho jaate hain.

Har model do conditions par test hota hai: clean aur degraded (fog / dust / dark, synthetic, har model ko
bilkul same degraded images milti hain).

Output: AP50 (all-point interpolation, Ultralytics ke mAP50 se thoda alag ho sakta hai, par models ke
beech compare ke liye consistent), recall@conf, precision@conf, aur recall ka 95% confidence interval (bootstrap).
Test set chhota ho toh CI chauda aayega. Tab numbers par bharosa mat karo.
"""
import argparse
from pathlib import Path

import numpy as np

IMG_EXT = {".jpg", ".jpeg", ".png"}


# ---------------- matching / metrics ----------------
def iou_matrix(a, b):
    """a: Nx4, b: Mx4 (x1,y1,x2,y2) -> NxM IoU."""
    if len(a) == 0 or len(b) == 0:
        return np.zeros((len(a), len(b)))
    ix1 = np.maximum(a[:, None, 0], b[None, :, 0])
    iy1 = np.maximum(a[:, None, 1], b[None, :, 1])
    ix2 = np.minimum(a[:, None, 2], b[None, :, 2])
    iy2 = np.minimum(a[:, None, 3], b[None, :, 3])
    inter = np.clip(ix2 - ix1, 0, None) * np.clip(iy2 - iy1, 0, None)
    area_a = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    area_b = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / (area_a[:, None] + area_b[None, :] - inter + 1e-9)


def match_all(dets_per_img, gts_per_img, iou_thr=0.5):
    """Har image ke detections ko (confidence ke ghatte kram mein) GT se greedy match karo.
    Returns: conf, tp_flag, img_idx (teeno sab detections ke liye, conf ke hisaab se sorted), n_gt."""
    confs, tps, idxs = [], [], []
    for i, (d, g) in enumerate(zip(dets_per_img, gts_per_img)):
        d = np.asarray(d, dtype=float).reshape(-1, 5)
        g = np.asarray(g, dtype=float).reshape(-1, 4)
        order = np.argsort(-d[:, 4])
        d = d[order]
        used = np.zeros(len(g), bool)
        ious = iou_matrix(d[:, :4], g)
        for k in range(len(d)):
            best, best_iou = -1, iou_thr
            for j in range(len(g)):
                if not used[j] and ious[k, j] >= best_iou:
                    best, best_iou = j, ious[k, j]
            if best >= 0:
                used[best] = True
            confs.append(d[k, 4]); tps.append(best >= 0); idxs.append(i)
    confs, tps, idxs = np.array(confs), np.array(tps, bool), np.array(idxs, int)
    order = np.argsort(-confs, kind="stable")
    n_gt = int(sum(len(np.asarray(g).reshape(-1, 4)) for g in gts_per_img))
    return confs[order], tps[order], idxs[order], n_gt


def average_precision(confs, tps, n_gt):
    if n_gt == 0 or len(confs) == 0:
        return 0.0
    tpc, fpc = np.cumsum(tps), np.cumsum(~tps)
    rec = tpc / n_gt
    prec = tpc / np.maximum(tpc + fpc, 1)
    mrec = np.concatenate([[0.0], rec, [1.0]])
    mpre = np.concatenate([[1.0], prec, [0.0]])
    mpre = np.maximum.accumulate(mpre[::-1])[::-1]
    i = np.where(mrec[1:] != mrec[:-1])[0]          # all-point interpolation (VOC style)
    return float(np.sum((mrec[i + 1] - mrec[i]) * mpre[i + 1]))


def evaluate(dets_per_img, gts_per_img, conf_thr=0.25, n_boot=300, seed=0):
    confs, tps, idxs, n_gt = match_all(dets_per_img, gts_per_img)
    ap50 = average_precision(confs, tps, n_gt)
    keep = confs >= conf_thr
    tp, n_det = int(tps[keep].sum()), int(keep.sum())
    recall = tp / n_gt if n_gt else float("nan")
    precision = tp / n_det if n_det else float("nan")

    # bootstrap: images ko resample karke recall ka 95% interval
    n_img = len(gts_per_img)
    tp_i = np.bincount(idxs[keep & tps], minlength=n_img).astype(float)
    gt_i = np.array([len(np.asarray(g).reshape(-1, 4)) for g in gts_per_img], float)
    rng = np.random.default_rng(seed)
    rec_b = []
    for _ in range(n_boot):
        s = rng.integers(0, n_img, n_img)
        if gt_i[s].sum() > 0:
            rec_b.append(tp_i[s].sum() / gt_i[s].sum())
    lo, hi = (np.percentile(rec_b, [2.5, 97.5]) if rec_b else (float("nan"), float("nan")))
    return {"ap50": ap50, "recall": recall, "precision": precision, "rec_lo": float(lo), "rec_hi": float(hi),
            "n_gt": n_gt, "n_img": n_img}


# ---------------- degradations (fog / dust / dark) ----------------
def degrade(img, idx):
    import cv2
    rng = np.random.default_rng(1000 + idx)          # har image ke liye fixed, har model ko same
    kind = idx % 3
    f = img.astype(np.float32)
    if kind == 0:                                     # fog
        t, A = rng.uniform(0.3, 0.7), rng.uniform(190, 235)
        out = f * (1 - t) + A * t
        out = cv2.GaussianBlur(out, (0, 0), rng.uniform(0.5, 2.0))
    elif kind == 1:                                   # dust
        t = rng.uniform(0.2, 0.6)
        out = f * (1 - t) + np.array([110, 160, 200], np.float32) * t
        out = cv2.GaussianBlur(out, (0, 0), rng.uniform(0.5, 1.8)) + rng.normal(0, 5, f.shape)
    else:                                             # dark
        g = rng.uniform(1.8, 3.0)
        out = 255 * (f / 255) ** g * rng.uniform(0.5, 0.9) + rng.normal(0, rng.uniform(6, 12), f.shape)
    return np.clip(out, 0, 255).astype(np.uint8)


# ---------------- data / models ----------------
def load_dataset(img_dir, lbl_dir, person_id, max_images):
    import cv2
    paths = sorted(p for p in Path(img_dir).iterdir() if p.suffix.lower() in IMG_EXT)
    if max_images and len(paths) > max_images:
        sel = np.random.default_rng(0).choice(len(paths), max_images, replace=False)
        paths = [paths[i] for i in sorted(sel)]
    imgs, gts = [], []
    for p in paths:
        im = cv2.imread(str(p))
        if im is None:
            continue
        H, W = im.shape[:2]
        boxes = []
        lf = Path(lbl_dir) / (p.stem + ".txt")
        if lf.exists():
            for ln in lf.read_text().splitlines():
                q = ln.split()
                if len(q) >= 5 and int(float(q[0])) == person_id:
                    cx, cy, w, h = [float(v) for v in q[1:5]]
                    boxes.append([(cx - w / 2) * W, (cy - h / 2) * H, (cx + w / 2) * W, (cy + h / 2) * H])
        imgs.append(im)
        gts.append(boxes)
    return imgs, gts


def make_yolo_predict(path, imgsz=640):
    from ultralytics import YOLO
    m = YOLO(path)
    pids = {k for k, v in m.names.items() if str(v).lower() == "person"}
    if not pids:
        raise SystemExit(f"{path}: is model mein 'person' class hi nahi hai (names: {m.names})")

    def predict(img):
        r = m(img, conf=0.001, imgsz=imgsz, verbose=False)[0]
        out = []
        for b in r.boxes:
            if int(b.cls[0]) in pids:
                x1, y1, x2, y2 = b.xyxy[0].tolist()
                out.append((x1, y1, x2, y2, float(b.conf[0])))
        return out
    return predict


def run(predict_fns, imgs, gts, conf_thr=0.25):
    """predict_fns: {naam: fn(img)->[(x1,y1,x2,y2,conf)]}. Returns list of result rows."""
    degraded = [degrade(im, i) for i, im in enumerate(imgs)]
    rows = []
    for name, fn in predict_fns.items():
        for cond, ims in (("clean", imgs), ("degraded", degraded)):
            dets = [fn(im) for im in ims]
            r = evaluate(dets, gts, conf_thr)
            r.update(model=name, cond=cond)
            rows.append(r)
    return rows


def print_table(rows, conf_thr):
    print(f"\n{'model':32s} {'condition':9s} {'AP50':>6s} {'recall@'+str(conf_thr):>11s} {'95% CI':>13s} {'prec@'+str(conf_thr):>10s}")
    print("-" * 88)
    for r in rows:
        print(f"{Path(r['model']).name[:32]:32s} {r['cond']:9s} {r['ap50']:6.3f} {r['recall']:11.3f} "
              f"[{r['rec_lo']:.2f},{r['rec_hi']:.2f}] {r['precision']:10.3f}")
    n_gt, n_img = rows[0]["n_gt"], rows[0]["n_img"]
    print(f"\nTest set: {n_img} images, {n_gt} person instances.")
    if n_gt < 200:
        print("WARNING: 200 se kam person instances. CI chauda hai, chhote farq ko 'behtar' mat maano.")
    print("Recall ka CI aapas mein overlap kare toh models mein asli farak sabit nahi hota.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", required=True)
    ap.add_argument("--labels", required=True)
    ap.add_argument("--models", nargs="+", required=True)
    ap.add_argument("--person-label-id", type=int, default=0, help="labels files mein person ki class id")
    ap.add_argument("--max-images", type=int, default=500)
    ap.add_argument("--conf", type=float, default=0.25)
    ap.add_argument("--imgsz", type=int, default=640)
    a = ap.parse_args()

    imgs, gts = load_dataset(a.images, a.labels, a.person_label_id, a.max_images)
    print(f"Loaded {len(imgs)} images, {sum(len(g) for g in gts)} person boxes")
    if not imgs:
        raise SystemExit("Koi image nahi mili. --images path check karo.")
    fns = {m: make_yolo_predict(m, a.imgsz) for m in a.models}
    print_table(run(fns, imgs, gts, a.conf), a.conf)


if __name__ == "__main__":
    main()