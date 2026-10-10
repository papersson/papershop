import React from 'react';
import {Arrow, Rect, Svg, Txt, kitMeans, type XY} from './stage';
import {CORAL, ICE, INK, MUTED, PANEL, TRAY_EDGE, TRAY_FILL, mix} from './theme';
import {ramp, spring} from './time';

/**
 * The building blocks explainer scenes kept rewriting: a labelled box, a connector, a code or text
 * card, a panel, a terminal line, a stack of layers. Writing them per video was a large share of a
 * build's scene time, and copies drifted; they live here so a chapter is mostly layout and timing.
 * All take stage units and an opacity, and follow the colour rules in style.md: ice for the thing
 * explained, amber for a number to watch, coral for failure only, neutral otherwise.
 */

/** A linear 0..1 progress, clamped (an unclamped linear ease overshoots past its end). */
export const lin = (t: number, start: number, dur: number) => Math.max(0, Math.min(1, (t - start) / Math.max(dur, 1e-6)));

/** Visible from sentence `a` until sentence `b` starts, fading in and out; `b` omitted: to the end. */
export function span(t: number, at: (id: string, off?: number) => number, a: string, b?: string, aOff = 0, bOff = -0.3) {
	const i = ramp(t, at(a, aOff), 0.45);
	return b ? i * (1 - ramp(t, at(b, bOff), 0.4)) : i;
}

/** A labelled box. `lit` turns it ice; `bad` coral; `sub` is a smaller second line; `means` tags the box and its text (stage.tsx). */
export const Box: React.FC<{at: XY; w: number; h?: number; text: string; opacity?: number; lit?: number; bad?: number; size?: number;
	color?: string; sub?: string; name?: string; means?: string}> = ({at, w, h = 0.8, text, opacity = 1, lit = 0, bad = 0, size = 18, color, sub, name, means}) => {
	if (opacity <= 0) return null;
	const edge = bad ? CORAL : color ?? mix(TRAY_EDGE, ICE, lit);
	means = kitMeans(means, bad || (lit && !color));
	return (
		<>
			<Rect at={at} w={w} h={h} radius={0.1} stroke={edge} strokeWidth={2 + lit} fill={TRAY_FILL} opacity={opacity} name={name ?? `box ${text}`} means={means} />
			<Txt at={[at[0], at[1] + (sub ? 0.15 : 0)]} size={size} color={bad ? CORAL : color ?? mix(INK, ICE, lit)} opacity={opacity} means={means}>{text}</Txt>
			{sub && <Txt at={[at[0], at[1] - 0.22]} size={14} color={MUTED} opacity={opacity} means={means}>{sub}</Txt>}
		</>
	);
};

/** A connector with an arrowhead (tip 0 for a plain line), drawn up to `progress`. */
export const Link: React.FC<{from: XY; to: XY; opacity?: number; color?: string; width?: number; progress?: number; tip?: number}> = ({
	from, to, opacity = 1, color = MUTED, width = 2, progress = 1, tip = 0.14,
}) => (opacity > 0 ? <Svg opacity={opacity}><Arrow from={from} to={to} color={color} width={width} progress={progress} tip={tip} /></Svg> : null);

/** A card of text or code lines; `lit` and `bad` per line (0..1). Its height follows the lines. `means` tags the lit and failed lines. */
export const Card: React.FC<{at: XY; w: number; lines: string[]; lit?: number[]; bad?: number[]; opacity?: number; size?: number;
	name?: string; means?: string}> = ({at, w, lines, lit = [], bad = [], opacity = 1, size = 18, name = 'card', means}) => {
	if (opacity <= 0) return null;
	const lh = size * 0.031;
	const h = lh * lines.length + 0.5;
	return (
		<>
			<Rect at={at} w={w} h={h} radius={0.12} stroke={TRAY_EDGE} strokeWidth={2} fill={TRAY_FILL} opacity={opacity} name={name} />
			{lines.map((l, i) => (
				<Txt key={i} at={[at[0] - w / 2 + 0.4, at[1] + h / 2 - 0.25 - lh / 2 - i * lh]} anchor="left" size={size}
					color={mix(mix(MUTED, ICE, lit[i] ?? 0), CORAL, bad[i] ?? 0)} opacity={opacity} name={`${name} line ${i + 1}`}
					means={kitMeans(means, lit[i] || bad[i])}>{l}</Txt>
			))}
		</>
	);
};

/** A framed region with a small title in its top-left corner. Its box is named `name`, else after its title. */
export const Panel: React.FC<{at: XY; w: number; h: number; opacity?: number; title?: string; stroke?: string; name?: string}> = ({
	at, w, h, opacity = 1, title, stroke = TRAY_EDGE, name,
}) => (opacity > 0 ? (
	<>
		<Rect at={at} w={w} h={h} radius={0.16} stroke={stroke} strokeWidth={2} fill={PANEL} opacity={opacity} name={name ?? (title ? `panel ${title}` : 'panel')} />
		{title && <Txt at={[at[0] - w / 2 + 0.3, at[1] + h / 2 - 0.32]} anchor="left" size={16} color={stroke === TRAY_EDGE ? MUTED : stroke} opacity={opacity}>{title}</Txt>}
	</>
) : null);

/** A terminal line: `$ command`. */
export const Term: React.FC<{at: XY; w: number; text: string; opacity?: number; size?: number}> = ({at, w, text, opacity = 1, size = 17}) => (
	opacity > 0 ? (
		<>
			<Rect at={at} w={w} h={0.62} radius={0.08} stroke={TRAY_EDGE} strokeWidth={1.5} fill="#0B0F13" opacity={opacity} name={`term ${text}`} />
			<Txt at={[at[0] - w / 2 + 0.3, at[1]]} anchor="left" size={size} color={INK} opacity={opacity}>{`$ ${text}`}</Txt>
		</>
	) : null
);

/** A vertical stack of layers (top first); `focus` lights one, by index, and `means` tags it. */
export const Stack: React.FC<{at: XY; layers: string[]; focus?: number; opacity?: number; w?: number; h?: number; gap?: number; means?: string}> = ({
	at, layers, focus = -1, opacity = 1, w = 5.2, h = 0.8, gap = 0.22, means,
}) => {
	if (opacity <= 0) return null;
	const top = at[1] + ((layers.length - 1) / 2) * (h + gap);
	return (
		<>
			{layers.map((l, i) => (
				<Box key={l} at={[at[0], top - i * (h + gap)]} w={w} h={h} text={l} opacity={opacity} lit={focus === i ? 1 : 0} name={`layer ${l}`}
					means={focus === i ? means : undefined} />
			))}
		</>
	);
};

/** A value that moves to each target in turn with a spring: one spring per move. */
export const steps = (t: number, cues: number[]) => cues.reduce((d, c) => d + spring(Math.max(0, t - c)), 0);
