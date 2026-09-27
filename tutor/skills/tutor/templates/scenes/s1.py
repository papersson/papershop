from lkit import *


class S1(CueScene):
    """Chapter 1. Each `self.at("NN")` waits for sentence s1_NN to start; the picture that a
    sentence describes appears as it is said, not after. `finish()` holds the last frame to the
    chapter's exact end, so consecutive chapters cut cleanly."""
    SEG = "s1"

    def construct(self):
        c = chip("{{Chapter title}}")
        self.at("01")
        self.play(FadeIn(c), run_time=0.4)
        # ... one block per sentence that changes the picture ...
        self.until(self.dur - 0.5)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.45)
        self.finish()
