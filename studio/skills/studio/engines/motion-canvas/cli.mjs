// The Motion Canvas engine's side of the studio's engine interface (the same operations and JSON
// as the Remotion engine): it serves the video's scenes with Vite, opens the render page in a
// headless browser, and seeks to exactly the frames it needs.
//
//   node cli.mjs still    --video DIR --clip ID --t SEC --out PNG [--layers L] [--scale S]
//   node cli.mjs stills   --video DIR --requests JSON
//   node cli.mjs render   --video DIR --clip ID --out MP4 [--quality draft|final] [--range A B]
//   node cli.mjs boxes    --video DIR --clip ID --t SEC
//   node cli.mjs boxesAt  --video DIR --requests JSON
//   node cli.mjs duration --video DIR --clip ID
//
// A video's scenes live in scenes/project.ts (makeProject with one scene per clip, in order).
import motionCanvasPlugin from '@motion-canvas/vite-plugin';
import {chromium} from 'playwright-core';
import {spawn, spawnSync} from 'node:child_process';
import {existsSync, mkdirSync, readFileSync, statSync, writeFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createServer} from 'vite';
import {frameOf} from '../shared/timing.js';

// The plugin is CommonJS: its default export is the module, with the plugin factory inside.
const motionCanvas = motionCanvasPlugin.default ?? motionCanvasPlugin.motionCanvas ?? motionCanvasPlugin;
const ENGINE = path.dirname(fileURLToPath(import.meta.url));
const QUALITY = {draft: {scale: 0.5, crf: 26}, final: {scale: 1, crf: 18}};

const [op, ...rest] = process.argv.slice(2);
const opt = {};
for (let i = 0; i < rest.length; i++) {
	if (!rest[i].startsWith('--')) continue;
	const key = rest[i].slice(2);
	if (key === 'range') opt.range = [Number(rest[++i]), Number(rest[++i])];
	else opt[key] = rest[i + 1] && !rest[i + 1].startsWith('--') ? rest[++i] : true;
}
const log = (...a) => console.error(...a);

function timeline(video) {
	return JSON.parse(readFileSync(path.join(video, 'timeline.json'), 'utf8'));
}
const clipOf = (t, id) => {
	const c = t.tracks.scene.find((x) => x.id === id);
	if (!c) throw new Error(`no clip ${id} in timeline.json`);
	return c;
};
// A clip time as a frame of the whole video; boundaries round half up, like the kit's
// timeline.half_up, so clips tile the video.
const videoFrame = (t, clip, sec) => {
	const c = clipOf(t, clip);
	const first = frameOf(c.start, t.fps);
	const frames = frameOf(c.end, t.fps) - first;
	return first + Math.min(frames - 1, Math.max(0, frameOf(Number(sec), t.fps)));
};

// Chrome's headless builds don't decode H.264, so each recording in the footage track is transcoded
// once to a seekable WebM (every frame a keyframe, so a seek lands on the exact frame). Cached by
// modification time; the scene's `footage()` reads them from .cache/mc-footage/.
function prepareFootage(video) {
	const t = timeline(video);
	const files = [...new Set((t.tracks.footage ?? []).map((f) => f.file))];
	for (const file of files) {
		const src = path.join(video, 'assets', file);
		const out = path.join(video, '.cache', 'mc-footage', file.replace(/\.[^.]+$/, '') + '.webm');
		if (existsSync(out) && statSync(out).mtimeMs >= statSync(src).mtimeMs) continue;
		mkdirSync(path.dirname(out), {recursive: true});
		const r = spawnSync('ffmpeg', ['-v', 'error', '-y', '-i', src, '-an', '-vf', 'scale=-2:min(ih\\,1080)', '-c:v', 'libvpx-vp9', '-g', '1',
			'-deadline', 'realtime', '-cpu-used', '8', '-b:v', '6M', out], {stdio: ['ignore', 'inherit', 'inherit']});
		if (r.status !== 0) throw new Error(`could not transcode ${file} for Motion Canvas`);
	}
}

async function withPage(video, layers, fn) {
	prepareFootage(video);
	const layoutFile = opt.layout ? path.resolve(opt.layout) : path.join(video, 'layout.json');
	const project = path.join(video, 'scenes', 'project.ts');
	if (!existsSync(project)) throw new Error(`no scenes/project.ts in ${video}`);
	const server = await createServer({
		root: ENGINE, configFile: false, logLevel: 'error', clearScreen: false,
		cacheDir: path.join(ENGINE, 'node_modules', '.vite'),
		server: {port: 0, host: '127.0.0.1', fs: {strict: false}},
		define: {
			__STUDIO_PROJECT__: JSON.stringify(`/@fs${project}?project`),
			__STUDIO_ASSETS__: JSON.stringify(`/@fs${video}/assets/`),
			__STUDIO_FOOTAGE__: JSON.stringify(`/@fs${video}/.cache/mc-footage/`),
		},
		resolve: {
			alias: [
				{find: '@timeline', replacement: path.join(video, 'timeline.json')},
				{find: '@layout', replacement: existsSync(layoutFile) ? layoutFile : path.join(ENGINE, 'src', 'default-layout.json')},
				{find: '@studio-mc', replacement: path.join(ENGINE, 'src', 'kit.ts')},
			],
			dedupe: ['@motion-canvas/core', '@motion-canvas/2d'],
		},
		plugins: [
			// A video's scenes live outside the engine folder, so their bare imports resolve as if made
			// from the engine: one instance of each package, shared with the player.
			{
				name: 'studio:video-imports', enforce: 'pre',
				async resolveId(source, importer, options) {
					if (!importer || !importer.startsWith(video) || !/^[@a-z]/.test(source) || source.startsWith('@timeline') || source.startsWith('@layout') || source.startsWith('@studio-mc')) return null;
					return this.resolve(source, path.join(ENGINE, 'src', 'kit.ts'), {...options, skipSelf: true});
				},
			},
			motionCanvas({project: project, output: path.join(video, '.cache', 'mc-output')}),
		],
	});
	await server.listen();
	const port = server.httpServer.address().port;
	const browser = await chromium.launch({executablePath: opt.browser || undefined, args: ['--disable-gpu', '--hide-scrollbars']});
	try {
		const page = await browser.newPage({viewport: {width: 1920, height: 1080}});
		page.on('console', (m) => (process.env.STUDIO_DEBUG || m.type() === 'error') && log('page', m.type() + ':', m.text()));
		page.on('pageerror', (e) => log('page error:', e.message));
		await page.goto(`http://127.0.0.1:${port}/render.html?layers=${layers}`);
		await page.waitForFunction(() => window.studioReady || window.studioError, null, {timeout: 120_000});
		const err = await page.evaluate(() => window.studioError);
		if (err) throw new Error(err);
		return await fn(page);
	} finally {
		await browser.close();
		await server.close();
	}
}

const dataUrlToBuffer = (u) => Buffer.from(u.split(',')[1], 'base64');

async function stills(video, requests) {
	const t = timeline(video);
	const groups = {};
	requests.forEach((r, i) => (groups[r.layers ?? 'all'] ??= []).push({...r, i}));
	const done = new Array(requests.length);
	for (const [layers, reqs] of Object.entries(groups)) {
		await withPage(video, layers, async (page) => {
			for (const r of reqs) {
				const frame = videoFrame(t, r.clip, r.t);
				const mime = /\.jpe?g$/i.test(r.out) ? 'image/jpeg' : 'image/png';
				const img = dataUrlToBuffer(await page.evaluate(([f, m, sc]) => window.studio.seek(f, m, sc), [frame, mime, Number(r.scale ?? 1)]));
				mkdirSync(path.dirname(r.out), {recursive: true});
				writeFileSync(r.out, img);
				done[r.i] = {clip: r.clip, t: Number(r.t), frame, out: r.out};
			}
		});
	}
	return {stills: done};
}

async function boxesAt(video, requests) {
	const t = timeline(video);
	const lay = JSON.parse(readFileSync(opt.layout ? path.resolve(opt.layout) : path.join(video, 'layout.json'), 'utf8'));
	const frames = await withPage(video, 'all', async (page) => {
		const out = [];
		for (const r of requests) {
			await page.evaluate((f) => window.studio.seek(f), videoFrame(t, r.clip, r.t));
			out.push({clip: r.clip, t: Number(r.t), band: {y: lay.height - lay.band.height, h: lay.band.height}, boxes: await page.evaluate(() => window.studio.boxes())});
		}
		return out;
	});
	return {frames};
}

async function render(video, clip, out, quality, range) {
	const q = QUALITY[quality ?? 'draft'];
	if (!q) throw new Error(`unknown quality ${quality}`);
	const t = timeline(video);
	const c = clipOf(t, clip);
	const first = frameOf(c.start, t.fps);
	const frames = frameOf(c.end, t.fps) - first;
	const [a, b] = range ? [frameOf(range[0], t.fps), Math.min(frames - 1, frameOf(range[1], t.fps))] : [0, frames - 1];
	mkdirSync(path.dirname(out), {recursive: true});
	const started = Date.now();
	await withPage(video, 'all', async (page) => {
		const scale = q.scale === 1 ? [] : ['-vf', `scale=iw*${q.scale}:ih*${q.scale}`];
		const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(t.fps), '-i', '-', ...scale,
			'-c:v', 'libx264', '-crf', String(q.crf), '-pix_fmt', 'yuv420p', out], {stdio: ['pipe', 'inherit', 'inherit']});
		for (let f = a; f <= b; f++) {
			const png = dataUrlToBuffer(await page.evaluate((n) => window.studio.seek(n), first + f));
			if (!ff.stdin.write(png)) await new Promise((r) => ff.stdin.once('drain', r));
		}
		ff.stdin.end();
		await new Promise((res, rej) => ff.on('close', (code) => (code === 0 ? res() : rej(new Error(`ffmpeg exited ${code}`)))));
	});
	return {clip, out, quality: quality ?? 'draft', frames: b - a + 1, seconds: (Date.now() - started) / 1000};
}

async function duration(video, clip) {
	const t = timeline(video);
	const index = t.tracks.scene.findIndex((x) => x.id === clip);
	if (index < 0) throw new Error(`no clip ${clip} in timeline.json`);
	const info = await withPage(video, 'all', (page) => page.evaluate(() => window.studio.info()));
	const sc = info.scenes[index];
	if (!sc) throw new Error(`scenes/project.ts has no scene number ${index + 1} for clip ${clip}`);
	const frames = sc.last - sc.first;
	return {clip, frames, fps: t.fps, seconds: frames / t.fps};
}

const ops = {
	still: () => stills(opt.video, [{clip: opt.clip, t: opt.t, out: opt.out, layers: opt.layers}]),
	stills: () => stills(opt.video, JSON.parse(readFileSync(opt.requests, 'utf8'))),
	render: () => render(opt.video, opt.clip, opt.out, opt.quality, opt.range),
	boxes: async () => {
		const {frames} = await boxesAt(opt.video, [{clip: opt.clip, t: opt.t}]);
		return {clip: opt.clip, t: Number(opt.t), boxes: {band: frames[0].band, boxes: frames[0].boxes}};
	},
	boxesAt: () => boxesAt(opt.video, JSON.parse(readFileSync(opt.requests, 'utf8'))),
	duration: () => duration(opt.video, opt.clip),
};
if (!ops[op]) {
	log(`unknown op ${op}; expected one of ${Object.keys(ops).join(', ')}`);
	process.exit(2);
}
opt.video = path.resolve(opt.video);
ops[op]().then(
	(r) => {
		console.log(JSON.stringify(r));
		process.exit(0);
	},
	(e) => {
		log(e.stack || String(e));
		process.exit(1);
	},
);
