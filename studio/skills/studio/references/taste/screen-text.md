# Text on screen

On-screen text names things and shows real numbers; the narration explains. The user removed the
rest from a finished film: a banner over a shot ("ONE PLATTER, ONE RECORDING SURFACE") was "meh",
and footnotes under one ("Spacing and head tips enlarged / colored marks are overlays") were "noisy".

- **Labels, not captions.** On-screen text never repeats a sentence the narration is saying.
- **Labels sit on the thing they name**, connected to it, and nowhere else. No title banners over a
  shot, no subtitles under a heading, no footnotes. A chapter label in the header is the one
  exception, small and the same in every chapter.
- **A qualification is said, not footnoted.** When the picture bends the truth to be seen (an
  enlarged gap, a slowed spin, overlay colours), the narration says so once, or the picture shows
  the real thing first (`look.md`, Geometry is a claim).
- **Let labels land.** Labels that arrive while the camera moves are read only once it settles, and
  a run of them read as rushed: give each one about two seconds of stillness after the camera stops
  before the next appears, and stagger a group rather than revealing it at once. A pause in the
  narration (`[pause 2]`) is the way to buy that time; more narration is not.
- **Captions are a layout primitive.** They are burned in, in a reserved band at the bottom (160 px
  at 1080p, opaque by default), and nothing else enters it. The band is a subtitle layer, so "no
  text repeating the narration" applies to the stage, not the band. Chunks: at most two lines of
  about 42 characters, broken at phrase boundaries, held at least 1.2 s; the kit does this. There
  is no switch for them: a video without captions sets the band's height to 0 in layout.json.
- **Legible at phone width:** labels at least 18 px at 1080p (earlier builds used 26 px), contrast
  at least 4.5:1, and lines that carry meaning (a map's arrows, idle or not) at least 3:1. Frame
  reviews flagged 14 px grey-on-black as unreadable. A long code line shrinks to fit its panel,
  down to 18 px; past that, break the line or widen the panel.
- **Nothing floats inside a plot area.** Status text over a time axis reads as an event at that time.
- **Real quotes are short**, and only when the narration discusses them.
