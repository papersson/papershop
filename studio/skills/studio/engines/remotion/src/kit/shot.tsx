import React from 'react';
import {Img, staticFile} from 'remotion';
import {Txt, useStage, toPx, type XY} from './stage';
import {MUTED} from './theme';

/**
 * A captured or supplied image from the video's assets/ folder, placed in stage units: `at` is its
 * centre and `h` its height (the width follows the image's aspect). Real captured UI beats an
 * illustration, so a launch video crops and animates the real screenshot instead of redrawing it.
 * `crop` is [x, y, w, h] as fractions of the image; `scale` zooms about the crop's centre.
 */
export const Shot: React.FC<{
	file: string; at: XY; h: number; aspect: number; crop?: [number, number, number, number]; scale?: number;
	opacity?: number; radius?: number; caption?: string; name?: string;
}> = ({file, at, h, aspect, crop = [0, 0, 1, 1], scale = 1, opacity = 1, radius = 0.1, caption, name}) => {
	const s = useStage();
	if (opacity <= 0) return null;
	const [cx, cy] = toPx(s, at);
	const H = h * s.unit;
	const fw = crop[2];
	const fh = crop[3];
	const W = (H * aspect * fw) / fh;                      // the frame shows the crop, so it has the crop's shape
	return (
		<>
			<div data-box={name ?? file}
				style={{position: 'absolute', left: cx - W / 2, top: cy - H / 2, width: W, height: H, overflow: 'hidden',
					borderRadius: radius * s.unit, opacity, transform: `scale(${scale})`}}>
				<Img src={staticFile(file)}
					style={{position: 'absolute', width: W / fw, height: H / fh, left: -(crop[0] / fw) * W, top: -(crop[1] / fh) * H}} />
			</div>
			{caption && <Txt at={[at[0], at[1] - h / 2 - 0.3]} size={14} color={MUTED} opacity={opacity}>{caption}</Txt>}
		</>
	);
};
