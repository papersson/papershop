// The footage track of the timeline, as picture: each segment of the edit list plays its recording
// from its `in` time, back to back. The engine driver transcodes each recording to a seekable WebM
// proxy first (Chrome's headless builds don't decode H.264), and this component seeks a video node to
// the right moment every frame. Muted: the kit mixes each segment's sound from the same edit list.
import {Rect} from '@motion-canvas/2d';
import {Video} from '@motion-canvas/2d';
import timeline from '@timeline';
import type {Ctx} from './kit';
import {layout, stageH, band} from './base';

type Segment = {id: string; file: string; in: number; out: number; start: number; end: number};

/** `aspect` is the recordings' width over height (default 16:9); `fit` is 'contain' or 'cover'. */
export function footage(c: Ctx, o: {aspect?: number; fit?: 'contain' | 'cover'} = {}) {
	const segments = ((timeline as {tracks: {footage?: Segment[]}}).tracks.footage ?? []);
	const aspect = o.aspect ?? 16 / 9;
	const W = layout.width, H = stageH;
	const cover = o.fit === 'cover';
	const w = cover ? Math.max(W, H * aspect) : Math.min(W, H * aspect);
	const h = w / aspect;
	const holder = new Rect({position: [0, -band / 2], width: W, height: H, clip: true, key: 'box:footage'});
	const videos = segments.map((seg) => {
		const stem = seg.file.replace(/\.[^.]+$/, '');
		const v = new Video({src: `${__STUDIO_FOOTAGE__}${stem}.webm`, width: w, height: h, opacity: 0, smoothing: true});
		holder.add(v);
		return {seg, v};
	});
	c.view.add(holder);
	c.every((t) => {
		const now = c.start + t;
		for (const {seg, v} of videos) {
			const active = now >= seg.start && now < seg.end;
			v.opacity(active ? 1 : 0);
			if (active) v.seek(seg.in + (now - seg.start));
		}
	});
	return holder;
}
