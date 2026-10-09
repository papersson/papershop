import React from 'react';
import {Arrow, Rect, Svg, Txt, useStage, type XY} from './stage';
import {AMBER, CORAL, ICE, INK, MUTED, PANEL, TRAY_EDGE, TRAY_FILL, mix} from './theme';

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

/**
 * The camera frames the boxes that exist so far and stays centred as boxes appear, so early chapters
 * aren't top-heavy. A node contributes its box scaled toward the centroid by its visibility, which
 * keeps the frame continuous while a box fades in. Returns the stage-unit centre and a zoom (1 = the
 * stage as drawn; less than 1 pulls back to fit).
 */
export function frameCamera(nodes: MapNode[], visible: Record<string, number>, stageUnits: [number, number]) {
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
	const w = x1 - x0 + 2 * MARGIN;
	const h = y1 - y0 + 2 * MARGIN;
	const zoom = Math.min(1, Math.max(MIN_ZOOM, Math.min(stageUnits[0] / w, stageUnits[1] / h)));
	return {cx: (x0 + x1) / 2, cy: (y0 + y1) / 2, zoom};
}

/** A wrapper that applies the camera: `cx`, `cy` become the stage centre, at `zoom`. */
export const Camera: React.FC<{cx: number; cy: number; zoom: number; opacity?: number; children: React.ReactNode}> = ({
	cx, cy, zoom, opacity = 1, children,
}) => {
	const s = useStage();
	return (
		<div style={{position: 'absolute', inset: 0, opacity, transformOrigin: 'center',
			transform: `scale(${zoom}) translate(${-cx * s.unit}px, ${cy * s.unit}px)`}}>
			{children}
		</div>
	);
};

export const MapView: React.FC<{
	nodes: MapNode[]; edges?: MapEdge[]; visible: Record<string, number>; lit?: Record<string, number>;
	litEdges?: Record<string, number>; opacity?: number; frame?: boolean; children?: React.ReactNode;
}> = ({nodes, edges = [], visible, lit = {}, litEdges = {}, opacity = 1, frame = true, children}) => {
	const s = useStage();
	const cam = frame ? frameCamera(nodes, visible, [s.width / s.unit, s.height / s.unit]) : {cx: 0, cy: 0, zoom: 1};
	const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
	return (
		<Camera {...cam} opacity={opacity}>
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
							color={mix(MUTED, ICE, on)} width={2 + on} progress={v} />
					);
				})}
			</Svg>
			{nodes.map((n) => {
				const v = visible[n.id] ?? 0;
				const on = lit[n.id] ?? 0;
				const [w, h] = size(n);
				return (
					<React.Fragment key={n.id}>
						<Rect at={n.at} w={w} h={h} radius={0.12} stroke={mix(TRAY_EDGE, ICE, on)} strokeWidth={2 + on}
							fill={mix(TRAY_FILL, '#1D3242', on)} opacity={v} name={`node ${n.name}`} />
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

/** The thing the video follows: a token whose glyph shows its state. Keep it on screen. */
export const Token: React.FC<{at: XY; state?: TokenState; opacity?: number; label?: string}> = ({at, state = 'idle', opacity = 1, label}) => {
	const [glyph, color] = GLYPH[state];
	return (
		<>
			<Rect at={at} w={0.5} h={0.5} radius={0.25} stroke={color} strokeWidth={3} fill={PANEL} opacity={opacity} name="token" />
			<Txt at={at} size={18} color={color} opacity={opacity} name={`token ${state}`}>{glyph}</Txt>
			{label && <Txt at={[at[0], at[1] - 0.5]} size={14} color={MUTED} opacity={opacity}>{label}</Txt>}
		</>
	);
};

/** A proposed change, drawn as a translucent copy of the thing it would replace. */
export const GhostCard: React.FC<{at: XY; w: number; h: number; opacity?: number; children?: React.ReactNode}> = ({at, w, h, opacity = 1, children}) => (
	<>
		<Rect at={at} w={w} h={h} radius={0.1} stroke={ICE} strokeWidth={2} fill="rgba(143, 211, 255, 0.10)" opacity={opacity * 0.9} name="ghost" />
		{children}
	</>
);

/**
 * A close-up: one component or record, full screen, opened from its box. `open` runs 0 to 1: the
 * source box grows into the stage, then `children` fade in inside it. The header is the item's
 * name only. A corner minimap has no labels and fills only the source box.
 */
export const CloseUp: React.FC<{
	open: number; from: MapNode; name: string; nodes: MapNode[]; children: React.ReactNode;
}> = ({open, from, name, nodes, children}) => {
	const s = useStage();
	if (open <= 0) return null;
	const [fw, fh] = size(from);
	const W = s.width / s.unit - 0.6;
	const H = s.height / s.unit - 0.6;
	const k = Math.min(1, open);
	const at: XY = [from.at[0] * (1 - k), from.at[1] * (1 - k)];
	const inner = Math.max(0, (open - 0.55) / 0.45);
	const mini = 3.2;                                       // minimap width, stage units
	const minis = mini / (2 * Math.max(...nodes.map((n) => Math.abs(n.at[0]) + size(n)[0] / 2), 1));
	return (
		<>
			<Rect at={at} w={fw + (W - fw) * k} h={fh + (H - fh) * k} radius={0.16} stroke={TRAY_EDGE} strokeWidth={2.5}
				fill={PANEL} opacity={Math.min(1, open * 3)} name="close-up" />
			<Txt at={[0, H / 2 - 0.35]} size={24} weight={500} opacity={inner} name={`close-up ${name}`}>{name}</Txt>
			<div style={{opacity: inner, position: 'absolute', inset: 0}}>{children}</div>
			<div style={{opacity: inner, position: 'absolute', inset: 0}}>
				{nodes.map((n) => {
					const [w, h] = size(n);
					const on = n.id === from.id;
					const p: XY = [W / 2 - mini / 2 - 0.15 + n.at[0] * minis, H / 2 - 0.4 + n.at[1] * minis];
					return <Rect key={n.id} at={p} w={w * minis} h={h * minis} radius={0.03} stroke={on ? ICE : MUTED} strokeWidth={1.5}
						fill={on ? ICE : 'transparent'} name="minimap" />;
				})}
			</div>
		</>
	);
};
