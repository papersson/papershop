import React from 'react';
import {Txt, useStage, type XY} from './stage';
import {MUTED} from './theme';
import {ramp, useClip} from './time';

/** A small uppercase label. */
export const Label: React.FC<{at: XY; size?: number; color?: string; opacity?: number; anchor?: 'left' | 'center' | 'right'; children: string}> = ({
	at, size = 20, color = MUTED, opacity = 1, anchor = 'center', children,
}) => (
	<Txt at={at} size={size} color={color} weight={500} opacity={opacity} anchor={anchor}>{children.toUpperCase()}</Txt>
);

/** The chapter's name in the stage's top-left corner. */
export const Chip: React.FC<{text: string; opacity: number}> = ({text, opacity}) => {
	const s = useStage();
	return <Label at={[-s.width / 2 / s.unit + 0.45, 4 - 0.6]} anchor="left" opacity={opacity}>{text}</Label>;
};

/** Fades the whole scene out over its last half second, so consecutive chapters cut on the background. */
export const Chapter: React.FC<{children: React.ReactNode; outAt?: number}> = ({children, outAt}) => {
	const {t, dur} = useClip();
	const out = 1 - ramp(t, outAt ?? dur - 0.5, 0.45);
	return <div style={{position: 'absolute', inset: 0, opacity: out}}>{children}</div>;
};
