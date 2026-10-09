// The Motion Canvas engine's scene kit: the same contract as the Remotion kit (a stage of
// 8 units tall above the caption band, cues from timeline.json), written for generator scenes.
import {Vector2} from '@motion-canvas/core';
import timeline from '@timeline';
import layout from '@layout';

// The motion maths and narration times are the engines' shared modules (engines/shared/). `mix`
// here blends #rrggbb colours, unlike the live kit's array mix.
export {spring, track, swapAlpha, loopT, rng} from '../../shared/motion.js';
export {phraseStart} from '../../shared/timing.js';

export type LayoutJson = {width: number; height: number; fps: number; format?: string; band: {height: number; style: string; font?: number; chars?: number}};
export type NarrationEntry = {id: string; start: number; end: number; caption?: string; text?: string; words: {w: string; start: number; end: number}[]};

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
