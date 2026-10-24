# Other kinds of video

For a motion graphic, sketch the states and transitions and write a live scene as a function of
clip time. Use `video.json` duration or clips for a silent piece. Put contacts on the beat sheet,
place their sound with the kit, and check a deliberate loop's seam with `studio check --only loop`.

For a product film, capture the actual product with `studio capture` or add supplied assets with
`studio asset add`. Frame the action, show its consequence and keep each asset's source. The live
engine or Remotion can draw the scenes; the kit still supplies sound, cuts and the desk.

For pixel art, draw on a small canvas with an explicit palette. Scale by whole numbers with nearest
neighbour sampling. Inspect the exported frames for stray colours and fractional movement.

For recordings, use ffmpeg to trim and join selected spans. Keep the edit decisions and original
transcript in the video's data folder. Add the resulting media as an asset with its provenance,
and use the scene engine to place it. Supply word timings when captions need to follow the
recording. The mix accepts a recording track with its start, source in/out points and gain.
