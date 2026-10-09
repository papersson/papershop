import React from 'react';
import {Composition} from 'remotion';
import scenes from '@video/index';
import timeline from '@timeline';
import layout from '@layout';
import boards from '@boards';
import boardNotes from '@board-notes';
import look from '@look';
import {Board, type BoardFrame} from './kit/board';
import {Frame, type Layers} from './kit/Frame';
import {LOOK_PAGES, LookSheet} from './kit/look';
import type {Layout, Timeline} from './kit/types';
import {frameOf} from '../../shared/timing.js';

// One composition per scene clip. Frame boundaries come from absolute times, rounded once, so the
// clips rendered separately tile the video exactly (the Python kit uses the same rule). A chapter
// with no scene yet renders its board, so a cut can be made at any point and shows the finished
// chapters animated and the rest as boards; the `boards` prop shows boards for every chapter.
// `studio-look` is the look sheet, one page per frame: the kit's pages, then scenes/look.tsx's.
export const Root: React.FC = () => {
	const t = timeline as Timeline;
	const l = layout as Layout;
	const own = Object.entries(look as Record<string, React.FC>);
	const pages = [...LOOK_PAGES.map((p) => p.title), ...own.map(([title]) => title)];
	const Look: React.FC<{caption?: string[]; pages: string[]}> = (props) => <LookSheet pages={props.pages} own={own.map(([, c]) => c)} caption={props.caption} />;
	return (
		<>
			<Composition id="studio-look" component={Look} durationInFrames={pages.length} fps={t.fps} width={l.width} height={l.height}
				defaultProps={{caption: [] as string[], pages}} />
			{t.tracks.scene.map((clip) => {
				const first = frameOf(clip.start, t.fps);
				const frames = frameOf(clip.end, t.fps) - first;
				const Scene = (scenes as Record<string, React.FC | undefined>)[clip.id];
				const Component: React.FC<{layers: Layers; reportBoxes?: boolean; boards?: boolean}> = (props) => (
					<Frame clip={clip.id} first={first} layers={props.layers} reportBoxes={props.reportBoxes}>
						{Scene && !props.boards ? <Scene /> : (
							<Board clip={clip.id} frames={(boards as Record<string, BoardFrame[]>)[clip.id]}
								notes={boardNotes as Record<string, string>} />
						)}
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
						defaultProps={{layers: 'all' as Layers, reportBoxes: false, boards: false}}
					/>
				);
			})}
		</>
	);
};
