# Run inside Blender (Text Editor > Open this file > Run Script) on an episode.blend built before
# the end-key fix: every shot's camera spheres (<shot>_rig, <shot>_lookat) get their last keys moved
# back onto the shot's last visible frame, so the B point can be seen and adjusted there. It also
# marks the spheres' current keys as "built", so pipeline/grab_looks.py keeps any moves you make
# from now on. Safe to run more than once.
import json

import bpy


def fcurves(ob):
    ad = ob.animation_data
    a = ad.action if ad else None
    if a is None:
        return []
    if hasattr(a, "layers") and a.layers:
        return [fc for layer in a.layers for st in layer.strips for cb in st.channelbags for fc in cb.fcurves]
    return list(getattr(a, "fcurves", []))


def location_keys(ob, f0):
    fcs = {fc.array_index: fc for fc in fcurves(ob) if fc.data_path == "location"}
    if len(fcs) < 3:
        return []
    return [[round(kp.co.x - f0, 3), *[round(fcs[i].evaluate(kp.co.x), 4) for i in range(3)], kp.interpolation, kp.easing]
            for kp in fcs[0].keyframe_points]


spans = {c["shot"]: (c["f0"], c["f1"]) for c in bpy.data.collections if c.name.endswith("_Lights") and "f0" in c}
moved = 0
for shot, (f0, f1) in spans.items():
    for suffix in ("_rig", "_lookat"):
        ob = bpy.data.objects.get(shot + suffix)
        if ob is None:
            continue
        for fc in fcurves(ob):
            if fc.data_path != "location":
                continue
            for kp in fc.keyframe_points:
                if kp.co.x > f1:
                    d = kp.co.x - f1
                    kp.co.x -= d
                    kp.handle_left.x -= d
                    kp.handle_right.x -= d
                    moved += 1
            fc.update()
        ob["shot_f0"], ob["shot_f1"] = f0, f1
        ob["built_keys"] = json.dumps(location_keys(ob, f0))
print(f"moved {moved} end keys onto their shot's last frame; {len(spans)} shots marked")
bpy.context.scene.frame_set(bpy.context.scene.frame_current)
