// Pixel art for Motion Canvas: a fixed logical grid drawn on a canvas and scaled by a whole number
// with nearest-neighbour. The drawing helper and the bitmap font are shared with the Remotion kit.
import {Layout} from '@motion-canvas/2d';
import type {Ctx} from './kit';
import {layout, px, stageH} from './base';
import {Pixels, textWidth, FONT, type Draw, type Palette} from '../../shared/pixels';

export {Pixels, textWidth, FONT, type Draw, type Palette};

class PixelNode extends Layout {
	time = 0;
	private readonly off: HTMLCanvasElement;
	constructor(readonly w: number, readonly h: number, readonly k: number, readonly palette: Palette, readonly paint: Draw, at: [number, number]) {
		super({position: px(at[0], at[1]), width: w * k, height: h * k, key: 'box:pixel-canvas'});
		this.off = document.createElement('canvas');
		this.off.width = w;
		this.off.height = h;
	}
	protected override draw(context: CanvasRenderingContext2D) {
		const ctx = this.off.getContext('2d') as CanvasRenderingContext2D;
		ctx.imageSmoothingEnabled = false;
		this.paint(new Pixels(ctx, this.w, this.h, this.palette), this.time);
		context.imageSmoothingEnabled = false;
		context.drawImage(this.off, -(this.w * this.k) / 2, -(this.h * this.k) / 2, this.w * this.k, this.h * this.k);
	}
}

/**
 * A pixel canvas, centred on the stage: `draw(px, t)` paints the whole frame from the clip time (a pure
 * function of time). The scale is the largest whole number that fits, unless `scale` is given.
 */
export function pixelCanvas(c: Ctx, w: number, h: number, palette: Palette, draw: Draw, scale?: number) {
	const k = scale ?? Math.max(1, Math.floor(Math.min(layout.width / w, stageH / h)));
	const node = new PixelNode(w, h, k, palette, draw, [0, 0]);
	c.view.add(node);
	c.every((t) => {
		node.time = t;
	});
	return node;
}
