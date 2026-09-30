import {studioScene, ICE, INK, MUTED} from '@studio-mc';
import {all, easeOutCubic} from '@motion-canvas/core';

// Chapter 1 (Motion Canvas). Times come from the timeline: c.at('01') is when sentence s1_01
// starts. Scenes are generators; `yield*` an animation, and c.until(t) waits for a moment.
export default studioScene('s1', function* (c) {
	const box = c.box([0, 0], 4, 1.2, {stroke: ICE, radius: 0.12, opacity: 0, name: 'the thing'});
	const label = c.text('{{the thing}}', [0, 0], {size: 24, color: INK, opacity: 0});
	const note = c.text('a label, not a caption', [0, -1.2], {size: 18, color: MUTED, opacity: 0});
	yield* c.until(c.at('01'));
	yield* all(box.opacity(1, 0.6, easeOutCubic), label.opacity(1, 0.6, easeOutCubic));
	yield* note.opacity(1, 0.4);
});
