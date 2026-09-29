import React from 'react';
import {Beats, Chapter, Chip, ICE, INK, Rect, TRAY_EDGE, TRAY_FILL, Txt, ramp, useClip} from '@studio';

// Chapter 1. Every value derives from `t`; sentence times come from the timeline: at('01') is
// when sentence s1_01 starts. Beats sequences animations like a list of play() calls.
export const S1: React.FC = () => {
	const {t, at} = useClip();
	const b = new Beats();
	const chipIn = b.at(at('01'), 0.4);
	const boxIn = b.play(0.6);
	return (
		<Chapter>
			<Chip text="{{Chapter title}}" opacity={ramp(t, chipIn, 0.4)} />
			<Rect at={[0, 0]} w={4} h={1.2} radius={0.12} stroke={TRAY_EDGE} strokeWidth={2.5} fill={TRAY_FILL}
				opacity={ramp(t, boxIn, 0.6)} name="the thing" />
			<Txt at={[0, 0]} size={24} color={INK} opacity={ramp(t, boxIn, 0.6)}>{'{{the thing}}'}</Txt>
			<Txt at={[0, -1.2]} size={18} color={ICE} opacity={ramp(t, boxIn + 0.6, 0.4)}>a label, not a caption</Txt>
		</Chapter>
	);
};
