import React from 'react';
import {Box, Card, Chapter, Chip, Link, span, ramp, useClip} from '@studio';

// Chapter 1. Every value derives from `t`; sentence times come from the timeline: at('01') is
// when sentence s1_01 starts. The building blocks (Box, Card, Link, Panel, Term, Stack, span, lin)
// come from the kit; a chapter should be mostly layout and timing.
export const Example: React.FC = () => {
	const {t, at} = useClip();
	const idea = span(t, at, '01');
	return (
		<Chapter>
			<Chip text="{{Chapter title}}" opacity={ramp(t, at('01'), 0.4)} />
			<Box at={[-3, 0.5]} w={3.6} text="{{the thing}}" lit={ramp(t, at('01', 1), 0.4)} opacity={idea} />
			<Link from={[-1.1, 0.5]} to={[1.1, 0.5]} opacity={idea} progress={ramp(t, at('01', 1.5), 0.6)} />
			<Card at={[3.6, 0.5]} w={5.2} lines={['{{a label, not a caption}}']} opacity={idea} />
		</Chapter>
	);
};
