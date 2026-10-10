import React from 'react';
import {Composition} from 'remotion';
import timeline from '@timeline';
import layout from '@layout';
import look from '@look';
import {LOOK_PAGES, LookSheet} from './kit/look';
import type {Layout, Timeline} from './kit/types';

// The look sheet's own bundle (look-entry.tsx): `studio-look`, one page per frame, the kit's pages and
// then scenes/look.tsx's. Kept apart from Root so that a mistake in scenes/look.tsx breaks the look
// sheet alone, never a still, a render or a cut.
export const LookRoot: React.FC = () => {
	const t = timeline as Timeline;
	const l = layout as Layout;
	const own = Object.entries(look as Record<string, React.FC>);
	const pages = [...LOOK_PAGES.map((p) => p.title), ...own.map(([title]) => title)];
	const Look: React.FC<{caption?: string[]; pages: string[]}> = (props) => <LookSheet pages={props.pages} own={own.map(([, c]) => c)} caption={props.caption} />;
	return <Composition id="studio-look" component={Look} durationInFrames={pages.length} fps={t.fps} width={l.width} height={l.height}
		defaultProps={{caption: [] as string[], pages}} />;
};
