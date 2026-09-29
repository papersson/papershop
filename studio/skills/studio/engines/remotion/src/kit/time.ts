import {createContext, useContext} from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import timeline from '@timeline';
import type {Timeline} from './types';

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
	const sentence = (id: string) => {
		const full = id.includes('_') ? id : `${clip}_${id}`;
		const s = T.tracks.narration.find((n) => n.id === full);
		if (!s) throw new Error(`no sentence ${full} in timeline.json`);
		return s;
	};
	return {
		t: frame / fps,
		fps,
		dur: durationInFrames / fps,
		/** Start of a sentence, in clip seconds, plus an offset. */
		at: (id: string, off = 0) => sentence(id).start - start + off,
		/** End of a sentence, in clip seconds, plus an offset. */
		end: (id: string, off = 0) => sentence(id).end - start + off,
		/** Start of the i-th word of a sentence (needs `studio align`). */
		word: (id: string, i: number, off = 0) => {
			const w = sentence(id).words[i];
			if (!w) throw new Error(`sentence ${id} has no word ${i}; run studio align`);
			return w.start - start + off;
		},
		cue: (name: string, off = 0) => {
			if (!(name in T.cues)) throw new Error(`no cue ${name} in timeline.json`);
			return T.cues[name] - start + off;
		},
	};
}

/** Manim's default "smooth" easing: a sigmoid rescaled to run exactly 0 → 1. */
export function smooth(x: number): number {
	const c = Math.min(1, Math.max(0, x));
	const s = (v: number) => 1 / (1 + Math.exp(-v));
	return (s(10 * (c - 0.5)) - s(-5)) / (s(5) - s(-5));
}

/** 0 before `start`, 1 after `start + dur`, eased in between. */
export function ramp(t: number, start: number, dur = 0.4, ease = smooth): number {
	return dur <= 0 ? (t >= start ? 1 : 0) : ease((t - start) / dur);
}

/** 0 → 1 → 0 over `dur`, for a momentary emphasis. */
export function pulse(t: number, start: number, dur = 0.8): number {
	const x = (t - start) / dur;
	return x <= 0 || x >= 1 ? 0 : Math.sin(Math.PI * x);
}

/** Closed-form damped spring from 0 to 1 (stiffness k, damping d): a pure function of time. */
export function spring(t: number, k = 170, d = 26): number {
	if (t <= 0) return 0;
	const w0 = Math.sqrt(k);
	const z = d / (2 * w0);
	if (z < 1) {
		const wd = w0 * Math.sqrt(1 - z * z);
		return 1 - Math.exp(-z * w0 * t) * (Math.cos(wd * t) + ((z * w0) / wd) * Math.sin(wd * t));
	}
	return 1 - Math.exp(-w0 * t) * (1 + w0 * t);
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
