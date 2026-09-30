// A captured or supplied image from the video's assets/ folder, placed in stage units. Real captured
// UI beats an illustration: crop and animate the real screenshot, never redraw it.
import {Img, Rect, Txt} from '@motion-canvas/2d';
import type {Ctx} from './kit';
import {MONO, MUTED, pt, px, unit} from './base';

export type ShotOptions = {
	/** image width over height */ aspect: number;
	/** [x, y, w, h] as fractions of the image */ crop?: [number, number, number, number];
	opacity?: number; radius?: number; caption?: string; name?: string;
};

/** Returns the frame (a Rect that clips), so a scene can animate its opacity, scale or position. */
export function shot(c: Ctx, file: string, at: [number, number], h: number, o: ShotOptions) {
	const [cx, cy, fw, fh] = o.crop ?? [0, 0, 1, 1];
	const W = (h * o.aspect * fw) / fh;                       // the frame shows the crop, so it has the crop's shape
	const frame = new Rect({position: px(at[0], at[1]), width: W * unit, height: h * unit, radius: (o.radius ?? 0.1) * unit, clip: true,
		opacity: o.opacity ?? 1, key: `box:${o.name ?? file}`});
	const full: [number, number] = [(W * unit) / fw, (h * unit) / fh];
	frame.add(new Img({src: c.asset(file), size: full, position: [(0.5 - (cx + fw / 2)) * full[0], (0.5 - (cy + fh / 2)) * full[1]]}));
	c.view.add(frame);
	if (o.caption) c.view.add(new Txt({text: o.caption, position: px(at[0], at[1] - h / 2 - 0.3), fill: MUTED, fontSize: pt(14), fontFamily: MONO, key: `box:${o.caption}`}));
	return frame;
}
