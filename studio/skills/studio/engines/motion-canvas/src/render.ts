// The page the driver loads in a headless browser. It runs the project's scenes with Motion
// Canvas's own Player and Stage, and exposes what the four engine operations need:
//   studio.info()        {fps, frames, width, height}
//   studio.seek(frame)   paints that frame and returns it as a PNG data URL
//   studio.boxes()       pixel boxes of the labelled nodes in the frame last painted
import {Player, Stage, Vector2} from '@motion-canvas/core';
import {Txt, type Node} from '@motion-canvas/2d';
import layout from '@layout';
import timeline from '@timeline';
import type {TimelineJson} from './kit';

const T = timeline as TimelineJson;
const layers = new URLSearchParams(location.search).get('layers') ?? 'all';

const FONTS = ['400 20px "IBM Plex Sans"', '500 20px "IBM Plex Sans"', '600 20px "IBM Plex Sans"', '400 20px "IBM Plex Mono"', '500 20px "IBM Plex Mono"'];

async function boot() {
	await Promise.all(FONTS.map((f) => document.fonts.load(f)));
	const project = (await import(/* @vite-ignore */ __STUDIO_PROJECT__)).default;
	const settings = {
		...project.meta.getFullRenderingSettings(),
		size: new Vector2(layout.width, layout.height),
		resolutionScale: 1,
		fps: T.fps,
	};
	const stage = new Stage();
	stage.configure(settings);
	const player = new Player(project);
	player.setVariables({layers});
	await player.configure(settings);

	let painted: ((frame: number) => void) | null = null;
	player.onRender.subscribe(async () => {
		await stage.render(player.playback.currentScene, player.playback.previousScene);
		painted?.(player.playback.frame);
	});
	player.logger.onLogged.subscribe((l: any) => l.level === 'error' && console.error('scene error:', l.message));
	player.togglePlayback(false);
	player.activate();
	// The scenes are measured asynchronously; wait until the total duration is known.
	for (let i = 0; i < 400 && !(player.playback.duration > 0); i++) await new Promise((r) => setTimeout(r, 50));
	if (!(player.playback.duration > 0)) throw new Error('the scenes reported no duration');

	// Paints a frame and returns it as a data URL: PNG by default, JPEG for a .jpg request, scaled down
	// when the kit asks for a smaller still (the review page's thumbnails).
	const seek = (frame: number, mime = 'image/png', scale = 1) =>
		new Promise<string>((resolve, reject) => {
			const timer = setTimeout(() => reject(new Error(`seek to frame ${frame} timed out`)), 60_000);
			painted = (got) => {
				if (got !== frame) return;
				clearTimeout(timer);
				painted = null;
				const src = stage.finalBuffer;
				if (scale === 1) return resolve(src.toDataURL(mime, 0.85));
				const out = document.createElement('canvas');
				out.width = Math.max(1, Math.round(src.width * scale));
				out.height = Math.max(1, Math.round(src.height * scale));
				const g = out.getContext('2d') as CanvasRenderingContext2D;
				g.imageSmoothingQuality = 'high';
				g.drawImage(src, 0, 0, out.width, out.height);
				resolve(out.toDataURL(mime, 0.85));
			};
			player.requestSeek(frame);
		});

	const boxes = () => {
		const scene: any = player.playback.currentScene;
		const view: Node = scene.getView();
		const nodes = view.findAll((n: any) => typeof n.key === 'string' && (n.key.startsWith('box:') || n.key === 'caption')) as Node[];
		return nodes.map((n: any) => {
			const p = n.absolutePosition();      // canvas pixels, origin at the top-left
			const s = n.size();
			const cx = p.x;
			const cy = p.y;
			return {
				visible: n.absoluteOpacity() > 0.001,
				name: n.key === 'caption' ? 'caption' : n.key.slice(4), kind: n instanceof Txt ? 'text' : '',
				x: cx - s.x / 2, y: cy - s.y / 2, w: s.x, h: s.y,
			};
		}).filter((b) => b.w > 0 && b.h > 0 && b.visible).map(({visible, ...b}) => b);
	};

	(window as any).studio = {
		// Each scene's own length in frames, as Motion Canvas measured it (a scene that ends early or
		// late shows up here, and in the kit's length check).
		info: () => ({
			fps: T.fps, frames: player.playback.duration, width: layout.width, height: layout.height,
			scenes: ((player.playback as any).scenes.current as any[]).map((sc) => ({first: sc.firstFrame, last: sc.lastFrame})),
		}),
		seek, boxes,
	};
	(window as any).studioReady = true;
}

boot().catch((e) => {
	console.error(e);
	(window as any).studioError = String(e && e.stack ? e.stack : e);
});
