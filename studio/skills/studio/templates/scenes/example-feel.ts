import {wobble} from '@studio';

// Weight in time and in the camera, for a heavy contact in a physical subject (references/taste/
// delight.md, "Spend feel on meaning"): copy to scenes/feel.ts and import it from the chapters that
// use it, so a change re-renders only them. Use it only where the subject has mass and impact: a held
// frame or a shake on something weightless claims a weight the subject does not have.
//
// Both are pure functions of t, and both give nothing when `reduced` is true: set it from one
// constant in scenes/ when video.json motion is "reduced" (Remotion scenes don't read video.json).

/**
 * Scene time for whatever the contact moves: real time until the contact at t0, held for `frames`
 * frames, then catching up over `catchup` seconds, so it is back on real time (and every later cue
 * is where the narration puts it) a quarter second after. Pass the result to the element's motion,
 * not to cue times. Give the cue "hitstop": frames in cues.json, so the motion review reads the held
 * frames as intended, and play the contact's sound on t0 so it rings through.
 */
export function hitstop(t: number, t0: number, frames: number, fps: number, {catchup = 0.25, reduced = false} = {}): number {
	const d = frames / fps;
	if (reduced || t < t0) return t;
	if (t < t0 + d) return t0;
	if (t < t0 + d + catchup) return t0 + ((t - t0 - d) * (d + catchup)) / catchup;
	return t;
}

const SHAKE = {px: 12, deg: 1, dur: 0.5, hz: 8}; // the limits at 1080p (delight.md)

/**
 * A camera kick for a contact at t0 (Eiserloh's trauma shake): offset and rotation from smooth noise,
 * scaled by the square of the trauma (0..1), so small hits barely move and big ones jolt, decaying to
 * nothing over half a second. Never a fixed sine, which reads as a vibration. Never under a label
 * someone is reading.
 */
export function shake(t: number, t0: number, trauma: number, {seed = 0, reduced = false} = {}): {x: number; y: number; deg: number} {
	const s = t - t0;
	if (reduced || s < 0 || s >= SHAKE.dur) return {x: 0, y: 0, deg: 0};
	const tr = Math.min(1, Math.max(0, trauma)) * (1 - s / SHAKE.dur);
	const a = tr * tr;
	return {
		x: SHAKE.px * a * wobble(t, 1, SHAKE.hz, seed),
		y: SHAKE.px * a * wobble(t, 1, SHAKE.hz, seed + 1),
		deg: SHAKE.deg * a * wobble(t, 1, SHAKE.hz, seed + 2),
	};
}
