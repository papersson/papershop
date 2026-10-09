// The Motion Canvas engine's scene kit: the same contract as the Remotion kit (a stage of
// 8 units tall above the caption band, cues from timeline.json), written for generator scenes.
// Everything is re-exported from here, so a scene imports `@studio-mc` and nothing else.
import {makeScene2D, Rect, Txt, type Node} from '@motion-canvas/2d';
import {all, useScene, useThread, waitFor, Vector2, type ThreadGenerator} from '@motion-canvas/core';
import timeline from '@timeline';
import layout from '@layout';
import {BAND, BG, INK, MONO, SANS, band, px, pt, unit, type TimelineJson} from './base';
import {captionLines, clipTimes, frameOf} from '../../shared/timing.js';

export * from './base';
export * from './map';
export * from './pixel';
export * from './shot';
export * from './footage';

export type Ctx = {
	view: Node;
	clip: string;
	/** Seconds from the clip's start to sentence `id` ("03" is "<clip>_03"), plus an offset. */
	at: (id: string, off?: number) => number;
	end: (id: string, off?: number) => number;
	word: (id: string, i: number, off?: number) => number;
	phrase: (id: string, text: string, off?: number) => number;
	cue: (name: string, off?: number) => number;
	dur: number;
	/** Wait until clip time t (does nothing if it has passed). */
	until: (t: number) => ThreadGenerator;
	now: () => number;
	/** Run `fn(t)` on every frame, t in clip seconds: set node properties from the time, and any frame renders alone. */
	every: (fn: (t: number) => void) => void;
	/** A URL for a file in the video's assets/ folder. */
	asset: (file: string) => string;
	/** A clip's start on the whole timeline, in seconds (footage segments are placed on it). */
	start: number;
	/** A labelled text node at a stage point, reported by `studio boxes`. */
	text: (s: string, at: [number, number], o?: {size?: number; color?: string; font?: 'mono' | 'sans'; weight?: number; opacity?: number; name?: string}) => Txt;
	/** A labelled rectangle at a stage point, w and h in stage units. */
	box: (at: [number, number], w: number, h: number, o?: {fill?: string; stroke?: string; radius?: number; opacity?: number; name?: string}) => Rect;
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
		const {at, end, word, phrase, cue} = clipTimes(T, clip, me.start);
		view.fill(BG);
		if (layers === 'background') {
			yield* waitFor(dur);
			return;
		}
		const ctx: Ctx = {
			view, clip, dur, start: me.start,
			every: () => {},
			asset: (file) => __STUDIO_ASSETS__ + file,
			at, end, word, phrase, cue,
			now: () => useThread().time(),
			// Whole frames, rounding halves up like the kit and the other engine, so a clip's scene lasts
			// exactly its timeline frames. A bare `yield` advances one frame, so counting frames is exact
			// (a thread's `time` is the exact sum of its waits, `fixed` the frame-quantised clock: only `fixed` counts frames).
			*until(t: number) {
				const fps = T.fps;
				const target = frameOf(t, fps);
				while (Math.round(useThread().fixed * fps) < target) yield;
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
		const ticks: ((t: number) => void)[] = [];
		ctx.every = (fn) => {
			ticks.push(fn);
			fn(useThread().time());
		};
		// Runs every registered per-frame update, then lets the frame render: each update is a function of
		// the clip time, so any frame is the same however it is reached.
		yield (function* () {
			for (;;) {
				const t = useThread().time();
				for (const f of ticks) f(t);
				yield;
			}
		})();
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
	const lines = new Txt({position: new Vector2(0, layout.height / 2 - band / 2), fill: INK, fontSize: font, fontFamily: SANS, lineHeight: font * 1.3, textAlign: 'center', key: 'caption'});
	view.add(lines);
	let t = 0;
	for (const c of T.tracks.captions.filter((x) => x.end > start && x.start < end)) {
		const a = Math.max(0, c.start - start);
		if (a > t) yield* waitFor(a - t);
		lines.text(captionLines(c, layout).join('\n'));
		const b = Math.min(end - start, c.end - start);
		yield* waitFor(Math.max(0, b - Math.max(a, t)));
		lines.text('');
		t = b;
	}
}

