import {studioScene, pixelCanvas, textWidth} from '@studio-mc';

// A fixed logical grid drawn on a canvas and scaled by a whole number. draw(px, t) paints the whole
// frame from the clip time. Colours are palette names; video.json's "pixel" lists the palette and grid,
// and `studio check` verifies the output is on-grid and on-palette.
const PALETTE = {bg: '#0f1318', ink: '#e6ebf0', ice: '#8fd3ff', amber: '#f2a93b', coral: '#e4715f', dim: '#2b333c'};
const W = 320, H = 180;

export default studioScene('s1', function* (c) {
	pixelCanvas(c, W, H, PALETTE, (px, t) => {
		px.clear('bg');
		const label = 'HELLO';
		px.text(label, Math.round((W - textWidth(label, 3)) / 2), 80, 'amber', 3);
		px.rect(0, H - 4, W, 4, 'dim');
	});
});
