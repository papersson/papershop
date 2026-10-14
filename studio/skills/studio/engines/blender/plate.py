"""Blender's side of a plate: render frames of a chapter's background from a video's scene script.

  blender --background --factory-startup --python plate.py -- --request REQUEST.json

The kit (kit/src/studio_kit/plates.py) writes the request and reads what this leaves in its `out`
folder: one PNG per frame (f00012.png, frames counted from the clip's first) and frames.jsonl, a line
per frame with the seconds it took and the screen points of the objects the request names, so the
live scene can put its labels on them (`c.plate.at(name)`).

The scene script is the video's own Python (in sims/), and defines two functions:

  build(scene, ctx)       once: the objects, materials, lights and the camera (scene.camera)
  pose(scene, t, ctx)     every frame: where everything is at clip time t (seconds)

ctx holds the clip's cues in clip seconds (ctx["cues"]["contact"]), fps, duration, the profile
(samples and scale for draft or final) and the request's own fields. pose must be a function of t
alone, so any frame renders on its own, as every studio frame does. Hide what is invisible
(`hide_render`) rather than fading it to nothing: a transparent object still costs its render, and
in one film its fades tripled the time a frame took.
"""
import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view


def load(script):
    spec = importlib.util.spec_from_file_location("studio_plate_scene", script)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(Path(script).parent))       # helpers beside the script import as usual
    spec.loader.exec_module(mod)
    for name in ("build", "pose"):
        if not callable(getattr(mod, name, None)):
            raise SystemExit(f"{script} defines no {name}(…): a plate's scene script defines build(scene, ctx) and pose(scene, t, ctx)")
    return mod


def setup(req):
    scene = bpy.context.scene
    for o in list(bpy.data.objects):                    # the factory scene's cube, light and camera
        bpy.data.objects.remove(o, do_unlink=True)
    scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in {
        e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items} else "BLENDER_EEVEE"
    scene.render.resolution_x, scene.render.resolution_y = req["width"], req["height"]
    scene.render.resolution_percentage = 100
    scene.render.fps = int(round(req["fps"]))
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    profile = req.get("profile", {})
    if hasattr(scene, "eevee") and "samples" in profile:
        scene.eevee.taa_render_samples = int(profile["samples"])
    return scene


def points(scene, names):
    """{name: [x, y, in front]} in output pixels, y down, for each named object's origin."""
    out = {}
    w, h = scene.render.resolution_x, scene.render.resolution_y
    for name in names:
        o = bpy.data.objects.get(name)
        if o is None or scene.camera is None:
            continue
        v = world_to_camera_view(scene, scene.camera, o.matrix_world.translation)
        out[name] = [round(v.x * w, 2), round((1 - v.y) * h, 2), v.z > 0]
    return out


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--request", required=True)
    req = json.loads(Path(ap.parse_args(argv).request).read_text())
    out = Path(req["out"])
    out.mkdir(parents=True, exist_ok=True)
    scene = setup(req)
    mod = load(req["script"])
    ctx = {**req, "cues": req.get("cues", {}), "profile": req.get("profile", {})}
    mod.build(scene, ctx)
    if scene.camera is None:
        raise SystemExit(f"{req['script']}: build() left no camera (scene.camera)")
    with open(out / "frames.jsonl", "a") as log:
        for f in req["frames"]:
            started = time.monotonic()
            mod.pose(scene, f / req["fps"], ctx)
            bpy.context.view_layer.update()
            scene.render.filepath = str(out / f"f{f:05d}.png")
            bpy.ops.render.render(write_still=True)
            log.write(json.dumps({"frame": f, "seconds": round(time.monotonic() - started, 3),
                                  "points": points(scene, req.get("project", []))}) + "\n")
            log.flush()
    print(json.dumps({"blender": bpy.app.version_string, "frames": len(req["frames"])}))


main()
