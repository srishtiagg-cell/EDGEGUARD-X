"""Validate an Ultralytics checkpoint and save actual aggregate/per-class metrics."""
import argparse,json
from pathlib import Path
import torch
from ultralytics import YOLO
def main():
 p=argparse.ArgumentParser();p.add_argument("--model",required=True);p.add_argument("--data",default="data.yaml");p.add_argument("--imgsz",type=int,default=640);p.add_argument("--device",default="");p.add_argument("--output",default="reports/evaluation.json");a=p.parse_args()
 model=YOLO(a.model);metrics=model.val(data=a.data,imgsz=a.imgsz,device=a.device or None,plots=True);box=metrics.box
 names=getattr(metrics,"names",model.names)
 per_class={str(names[i]):dict(zip(("precision","recall","map50","map50_95"),map(float,box.class_result(i)))) for i in range(len(box.ap))}
 report={"checkpoint":str(Path(a.model).resolve()),"data":str(Path(a.data).resolve()),"hardware_device":a.device or ("cuda" if torch.cuda.is_available() else "cpu"),"precision":float(box.mp),"recall":float(box.mr),"map50":float(box.map50),"map50_95":float(box.map),"per_class":per_class}
 out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding="utf8");print(json.dumps(report,indent=2))
if __name__=="__main__":main()
