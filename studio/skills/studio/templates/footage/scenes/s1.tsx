import React from 'react';
import {Footage, Rect, Txt, ramp, useClip, ICE, INK} from '@studio';

// The whole edit is one clip: the footage track (see `studio edit`) is the picture, and overlays
// are drawn over it. Times are timeline seconds: use `t`, and cue overlays on the words with
// `at('01')` (sentence 1 of the edit) or `word('01', 3)`. The footage plays muted; its sound is mixed
// from the same edit list.
export const S1: React.FC = () => {
	const {t, at} = useClip();
	const callout = ramp(t, at('01'), 0.4) * (1 - ramp(t, at('01', 3), 0.4));
	return (
		<>
			<Footage fit="contain" />
			<Rect at={[-4.6, -3.1]} w={4.2} h={0.7} radius={0.08} fill="rgba(15, 19, 24, 0.85)" stroke={ICE} strokeWidth={2} opacity={callout} name="callout" />
			<Txt at={[-4.6, -3.1]} size={20} color={INK} opacity={callout}>{'{{a callout over the footage}}'}</Txt>
		</>
	);
};
