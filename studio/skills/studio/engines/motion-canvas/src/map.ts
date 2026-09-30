// The map and close-up components, for Motion Canvas: the same look and rules as the Remotion kit.
// A map shows component names only, plus state (which box or arrow is lit, where the token is); a
// close-up is one component or record, full screen, opened from its box. Scenes drive them from
// `c.every`, so every frame is a function of time:
//
//   const map = new MapView(c, NODES, EDGES);
//   c.every((t) => map.update({visible: {client: ramp(t, 1, 0.5)}, lit: {server: ramp(t, 3, 0.4)}}));
import {Line, Node, Rect, Txt} from '@motion-canvas/2d';
import {Vector2} from '@motion-canvas/core';
import type {Ctx} from './kit';
import {AMBER, CORAL, DIM, ICE, INK, MONO, MUTED, PANEL, TRAY_EDGE, TRAY_FILL, band, layout, mix, pt, px, stageH, unit} from './base';

export type MapNode = {id: string; name: string; at: [number, number]; w?: number; h?: number};
export type MapEdge = {from: string; to: string};

const NODE_W = 2.4;
const NODE_H = 0.9;
const MIN_ZOOM = 0.55;
const MARGIN = 1.0;
const size = (n: MapNode): [number, number] => [n.w ?? NODE_W, n.h ?? NODE_H];

/** The smooth 0..1 ramp used across the kit (Manim's default easing). */
export function ramp(t: number, start: number, dur = 0.4): number {
	const c = dur <= 0 ? (t >= start ? 1 : 0) : Math.min(1, Math.max(0, (t - start) / dur));
	const sg = (v: number) => 1 / (1 + Math.exp(-v));
	return (sg(10 * (c - 0.5)) - sg(-5)) / (sg(5) - sg(-5));
}

/**
 * The camera frames the boxes that exist so far and stays centred as boxes appear, so early chapters
 * aren't top-heavy. A node contributes its box scaled toward the centroid by its visibility, which
 * keeps the frame continuous while a box fades in.
 */
export function frameCamera(nodes: MapNode[], visible: Record<string, number>) {
	const on = nodes.filter((n) => (visible[n.id] ?? 0) > 0.001);
	if (!on.length) return {cx: 0, cy: 0, zoom: 1};
	const cx0 = on.reduce((s, n) => s + n.at[0], 0) / on.length;
	const cy0 = on.reduce((s, n) => s + n.at[1], 0) / on.length;
	let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
	for (const n of on) {
		const v = Math.min(1, visible[n.id] ?? 0);
		const [w, h] = size(n);
		const x = cx0 + (n.at[0] - cx0) * v;
		const y = cy0 + (n.at[1] - cy0) * v;
		x0 = Math.min(x0, x - (w * v) / 2); x1 = Math.max(x1, x + (w * v) / 2);
		y0 = Math.min(y0, y - (h * v) / 2); y1 = Math.max(y1, y + (h * v) / 2);
	}
	const w = x1 - x0 + 2 * MARGIN;
	const h = y1 - y0 + 2 * MARGIN;
	const zoom = Math.min(1, Math.max(MIN_ZOOM, Math.min(layout.width / unit / w, stageH / unit / h)));
	return {cx: (x0 + x1) / 2, cy: (y0 + y1) / 2, zoom};
}

export type MapState = {
	visible: Record<string, number>; lit?: Record<string, number>; litEdges?: Record<string, number>;
	opacity?: number; frame?: boolean;
};

export class MapView {
	/** Everything the camera moves: add your own nodes here (a token, a label), in stage-unit positions via `unitPos`. */
	readonly cam = new Node({});
	private readonly parts: Record<string, {rect: Rect; label: Txt}> = {};
	private readonly lines: {key: string; from: string; to: string; line: Line}[] = [];

	constructor(c: Ctx, private readonly nodes: MapNode[], edges: MapEdge[] = []) {
		c.view.add(this.cam);
		const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
		for (const e of edges) {
			const line = new Line({points: [[0, 0], [0, 0]], stroke: DIM, lineWidth: 2, endArrow: true, arrowSize: 0.18 * unit, end: 0, opacity: 0});
			this.cam.add(line);
			this.lines.push({key: `${e.from}>${e.to}`, from: e.from, to: e.to, line});
		}
		for (const n of nodes) {
			const [w, h] = size(n);
			const rect = new Rect({position: this.at(n.at), width: w * unit, height: h * unit, radius: 0.12 * unit, stroke: TRAY_EDGE, lineWidth: 2,
				fill: TRAY_FILL, opacity: 0, key: `box:node ${n.name}`});
			const label = new Txt({text: n.name, position: this.at(n.at), fill: INK, fontSize: pt(20), fontFamily: MONO, opacity: 0, key: `box:${n.name}`});
			this.cam.add(rect);
			this.cam.add(label);
			this.parts[n.id] = {rect, label};
		}
		this.byId = byId;
	}

	private readonly byId: Record<string, MapNode>;

	/** A point in stage units, as a position inside the camera (before the camera moves it). */
	at(p: [number, number]) {
		return new Vector2(p[0] * unit, -p[1] * unit);
	}

	update(s: MapState) {
		const lit = s.lit ?? {};
		const cam = s.frame === false ? {cx: 0, cy: 0, zoom: 1} : frameCamera(this.nodes, s.visible);
		const centre = px(0, 0);
		this.cam.scale(cam.zoom);
		this.cam.position(new Vector2(centre.x - cam.cx * unit * cam.zoom, centre.y + cam.cy * unit * cam.zoom));
		this.cam.opacity(s.opacity ?? 1);
		for (const n of this.nodes) {
			const v = s.visible[n.id] ?? 0;
			const on = lit[n.id] ?? 0;
			const {rect, label} = this.parts[n.id];
			rect.opacity(v); label.opacity(v);
			rect.stroke(mix(TRAY_EDGE, ICE, on)); rect.lineWidth(2 + on); rect.fill(mix(TRAY_FILL, '#1D3242', on));
		}
		for (const l of this.lines) {
			const a = this.byId[l.from], b = this.byId[l.to];
			const v = Math.min(s.visible[l.from] ?? 0, s.visible[l.to] ?? 0);
			const [aw, ah] = size(a), [bw, bh] = size(b);
			const dx = b.at[0] - a.at[0], dy = b.at[1] - a.at[1];
			const horizontal = Math.abs(dx) >= Math.abs(dy);         // route along the dominant axis
			const sx = Math.sign(dx) || 1, sy = Math.sign(dy) || 1;
			const from: [number, number] = horizontal ? [a.at[0] + sx * (aw / 2 + 0.05), a.at[1]] : [a.at[0], a.at[1] + sy * (ah / 2 + 0.05)];
			const to: [number, number] = horizontal ? [b.at[0] - sx * (bw / 2 + 0.05), b.at[1]] : [b.at[0], b.at[1] - sy * (bh / 2 + 0.05)];
			const on = (s.litEdges ?? {})[l.key] ?? 0;
			l.line.points([this.at(from), this.at(to)]);
			l.line.stroke(mix(DIM, ICE, on)); l.line.lineWidth(2 + on); l.line.end(v); l.line.opacity(v > 0 ? 1 : 0);
		}
	}
}

export type TokenState = 'idle' | 'ok' | 'bad' | 'wait';
const GLYPH: Record<TokenState, [string, string]> = {idle: ['○', MUTED], ok: ['✓', ICE], bad: ['✕', CORAL], wait: ['…', AMBER]};

/** The thing the video follows: a token whose glyph shows its state. Keep it on screen. */
export class Token {
	private readonly ring: Rect;
	private readonly glyph: Txt;
	constructor(parent: Node, at: Vector2) {
		this.ring = new Rect({position: at, width: 0.5 * unit, height: 0.5 * unit, radius: 0.25 * unit, stroke: MUTED, lineWidth: 3, fill: PANEL, opacity: 0, key: 'box:token'});
		this.glyph = new Txt({text: '○', position: at, fill: MUTED, fontSize: pt(18), fontFamily: MONO, opacity: 0, key: 'box:token glyph'});
		parent.add(this.ring);
		parent.add(this.glyph);
	}
	set(state: TokenState, opacity = 1, at?: Vector2) {
		const [g, color] = GLYPH[state];
		this.ring.stroke(color); this.ring.opacity(opacity);
		this.glyph.text(g); this.glyph.fill(color); this.glyph.opacity(opacity);
		if (at) { this.ring.position(at); this.glyph.position(at); }
	}
}

/** A proposed change, drawn as a translucent copy of the thing it would replace. */
export class GhostCard {
	readonly rect: Rect;
	constructor(parent: Node, at: Vector2, w: number, h: number) {
		this.rect = new Rect({position: at, width: w * unit, height: h * unit, radius: 0.1 * unit, stroke: ICE, lineWidth: 2,
			fill: 'rgba(143, 211, 255, 0.10)', opacity: 0, key: 'box:ghost'});
		parent.add(this.rect);
	}
	set(opacity: number) {
		this.rect.opacity(opacity * 0.9);
	}
}

/**
 * A close-up: the source box grows into the stage, then `content` fades in inside it. The header is
 * the item's name only. A corner minimap has no labels and fills only the source box. Put your own
 * nodes in `content`, positioned in stage units with `px`.
 */
export class CloseUp {
	readonly content = new Node({});
	private readonly panel: Rect;
	private readonly header: Txt;
	private readonly mini: Rect[];
	constructor(c: Ctx, private readonly from: MapNode, name: string, private readonly nodes: MapNode[]) {
		this.panel = new Rect({radius: 0.16 * unit, stroke: TRAY_EDGE, lineWidth: 2.5, fill: PANEL, opacity: 0, key: 'box:close-up'});
		this.header = new Txt({text: name, fill: INK, fontSize: pt(24), fontWeight: 500, fontFamily: MONO, opacity: 0, key: `box:close-up ${name}`});
		this.mini = nodes.map((n) => new Rect({stroke: n.id === from.id ? ICE : MUTED, lineWidth: 1.5, fill: n.id === from.id ? ICE : null, radius: 0.03 * unit, opacity: 0, key: 'box:minimap'}));
		c.view.add(this.panel);
		c.view.add(this.content);
		c.view.add(this.header);
		this.mini.forEach((m) => c.view.add(m));
		this.content.opacity(0);
	}
	/** `open` runs 0 to 1. */
	update(open: number) {
		const [fw, fh] = size(this.from);
		const W = layout.width / unit - 0.6;
		const H = stageH / unit - 0.6;
		const k = Math.min(1, Math.max(0, open));
		const inner = Math.max(0, (open - 0.55) / 0.45);
		this.panel.opacity(Math.min(1, open * 3));
		this.panel.position(px(this.from.at[0] * (1 - k), this.from.at[1] * (1 - k)));
		this.panel.width((fw + (W - fw) * k) * unit);
		this.panel.height((fh + (H - fh) * k) * unit);
		this.header.opacity(inner);
		this.header.position(px(0, H / 2 - 0.35));
		this.content.opacity(inner);
		const mini = 3.2;
		const minis = mini / (2 * Math.max(...this.nodes.map((n) => Math.abs(n.at[0]) + size(n)[0] / 2), 1));
		this.nodes.forEach((n, i) => {
			const [w, h] = size(n);
			this.mini[i].opacity(inner);
			this.mini[i].position(px(W / 2 - mini / 2 - 0.15 + n.at[0] * minis, H / 2 - 0.4 + n.at[1] * minis));
			this.mini[i].width(w * minis * unit);
			this.mini[i].height(h * minis * unit);
		});
	}
}
