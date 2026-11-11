"""Safety prototype primitives; all decisions are advisory/simulated."""
from dataclasses import dataclass
from math import hypot,isfinite,inf
REAL_HEIGHT={"person":1.7,"car":1.5,"truck":3.0}
WARN={"person":4.0,"car":3.0,"truck":3.0}; BRAKE={"person":2.0,"car":1.5,"truck":1.5}
def class_id_map(names, targets=("person","car","truck")):
    names=names if isinstance(names,dict) else dict(enumerate(names))
    by_name={str(v).strip().lower():int(k) for k,v in names.items()}
    return {by_name[n]:n for n in targets if n in by_name}
def camera_distance_m(height_px,cls,focal_px=388.0):
    try: h=float(height_px)
    except (TypeError,ValueError): return None
    if cls not in REAL_HEIGHT or not isfinite(h) or h<=2:return None
    d=focal_px*REAL_HEIGHT[cls]/h
    return d if .2<=d<=100 else None
@dataclass
class Detection:
    cx:float; cy:float; distance_m:float|None; cls:str
    box:tuple=(0,0,0,0); confidence:float=1.0
@dataclass
class Track:
    track_id:int; detection:Detection; alpha:float=.65; beta:float=.12; max_missed:int=8
    distance_m:float|None=None; radial_velocity_mps:float=0.; age:int=1; missed:int=0
    closing_evidence:int=0; updated_this_frame:bool=True
    def __post_init__(self): self.distance_m=self.detection.distance_m
    @property
    def cx(self):return self.detection.cx
    @property
    def cy(self):return self.detection.cy
    @property
    def cls(self):return self.detection.cls
    def update(self,d,dt):
        self.detection=d;self.updated_this_frame=True;self.age+=1;self.missed=0
        m=d.distance_m
        if m is None or not isfinite(m) or m<=0:self.closing_evidence=0;return
        if self.distance_m is None or dt<=1e-4 or dt>2:self.distance_m=m;self.closing_evidence=0;return
        pred=max(0,self.distance_m+self.radial_velocity_mps*dt);r=m-pred
        self.distance_m=max(0,pred+self.alpha*r);self.radial_velocity_mps+=self.beta*r/dt
        self.closing_evidence=self.closing_evidence+1 if self.radial_velocity_mps<-.2 else 0
    def ttc_s(self):
        closing=-self.radial_velocity_mps
        return self.distance_m/closing if self.distance_m is not None and self.closing_evidence>=2 and closing>.2 else inf
class Tracker:
    def __init__(self,max_missed=8,max_center_px=150):
        self.tracks=[];self.max_missed=max_missed;self.max_center_px=max_center_px;self.next_id=1
    def update(self,detections,dt):
        for t in self.tracks:t.updated_this_frame=False
        pairs=[]
        for ti,t in enumerate(self.tracks):
            for di,d in enumerate(detections):
                if t.cls!=d.cls:continue
                px=hypot(d.cx-t.cx,d.cy-t.cy)
                if px>self.max_center_px:continue
                if t.distance_m is not None and d.distance_m is not None and abs(t.distance_m-d.distance_m)>max(4,t.distance_m*.65):continue
                pairs.append((px,ti,di))
        ut=set();ud=set()
        for _,ti,di in sorted(pairs):
            if ti in ut or di in ud:continue
            self.tracks[ti].update(detections[di],dt);ut.add(ti);ud.add(di)
        for i,t in enumerate(self.tracks):
            if i not in ut:t.missed+=1
        for i,d in enumerate(detections):
            if i not in ud:self.tracks.append(Track(self.next_id,d,max_missed=self.max_missed));self.next_id+=1
        self.tracks=[t for t in self.tracks if t.missed<=self.max_missed]
        return self.tracks
def decide_risk(tracks,min_safe_dist_m=1.5):
    state="SAFE"
    for t in tracks:
        if not t.updated_this_frame or t.distance_m is None:continue
        ttc=t.ttc_s()
        if t.distance_m<=min_safe_dist_m or ttc<BRAKE.get(t.cls,1.5):return "BRAKE"
        if ttc<WARN.get(t.cls,3):state="WARNING"
    return state
