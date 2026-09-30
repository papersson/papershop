import React, {useLayoutEffect, useRef} from 'react';
import {useStage} from './stage';
import {useClip} from './time';

/**
 * Pixel art: a fixed logical grid drawn on a canvas and scaled by a whole number with
 * nearest-neighbour, so every logical pixel is an exact k×k block. `draw` is called with the clip
 * time and paints the whole frame (a pure function of time, like every scene). Coordinates are
 * rounded to whole pixels by the helpers, so nothing moves by a fraction of a pixel, and text uses
 * the bitmap font below so it stays on the palette instead of being anti-aliased.
 */
export {Pixels, textWidth, FONT, type Draw, type Palette} from '../../../shared/pixels';
import {Pixels, type Draw, type Palette} from '../../../shared/pixels';

export const PixelCanvas: React.FC<{w: number; h: number; palette: Palette; draw: Draw; scale?: number}> = ({w, h, palette, draw, scale}) => {
	const s = useStage();
	const {t} = useClip();
	const ref = useRef<HTMLCanvasElement>(null);
	const k = scale ?? Math.max(1, Math.floor(Math.min(s.width / w, s.height / h)));
	useLayoutEffect(() => {
		const ctx = ref.current?.getContext('2d');
		if (!ctx) return;
		ctx.imageSmoothingEnabled = false;
		draw(new Pixels(ctx, w, h, palette), t);
	});
	return (
		<canvas ref={ref} width={w} height={h} data-box="pixel-canvas" data-pixel={`${w}x${h}@${k}`}
			style={{position: 'absolute', left: (s.width - w * k) / 2, top: (s.height - h * k) / 2, width: w * k, height: h * k,
				imageRendering: 'pixelated'}} />
	);
};

