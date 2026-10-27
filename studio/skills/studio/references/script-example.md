# A whole script, rewritten

The origins film "Why the web escaped TCP" (2026-10-27), rewritten to [script.md](script.md). The
picture, beats and facts are unchanged apart from two split screen notes; the narration and its
rests moved. It runs about a third longer (553 words against 402): the letter, the prediction,
the voiced interruption and the admission are new, and the rest is sentences joined the way a
person speaks. Cut it back if the film can't spare the minute. Read the two aloud, one after the
other. The original is in the video's `SCRIPT.md`.

## Narration

### 1. Why the web escaped TCP

> Open a web page, and your browser asks for dozens of things at once: words, pictures, fonts and code, and each of them could appear the moment it arrives. And yet one lost packet, carrying a sliver of one picture, can hold up all the rest, even the parts that have already arrived. Why would a network make finished work wait? To find out, we have to go back to a promise made in nineteen eighty-one.

*Screen:* Large illustrated browser; its resources become three cables. Pull back to reveal the
world and travel into 1981.

> That promise is TCP's, made on top of a network that loses packets and shuffles them out of order. TCP numbers every byte and resends whatever goes missing, so what comes out is one clean, ordered stream. It keeps that promise with one strict rule. Nothing gets delivered past a gap. [breath 1.5]

*Screen:* RFC artifact above a network; enter numbered packets. Packet disappears and is
recovered; ordered output resumes.

> For one long conversation, that's exactly what we want: if page three of a letter went missing, you'd wait for it before reading on.

*Screen:* Hold on the restored ordered stream.

> Eight years later, at CERN, Tim Berners-Lee had a more ordinary problem, which was that people kept losing track of information. He linked documents together, and his web ran on the internet's existing machinery, TCP included. Then pages grew pictures, stylesheets, fonts and scripts, until loading a single page meant dozens of separate conversations.

*Screen:* Approach an original editorial redraw of the 1989 proposal, then a workstation with
linked documents. Links branch into modern resources.

> HTTP/2 interleaves all of them on one TCP connection: a slice of picture, then a slice of font, then a slice of code. Now let's lose one packet from the picture. What happens to the font? [predict 2] Its bytes are already here. But TCP sees one stream, and nothing gets delivered past a gap. So the font waits for the picture. [breath 1.5]

*Screen:* Picture, font and code streams merge. A picture packet vanishes; the later font/code
bytes arrive in the receive buffer but cannot pass the delivery gate. Hold landed blockage.

> So why not just fix TCP? Because it's built into nearly every computer and phone, and changing it means changing all of them. The escape route had been there since nineteen eighty, in a protocol called UDP that promises almost nothing: here's a packet, good luck. That sounds like a step backwards, and I'll admit it did to me. But a protocol that promises nothing also forbids nothing, which means we can build our own promises on top of it, in software that ships with the browser.

*Screen:* Travel backward along an older branch to the 1980 UDP sheet. Its datagram is an
envelope with deliberately little machinery. Follow this branch forward again.

> That's QUIC. It rebuilds reliability on top of UDP one stream at a time, so the picture, the font and the code each get their own ordered line. It weaves in the TLS one point three handshake, so every connection is encrypted, and HTTP/3 carries the web on top. Now lose that same picture packet. The picture waits for its missing piece, but the font and the code don't. They were never in its line. [breath 1.5]

*Screen:* Enter a key-exchange station on the security branch, pull back for three histories
converging, enter QUIC's independent streams. The same picture packet is lost while font and
code reach their destinations. A single enclosing transport boundary remains.

> All three streams still share one crowded path, but one lost piece no longer holds up the rest. And there's a bonus. TCP names a connection by the addresses at both ends, so when your phone hops from Wi-Fi to mobile data, the connection breaks. QUIC gives each connection a name of its own, and it simply moves to the new path. It can't conjure a signal in a tunnel, though.

*Screen:* Phone changes between two real network paths.

> Back to the page you opened. Its pictures and fonts now travel on a minimal protocol from nineteen eighty, rebuilt to get around a promise from nineteen eighty-one. That promise was never a mistake. It was made for one long conversation, and the web turned out to be dozens of short ones, all at once. [breath 2]

*Screen:* Return to original browser above the merged histories. Final silent still.

## Evidence added

| Claim | Source | Scope |
|---|---|---|
| TCP runs in operating-system kernels, so changing it requires OS updates; QUIC runs in user space and ships with applications | Langley et al., "The QUIC Transport Protocol", SIGCOMM 2017, sections 1–2 | Verify against the paper before use. |
| A TCP connection is identified by its address and port pairs; QUIC connection IDs survive an address change | RFC 793 section 2.7; RFC 9000 sections 5.1 and 9 | Migration needs a usable new path. |

The remaining rows of the original Evidence table still apply. The date for HTTP/2 (2015), QUIC
(2021) and HTTP/3 (2022) moved from the voice to the screen and the table.

## What changed, and why

- **The open asks a question.** The original's first paragraph explained; this one ends on "Why
  would a network make finished work wait?" and promises an answer from 1981. The viewer has a
  reason to stay before the history starts.
- **One rule, said twice on purpose.** "Nothing gets delivered past a gap" is planted with
  TCP, returns at the HTTP/2 turn, and is answered by "They were never in its line." The viewer
  hears the mechanism become the problem.
- **The viewer predicts the turn.** `[predict 2]` after "What happens to the font?" lets them
  apply the rule they've just learned. They get there half a second before we do.
- **The interruption is voiced.** "So why not just fix TCP?" is what a sharp viewer would ask at
  that point, and its answer is why UDP matters at all. The original only hinted at it.
- **Pronouns and contractions.** "We" goes back in time, wants the ordered stream, loses the
  packet and builds on UDP; "you" reads the letter and carries the phone. The original had no
  "you", no "I" and no contractions; this has ten contractions and one "I".
- **Dates: five spoken years, now two.** 1981 and 1980 carry the story, and each returns in
  the ending. 1989 becomes "eight years later", and the standards' years go to the screen.
- **The caveats became facts.** "Shared congestion and application dependencies can still make
  them wait" became "All three streams still share one crowded path." It's still true, and now it's
  something a listener can picture.
- **Camera narration went.** "Follow the three streams into the same byte sequence" and "Back at
  the browser, the lesson is visible" are gone; the picture already does both.
- **The ending is a callback.** It returns to the opening's "dozens of things at once" and to the
  imagined letter: TCP was right for one long conversation.
