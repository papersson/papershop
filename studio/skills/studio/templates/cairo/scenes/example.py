"""A starter scene for the cairo engine: a chapter is scenes/<clip>.py (s1.py for chapter 1) defining
scene(c), called once per frame. Everything drawn must be a function of c.t alone. Copy this to s1.py,
rename and replace; engines/cairo/cli.py lists what `c` offers."""


def scene(c):
    W, H = c.width, c.stage_height
    c.text("title", W / 2, 140, "A scene drawn natively", size=64, anchor="center")
    x = 240 + min(1.0, c.t / 3.0) * (W - 480)          # a token crossing the stage in three seconds
    c.rect("track", 240, H / 2 - 4, W - 480, 8, fill="#2b333c")
    c.rect("token", x - 40, H / 2 - 40, 80, 80, fill="#8fd3ff", radius=12)
