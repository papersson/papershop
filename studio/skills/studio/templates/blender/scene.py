"""A plate's scene script: Blender draws the picture behind a live chapter (kit/src/studio_kit/plates.py).

Copy it into the video's sims/, name it in video.json plates, and draw the labels in the chapter's
live scene on the points this reports (c.plate.at('disk')). build() runs once; pose() runs every
frame and must depend on t alone, so any frame renders on its own.
"""
import math

import bpy


def build(scene, ctx):
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=1.8, depth=0.06)
    disk = scene.objects[-1]
    disk.name = "disk"
    metal = bpy.data.materials.new("brushed metal")
    metal.use_nodes = True
    bsdf = metal.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.62, 0.64, 0.67, 1)
    bsdf.inputs["Metallic"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = 0.28
    disk.data.materials.append(metal)
    bpy.ops.object.camera_add(location=(0, -5.2, 3.2), rotation=(math.radians(58), 0, 0))
    scene.camera = scene.objects[-1]
    bpy.ops.object.light_add(type="AREA", location=(2.5, -2.5, 4))
    scene.objects[-1].data.energy = 600
    bpy.ops.object.light_add(type="AREA", location=(-3, 1, 2.5))
    scene.objects[-1].data.energy = 150


def pose(scene, t, ctx):
    # spin the platter; ctx["cues"]["spin"] (clip seconds) could start it on the narration's word
    bpy.data.objects["disk"].rotation_euler.z = t * 2 * math.pi * 0.5
