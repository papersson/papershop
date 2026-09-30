import React from 'react';
import {Shot, Txt, INK, MUTED, ramp, useClip, useStage} from '@studio';

// A product film uses the real product: capture its screens (`studio capture URL VIDEO`) and animate
// those; never redraw the UI from imagination. Beats are 2 to 4 seconds each: a hook in big type,
// the product appearing, three features as real UI moments, one number, a call to action.
// The stage changes shape with the format (`studio export --formats 16:9,9:16,1:1`), so lay out
// against its size: `w` is the stage's width in units (about 16.7 landscape, 5.3 portrait), and
// type scales with it. `studio check --format 9:16` catches anything that leaves the frame.
export const S1: React.FC = () => {
	const {t} = useClip();
	const s = useStage();
	const w = s.width / s.unit;
	const k = Math.min(1, w / 9);                       // type scale: full size from 9 units wide
	const ASPECT = 16 / 10;                             // the captured screen's width over its height
	const shotH = Math.min(5.2, (w - 0.8) / ASPECT);    // fits the width in portrait, the height in landscape
	const hook = ramp(t, 0.2, 0.5) * (1 - ramp(t, 2.6, 0.4));
	const shot = ramp(t, 2.8, 0.6);
	return (
		<>
			<Txt at={[0, 0.9]} size={64 * k} font="sans" weight={600} color={INK} opacity={hook}>{'{{the problem,}}'}</Txt>
			<Txt at={[0, -0.3]} size={64 * k} font="sans" weight={600} color={INK} opacity={hook}>{'{{in five words}}'}</Txt>
			<Shot file="{{captured-screen.png}}" at={[0, 0.3]} h={shotH} aspect={ASPECT} opacity={shot} caption="{{what this screen shows}}" />
			<Txt at={[0, -3.3]} size={30 * k} color={MUTED} opacity={shot}>{'{{a real number}}'}</Txt>
		</>
	);
};
