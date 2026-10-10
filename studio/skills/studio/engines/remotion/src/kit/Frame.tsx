import '@fontsource/ibm-plex-sans/400.css';
import '@fontsource/ibm-plex-sans/500.css';
import '@fontsource/ibm-plex-sans/600.css';
import '@fontsource/ibm-plex-mono/400.css';
import '@fontsource/ibm-plex-mono/500.css';
import React, {useLayoutEffect, useRef, useState} from 'react';
import {AbsoluteFill, continueRender, delayRender, useCurrentFrame, useVideoConfig} from 'remotion';
import layout from '@layout';
import timeline from '@timeline';
import {StageContext} from './stage';
import {ClipContext} from './time';
import {BAND, BG, INK, SANS} from './theme';
import type {Layout, Timeline} from './types';
import {captionLines} from '../../../shared/timing.js';

// all; no-captions (band, no caption text); no-band (the scene alone, no band); background (nothing but the background).
export type Layers = 'all' | 'no-captions' | 'no-band' | 'background';

export const FONTS = ['400 20px "IBM Plex Sans"', '500 20px "IBM Plex Sans"', '600 20px "IBM Plex Sans"',
	'400 20px "IBM Plex Mono"', '500 20px "IBM Plex Mono"'];

/**
 * Every clip renders inside a Frame: the background, the stage the scene draws on, and the caption
 * band below it, which belongs to the captions track alone. The layers prop drops parts of this for
 * the band checks. With reportBoxes, the frame logs every labelled element's pixel box, with its
 * colours and meaning tag (paint).
 */
/**
 * An element's colours as the browser resolves them ("rgb(…)"), for the legend check: a text's is its
 * colour; a box's its background and, when it has a border, the border's; an SVG node's its fill
 * and stroke. `means` is its data-means tag (Txt, Rect and Box take a `means` prop).
 */
function paint(el: Element) {
	const st = getComputedStyle(el);
	const means = el.getAttribute('data-means');
	const colours = el instanceof SVGElement ? {fill: st.fill, stroke: st.stroke}
		: el.getAttribute('data-kind') === 'text' ? {fill: st.color, stroke: 'none'}
		: {fill: st.backgroundColor, stroke: parseFloat(st.borderTopWidth) > 0 && st.borderTopStyle !== 'none' ? st.borderTopColor : 'none'};
	return {...colours, ...(means ? {means} : {})};
}

export const Frame: React.FC<{clip: string; first: number; layers: Layers; reportBoxes?: boolean; children: React.ReactNode}> = ({
	clip, first, layers, reportBoxes, children,
}) => {
	const l = layout as Layout;
	const {fps} = useVideoConfig();
	const [fontsHandle] = useState(() => delayRender('fonts'));
	const [ready, setReady] = useState(false);
	useLayoutEffect(() => {
		Promise.all(FONTS.map((f) => document.fonts.load(f))).then(() => {
			setReady(true);
			continueRender(fontsHandle);
		});
	}, [fontsHandle]);
	const stageH = l.height - l.band.height;
	const stage = {width: l.width, height: stageH, unit: stageH / 8, header: l.header?.height ?? 0};
	const root = useRef<HTMLDivElement>(null);
	const frame = useCurrentFrame();
	useLayoutEffect(() => {
		if (!reportBoxes || !ready || !root.current) return;
		const origin = root.current.getBoundingClientRect();
		// opacity: the element's own times its ancestors', so a check can tell a faded-out element from a shown one.
		const shown = (el: HTMLElement) => {
			let o = 1;
			for (let n: HTMLElement | null = el; n && n !== root.current; n = n.parentElement) o *= Number(getComputedStyle(n).opacity);
			return o;
		};
		// A box inside a clip (a CloseUp with clip: data-clip, the clip's box in stage pixels) is the part
		// the clip shows; one it hides entirely is left out.
		const clipped = (el: HTMLElement, x: number, y: number, w: number, h: number) => {
			const c = el.closest<HTMLElement>('[data-clip]')?.dataset.clip?.split(',').map(Number);
			if (!c) return {x, y, w, h};
			const [x0, y0, x1, y1] = [Math.max(x, c[0]), Math.max(y, c[1]), Math.min(x + w, c[2]), Math.min(y + h, c[3])];
			return x1 > x0 && y1 > y0 ? {x: x0, y: y0, w: x1 - x0, h: y1 - y0} : null;
		};
		const boxes = [...root.current.querySelectorAll<HTMLElement>('[data-box],[data-caption]')].flatMap((el) => {
			const r = el.getBoundingClientRect();
			const at = clipped(el, r.left - origin.left, r.top - origin.top, r.width, r.height);
			if (!at) return [];
			return [{name: el.dataset.box ?? 'caption', kind: el.dataset.kind ?? '', ...at,
				// camera: under a Camera that has moved (data-camera), whose crop is the inframe check's, not bounds'
				opacity: shown(el), camera: !!el.closest('[data-camera]'),
				// named: false for a shape given no name of its own (reported as "rect"), which bounds leaves alone
				...(el.hasAttribute('data-default') ? {named: false} : {}), ...paint(el)}];
		});
		console.log('STUDIO_BOXES ' + JSON.stringify({band: {y: stageH, h: l.band.height}, boxes}));
	}, [reportBoxes, ready, frame, stageH, l.band.height]);
	return (
		<AbsoluteFill ref={root} style={{background: BG}}>
			{ready && layers !== 'background' && (
				<StageContext.Provider value={stage}>
					<ClipContext.Provider value={{clip, start: first / fps}}>
						<div style={{position: 'absolute', left: 0, top: 0, width: l.width, height: stageH}}>{children}</div>
					</ClipContext.Provider>
				</StageContext.Provider>
			)}
			{layers !== 'no-band' && layers !== 'background' && (
				<CaptionBand top={stageH} height={l.band.height} font={l.band.font ?? 38}
					time={first / fps + frame / fps} show={ready && layers === 'all'} />
			)}
		</AbsoluteFill>
	);
};

/** The caption band, showing the chunk spoken at `time`, or `given` lines (the look sheet's sample). */
export const CaptionBand: React.FC<{top: number; height: number; time: number; show: boolean; font: number; given?: string[]}> = ({
	top, height, time, show, font, given,
}) => {
	const chunk = show && !given ? (timeline as Timeline).tracks.captions.find((c) => c.start <= time && time < c.end) : undefined;
	const lines = show && given ? given : chunk ? captionLines(chunk, layout as Layout) : [];
	return (
		<div style={{position: 'absolute', left: 0, top, width: '100%', height, background: BAND,
			display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center'}}>
			{lines.map((line, i) => (
				<div key={i} data-caption style={{fontFamily: SANS, fontSize: font, lineHeight: 1.3, color: INK, whiteSpace: 'pre'}}>
					{line}
				</div>
			))}
		</div>
	);
};
