import {studioScene, footage, ramp, ICE, INK} from '@studio-mc';

// The whole edit is one clip: the footage track (see `studio edit`) is the picture, and overlays are
// drawn over it, cued on the words (c.at('03') is sentence 3 of the edit). The footage plays muted; its
// sound is mixed from the same edit list. `aspect` is the recordings' width over height.
export default studioScene('s1', function* (c) {
	footage(c, {aspect: 16 / 9, fit: 'contain'});
	const box = c.box([-4.6, -3.1], 4.2, 0.7, {fill: 'rgba(15, 19, 24, 0.85)', stroke: ICE, radius: 0.08, opacity: 0, name: 'callout'});
	const label = c.text('{{a callout over the footage}}', [-4.6, -3.1], {size: 20, color: INK, opacity: 0});
	c.every((t) => {
		const a = ramp(t, c.at('01'), 0.4) * (1 - ramp(t, c.at('01', 3), 0.4));
		box.opacity(a); label.opacity(a);
	});
});
