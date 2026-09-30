import {studioScene, shot, ramp, layout, unit, INK, MUTED} from '@studio-mc';

// A product film uses the real product: capture its screens (`studio capture URL VIDEO`) and animate
// those; never redraw the UI. Lay out against the stage's width so one timeline exports 16:9, 9:16 and
// 1:1 (`studio check --format 9:16` catches anything that leaves the frame).
export default studioScene('s1', function* (c) {
	const w = layout.width / unit;                        // about 16.7 landscape, 5.3 portrait
	const k = Math.min(1, w / 9);                          // type scale
	const ASPECT = 16 / 10;                                // the captured screen's width over its height
	const shotH = Math.min(5.2, (w - 0.8) / ASPECT);
	const l1 = c.text('{{the problem,}}', [0, 0.9], {size: 64 * k, color: INK, font: 'sans', weight: 600, opacity: 0});
	const l2 = c.text('{{in five words}}', [0, -0.3], {size: 64 * k, color: INK, font: 'sans', weight: 600, opacity: 0});
	const frame = shot(c, '{{captured-screen.png}}', [0, 0.3], shotH, {aspect: ASPECT, opacity: 0, caption: '{{what this screen shows}}'});
	const num = c.text('{{a real number}}', [0, -3.3], {size: 30 * k, color: MUTED, opacity: 0});
	c.every((t) => {
		const hook = ramp(t, 0.2, 0.5) * (1 - ramp(t, 2.6, 0.4));
		l1.opacity(hook); l2.opacity(hook);
		const s = ramp(t, 2.8, 0.6);
		frame.opacity(s); num.opacity(s);
	});
	yield* c.until(c.dur);
});
