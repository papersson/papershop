import {createContext, useContext} from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import timeline from '@timeline';
import * as motion from '../../../shared/motion.js';
import {clipTimes} from '../../../shared/timing.js';
import type {Timeline} from './types';

// The motion maths and narration times are the engines' shared modules (engines/shared/); only the
// defaults that are this kit's own (ramp's ease and length, pulse's length) are set here.
export {smooth, spring, track, swapAlpha, loopT, rng, ease, follow, settle, wobble} from '../../../shared/motion.js';
/** See useClip().phrase; exported for scenes that hold a narration entry directly. */
export {phraseStart} from '../../../shared/timing.js';

const T = timeline as Timeline;

export const ClipContext = createContext<{clip: string; start: number}>({clip: '', start: 0});

/**
 * Time inside the current clip, and the narration's times relative to it. Every value a scene
 * computes should derive from `t`, so any frame renders alone (no state carried between frames).
 * Sentence ids may be short ("03" is "<clip>_03").
 */
export function useClip() {
	const frame = useCurrentFrame();
	const {fps, durationInFrames} = useVideoConfig();
	const {clip, start} = useContext(ClipContext);
	const {at, end, word, phrase, cue} = clipTimes(T, clip, start);
	return {
		t: frame / fps,
		fps,
		dur: durationInFrames / fps,
		/** Start of a sentence, in clip seconds, plus an offset. */
		at,
		/** End of a sentence, in clip seconds, plus an offset. */
		end,
		/** Start of the i-th word of a sentence (needs `studio align`). */
		word,
		/**
		 * When a sentence reaches a phrase, in clip seconds: its words matched in the spoken words, or,
		 * where a spoken rule rewrote them, its place in the caption. Same rule as timeline.phrase_start.
		 */
		phrase,
		/** The i-th beat of the track (1-based), in clip seconds; needs `studio beats`. */
		beat: (i: number, off = 0) => {
			const b = T.beats?.beats[i - 1];
			if (b === undefined) throw new Error(`no beat ${i}; run studio beats`);
			return b - start + off;
		},
		/** The i-th downbeat (1-based), in clip seconds. */
		downbeat: (i: number, off = 0) => {
			const b = T.beats?.downbeats[i - 1];
			if (b === undefined) throw new Error(`no downbeat ${i}; run studio beats`);
			return b - start + off;
		},
		/** Every onset peak of the track, in clip seconds (for hits and effects). */
		hits: (T.beats?.hits ?? []).map((h) => h - start),
		bpm: T.beats?.bpm,
		cue,
	};
}

/** 0 before `start`, 1 after `start + dur`, eased in between. */
export function ramp(t: number, start: number, dur = 0.4, ease = motion.smooth): number {
	return motion.ramp(t, start, dur, ease);
}

/**
 * Keyframes [time, value, ease?] (a value a number or an array); a key's ease shapes the move into
 * it, a function or a name in `ease` (heavy, float, back, snap, ...), `smooth` by default as ramp's.
 */
export function keyed<V extends number | number[]>(t: number, keys: [number, V, (motion.Ease | keyof typeof motion.ease)?][], ease: motion.Ease = motion.smooth): V {
	return motion.keyed(t, keys, ease) as V;
}

/** 0 → 1 → 0 over `dur`, for a momentary emphasis. */
export function pulse(t: number, start: number, dur = 0.8): number {
	return motion.pulse(t, start, dur);
}

/**
 * Sequential beats, like a Manim scene's play() calls: `wait(t)` moves to t unless already past
 * it, `play(d)` returns the start of a d-second beat and moves past it. Built fresh on every
 * render from constants, so it carries no state between frames.
 */
export class Beats {
	now = 0;
	wait(t: number): number {
		this.now = Math.max(this.now, t);
		return this.now;
	}
	play(d: number): number {
		const start = this.now;
		this.now += d;
		return start;
	}
	/** wait(t), then play(d). */
	at(t: number, d: number): number {
		this.wait(t);
		return this.play(d);
	}
}
