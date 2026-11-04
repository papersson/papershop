# Film grammar

Four moves every explainer makes, done by the engine so that every film makes them the same way. Each one
addresses things by the names scenes already give them (`box: 'payment'`, or a text's key). A name
matches a node whose box name or key contains all of its words, so `'payment'` also matches the
label `name-payment`.

- **Focus on what's named.** `c.focus('bank', c.phrase('02', 'the bank'))` softens and dims
  everything under the camera that isn't named, from that word until the end of its sentence
  (`{until}` to choose, `{dim, blur}` to adjust). A newer focus takes over from an older one. Use
  it whenever the voice names one part of a busy picture. It is the cinematographer's rack focus,
  and Mayer's signalling.
- **Shots.** `c.shots([[0, 'wide'], [c.at('02'), ['close', 'payment']], [c.phrase('03', 'Step back'), 'back']])`
  moves the camera between the whole view, a close shot fitted to a named thing (and its label),
  and back to the last wide shot. Each move takes 1.1 s (`{move}`); a key can also be a plain
  `{x, y, z}`. Draw labels with `{keep: true}` so that they stay the same size on screen in every
  shot. Show where we are before showing detail, and come back out when the detail's
  consequence is somewhere else.
- **Chapter joins.** By default a chapter dissolves into the next one, in the quiet after its last
  word: up to 0.6 s, keeping 0.1 s clear of the voice. A cut needs at least 0.2 s of quiet,
  otherwise it stays hard. The incoming chapter chooses how it is joined: `export const join = { match: 'payment' }`
  is a match cut, where the outgoing camera carries the named thing to where the next chapter first
  draws it, while the dissolve runs. `export const join = 'hard'` is a straight cut, for a
  deliberate jolt. A join renders as its own short piece of the outgoing clip, so editing a chapter
  re-renders only its own clip and the join into it.
- **Callbacks.** `c.recall('s2', 'end', { into: [x, y, w, h] })` draws chapter s2's own frame
  (at a clip time, or `'end'`) fitted into a box on the overlay layer. Without `into`, it fills the
  stage. The payoff shows the setup exactly as it was, because it is the same drawing. Which setups return,
  and where, is planned in the beat table's `Sets up or returns` column (script.md, "Bring things back").
  `c.scene(id, t, {layer, op})` is the general form. A recalled chapter is part of the recalling
  chapter's cache key, and the checks measure each chapter's drawing in its own chapter only.
