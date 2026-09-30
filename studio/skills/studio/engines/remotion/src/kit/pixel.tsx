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
export type Palette = Record<string, string>;
export type Draw = (px: Pixels, t: number) => void;

export class Pixels {
	constructor(readonly ctx: CanvasRenderingContext2D, readonly w: number, readonly h: number, readonly palette: Palette) {}

	private colour(c: string): string {
		return this.palette[c] ?? c;
	}

	clear(c: string) {
		this.ctx.fillStyle = this.colour(c);
		this.ctx.fillRect(0, 0, this.w, this.h);
	}

	rect(x: number, y: number, w: number, h: number, c: string) {
		this.ctx.fillStyle = this.colour(c);
		this.ctx.fillRect(Math.round(x), Math.round(y), Math.round(w), Math.round(h));
	}

	/** One pixel. */
	dot(x: number, y: number, c: string) {
		this.rect(x, y, 1, 1, c);
	}

	/** A sprite from rows of characters: each character is a key of `legend` (or a palette name), '.' is clear. */
	sprite(rows: string[], x: number, y: number, legend: Record<string, string>) {
		rows.forEach((row, j) => [...row].forEach((ch, i) => ch !== '.' && ch !== ' ' && legend[ch] && this.dot(x + i, y + j, legend[ch])));
	}

	/** Text in the 3×5 bitmap font, upper-case, `scale` pixels per font pixel. Returns its width. */
	text(s: string, x: number, y: number, c: string, scale = 1): number {
		let cx = Math.round(x);
		for (const ch of s.toUpperCase()) {
			const g = FONT[ch] ?? FONT['?'];
			g.forEach((row, j) => [...row].forEach((bit, i) => bit === '#' && this.rect(cx + i * scale, y + j * scale, scale, scale, c)));
			cx += 4 * scale;
		}
		return cx - Math.round(x) - scale;
	}
}

export const textWidth = (s: string, scale = 1) => Math.max(0, s.length * 4 * scale - scale);

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

// 3×5 glyphs: rows of '#' and '.'.
const G = (...rows: string[]) => rows;
export const FONT: Record<string, string[]> = {
	' ': G('...', '...', '...', '...', '...'),
	'A': G('.#.', '#.#', '###', '#.#', '#.#'), 'B': G('##.', '#.#', '##.', '#.#', '##.'), 'C': G('.##', '#..', '#..', '#..', '.##'),
	'D': G('##.', '#.#', '#.#', '#.#', '##.'), 'E': G('###', '#..', '##.', '#..', '###'), 'F': G('###', '#..', '##.', '#..', '#..'),
	'G': G('.##', '#..', '#.#', '#.#', '.##'), 'H': G('#.#', '#.#', '###', '#.#', '#.#'), 'I': G('###', '.#.', '.#.', '.#.', '###'),
	'J': G('..#', '..#', '..#', '#.#', '.#.'), 'K': G('#.#', '#.#', '##.', '#.#', '#.#'), 'L': G('#..', '#..', '#..', '#..', '###'),
	'M': G('#.#', '###', '###', '#.#', '#.#'), 'N': G('##.', '#.#', '#.#', '#.#', '#.#'), 'O': G('.#.', '#.#', '#.#', '#.#', '.#.'),
	'P': G('##.', '#.#', '##.', '#..', '#..'), 'Q': G('.#.', '#.#', '#.#', '##.', '.##'), 'R': G('##.', '#.#', '##.', '#.#', '#.#'),
	'S': G('.##', '#..', '.#.', '..#', '##.'), 'T': G('###', '.#.', '.#.', '.#.', '.#.'), 'U': G('#.#', '#.#', '#.#', '#.#', '###'),
	'V': G('#.#', '#.#', '#.#', '#.#', '.#.'), 'W': G('#.#', '#.#', '###', '###', '#.#'), 'X': G('#.#', '#.#', '.#.', '#.#', '#.#'),
	'Y': G('#.#', '#.#', '.#.', '.#.', '.#.'), 'Z': G('###', '..#', '.#.', '#..', '###'),
	'0': G('###', '#.#', '#.#', '#.#', '###'), '1': G('.#.', '##.', '.#.', '.#.', '###'), '2': G('##.', '..#', '.#.', '#..', '###'),
	'3': G('##.', '..#', '.#.', '..#', '##.'), '4': G('#.#', '#.#', '###', '..#', '..#'), '5': G('###', '#..', '##.', '..#', '##.'),
	'6': G('.##', '#..', '###', '#.#', '###'), '7': G('###', '..#', '.#.', '.#.', '.#.'), '8': G('###', '#.#', '###', '#.#', '###'),
	'9': G('###', '#.#', '###', '..#', '##.'),
	'.': G('...', '...', '...', '...', '.#.'), ',': G('...', '...', '...', '.#.', '#..'), ':': G('...', '.#.', '...', '.#.', '...'),
	'!': G('.#.', '.#.', '.#.', '...', '.#.'), '?': G('##.', '..#', '.#.', '...', '.#.'), '-': G('...', '...', '###', '...', '...'),
	'+': G('...', '.#.', '###', '.#.', '...'), '/': G('..#', '..#', '.#.', '#..', '#..'), '%': G('#.#', '..#', '.#.', '#..', '#.#'),
	'$': G('.##', '##.', '.#.', '.##', '##.'), '>': G('#..', '.#.', '..#', '.#.', '#..'), '<': G('..#', '.#.', '#..', '.#.', '..#'),
	'=': G('...', '###', '...', '###', '...'), '\'': G('.#.', '.#.', '...', '...', '...'), '(': G('.#.', '#..', '#..', '#..', '.#.'),
	')': G('.#.', '..#', '..#', '..#', '.#.'), '_': G('...', '...', '...', '...', '###'), '#': G('#.#', '###', '#.#', '###', '#.#'),
};
