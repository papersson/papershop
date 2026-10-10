// The Remotion engine's side of the studio's engine interface. The Python kit calls it; each call
// prints one JSON object on stdout (logs go to stderr).
//
//   node cli.mjs still    --video DIR --clip ID --t SEC --out PNG [--layers L] [--scale S]
//   node cli.mjs stills   --video DIR --requests JSON        [{clip, t, out, layers?, scale?, boards?}], one browser
//   node cli.mjs render   --video DIR --clip ID --out MP4 [--quality draft|final] [--range A B]
//   node cli.mjs boxes    --video DIR --clip ID --t SEC
//   node cli.mjs boxesAt  --video DIR --requests JSON        [{clip, t, out?}], one browser
//   node cli.mjs duration --video DIR --clip ID
//   node cli.mjs durations --video DIR --clips ID,ID,...      one browser
//   node cli.mjs render ... [--concurrency N]                 default: every core
//   node cli.mjs look     --video DIR --out DIR [--caption JSON]  the look sheet: look-<n>.png per page
//
// Layers: all (default), no-captions (the band stays, its text goes), no-band (the scene alone),
// background (nothing but the background).
// The bundle is cached per content hash of the engine source, the video's scenes, timeline and
// layout, so a still after an edit costs one incremental bundle plus one frame.
import {bundle} from '@remotion/bundler';
import {openBrowser, renderMedia, renderStill, selectComposition} from '@remotion/renderer';
import {createHash} from 'node:crypto';
import {existsSync, mkdirSync, readdirSync, readFileSync, rmSync, statSync} from 'node:fs';
import {availableParallelism, tmpdir} from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {frameOf} from '../shared/timing.js';

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
// Every core by default: Remotion's own default is half of them, and rendering is CPU-bound (on an
// 8-core M3 a 1080p chapter went from 43 to 68 frames/s). --concurrency overrides it.
const CONCURRENCY = opt.concurrency ? Number(opt.concurrency) : availableParallelism();
// Stills render in parallel tabs of one browser; past a handful of tabs they only contend.
const STILL_TABS = Math.max(1, Math.min(6, CONCURRENCY));

/** Run `fn` over `items` with at most `n` in flight, keeping results in order. */
async function pool(items, n, fn) {
	const out = new Array(items.length);
	let next = 0;
	await Promise.all(Array.from({length: Math.min(n, items.length)}, async () => {
		while (next < items.length) {
			const i = next++;
			out[i] = await fn(items[i], i);
		}
	}));
	return out;
}

// Names relative to the hashed root, so a moved or copied video keeps its bundle key.
// Names, sizes and times only: assets can be large footage, and reading it on every render is slow.
function hashListing(h, p) {
	if (!existsSync(p) || !statSync(p).isDirectory()) return;
	for (const name of readdirSync(p).sort()) {
		const f = path.join(p, name);
		const st = statSync(f);
		if (st.isDirectory()) hashListing(h, f);
		else h.update(`${path.relative(p, f)}:${st.size}:${Math.floor(st.mtimeMs / 1000)}`);
	}
}

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

// The look sheet's own pages: scenes/look.tsx when the video has one.
function lookFile(video) {
	const own = ['tsx', 'ts', 'jsx'].map((ext) => path.join(video, 'scenes', `look.${ext}`)).find((f) => existsSync(f));
	return own ?? path.join(ENGINE, 'src', 'empty-look.ts');
}

function boardFile(video, name) {
	const f = path.join(video, 'boards', name);
	return existsSync(f) ? f : path.join(ENGINE, 'src', 'empty.json');
}

// entry: the bundle's entry point in src/; the look sheet's (look-entry.tsx) is a bundle of its own.
async function getBundle(video, entry = 'entry.tsx') {
	const h = createHash('sha1');
	h.update(entry);
	for (const p of [path.join(ENGINE, 'src'), path.join(ENGINE, '..', 'shared'), path.join(ENGINE, 'package-lock.json'),
		path.join(video, 'scenes'), path.join(video, 'data'), path.join(video, 'boards'), path.join(video, 'timeline.json'),
		opt.layout ? path.resolve(opt.layout) : path.join(video, 'layout.json')]) {
		hashTree(h, p);
	}
	hashListing(h, path.join(video, 'assets'));
	const key = h.digest('hex').slice(0, 16);
	// One folder per layout (format), so exporting several formats doesn't discard each other's bundles.
	const root = path.join(video, '.cache', 'bundle', (opt.layout ? path.basename(opt.layout, '.json') : 'default') + (entry === 'entry.tsx' ? '' : '-look'));
	const out = path.join(root, key);
	if (existsSync(path.join(out, 'index.html'))) return {serveUrl: out, cached: true};
	const layoutFile = opt.layout ? path.resolve(opt.layout) : path.join(video, 'layout.json');
	await bundle({
		entryPoint: path.join(ENGINE, 'src', entry),
		outDir: out,
		enableCaching: true,
		publicDir: existsSync(path.join(video, 'assets')) ? path.join(video, 'assets') : null,
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
					// Boards are optional: a video without them gets empty ones.
					'@boards': boardFile(video, 'boards.json'),
					'@board-notes': boardFile(video, 'notes.json'),
					'@look': lookFile(video),
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
	return Math.min(comp.durationInFrames - 1, Math.max(0, frameOf(Number(t), comp.fps)));
}

async function stills(video, requests) {
	const {serveUrl, cached} = await getBundle(video);
	const browser = await openBrowser('chrome', browserOptions());
	const comps = {};
	let done;
	try {
		// Compositions first (one per clip and layer set), then the frames in parallel tabs.
		for (const r of requests) {
			const inputProps = {layers: r.layers ?? 'all', boards: Boolean(r.boards)};
			const key = `${r.clip}/${inputProps.layers}/${inputProps.boards}`;
			comps[key] ??= await composition(serveUrl, r.clip, inputProps, browser);
		}
		done = await pool(requests, STILL_TABS, async (r) => {
			const inputProps = {layers: r.layers ?? 'all', boards: Boolean(r.boards)};
			const comp = comps[`${r.clip}/${inputProps.layers}/${inputProps.boards}`];
			const frame = frameAt(comp, r.t);
			mkdirSync(path.dirname(r.out), {recursive: true});
			await renderStill({
				composition: comp, serveUrl, output: r.out, frame, inputProps,
				scale: Number(r.scale ?? 1), imageFormat: r.out.endsWith('.jpg') ? 'jpeg' : 'png',
				puppeteerInstance: browser, overwrite: true, logLevel: 'error', ...browserOptions(),
			});
			return {clip: r.clip, t: Number(r.t), frame, out: r.out};
		});
	} finally {
		await browser.close({silent: true});
	}
	return {bundleCached: cached, stills: done};
}

async function boxesAt(video, requests) {
	// [{clip, t, out?}]: each frame's labelled boxes; with `out`, the full-resolution frame is kept
	// there too, so a caller that needs both renders the frame once.
	const {serveUrl} = await getBundle(video);
	const inputProps = {layers: 'all', reportBoxes: true};
	const browser = await openBrowser('chrome', browserOptions());
	const comps = {};
	let frames;
	try {
		for (const r of requests) comps[r.clip] ??= await composition(serveUrl, r.clip, inputProps, browser);
		frames = await pool(requests, STILL_TABS, async (r, i) => {
			let found = null;
			const output = r.out ?? path.join(tmpdir(), `studio-boxes-${process.pid}-${i}.png`);
			if (r.out) mkdirSync(path.dirname(r.out), {recursive: true});
			await renderStill({
				composition: comps[r.clip], serveUrl, frame: frameAt(comps[r.clip], r.t), inputProps, overwrite: true,
				output, logLevel: 'error', imageFormat: output.endsWith('.jpg') ? 'jpeg' : 'png',
				puppeteerInstance: browser, ...browserOptions(),
				onBrowserLog: (l) => {
					if (l.text.startsWith('STUDIO_BOXES ')) found = JSON.parse(l.text.slice('STUDIO_BOXES '.length));
				},
			});
			if (!r.out) rmSync(output, {force: true});
			if (!found) throw new Error(`the frame at ${r.clip} t=${r.t} reported no boxes`);
			return {clip: r.clip, t: Number(r.t), band: found.band, boxes: found.boxes, out: r.out ?? null};
		});
	} finally {
		await browser.close({silent: true});
	}
	return {frames};
}

async function durations(video, clips) {
	// Every clip's frame count in one browser session (the length check asked one process per clip).
	const {serveUrl} = await getBundle(video);
	const browser = await openBrowser('chrome', browserOptions());
	try {
		const out = [];
		for (const clip of clips) {
			const comp = await composition(serveUrl, clip, {layers: 'all'}, browser);
			out.push({clip, frames: comp.durationInFrames, fps: comp.fps});
		}
		return {clips: out};
	} finally {
		await browser.close({silent: true});
	}
}

async function boxes(video, clip, t) {
	const {frames} = await boxesAt(video, [{clip, t}]);
	return {clip, t: Number(t), boxes: {band: frames[0].band, boxes: frames[0].boxes}};
}

async function look(video, outDir, caption) {
	// The studio-look composition draws one page per frame; its titles are the kit's and scenes/look.tsx's.
	const {serveUrl} = await getBundle(video, 'look-entry.tsx');
	const inputProps = {caption: caption ? JSON.parse(caption) : []};
	const browser = await openBrowser('chrome', browserOptions());
	try {
		const comp = await composition(serveUrl, 'studio-look', inputProps, browser);
		mkdirSync(outDir, {recursive: true});
		const pages = await pool(Array.from({length: comp.durationInFrames}, (_, i) => i), STILL_TABS, async (i) => {
			const out = path.join(outDir, `look-${i + 1}.png`);
			await renderStill({composition: comp, serveUrl, output: out, frame: i, inputProps, imageFormat: 'png',
				puppeteerInstance: browser, overwrite: true, logLevel: 'error', ...browserOptions()});
			return {page: i + 1, title: comp.props.pages?.[i] ?? '', out};
		});
		return {pages};
	} finally {
		await browser.close({silent: true});
	}
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
		overwrite: true, logLevel: 'error', concurrency: CONCURRENCY, ...browserOptions(),
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
	durations: () => durations(opt.video, String(opt.clips).split(',')),
	bundle: () => getBundle(opt.video),
	look: () => look(opt.video, path.resolve(opt.out), opt.caption),
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
