
from edgeguard_core import Detection, Tracker, decide_risk

tracker = Tracker()

distances = [8.0, 6.0, 4.0]

for i, distance in enumerate(distances, start=1):
    detection = Detection(
        cx=100,
        cy=100,
        distance_m=distance,
        cls="person"
    )

    tracks = tracker.update([detection], dt=0.1)
    track = tracks[0]

    print(f"\nFrame {i}")
    print("Track ID:", track.track_id)
    print("Distance:", round(track.distance_m, 2), "m")
    print("Velocity:", round(track.radial_velocity_mps, 2), "m/s")
    print("Closing evidence:", track.closing_evidence)
    print("TTC:", track.ttc_s())
    print("Risk:", decide_risk(tracks))
