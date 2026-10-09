import React from 'react';
import {Rect, Txt, useStage, CORAL, ICE, MUTED, AMBER, PANEL, type XY} from '@studio';

// The look sheet's own pages: rename to scenes/look.tsx and `studio look-sheet VIDEO` draws them after
// the kit's pages (colour and type, elements and states, map, close-up, code), into out/look/. Draw
// this video's own elements here, each in every state a scene will show it in, before the scenes are
// built: the motion review checks that drawings stay on this sheet. Export each element as a
// component the scenes import too, so the sheet and the scenes stay the same. A page is drawn alone,
// on the stage above the band, at frame 0; it has no clip, so no useClip() times.

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
