// The Remotion engine's side of the studio's engine interface. The Python kit calls it; each call
// prints one JSON object on stdout (logs go to stderr).
//
//   node cli.mjs still    --video DIR --clip ID --t SEC --out PNG [--layers L] [--scale S]
//   node cli.mjs stills   --video DIR --requests JSON        [{clip, t, out, layers?, scale?}], one browser
//   node cli.mjs render   --video DIR --clip ID --out MP4 [--quality draft|final] [--range A B]
//   node cli.mjs boxes    --video DIR --clip ID --t SEC
//   node cli.mjs boxesAt  --video DIR --requests JSON        [{clip, t}], one browser
//   node cli.mjs duration --video DIR --clip ID
//
// Layers: all (default), no-captions (the band stays, its text goes), no-band (the scene alone),
// background (nothing but the background).
// The bundle is cached per content hash of the engine source, the video's scenes, timeline and
// layout, so a still after an edit costs one incremental bundle plus one frame.
import {bundle} from '@remotion/bundler';
import {openBrowser, renderMedia, renderStill, selectComposition} from '@remotion/renderer';
import {createHash} from 'node:crypto';
import {existsSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync} from 'node:fs';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const ENGINE = path.dirname(fileURLToPath(import.meta.url));
const QUALITY = {
	draft: {scale: 0.5, crf: 26, jpegQuality: 80},
	final: {scale: 1, crf: 18, jpegQuality: 95},
};

const [op, ...rest] = process.argv.slice(2);
const opt = {};
for (let i = 0; i < rest.length; i++) {
	if (!rest[i].startsWith('--')) continue;
	const key = rest[i].slice(2);
	if (key === 'range') {
		opt.range = [Number(rest[++i]), Number(rest[++i])];
	} else {
		opt[key] = rest[i + 1] && !rest[i + 1].startsWith('--') ? rest[++i] : true;
	}
}
const log = (...a) => console.error(...a);

// Names relative to the hashed root, so a moved or copied video keeps its bundle key.
function hashTree(h, p, root = p) {
	if (!existsSync(p)) return;
	if (statSync(p).isDirectory()) {
		for (const name of readdirSync(p).sort()) {
			if (name === 'node_modules' || name.startsWith('.')) continue;
			hashTree(h, path.join(p, name), root);
		}
	} else {
		h.update(path.relative(path.dirname(root), p));
		h.update(readFileSync(p));
	}
}

async function getBundle(video) {
	const h = createHash('sha1');
	for (const p of [path.join(ENGINE, 'src'), path.join(ENGINE, 'package-lock.json'),
		path.join(video, 'scenes'), path.join(video, 'data'), path.join(video, 'timeline.json'),
		path.join(video, 'layout.json')]) {
		hashTree(h, p);
	}
	const key = h.digest('hex').slice(0, 16);
	const root = path.join(video, '.cache', 'bundle');
	const out = path.join(root, key);
	if (existsSync(path.join(out, 'index.html'))) return {serveUrl: out, cached: true};
	const layoutFile = path.join(video, 'layout.json');
	await bundle({
		entryPoint: path.join(ENGINE, 'src', 'entry.tsx'),
		outDir: out,
		enableCaching: true,
		webpackOverride: (config) => ({
			...config,
			resolve: {
				...config.resolve,
				alias: {
					...config.resolve?.alias,
					'@studio': path.join(ENGINE, 'src', 'kit'),
					'@video': path.join(video, 'scenes'),
					'@timeline': path.join(video, 'timeline.json'),
					'@layout': existsSync(layoutFile) ? layoutFile : path.join(ENGINE, 'src', 'default-layout.json'),
				},
				// Scene files live outside the engine, so resolve their imports from the engine's packages.
				modules: [path.join(ENGINE, 'node_modules'), 'node_modules'],
			},
		}),
	});
	for (const old of existsSync(root) ? readdirSync(root) : []) {
		if (old !== key) rmSync(path.join(root, old), {recursive: true, force: true});
	}
	return {serveUrl: out, cached: false};
}

function browserOptions() {
	// A full Chrome needs the new headless mode; the headless shell runs as itself. Without a path,
	// Remotion downloads its own shell.
	if (!opt.browser) return {};
	const shell = path.basename(opt.browser).startsWith('chrome-headless-shell');
	return {browserExecutable: opt.browser, chromeMode: shell ? 'headless-shell' : 'chrome-for-testing'};
}

async function composition(serveUrl, clip, inputProps, puppeteerInstance) {
	return selectComposition({serveUrl, id: clip, inputProps, puppeteerInstance, ...browserOptions(), logLevel: 'error'});
}

function frameAt(comp, t) {
	return Math.min(comp.durationInFrames - 1, Math.max(0, Math.round(Number(t) * comp.fps)));
}

async function stills(video, requests) {
	const {serveUrl, cached} = await getBundle(video);
	const browser = await openBrowser('chrome', browserOptions());
	const comps = {};
	const done = [];
	try {
		for (const r of requests) {
			const inputProps = {layers: r.layers ?? 'all'};
			const key = `${r.clip}/${inputProps.layers}`;
			comps[key] ??= await composition(serveUrl, r.clip, inputProps, browser);
			const frame = frameAt(comps[key], r.t);
			mkdirSync(path.dirname(r.out), {recursive: true});
			await renderStill({
				composition: comps[key], serveUrl, output: r.out, frame, inputProps,
				scale: Number(r.scale ?? 1), imageFormat: r.out.endsWith('.jpg') ? 'jpeg' : 'png',
				puppeteerInstance: browser, overwrite: true, logLevel: 'error', ...browserOptions(),
			});
			done.push({clip: r.clip, t: Number(r.t), frame, out: r.out});
		}
	} finally {
		await browser.close({silent: true});
	}
	return {bundleCached: cached, stills: done};
}

async function boxesAt(video, requests) {
	const {serveUrl} = await getBundle(video);
	const inputProps = {layers: 'all', reportBoxes: true};
	const browser = await openBrowser('chrome', browserOptions());
	const comps = {};
	const frames = [];
	try {
		for (const r of requests) {
			comps[r.clip] ??= await composition(serveUrl, r.clip, inputProps, browser);
			let found = null;
			await renderStill({
				composition: comps[r.clip], serveUrl, frame: frameAt(comps[r.clip], r.t), inputProps, overwrite: true,
				output: path.join(tmpdir(), `studio-boxes-${process.pid}.png`), logLevel: 'error',
				puppeteerInstance: browser, ...browserOptions(),
				onBrowserLog: (l) => {
					if (l.text.startsWith('STUDIO_BOXES ')) found = JSON.parse(l.text.slice('STUDIO_BOXES '.length));
				},
			});
			if (!found) throw new Error(`the frame at ${r.clip} t=${r.t} reported no boxes`);
			frames.push({clip: r.clip, t: Number(r.t), band: found.band, boxes: found.boxes});
		}
	} finally {
		await browser.close({silent: true});
	}
	return {frames};
}

async function boxes(video, clip, t) {
	const {frames} = await boxesAt(video, [{clip, t}]);
	return {clip, t: Number(t), boxes: {band: frames[0].band, boxes: frames[0].boxes}};
}

async function render(video, clip, out, quality, range) {
	const q = QUALITY[quality ?? 'draft'];
	if (!q) throw new Error(`unknown quality ${quality}`);
	const {serveUrl, cached} = await getBundle(video);
	const inputProps = {layers: 'all'};
	const comp = await composition(serveUrl, clip, inputProps);
	const frameRange = range ? [frameAt(comp, range[0]), frameAt(comp, range[1])] : null;
	mkdirSync(path.dirname(out), {recursive: true});
	const started = Date.now();
	await renderMedia({
		composition: comp, serveUrl, codec: 'h264', outputLocation: out, inputProps, muted: true,
		scale: q.scale, crf: q.crf, jpegQuality: q.jpegQuality, imageFormat: 'jpeg', frameRange,
		overwrite: true, logLevel: 'error', concurrency: opt.concurrency ? Number(opt.concurrency) : null, ...browserOptions(),
	});
	return {clip, out, quality: quality ?? 'draft', frames: comp.durationInFrames, bundleCached: cached,
		seconds: (Date.now() - started) / 1000};
}

async function duration(video, clip) {
	const {serveUrl} = await getBundle(video);
	const comp = await composition(serveUrl, clip, {layers: 'all'});
	return {clip, frames: comp.durationInFrames, fps: comp.fps, seconds: comp.durationInFrames / comp.fps};
}

const ops = {
	still: () => stills(opt.video, [{clip: opt.clip, t: opt.t, out: opt.out, layers: opt.layers, scale: opt.scale}]),
	stills: () => stills(opt.video, JSON.parse(readFileSync(opt.requests, 'utf8'))),
	render: () => render(opt.video, opt.clip, opt.out, opt.quality, opt.range),
	boxes: () => boxes(opt.video, opt.clip, opt.t),
	boxesAt: () => boxesAt(opt.video, JSON.parse(readFileSync(opt.requests, 'utf8'))),
	duration: () => duration(opt.video, opt.clip),
	bundle: () => getBundle(opt.video),
};

if (!ops[op]) {
	log(`unknown op ${op}; expected one of ${Object.keys(ops).join(', ')}`);
	process.exit(2);
}
opt.video = path.resolve(opt.video);
ops[op]().then(
	(r) => console.log(JSON.stringify(r)),
	(e) => {
		log(e.stack || String(e));
		process.exit(1);
	},
);
