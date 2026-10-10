import React, {createContext, useContext} from 'react';
import {INK, MONO, SANS} from './theme';

/**
 * The stage is the frame above the caption band. Scenes place things in stage units: the origin is
 * the stage's centre, y points up, and the stage is 8 units tall (Manim's convention, so scenes
 * port across). Text sizes are in the same points Manim scenes used; `pt` converts to pixels.
 * `header` is the strip at the stage's top, in pixels, that framing keeps clear (layout.json
 * `header.height`, 0 by default): the camera, the map's framing and a close-up fit below it.
 */
export type Stage = {width: number; height: number; unit: number; header?: number};
export const StageContext = createContext<Stage>({width: 1920, height: 920, unit: 115});
export const useStage = () => useContext(StageContext);

export type XY = [number, number];

export function toPx(s: Stage, [x, y]: XY): [number, number] {
	return [s.width / 2 + x * s.unit, s.height / 2 - y * s.unit];
}

/** A Manim font size in pixels on this stage (matched against a Manim render: mono text spans the same share of its box). */
export const pt = (s: Stage, size: number) => size * s.unit * (1.82 / 135);

type Anchor = 'center' | 'left' | 'right';
const SHIFT: Record<Anchor, string> = {center: '-50%', left: '0%', right: '-100%'};

/**
 * Text at a stage point. `anchor` picks which edge sits on x. `name` labels it for `boxes`;
 * unnamed text is reported by its content.
 */
export const Txt: React.FC<{
	at: XY; size?: number; color?: string; font?: 'mono' | 'sans'; weight?: number; anchor?: Anchor;
	rotate?: number; opacity?: number; scale?: number; dx?: number; dy?: number; name?: string;
	children: React.ReactNode;
}> = ({at, size = 20, color = INK, font = 'mono', weight = 400, anchor = 'center', rotate = 0, opacity = 1,
	scale = 1, dx = 0, dy = 0, name, children}) => {
	const s = useStage();
	const [left, top] = toPx(s, [at[0] + dx, at[1] + dy]);
	if (opacity <= 0) return null;
	return (
		<div
			data-box={name ?? String(children)}
			data-kind="text"
			style={{
				position: 'absolute', left, top, whiteSpace: 'pre', color, opacity, lineHeight: 1,
				fontFamily: font === 'mono' ? MONO : SANS, fontSize: pt(s, size), fontWeight: weight,
				transform: `translate(${SHIFT[anchor]}, -50%) rotate(${-rotate}rad) scale(${scale})`,
				transformOrigin: `${anchor === 'center' ? 'center' : anchor} center`,
			}}
		>
			{children}
		</div>
	);
};

/** A rectangle centred at a stage point, w×h stage units. */
export const Rect: React.FC<{
	at: XY; w: number; h: number; radius?: number; stroke?: string; strokeWidth?: number; fill?: string;
	opacity?: number; scale?: number; name?: string; dashed?: boolean;
}> = ({at, w, h, radius = 0, stroke = 'transparent', strokeWidth = 2, fill = 'transparent', opacity = 1,
	scale = 1, name, dashed}) => {
	const s = useStage();
	const [cx, cy] = toPx(s, at);
	if (opacity <= 0) return null;
	return (
		<div
			data-box={name ?? 'rect'}
			data-default={name === undefined ? '' : undefined}
			style={{
				position: 'absolute', left: cx - (w * s.unit) / 2, top: cy - (h * s.unit) / 2,
				width: w * s.unit, height: h * s.unit, borderRadius: radius * s.unit, background: fill,
				border: `${strokeWidth}px ${dashed ? 'dashed' : 'solid'} ${stroke}`, boxSizing: 'border-box',
				opacity, transform: `scale(${scale})`,
			}}
		/>
	);
};

/** One SVG layer the size of the stage, for lines and arrows. */
export const Svg: React.FC<{children: React.ReactNode; opacity?: number}> = ({children, opacity = 1}) => {
	const s = useStage();
	return (
		<svg width={s.width} height={s.height} style={{position: 'absolute', left: 0, top: 0, overflow: 'visible', opacity}}>
			{children}
		</svg>
	);
};

/** A line from a to b, drawn up to `progress` (0..1), with an arrow tip when `tip` > 0. */
export const Arrow: React.FC<{
	from: XY; to: XY; color?: string; width?: number; progress?: number; tip?: number; dash?: number;
}> = ({from, to, color = INK, width = 3, progress = 1, tip = 0.18, dash}) => {
	const s = useStage();
	if (progress <= 0) return null;
	const [x1, y1] = toPx(s, from);
	const [bx, by] = toPx(s, to);
	const x2 = x1 + (bx - x1) * progress;
	const y2 = y1 + (by - y1) * progress;
	const len = Math.hypot(x2 - x1, y2 - y1);
	const tl = Math.min(tip * s.unit, len * 0.5);
	const ux = (x2 - x1) / (len || 1);
	const uy = (y2 - y1) / (len || 1);
	const base = [x2 - ux * tl, y2 - uy * tl];
	const half = tl * 0.5;
	return (
		<g>
			<line x1={x1} y1={y1} x2={tip > 0 ? base[0] : x2} y2={tip > 0 ? base[1] : y2} stroke={color}
				strokeWidth={width} strokeDasharray={dash ? `${dash * s.unit} ${dash * s.unit}` : undefined} />
			{tip > 0 && (
				<polygon fill={color}
					points={`${x2},${y2} ${base[0] - uy * half},${base[1] + ux * half} ${base[0] + uy * half},${base[1] - ux * half}`} />
			)}
		</g>
	);
};
