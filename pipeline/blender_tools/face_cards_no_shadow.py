# Run inside Blender (Text Editor > Open this file > Run Script): no face card casts a shadow.
# New builds do this by themselves (lib/imported.py _face_plane).
import bpy

cards = [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("face_")]
for o in cards:
    o.visible_shadow = False
print(f"{len(cards)} face cards no longer cast shadows")
