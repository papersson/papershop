import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {Arrow, Rect, Svg, Txt, useStage, type Stage, type XY} from './stage';
import {AMBER, CORAL, ICE, INK, MUTED, PANEL, TRAY_EDGE, TRAY_FILL, mix} from './theme';
import * as motion from '../../../shared/motion.js';
import {cameraAt, frameOn as fit} from '../../../shared/camera.js';

/**
 * The map is the system overview: component names only, plus state (which box or arrow is lit, where
 * the token is). The test for a map: any text on it that is not a component name is a bug. An idle
 * arrow is MUTED, at least 3:1 against the stage and panels, so a phone still shows the connection.
 * A close-up is one component or one record, full screen, opened from its box.
 */

export type MapNode = {id: string; name: string; at: XY; w?: number; h?: number};
export type MapEdge = {from: string; to: string};

const NODE_W = 2.4;
const NODE_H = 0.9;
const MIN_ZOOM = 0.55;
const MARGIN = 1.0;

const size = (n: MapNode): [number, number] => [n.w ?? NODE_W, n.h ?? NODE_H];
/** The stage's header strip in stage units (layout.json header.height; 0 when there is none). */
const headerOf = (s: Stage) => (s.header ?? 0) / s.unit;

/** A camera: the stage point it centres (below the header) and its zoom (1 = the stage as drawn). */
export type Framing = {cx: number; cy: number; zoom: number};
/** A camera key: [time in clip seconds, shot, ease of the move into it (a function or a name in `ease`)]. */
export type CamKey = [number, Framing, (motion.Ease | keyof typeof motion.ease)?];

/**
 * The camera at time t from keys in time order (engines/shared/camera.js): a key's ease shapes the
 * move into it, `inOut` by default as in live (not `ramp`'s `smooth`), so the same keys give the same
 * camera in both engines. The zoom moves in proportion and the centre in step with 1/zoom, so the
 * subject travels a straight line on screen. Before the first key the camera is the first, after the
 * last the last. Keys out of order, a zoom that isn't a finite number above 0 or an unknown ease throw.
 */
export function camAt(t: number, keys: CamKey[], ease?: motion.Ease | keyof typeof motion.ease): Framing {
	const c = cameraAt(t, keys.map(([time, k, e]): [number, {x: number; y: number; zoom: number}, CamKey[2]] => [time, {x: k.cx, y: k.cy, zoom: k.zoom}, e]), ease);
	return {cx: c.x, cy: c.y, zoom: c.zoom};
}

/**
 * The shot that fits a region [x0, y0, x1, y1] of stage units, with `margin` round it, into the stage
 * below its header: a "frame on" key for a camera.
 */
export function frameOn(s: Stage, region: [number, number, number, number],
	{margin = 0.5, min = 0.25, max = 4, headerInset}: {margin?: number; min?: number; max?: number; headerInset?: number} = {}): Framing {
	const c = fit(region, [s.width / s.unit, s.height / s.unit - (headerInset ?? headerOf(s))], {margin, min, max});
	return {cx: c.x, cy: c.y, zoom: c.zoom};
}

/**
 * The camera frames the boxes that exist so far and stays centred as boxes appear, so early chapters
 * aren't top-heavy. A node contributes its box scaled toward the centroid by its visibility, which
 * keeps the frame continuous while a box fades in. Returns the stage-unit centre and a zoom (1 = the
 * stage as drawn; less than 1 pulls back to fit). `headerInset` (stage units) is kept clear at the top:
 * the boxes fit the stage below it, and a Camera given the same inset centres them there.
 */
export function frameCamera(nodes: MapNode[], visible: Record<string, number>, stageUnits: [number, number], headerInset = 0): Framing {
	const all = nodes.filter((n) => (visible[n.id] ?? 0) > 0.001);
	if (!all.length) return {cx: 0, cy: 0, zoom: 1};
	const cx0 = all.reduce((s, n) => s + n.at[0], 0) / all.length;
	const cy0 = all.reduce((s, n) => s + n.at[1], 0) / all.length;
	let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
	for (const n of all) {
		const v = Math.min(1, visible[n.id] ?? 0);
		const [w, h] = size(n);
		const x = cx0 + (n.at[0] - cx0) * v;
		const y = cy0 + (n.at[1] - cy0) * v;
		x0 = Math.min(x0, x - (w * v) / 2); x1 = Math.max(x1, x + (w * v) / 2);
		y0 = Math.min(y0, y - (h * v) / 2); y1 = Math.max(y1, y + (h * v) / 2);
	}
	const c = fit([x0, y0, x1, y1], [stageUnits[0], stageUnits[1] - headerInset], {margin: MARGIN, min: MIN_ZOOM, max: 1});
	return {cx: c.x, cy: c.y, zoom: c.zoom};
}

/**
 * A wrapper that applies the camera: the point `cx`, `cy` is centred in the stage below the header, at
 * `zoom`. With `keys` ([time, {cx, cy, zoom}, ease?], see camAt) the camera moves on its own, so a
 * push-in, a pan or a move to a `frameOn` shot is one declaration, and any frame renders alone.
 * `headerInset` (stage units) defaults to the layout's header.
 */
export const Camera: React.FC<{cx?: number; cy?: number; zoom?: number; keys?: CamKey[]; ease?: motion.Ease; headerInset?: number;
	opacity?: number; children: React.ReactNode}> = ({cx = 0, cy = 0, zoom = 1, keys, ease, headerInset, opacity = 1, children}) => {
	const s = useStage();
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const shot = keys ? camAt(frame / fps, keys, ease) : {cx, cy, zoom};
	const y = shot.cy + (headerInset ?? headerOf(s)) / (2 * shot.zoom);    // the shot's centre, moved to the middle of the stage below the header
	return (
		<div data-camera={shot.zoom !== 1 || shot.cx !== 0 || shot.cy !== 0 ? '' : undefined} style={{position: 'absolute', inset: 0, opacity, transformOrigin: 'center',
			transform: `scale(${shot.zoom}) translate(${-shot.cx * s.unit}px, ${y * s.unit}px)`}}>
			{children}
		</div>
	);
};

/**
 * The map. With `frame` (the default) the camera frames the boxes shown so far, below the header
 * (`headerInset`, stage units, defaults to the layout's); without it the map is drawn where it is.
 * `accent` is the colour a lit box or arrow turns (ice, the thing being explained); `litMeans` tags a
 * lit box with that meaning from the video's colour legend, for the legend check.
 */
export const MapView: React.FC<{
	nodes: MapNode[]; edges?: MapEdge[]; visible: Record<string, number>; lit?: Record<string, number>;
	litEdges?: Record<string, number>; opacity?: number; frame?: boolean; headerInset?: number; accent?: string; litMeans?: string;
	children?: React.ReactNode;
}> = ({nodes, edges = [], visible, lit = {}, litEdges = {}, opacity = 1, frame = true, headerInset, accent = ICE, litMeans, children}) => {
	const s = useStage();
	const hi = frame ? headerInset ?? headerOf(s) : 0;
	const cam = frame ? frameCamera(nodes, visible, [s.width / s.unit, s.height / s.unit], hi) : {cx: 0, cy: 0, zoom: 1};
	const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
	const litFill = accent === ICE ? '#1D3242' : mix(TRAY_FILL, accent, 0.1);
	return (
		<Camera {...cam} headerInset={hi} opacity={opacity}>
			<Svg>
				{edges.map((e) => {
					const a = byId[e.from];
					const b = byId[e.to];
					const v = Math.min(visible[e.from] ?? 0, visible[e.to] ?? 0);
					if (!a || !b || v <= 0) return null;
					const [aw, ah] = size(a);
					const [bw, bh] = size(b);
					const dx = b.at[0] - a.at[0];
					const dy = b.at[1] - a.at[1];
					const horizontal = Math.abs(dx) >= Math.abs(dy);       // route along the dominant axis
					const sx = Math.sign(dx) || 1;
					const sy = Math.sign(dy) || 1;
					const from: XY = horizontal ? [a.at[0] + sx * (aw / 2 + 0.05), a.at[1]] : [a.at[0], a.at[1] + sy * (ah / 2 + 0.05)];
					const to: XY = horizontal ? [b.at[0] - sx * (bw / 2 + 0.05), b.at[1]] : [b.at[0], b.at[1] - sy * (bh / 2 + 0.05)];
					const on = litEdges[`${e.from}>${e.to}`] ?? 0;
					return (
						<Arrow key={`${e.from}>${e.to}`} from={from} to={to}
							color={mix(MUTED, accent, on)} width={2 + on} progress={v} />
					);
				})}
			</Svg>
			{nodes.map((n) => {
				const v = visible[n.id] ?? 0;
				const on = lit[n.id] ?? 0;
				const [w, h] = size(n);
				return (
					<React.Fragment key={n.id}>
						<Rect at={n.at} w={w} h={h} radius={0.12} stroke={mix(TRAY_EDGE, accent, on)} strokeWidth={2 + on}
							fill={mix(TRAY_FILL, litFill, on)} opacity={v} name={`node ${n.name}`} means={on > 0 ? litMeans : undefined} />
						<Txt at={n.at} size={20} color={INK} opacity={v} name={n.name}>{n.name}</Txt>
					</React.Fragment>
				);
			})}
			{children}
		</Camera>
	);
};

export type TokenState = 'idle' | 'ok' | 'bad' | 'wait';
const GLYPH: Record<TokenState, [string, string]> = {idle: ['○', MUTED], ok: ['✓', ICE], bad: ['✕', CORAL], wait: ['…', AMBER]};

/** The thing the video follows: a token whose glyph shows its state. Keep it on screen. `means` tags it (stage.tsx). */
export const Token: React.FC<{at: XY; state?: TokenState; opacity?: number; label?: string; means?: string}> = ({at, state = 'idle', opacity = 1, label, means}) => {
	const [glyph, color] = GLYPH[state];
	return (
		<>
			<Rect at={at} w={0.5} h={0.5} radius={0.25} stroke={color} strokeWidth={3} fill={PANEL} opacity={opacity} name="token" means={means} />
			<Txt at={at} size={18} color={color} opacity={opacity} name={`token ${state}`} means={means}>{glyph}</Txt>
			{label && <Txt at={[at[0], at[1] - 0.5]} size={14} color={MUTED} opacity={opacity}>{label}</Txt>}
		</>
	);
};

/** A proposed change, drawn as a translucent copy of the thing it would replace. `means` tags it (stage.tsx). */
export const GhostCard: React.FC<{at: XY; w: number; h: number; opacity?: number; means?: string; children?: React.ReactNode}> = ({at, w, h, opacity = 1, means, children}) => (
	<>
		<Rect at={at} w={w} h={h} radius={0.1} stroke={ICE} strokeWidth={2} fill="rgba(143, 211, 255, 0.10)" opacity={opacity * 0.9} name="ghost" means={means} />
		{children}
	</>
);

/**
 * A close-up: one component or record, full screen, opened from its box. `open` runs 0 to 1: the
 * source box grows into the stage below the header, then `children` fade in inside it. The header is
 * the item's name only. A corner minimap has no labels and fills only the source box, in `accent`.
 * Children are drawn on the whole stage, so a part can sit outside the panel; with `clip` they are
 * cut to the panel, grown by `bleed` stage units, so a part may cross its edge by that much and no
 * more. `headerInset` (stage units) defaults to the layout's header. `means` tags the minimap's filled
 * box with a meaning from the video's colour legend, as MapView's `litMeans` does its lit box.
 */
export const CloseUp: React.FC<{
	open: number; from: MapNode; name: string; nodes: MapNode[]; accent?: string; clip?: boolean; bleed?: number;
	headerInset?: number; means?: string; children: React.ReactNode;
}> = ({open, from, name, nodes, accent = ICE, clip = false, bleed = 0, headerInset, means, children}) => {
	const s = useStage();
	if (open <= 0) return null;
	const hi = headerInset ?? headerOf(s);
	const [fw, fh] = size(from);
	const W = s.width / s.unit - 0.6;
	const H = s.height / s.unit - 0.6 - hi;
	const y0 = -hi / 2;                                     // the open panel's centre: the middle of the stage below the header
	const k = Math.min(1, open);
	const at: XY = [from.at[0] * (1 - k), from.at[1] * (1 - k) + y0 * k];
	const pw = fw + (W - fw) * k;
	const ph = fh + (H - fh) * k;
	const inner = Math.max(0, (open - 0.55) / 0.45);
	const mini = s.width < s.height ? W * 0.28 : 3.2;       // minimap width, stage units; on a narrow stage, clear of the header
	const minis = mini / (2 * Math.max(...nodes.map((n) => Math.abs(n.at[0]) + size(n)[0] / 2), 1));
	// The panel as it is now, grown by the bleed: a CSS inset, and its box in stage pixels (data-clip), so
	// the boxes the checks get are the parts the clip shows.
	const cut = (() => {
		if (!clip) return undefined;
		const [cx, cy] = [s.width / 2 + at[0] * s.unit, s.height / 2 - at[1] * s.unit];
		const [hw, hh, r] = [(pw / 2 + bleed) * s.unit, (ph / 2 + bleed) * s.unit, (0.16 + bleed) * s.unit];
		return {css: `inset(${cy - hh}px ${s.width - cx - hw}px ${s.height - cy - hh}px ${cx - hw}px round ${Math.max(0, r)}px)`,
			box: [cx - hw, cy - hh, cx + hw, cy + hh].join(',')};
	})();
	return (
		<>
			<Rect at={at} w={pw} h={ph} radius={0.16} stroke={TRAY_EDGE} strokeWidth={2.5}
				fill={PANEL} opacity={Math.min(1, open * 3)} name="close-up" />
			<Txt at={[0, y0 + H / 2 - 0.35]} size={24} weight={500} opacity={inner} name={`close-up ${name}`}>{name}</Txt>
			<div data-clip={cut?.box} style={{opacity: inner, position: 'absolute', inset: 0, clipPath: cut?.css}}>{children}</div>
			<div style={{opacity: inner, position: 'absolute', inset: 0}}>
				{nodes.map((n) => {
					const [w, h] = size(n);
					const on = n.id === from.id;
					const p: XY = [W / 2 - mini / 2 - 0.15 + n.at[0] * minis, y0 + H / 2 - 0.4 + n.at[1] * minis];
					return <Rect key={n.id} at={p} w={w * minis} h={h * minis} radius={0.03} stroke={on ? accent : MUTED} strokeWidth={1.5}
						fill={on ? accent : 'transparent'} name="minimap" means={on ? means : undefined} />;
				})}
			</div>
		</>
	);
};
