import React from 'react';
import {Rect, Txt, ICE, AMBER, INK, loopT, swapAlpha, track, useClip} from '@studio';

// One shape, never cut: a single element changes size, radius and colour from state to state, and
// its content swaps inside it. Every value is a closed-form spring of time, so any frame renders
// alone, and the last state equals the first so the piece loops (video.json "loop": true).
// States are [time, value] keys, on a 120 BPM grid (0.5 s a beat). The return to the first state starts a
// second before the end, so it has settled by the loop point: a change that starts at the last frame leaves a seam.
const STATES = {
	w: [[0, 2], [2, 6], [4, 3], [5, 2]] as [number, number][],
	h: [[0, 2], [2, 1.4], [4, 3], [5, 2]] as [number, number][],
	r: [[0, 1], [2, 0.2], [4, 0.6], [5, 1]] as [number, number][],
};
const LABELS = [{text: 'one shape', in: 0.5, out: 1.9}, {text: 'never cut', in: 2.5, out: 3.9}, {text: 'loops', in: 4.5, out: 5.9}];

export const S1: React.FC = () => {
	const {t, dur} = useClip();
	const u = loopT(t, dur);
	const w = track(u, STATES.w);
	const h = track(u, STATES.h);
	const r = track(u, STATES.r);
	return (
		<>
			<Rect at={[0, 0]} w={w} h={h} radius={r} fill={u > 2 && u < 4 ? AMBER : ICE} name="shape" />
			{LABELS.map((l) => (
				<Txt key={l.text} at={[0, 0]} size={26} color="#0F1318" weight={500} opacity={swapAlpha(u, l.in, l.out)} name={l.text}>{l.text}</Txt>
			))}
		</>
	);
};
