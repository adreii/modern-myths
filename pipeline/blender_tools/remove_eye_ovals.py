# Run inside Blender (Text Editor > Open this file > Run Script): removes the eye-oval geometry
# from every avatar head in the open file, since the face plane draws the eyes. Heads already
# cleaned are left alone. New builds do this by themselves (lib/imported.py _drop_eyes).
import bmesh
import bpy

done = 0
for me in {o.data for o in bpy.data.objects if o.type == "MESH" and o.name.split(".")[0] == "Hero1"}:
    bm = bmesh.new()
    bm.from_mesh(me)
    seen, drop = set(), []
    for v in bm.verts:
        if v in seen:
            continue
        comp, stack = [], [v]
        seen.add(v)
        while stack:
            x = stack.pop()
            comp.append(x)
            for e in x.link_edges:
                y = e.other_vert(x)
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        ys = [c.co.y for c in comp]
        zs = [c.co.z for c in comp]
        if len(comp) < 100 and max(ys) < -0.09 and min(zs) > 0.88 and max(zs) < 0.99:  # the two eye ovals
            drop += comp
    if drop:
        bmesh.ops.delete(bm, geom=drop, context="VERTS")
        bm.to_mesh(me)
        me.update()
        done += 1
    bm.free()
print(f"removed the eye ovals from {done} heads")
