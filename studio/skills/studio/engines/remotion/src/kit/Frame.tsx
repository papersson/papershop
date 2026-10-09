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

const FONTS = ['400 20px "IBM Plex Sans"', '500 20px "IBM Plex Sans"', '600 20px "IBM Plex Sans"',
	'400 20px "IBM Plex Mono"', '500 20px "IBM Plex Mono"'];

/**
 * Every clip renders inside a Frame: the background, the stage the scene draws on, and the caption
 * band below it, which belongs to the captions track alone. The layers prop drops parts of this for
 * the band checks. With reportBoxes, the frame logs every labelled element's pixel box.
 */
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
	const stage = {width: l.width, height: stageH, unit: stageH / 8};
	const root = useRef<HTMLDivElement>(null);
	const frame = useCurrentFrame();
	useLayoutEffect(() => {
		if (!reportBoxes || !ready || !root.current) return;
		const origin = root.current.getBoundingClientRect();
		const boxes = [...root.current.querySelectorAll<HTMLElement>('[data-box],[data-caption]')].map((el) => {
			const r = el.getBoundingClientRect();
			return {name: el.dataset.box ?? 'caption', kind: el.dataset.kind ?? '', x: r.left - origin.left, y: r.top - origin.top, w: r.width, h: r.height};
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

const CaptionBand: React.FC<{top: number; height: number; time: number; show: boolean; font: number}> = ({
	top, height, time, show, font,
}) => {
	const chunk = show ? (timeline as Timeline).tracks.captions.find((c) => c.start <= time && time < c.end) : undefined;
	const lines = chunk ? captionLines(chunk, layout as Layout) : [];
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
