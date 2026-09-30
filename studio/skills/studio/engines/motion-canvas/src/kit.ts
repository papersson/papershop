// The Motion Canvas engine's scene kit: the same contract as the Remotion kit (a stage of
// 8 units tall above the caption band, cues from timeline.json), written for generator scenes.
import {makeScene2D, Rect, Txt, type Node} from '@motion-canvas/2d';
import {all, useScene, useThread, waitFor, Vector2, type ThreadGenerator} from '@motion-canvas/core';
import timeline from '@timeline';
import layout from '@layout';

export type LayoutJson = {width: number; height: number; fps: number; band: {height: number; style: string; font?: number; chars?: number}};
export type TimelineJson = {
	fps: number; duration: number; cues: Record<string, number>;
	tracks: {
		scene: {id: string; start: number; end: number}[];
		narration: {id: string; start: number; end: number; words: {w: string; start: number; end: number}[]}[];
		captions: {start: number; end: number; lines: string[]}[];
	};
};

export const BG = '#0F1318';
export const BAND = '#0A0D11';
export const INK = '#E6EBF0';
export const MUTED = '#8C97A4';
export const ICE = '#8FD3FF';
export const AMBER = '#F2A93B';
export const CORAL = '#E4715F';
export const SANS = 'IBM Plex Sans';
export const MONO = 'IBM Plex Mono';

const band = layout.band.height;
export const stageH = layout.height - band;
/** Pixels per stage unit: the stage is 8 units tall, as in the Remotion engine. */
export const unit = stageH / 8;
/** A point in stage units (origin at the stage centre, y up) as a view position in pixels. */
export const px = (x: number, y: number) => new Vector2(x * unit, -y * unit - band / 2);
/** A Manim-style font size in pixels (matches the Remotion kit's `pt`). */
export const pt = (size: number) => (size * unit * 1.82) / 135;

export type Ctx = {
	view: Node;
	clip: string;
	/** Seconds from the clip's start to sentence `id` ("03" is "<clip>_03"), plus an offset. */
	at: (id: string, off?: number) => number;
	end: (id: string, off?: number) => number;
	word: (id: string, i: number, off?: number) => number;
	cue: (name: string, off?: number) => number;
	dur: number;
	/** Wait until clip time t (does nothing if it has passed). */
	until: (t: number) => ThreadGenerator;
	now: () => number;
	/** A labelled text node at a stage point, reported by `studio boxes`. */
	text: (s: string, at: [number, number], o?: {size?: number; color?: string; font?: 'mono' | 'sans'; weight?: number; opacity?: number; name?: string}) => Txt;
	/** A labelled rectangle at a stage point, w and h in stage units. */
	box: (at: [number, number], w: number, h: number, o?: {fill?: string; stroke?: string; radius?: number; opacity?: number; name?: string}) => Rect;
};

const wrap = (text: string, chars: number) => {
	const lines: string[] = [];
	let cur: string[] = [];
	for (const w of text.split(/\s+/).filter(Boolean)) {
		if (cur.length && [...cur, w].join(' ').length > chars) {
			const carry: string[] = [];
			while (cur.length > 1 && ['the', 'a', 'an', 'of', 'to'].includes(cur[cur.length - 1].toLowerCase())) carry.unshift(cur.pop() as string);
			lines.push(cur.join(' '));
			cur = carry;
		}
		cur.push(w);
	}
	if (cur.length) lines.push(cur.join(' '));
	return lines;
};

/**
 * A scene for one clip of the timeline. Draws the background, runs `body`, and holds the frame
 * until the clip's end so consecutive clips tile the video exactly. The caption band and the
 * layers (all, no-captions, no-band, background) follow the project variable `layers`, so the
 * kit's band checks work here as they do in the Remotion engine.
 */
export function studioScene(clip: string, body: (c: Ctx) => ThreadGenerator) {
	return makeScene2D(function* (view) {
		const layers = String(useScene().variables.get('layers', 'all')());
		const T = timeline as TimelineJson;
		const me = T.tracks.scene.find((s) => s.id === clip);
		if (!me) throw new Error(`no clip ${clip} in timeline.json`);
		const dur = me.end - me.start;
		const sentence = (id: string) => {
			const full = id.includes('_') ? id : `${clip}_${id}`;
			const s = T.tracks.narration.find((n) => n.id === full);
			if (!s) throw new Error(`no sentence ${full} in timeline.json`);
			return s;
		};
		view.fill(BG);
		if (layers === 'background') {
			yield* waitFor(dur);
			return;
		}
		const ctx: Ctx = {
			view, clip, dur,
			at: (id, off = 0) => sentence(id).start - me.start + off,
			end: (id, off = 0) => sentence(id).end - me.start + off,
			word: (id, i, off = 0) => {
				const w = sentence(id).words[i];
				if (!w) throw new Error(`sentence ${id} has no word ${i}; run studio align`);
				return w.start - me.start + off;
			},
			cue: (name, off = 0) => {
				if (!(name in T.cues)) throw new Error(`no cue ${name} in timeline.json`);
				return T.cues[name] - me.start + off;
			},
			now: () => useThread().time(),
			*until(t: number) {
				const d = t - useThread().time();
				if (d > 1 / T.fps) yield* waitFor(d);
			},
			text: (s, at, o = {}) => {
				const n = new Txt({
					text: s, position: px(at[0], at[1]), fill: o.color ?? INK, fontSize: pt(o.size ?? 20),
					fontFamily: o.font === 'sans' ? SANS : MONO, fontWeight: o.weight ?? 400, opacity: o.opacity ?? 1, key: `box:${o.name ?? s}`,
				});
				view.add(n);
				return n;
			},
			box: (at, w, h, o = {}) => {
				const r = new Rect({
					position: px(at[0], at[1]), width: w * unit, height: h * unit, radius: (o.radius ?? 0) * unit,
					fill: o.fill ?? null, stroke: o.stroke ?? null, lineWidth: o.stroke ? 2 : 0, opacity: o.opacity ?? 1, key: `box:${o.name ?? 'rect'}`,
				});
				view.add(r);
				return r;
			},
		};
		const tasks: ThreadGenerator[] = [
			(function* () {
				yield* body(ctx);
				yield* ctx.until(dur);
			})(),
		];
		if (layers !== 'no-band') {
			view.add(new Rect({position: new Vector2(0, layout.height / 2 - band / 2), width: layout.width, height: band, fill: BAND}));
			if (layers === 'all') tasks.push(captions(view, me.start, me.end, T));
		}
		yield* all(...tasks);
	});
}

/** The caption band's text, changing at each chunk boundary of the timeline's captions track. */
function* captions(view: Node, start: number, end: number, T: TimelineJson): ThreadGenerator {
	const font = layout.band.font ?? 38;
	const chars = layout.band.chars ?? 42;
	const lines = new Txt({position: new Vector2(0, layout.height / 2 - band / 2), fill: INK, fontSize: font, fontFamily: SANS, lineHeight: font * 1.3, textAlign: 'center', key: 'caption'});
	view.add(lines);
	let t = 0;
	for (const c of T.tracks.captions.filter((x) => x.end > start && x.start < end)) {
		const a = Math.max(0, c.start - start);
		if (a > t) yield* waitFor(a - t);
		lines.text(wrap(c.lines.join(' '), chars).join('\n'));
		const b = Math.min(end - start, c.end - start);
		yield* waitFor(Math.max(0, b - Math.max(a, t)));
		lines.text('');
		t = b;
	}
}

/** Manim's smooth easing and closed-form springs, as in the Remotion kit. */
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
