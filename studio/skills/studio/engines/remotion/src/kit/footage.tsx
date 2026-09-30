import React, {useContext} from 'react';
import {OffthreadVideo, Sequence, staticFile, useVideoConfig} from 'remotion';
import timeline from '@timeline';
import {ClipContext} from './time';
import type {Timeline} from './types';

/**
 * The footage track of the timeline, as picture: each segment of the edit list plays its recording
 * from its `in` time, back to back (a jump cut is two segments). Muted here; the kit mixes each
 * segment's sound from the same list. Fills the stage, so overlays (callouts, titles, zooms) are
 * drawn over it in the scene; `fit` is 'contain' (the whole frame, letterboxed) or 'cover'.
 */
export const Footage: React.FC<{fit?: 'contain' | 'cover'}> = ({fit = 'contain'}) => {
	const {fps} = useVideoConfig();
	const {start} = useContext(ClipContext);
	const segments = (timeline as Timeline).tracks.footage ?? [];
	return (
		<div style={{position: 'absolute', inset: 0, overflow: 'hidden'}} data-box="footage">
			{segments.map((seg) => {
				const from = Math.round((seg.start - start) * fps);
				const frames = Math.round((seg.end - start) * fps) - from;
				if (frames <= 0) return null;
				return (
					<Sequence key={seg.id} from={from} durationInFrames={frames}>
						<OffthreadVideo src={staticFile(seg.file)} startFrom={Math.round(seg.in * fps)} muted
							style={{width: '100%', height: '100%', objectFit: fit}} />
					</Sequence>
				);
			})}
		</div>
	);
};
