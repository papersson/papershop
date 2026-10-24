import React from 'react';
import {Rect, Txt, useStage, CORAL, ICE, MUTED, AMBER, PANEL, type XY} from '@studio';

// Draw shared element components here and in the scenes so style changes stay visible together.
// Copy this file to scenes/look.tsx; studio look-sheet draws its pages at frame zero.
// There is no clip, so a look sheet has no useClip() times.

// What each element is made of, so everything it does agrees: how it springs and settles when it
// lands, and what it sounds like (references/taste.md). Scenes pass these to the kit's
// motion helpers, spring(t, ...m.spring) and settle(t, t0, ...m.settle), and effects take the pool,
// instead of each scene choosing its own numbers.
export const materials = {
	protagonist: {spring: [170, 26], settle: [6, 3, 5], sound: ['pop-small']},   // {{light and springy}}
} satisfies Record<string, {spring: [number, number]; settle: [number, number, number]; sound: string[]}>;

type State = 'idle' | 'ok' | 'bad' | 'wait';
const LOOK: Record<State, [string, string]> = {idle: ['○', MUTED], ok: ['✓', ICE], bad: ['✕', CORAL], wait: ['…', AMBER]};

/** {{The thing the video follows}}, in one state. Scenes import this. */
export const Protagonist: React.FC<{at: XY; state: State; opacity?: number}> = ({at, state, opacity = 1}) => {
	const [glyph, color] = LOOK[state];
	return (
		<>
			<Rect at={at} w={1} h={1} radius={0.14} stroke={color} strokeWidth={3} fill={PANEL} opacity={opacity} name={`protagonist ${state}`} />
			<Txt at={at} size={30} color={color} opacity={opacity}>{glyph}</Txt>
		</>
	);
};

const States: React.FC = () => {
	const s = useStage();
	const xs = [-0.3, -0.1, 0.1, 0.3].map((f) => (f * s.width) / s.unit);
	return (
		<>
			{(Object.keys(LOOK) as State[]).map((state, i) => (
				<React.Fragment key={state}>
					<Protagonist at={[xs[i], 0.3]} state={state} />
					<Txt at={[xs[i], -0.6]} size={14} color={MUTED}>{state}</Txt>
				</React.Fragment>
			))}
		</>
	);
};

// Page title -> page, in order.
export default {'{{the protagonist}}': States} as Record<string, React.FC>;
