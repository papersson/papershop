# Launch: a product film

A launch video, a feature demo, a product ad. The product is the subject, so its real screens are
the material. `studio new NAME --genre launch --duration 20`.

## Collect first, then decide together

Ask (at most a few questions, whose answers change the video): the product and its URL; the goal
and what the viewer should do after watching (the call to action); where it will be published and
in which formats; the length; brand colours, fonts and logo; a reference (a frame, a video, a
competitor's launch film); music (a file, or "synthesise"). Keys go in `.env`, never in a prompt.

## Real assets, never redrawn UI

- Capture the product: `studio capture URL VIDEO --name home --size 1440x900` (a page through the
  headless browser, recorded in `assets/provenance.json` with its URL, time, size and hash). Use
  the site's real logo, colours and fonts. List what you found before you animate.
- Crop and animate the real thing (`Shot` with `crop` and `scale`). Redrawn UI from imagination
  looks off: wrong spacing, placeholder boxes, fake-looking buttons, and anyone who has used good
  software feels it at once.
- Generated images (a hero background, a character) are allowed and recorded as `generated` with
  the prompt and tool: `studio asset add VIDEO file.png --kind generated --source "prompt … / tool"`.
  `studio check` fails when a scene refers to an asset that has no provenance row.

## The shape of the film

Beats of two to four seconds: (1) hook: the problem in five words of huge type; (2) the product
appears, its UI assembling piece by piece; (3) three features, each a UI moment with a cursor
doing a real action; (4) one number that proves it works, a real one, from the user; (5) logo and
call to action. Show the storyboard as stills before animating: what the viewer sees, the text on
screen, which parts are captures, how things move and how long each lasts, whether there is music,
effects or a voiceover. Fixing a storyboard is far cheaper than fixing a render: ask for three
variants and let the user choose a direction.

## Building it

- Lay every scene out against the stage's size, so one timeline exports 16:9, 9:16 and 1:1
  (`studio export VIDEO --formats 9:16,1:1,16:9`; type scales with `useStage()`; the starter scene
  shows how). `studio check --format 9:16` catches text or images that leave the frame.
- Sound: `studio beats` on a supplied track, or synthesised effects on the beat (clicks and
  whooshes for UI moments), `studio sound-lab` to choose them. Loudness for social is -14 LUFS.
- Voice: if the film has a narrator or a talking character, write a SCRIPT.md and use `studio
  narrate` (ElevenLabs for a character). Otherwise it needs no script.
- Notes go by timestamp and concrete camera words: "at 0:03 hold the product screen longer so the
  text is readable", "slow every zoom to 0.7x", "make the final call to action larger on mobile".
  "Make it better" gets random changes.
- Keep one project per brand: the renderer, components, assets and audio chain are reused, and a
  second film in the same project comes out faster.
