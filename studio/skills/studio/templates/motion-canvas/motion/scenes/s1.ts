import {studioScene, loopT, swapAlpha, track, unit, ICE, AMBER} from '@studio-mc';

// One shape, never cut: a single element changes size, radius and colour from state to state, and its
// content swaps inside it. Every value is a closed-form spring of the clip time (through c.every), so
// any frame renders alone, and the last state equals the first so the piece loops (video.json "loop").
// The return to the first state starts a second before the end so it has settled by the loop point.
const STATES = {
	w: [[0, 2], [2, 6], [4, 3], [5, 2]] as [number, number][],
	h: [[0, 2], [2, 1.4], [4, 3], [5, 2]] as [number, number][],
	r: [[0, 1], [2, 0.2], [4, 0.6], [5, 1]] as [number, number][],
};
const LABELS = [{text: 'one shape', in: 0.5, out: 1.9}, {text: 'never cut', in: 2.5, out: 3.9}, {text: 'loops', in: 4.5, out: 5.9}];

export default studioScene('s1', function* (c) {
	const shape = c.box([0, 0], 2, 2, {fill: ICE, radius: 1, name: 'shape'});
	const labels = LABELS.map((l) => c.text(l.text, [0, 0], {size: 26, color: '#0F1318', weight: 500, opacity: 0, name: l.text}));
	c.every((t) => {
		const u = loopT(t, c.dur);
		const w = track(u, STATES.w), h = track(u, STATES.h), r = track(u, STATES.r);
		shape.width(w * unit); shape.height(h * unit); shape.radius(r * unit);
		shape.fill(u > 2 && u < 4 ? AMBER : ICE);
		labels.forEach((n, i) => n.opacity(swapAlpha(u, LABELS[i].in, LABELS[i].out)));
	});
	yield* c.until(c.dur);
});
