// The Motion Canvas engine's scene kit: the same contract as the Remotion kit (a stage of
// 8 units tall above the caption band, cues from timeline.json), written for generator scenes.
import {Vector2} from '@motion-canvas/core';
import timeline from '@timeline';
import layout from '@layout';

export type LayoutJson = {width: number; height: number; fps: number; format?: string; band: {height: number; style: string; font?: number; chars?: number}};
export type NarrationEntry = {id: string; start: number; end: number; caption?: string; text?: string; words: {w: string; start: number; end: number}[]};

const norm = (w: string) => w.toLowerCase().replace(/[^\p{L}\p{N}_]/gu, '');

/**
 * When a sentence reaches a phrase, in timeline seconds: its words matched in the spoken words, or,
 * where a spoken rule rewrote them, its place in the caption. Same rule as timeline.phrase_start.
 */
export function phraseStart(s: NarrationEntry, phrase: string): number {
	const want = phrase.split(/\s+/).map(norm).filter(Boolean);
	const got = (s.words ?? []).map((w) => norm(w.w));
	for (let i = 0; want.length && i + want.length <= got.length; i++) {
		if (want.every((w, j) => got[i + j] === w)) return s.words[i].start;
	}
	const cap = s.caption ?? s.text ?? '';
	const k = cap.indexOf(phrase);
	if (k < 0) throw new Error(`sentence ${s.id} has no phrase "${phrase}"`);
	return s.start + (k / Math.max(1, cap.length)) * (s.end - s.start);
}

export type TimelineJson = {
	fps: number; duration: number; cues: Record<string, number>;
	tracks: {
		scene: {id: string; start: number; end: number}[];
		narration: NarrationEntry[];
		captions: {start: number; end: number; lines: string[]; wrapped?: Record<string, string[]>}[];
	};
};

export {layout};
export const BG = '#0F1318';
export const BAND = '#0A0D11';
export const INK = '#E6EBF0';
export const MUTED = '#8C97A4';
export const ICE = '#8FD3FF';
export const AMBER = '#F2A93B';
export const CORAL = '#E4715F';
export const SANS = 'IBM Plex Sans';
export const MONO = 'IBM Plex Mono';

export const band = layout.band.height;
export const stageH = layout.height - band;
/** Pixels per stage unit: the stage is 8 units tall, as in the Remotion engine. */
export const unit = stageH / 8;
/** A point in stage units (origin at the stage centre, y up) as a view position in pixels. */
export const px = (x: number, y: number) => new Vector2(x * unit, -y * unit - band / 2);
/** A Manim-style font size in pixels (matches the Remotion kit's `pt`). */
export const pt = (size: number) => (size * unit * 1.82) / 135;

/** Linear blend of two #rrggbb colours, k in 0..1. */
export function mix(a: string, b: string, k: number): string {
	const p = (c: string, i: number) => parseInt(c.slice(1 + 2 * i, 3 + 2 * i), 16);
	const kk = Math.min(1, Math.max(0, k));
	const ch = (i: number) => Math.round(p(a, i) + (p(b, i) - p(a, i)) * kk);
	return '#' + [0, 1, 2].map((i) => ch(i).toString(16).padStart(2, '0')).join('');
}

export const DIM = '#2B333C';
export const FAINT = '#56606B';
export const PANEL = '#151B22';
export const TRAY_FILL = '#17202A';
export const TRAY_EDGE = '#C9D3DD';

/** A closed-form damped spring from 0 to 1, as in the Remotion kit: a pure function of time. */
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

/** A value that changes target several times: one spring per change, so any frame renders alone. */
export function track(t: number, keys: [number, number][], k = 170, d = 26): number {
	let v = keys[0][1];
	for (let i = 1; i < keys.length; i++) v += (keys[i][1] - keys[i - 1][1]) * spring(t - keys[i][0], k, d);
	return v;
}

/** Text inside a morphing container: in just after the morph starts, out just before the next one. */
export function swapAlpha(t: number, tIn: number, tOut: number): number {
	const clamp = (x: number) => Math.min(1, Math.max(0, x));
	return Math.min(clamp((t - tIn - 0.08) / 0.12), clamp((tOut - 0.1 - t) / 0.1));
}

/** Wrap time so a piece loops seamlessly. */
export const loopT = (t: number, dur: number) => ((t % dur) + dur) % dur;

/** Seeded noise (mulberry32), never Math.random: a render must be identical every run. */
export function rng(seed: number): () => number {
	return () => {
		seed |= 0;
		seed = (seed + 0x6d2b79f5) | 0;
		let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
		t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
		return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
	};
}
