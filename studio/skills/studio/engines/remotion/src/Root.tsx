import React from 'react';
import {Composition} from 'remotion';
import scenes from '@video/index';
import timeline from '@timeline';
import layout from '@layout';
import {Frame, type Layers} from './kit/Frame';
import type {Layout, Timeline} from './kit/types';

// One composition per scene clip. Frame boundaries come from absolute times, rounded once, so the
// clips rendered separately tile the video exactly (the Python kit uses the same rule).
export const Root: React.FC = () => {
	const t = timeline as Timeline;
	const l = layout as Layout;
	return (
		<>
			{t.tracks.scene.map((clip) => {
				const first = Math.round(clip.start * t.fps);
				const frames = Math.round(clip.end * t.fps) - first;
				const Scene = (scenes as Record<string, React.FC>)[clip.id];
				const Component: React.FC<{layers: Layers; reportBoxes?: boolean}> = (props) => (
					<Frame clip={clip.id} first={first} layers={props.layers} reportBoxes={props.reportBoxes}>
						{Scene ? <Scene /> : null}
					</Frame>
				);
				return (
					<Composition
						key={clip.id}
						id={clip.id}
						component={Component}
						durationInFrames={frames}
						fps={t.fps}
						width={l.width}
						height={l.height}
						defaultProps={{layers: 'all' as Layers, reportBoxes: false}}
					/>
				);
			})}
		</>
	);
};
