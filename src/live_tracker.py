import math

from config import (
    LIVE_TRACK_ALPHA,
    LIVE_TRACK_CONFIDENCE,
    LIVE_TRACK_HOLD_FRAMES,
    LIVE_TRACK_MAX_STEP_RATIO,
)
from skeleton import distance


class LiveTracker:
    """Filtro temporal de baja latencia aplicado solo al LIVE."""

    def __init__(self):
        self.alpha=float(LIVE_TRACK_ALPHA)
        self.hold_frames=int(LIVE_TRACK_HOLD_FRAMES)
        self.max_step_ratio=float(LIVE_TRACK_MAX_STEP_RATIO)
        self.confidence=float(LIVE_TRACK_CONFIDENCE)
        self.previous=None
        self.missing={}
        self.scale=120.0
        self.motion=0.0
        self.active=False

    def reset(self):
        self.previous=None
        self.missing={}
        self.scale=120.0
        self.motion=0.0
        self.active=False

    def update(self,keypoints):
        if not keypoints:
            self.active=False
            return None
        current_scale=self._shoulder_width(keypoints)
        self.scale=self.scale*0.8+current_scale*0.2
        if self.previous is None:
            self.previous=self._copy(keypoints)
            self.missing={n:0 for n in keypoints}
            self.active=True
            return self._copy(self.previous)

        result={}
        changes=[]
        max_step=max(4.0,self.scale*self.max_step_ratio)
        for name in set(self.previous)|set(keypoints):
            current=keypoints.get(name)
            previous=self.previous.get(name)
            if current is None or float(current.get("confidence",0.0))<self.confidence:
                if previous is not None:
                    count=self.missing.get(name,0)+1
                    self.missing[name]=count
                    if count<=self.hold_frames:
                        result[name]={
                            "x":float(previous["x"]),
                            "y":float(previous["y"]),
                            "confidence":float(previous.get("confidence",0.0))*max(0.35,1.0-count*0.18),
                        }
                continue
            self.missing[name]=0
            if previous is None:
                result[name]=dict(current)
                continue
            dx=float(current["x"])-float(previous["x"])
            dy=float(current["y"])-float(previous["y"])
            d=math.hypot(dx,dy)
            if d>max_step:
                r=max_step/max(d,0.0001)
                cx=float(previous["x"])+dx*r
                cy=float(previous["y"])+dy*r
            else:
                cx=float(current["x"]); cy=float(current["y"])
            fx=float(previous["x"])*(1-self.alpha)+cx*self.alpha
            fy=float(previous["y"])*(1-self.alpha)+cy*self.alpha
            changes.append(math.hypot(fx-float(previous["x"]),fy-float(previous["y"])))
            result[name]={"x":fx,"y":fy,"confidence":float(current.get("confidence",0.0))}
        self.motion=(sum(changes)/len(changes))/max(self.scale,1.0) if changes else 0.0
        self.previous=self._copy(result)
        self.active=bool(result)
        return result

    @staticmethod
    def _shoulder_width(points):
        left=points.get("left_shoulder"); right=points.get("right_shoulder")
        if not left or not right:
            return 120.0
        return max(distance((float(left["x"]),float(left["y"])),(float(right["x"]),float(right["y"]))),20.0)

    @staticmethod
    def _copy(points):
        return {
            n:{"x":float(p["x"]),"y":float(p["y"]),"confidence":float(p.get("confidence",0.0))}
            for n,p in points.items()
        }
