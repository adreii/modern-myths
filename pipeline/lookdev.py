"""Environment look dev: one Blender scene per look, the town only, for approving light and sky.

Usage (Blender 5.2):
  blender -b --factory-startup -P pipeline/lookdev.py -- episodes/ep01_number            # build + stills
  blender -b --factory-startup -P pipeline/lookdev.py -- episodes/ep01_number --painterly # + Kuwahara variants
Options: --scale 50, --only LD_Day_Park

It builds the episode the same way build.py does (so every shot's world group, sun and grade
exist), then adds a scene per look that links the shared Town and light, sits on a representative
shot's frame, and films from that shot's camera with a grey ball and a chrome ball in the corner.
Each look scene sets its own `ep_shot`, so EP01_World shows that shot's group. Saved as
lookdev/<episode>_lookdev.blend, stills in lookdev/stills/.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(1, str(ROOT / ".deps" / "blender"))
sys.path.insert(2, str(ROOT / "pipeline"))

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import build as B  # noqa: E402

# look scene -> (representative shot, where in it 0-1, what it sets)
LOOKS = {
    "LD_PreDawn_Lane": ("s05", 0.5, "04 05"),
    "LD_Dawn_Doorstep": ("s06", 0.15, "06 13"),
    "LD_Dawn_Square": ("s02", 0.5, "01 02 03"),
    "LD_Day_Square": ("s07", 0.5, "07 08 09"),
    "LD_Day_Park": ("s10", 0.2, "10 11"),
    "LD_Dusk_Square": ("s12", 0.5, "11 end, 12"),
    "LD_Dawn_BakerRoom": ("s14", 0.5, "14"),
    "LD_Dawn_BakerDoor": ("s18", 0.95, "15 16 17 18 card"),
}


def balls(cam, coll):
    """Grey and chrome reference balls in the frame's lower-left corner, riding the camera."""
    out = []
    for i, (name, rough, metal, col) in enumerate((("LD_GreyBall", 0.5, 0.0, 0.18), ("LD_ChromeBall", 0.02, 1.0, 0.9))):
        me = bpy.data.meshes.get("LD_ball")
        if me is None:  # (bmesh, not an add-operator: in background the operator's context is unreliable)
            bm = bmesh.new()
            bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=1)
            me = bpy.data.meshes.new("LD_ball")
            bm.to_mesh(me)
            bm.free()
            me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
            me.materials.append(None)  # one slot; each ball sets its own material
        ob = bpy.data.objects.new(name, me)
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.use_nodes = True
        p = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
        p.inputs["Base Color"].default_value = (col, col, col, 1)
        p.inputs["Roughness"].default_value = rough
        p.inputs["Metallic"].default_value = metal
        ob.material_slots[0].link = "OBJECT"
        ob.material_slots[0].material = m
        # in camera space: 4 studs ahead, low-left; radius scaled to the lens
        d = 4.0
        half_h = d * 18 / cam.data.lens  # half the frame height at distance d (36 mm on the long side)
        half_w = half_h * 9 / 16
        r = half_h * 0.07
        ob.parent = cam
        ob.matrix_parent_inverse = Matrix.Identity(4)
        ob.location = (-half_w + r * (1.6 + i * 2.4), -half_h + r * 1.6, -d)
        ob.scale = (r, r, r)
        coll.objects.link(ob)
        out.append(ob)
    return out


def painterly_group(src):
    """A copy of the grade with a Kuwahara (brush-stroke) filter before the output."""
    ng = src.copy()
    ng.name = src.name + "_Painterly"
    out = next(n for n in ng.nodes if n.type == "GROUP_OUTPUT")
    link = next(l for l in ng.links if l.to_node == out)
    kw = ng.nodes.new("CompositorNodeKuwahara")
    for nm, v in (("Size", 12), ("Uniformity", 4), ("Sharpness", 0.5), ("Eccentricity", 1.0)):
        if nm in kw.inputs:
            kw.inputs[nm].default_value = v
    if "Variation" in kw.inputs:
        kw.inputs["Variation"].default_value = "Anisotropic"
    ng.links.new(link.from_socket, kw.inputs["Image"])
    ng.links.new(kw.outputs["Image"], out.inputs[0])
    return ng


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    p = argparse.ArgumentParser()
    p.add_argument("episode")
    p.add_argument("--scale", type=int, default=50)
    p.add_argument("--samples", type=int, default=24)
    p.add_argument("--fps", type=int, default=24)
    p.add_argument("--engine", default="BLENDER_EEVEE")
    p.add_argument("--style", default="")
    p.add_argument("--only", default="")
    p.add_argument("--painterly", action="store_true")
    a = p.parse_args(argv)
    ep = (ROOT / a.episode) if not Path(a.episode).is_absolute() else Path(a.episode)
    main_sc, built, _ = B.build(ep, a)
    by_name = {s.name: s for s in built}
    town = bpy.data.collections["Town"]
    light = bpy.data.collections["StoryKit_Light"]
    out = ROOT / "lookdev"
    (out / "stills").mkdir(parents=True, exist_ok=True)
    only = set(filter(None, a.only.split(",")))
    made = []
    for name, (shot, at, sets) in LOOKS.items():
        s = by_name[shot]
        frame = round(s.f0 + (s.f1 - s.f0) * at)
        B.solo(built, s)
        main_sc.frame_set(frame)
        # the shot's own camera (bound to its timeline marker), as evaluated at that frame
        cam_src = next(m.camera for m in main_sc.timeline_markers if m.name == s.name)
        cam_src = cam_src.evaluated_get(bpy.context.evaluated_depsgraph_get())
        sc = bpy.data.scenes.new(name)
        sc["ep_shot"] = s.index
        sc["sets_shots"] = sets
        sc.collection.children.link(town)
        sc.collection.children.link(light)
        own = bpy.data.collections.new(f"{name}_Camera")
        sc.collection.children.link(own)
        cd = cam_src.data.copy()
        cd.animation_data_clear()
        cd.lens = cam_src.data.lens
        cam = bpy.data.objects.new(f"{name}_Cam", cd)
        cam.matrix_basis = cam_src.matrix_world.copy()  # (matrix_world alone does not stick on a new object)
        own.objects.link(cam)
        sc.camera = cam
        own.objects.link(bpy.data.objects[f"{s.name}_Sun"])  # the shot's own sun lights the look
        balls(cam, own)
        # same render setup, held at the shot's frame (sun, grade and windows are keyed by frame)
        r, mr = sc.render, main_sc.render
        sc.render.engine = mr.engine
        r.resolution_x, r.resolution_y, r.resolution_percentage = mr.resolution_x, mr.resolution_y, a.scale
        r.fps = mr.fps
        if hasattr(sc, "eevee"):
            for prop in ("taa_render_samples", "use_raytracing", "use_shadows", "use_gtao", "bokeh_max_size"):
                if hasattr(main_sc.eevee, prop):
                    setattr(sc.eevee, prop, getattr(main_sc.eevee, prop))
        vs, mvs = sc.view_settings, main_sc.view_settings
        vs.view_transform, vs.look, vs.exposure, vs.gamma = mvs.view_transform, mvs.look, mvs.exposure, mvs.gamma
        sc.world = main_sc.world
        sc.compositing_node_group = main_sc.compositing_node_group
        sc.view_layers[0].use_pass_mist = True
        sc.frame_start = sc.frame_end = sc.frame_current = frame
        made.append((sc, name))
    if a.painterly:  # a second copy of each look with the brush-stroke grade
        for sc, name in list(made):
            pc = sc.copy()  # linked copy: same collections, camera and frame
            pc.name = f"{name}_Painterly"
            pc["ep_shot"] = sc["ep_shot"]
            pc.compositing_node_group = painterly_group(sc.compositing_node_group)
            made.append((pc, pc.name))
    bpy.ops.wm.save_as_mainfile(filepath=str(out / f"{ep.name}_lookdev.blend"))
    # Background Blender renders only the scene it started in, so the stills come from the episode
    # scene: no cast (every shot set excluded), the look's camera, the look's frame and grade.
    layer = bpy.context.view_layer.layer_collection
    for s in built:
        layer.children[s.coll.name].exclude = True
    for m in main_sc.timeline_markers:
        m.camera = None  # markers would switch the camera back to the shot's
    grade = main_sc.compositing_node_group
    for sc, name in made:
        if only and not any(name.startswith(o) for o in only):
            continue
        own = sc.camera.users_collection[0]
        main_sc.collection.children.link(own)
        main_sc.camera = sc.camera
        main_sc.compositing_node_group = sc.compositing_node_group
        main_sc.render.resolution_percentage = a.scale
        main_sc.frame_set(sc.frame_current)
        main_sc.render.filepath = str(out / "stills" / f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print("lookdev", main_sc.render.filepath, flush=True)
        main_sc.collection.children.unlink(own)
    main_sc.compositing_node_group = grade

if __name__ == "__main__":
    main()
