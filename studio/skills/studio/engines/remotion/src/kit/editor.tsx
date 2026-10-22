import React from 'react';
import {Rect, Txt, kitMeans, pt, toPx, useStage, type XY} from './stage';
import {Panel} from './blocks';
import {useClip} from './time';
import {AMBER, FAINT, ICE, INK, MUTED, mix} from './theme';

// Typed code (references/code.md): an editor, its terminal and the program's window, replaying
// data/typing.json, which `studio typing` writes from a plan. One keystroke stream drives this picture
// and the key sounds in the soundtrack, so every key lands on its own frame. A scene imports the file
// and passes it in: `import typing from '../data/typing.json'`, then <Editor typing={typing} ids={['draw']} … />.

type Step = [number, string, unknown[][]];
export type TypingBurst = {
	cue: string; clip: string; file: string; before: string[]; after: string[]; steps: Step[]; end: number; first?: number;
	run?: {cmd: string; up: number; enter: number; pop: number; log: [number, string][]};
};
export type Typing = Record<string, TypingBurst>;
type Line = {text: string; born: number};

/** data/codeview.json (kit/src/studio_kit/codeview.py is the model; this mirrors its `project`): how the
 *  teaching shows the program. Times are cue names, or [name, offset seconds]. */
type When = string | [string, number];
export type CodeView = {
	source?: string; open?: [When, When][]; payoff?: When;
	folds?: {lines: [number, number]; label: string; from?: When; to?: When}[];
	highlights?: {lines: [number, number]; from: When; to?: When; refer?: When}[];
	helpers?: {id: string; title: string; text: string; from: When; to: When}[];
};
const whenAt = (w: When | undefined, cue: (name: string) => number): number | null =>
	w === undefined ? null : typeof w === 'string' ? cue(w) : cue(w[0]) + w[1];
export type EditorState = {
	lines: Line[]; caret: [number, number] | null; mode: string; modeAt: number; lastKey: number; now: number;
	burst: TypingBurst; started: boolean;
};

const clamp = (n: number) => Math.max(0, Math.min(1, n));
const MONO_ADVANCE = 0.6;      // IBM Plex Mono's advance, in ems
const MIN_TEXT_PX = 18;        // the legible check's floor

/** The burst's frame now: frames since its cue. */
function framesSince(t: number, cue: (name: string) => number, fps: number, burst: TypingBurst) {
	return Math.round((t - cue(burst.cue)) * fps + 1e-6);
}

/** The editor at clip time t: the latest burst of `ids` that has started, replayed to t. */
export function editorAt(typing: Typing, ids: string[], t: number, cue: (name: string) => number, fps: number): EditorState {
	let pick = -1;
	ids.forEach((id, i) => {
		if (!typing[id]) throw new Error(`no burst ${id} in data/typing.json (studio typing writes it)`);
		if (framesSince(t, cue, fps, typing[id]) >= 0) pick = i;
	});
	const burst = typing[ids[Math.max(0, pick)]];
	const started = pick >= 0, now = started ? framesSince(t, cue, fps, burst) : -1;
	const lines: Line[] = burst.before.map((text) => ({text, born: -1e6}));
	let caret: [number, number] | null = [Math.max(0, lines.length - 1), 0];
	let mode = 'NORMAL', modeAt = -1e6, lastKey = -1e6;
	if (started) {
		for (const [f, , fx] of burst.steps) {
			if (f > now) break;
			lastKey = f;
			for (const e of fx) {
				const [k, a, b] = e as [string, number, unknown];
				if (k === 'ins') lines.splice(a, 0, ...(b as string[]).map((text) => ({text, born: f})));
				else if (k === 'set') lines[a] = {...lines[a], text: b as string};
				else if (k === 'del') lines.splice(a, 1);
				else if (k === 'caret') caret = [a, b as number];
				else if (k === 'mode') {mode = a as unknown as string; modeAt = f;}
			}
		}
	}
	if (!lines.length) lines.push({text: '', born: -1e6});
	return {lines, caret, mode, modeAt, lastKey, now, burst, started};
}

const KEYWORDS = 'int|float|double|char|bool|void|return|if|else|while|for|const|static|struct|true|false|def|fn|let|var|function|import|from|class|pub|use';
const TOKEN = new RegExp(`("[^"\\n]*"|'[^'\\n]*'|\\b(?:${KEYWORDS})\\b|\\b\\d+(?:\\.\\d+)?f?\\b|//.*$|#.*$)`, 'g');
function colour(part: string) {
	if (part.startsWith('//') || part.startsWith('#')) return FAINT;
	if (part.startsWith('"') || part.startsWith("'")) return mix(INK, AMBER, 0.45);
	if (/^\d/.test(part)) return AMBER;
	return new RegExp(`^(${KEYWORDS})$`).test(part) ? ICE : INK;
}
function syntax(line: string, key: string) {
	return line.split(TOKEN).filter(Boolean).map((part, i) => <span key={key + i} style={{color: colour(part)}}>{part}</span>);
}
/** Syntax colour lands when a token is finished: the word under a typing caret stays plain. */
function typedLine(text: string, col: number | null) {
	if (col === null || col !== text.length) return syntax(text || ' ', 'a');
	let s = col;
	while (s > 0 && /[\w."]/.test(text[s - 1])) s--;
	const quotes = (text.slice(0, col).match(/"/g) ?? []).length;
	if (quotes % 2 === 1) s = Math.min(s, text.lastIndexOf('"', col - 1));
	return <>{syntax(text.slice(0, s), 'a')}<span style={{color: INK}}>{text.slice(s, col)}</span></>;
}

/**
 * A Vim-style editor typing the bursts `ids` of data/typing.json: line numbers, the typed text with
 * syntax colour, the caret (a block in NORMAL, a bar in INSERT, blinking only while idle), new lines
 * growing in, and the mode line (-- INSERT --, :w, "main.c" 9L written). `rows` lines show, following
 * the caret; `from` names a line to scroll to first. Text keeps one size across the bursts, never
 * under 18 px. Name: `editor` by default; each line is `<name> line N`.
 */
export const Editor: React.FC<{
	typing: Typing; ids: string[]; at: XY; w: number; rows?: number; size?: number; from?: string[];
	focus?: string[]; title?: string; opacity?: number; name?: string; means?: string; view?: CodeView;
}> = ({typing, ids, at, w, rows = 14, size = 22, from = [], focus = [], title, opacity = 1, name = 'editor', means, view}) => {
	const s = useStage();
	const {t, cue, fps} = useClip();
	const st = editorAt(typing, ids, t, cue, fps);
	const spans = view?.open;
	if (spans && !spans.some(([a, b]) => t >= whenAt(a, cue)! && t < whenAt(b, cue)!)) {
		// collapsed between uses: just the file's title bar, so the stage is free for what is being explained
		return <>
			<Panel at={[at[0], at[1] + 0.0]} w={w} h={0.6} opacity={opacity * 0.8} name={`${name} collapsed`} />
			<Txt at={[at[0] - w / 2 + 0.3, at[1]]} anchor="left" size={16} color={MUTED} opacity={opacity * 0.8}
				name={`${name} file`}>{title || st.burst.file}</Txt>
		</>;
	}
	const complete = view?.payoff !== undefined && t >= whenAt(view.payoff, cue)!;      // the payoff: everything shows
	const folds = complete ? [] : (view?.folds ?? []).filter((f) => (f.from === undefined || t >= whenAt(f.from, cue)!)
		&& (f.to === undefined || t < whenAt(f.to, cue)!));
	const litLines = new Set<number>();
	if (!complete) for (const h of view?.highlights ?? []) {
		if (t >= whenAt(h.from, cue)! && (h.to === undefined || t < whenAt(h.to, cue)!)) for (let n = h.lines[0]; n <= h.lines[1]; n++) litLines.add(n);
	}
	const longest = Math.max(20, ...ids.flatMap((id) => [...typing[id].after, ...typing[id].before]).map((l) => l.length));
	const fit = (w - 1.4) * s.unit / (longest * MONO_ADVANCE * pt(s, 1));
	const sz = Math.max(MIN_TEXT_PX / pt(s, 1), Math.min(size, fit));
	const em = pt(s, sz) / s.unit, adv = em * MONO_ADVANCE, lh = em * 1.6;
	const bar = 0.55, h = rows * lh + bar * 2 + 0.2;
	const top = at[1] + h / 2 - bar - 0.1, left = at[0] - w / 2;
	let first = 0;
	for (const needle of from) {
		const i = st.lines.findIndex((l) => l.text.includes(needle));
		if (i >= 0) {first = i; break;}
	}
	if (st.caret && st.caret[0] > first + rows - 2) first = st.caret[0] - rows + 2;
	first = Math.max(0, Math.min(first, st.lines.length - 1));
	const typing_ = st.started && st.now - st.lastKey < Math.round(0.6 * fps) && st.now <= st.burst.end + 4;
	const insert = st.mode === 'INSERT';
	const blink = typing_ ? 1 : (Math.floor(t / 0.53) % 2 === 0 ? 1 : 0);
	const cmd = st.mode.startsWith('CMD:') ? st.mode.slice(4) : null;
	const age = st.now - st.modeAt;
	const msg = /^(WRITTEN|MSG):/.test(st.mode) && age < 2.5 * fps ? st.mode.replace(/^(WRITTEN|MSG):/, '') : null;
	const written = st.mode.startsWith('WRITTEN:') ? clamp(1 - age / 8) : 0;
	const base = (st.burst.first ?? 1) - 1;
	// rows: each line, or one row for a fold (its label), always in the program's own order
	type Row = {idx: number; text: string; fold: boolean};
	const all: Row[] = [];
	for (let i = 0; i < st.lines.length; i++) {
		const f = folds.find((x) => x.lines[0] === i + 1 + base);
		if (f) {all.push({idx: i, text: f.label, fold: true}); i += f.lines[1] - f.lines[0]; continue;}
		all.push({idx: i, text: st.lines[i].text, fold: false});
	}
	const firstRow = Math.max(0, all.findIndex((r) => r.idx >= first));
	const shown = all.slice(firstRow, firstRow + rows);
	return <>
		<Panel at={at} w={w} h={h} opacity={opacity} name={name} />
		{title !== undefined && <Txt at={[left + 0.3, at[1] + h / 2 - bar / 2]} anchor="left" size={16} color={MUTED} opacity={opacity}
			name={`${name} file`}>{title || st.burst.file}</Txt>}
		{shown.map((row, i) => {
			const n = row.idx, line = row.fold ? {text: row.text, born: -1e6} : st.lines[n], y = top - (i + 0.5) * lh;
			const caretHere = st.caret !== null && st.caret[0] === n && !cmd && !row.fold;
			const lit = (typing_ && caretHere) || (!typing_ && (litLines.has(n + 1 + base) || focus.some((f) => line.text.includes(f))));
			const grow = line.born > -1e5 ? clamp((st.now - line.born + 1) / 3) : 1;
			return <React.Fragment key={n}>
				{lit && <Rect at={[at[0], y]} w={w - 0.1} h={lh} fill={mix('#151B22', ICE, 0.12)} opacity={opacity} name={`${name} current line`} />}
				<Txt at={[left + 0.85, y]} anchor="right" size={sz * 0.8} color={caretHere ? MUTED : FAINT} opacity={opacity * grow}
					name={`${name} line number ${n + 1 + base}`}>{String(n + 1 + base)}</Txt>
				<Txt at={[left + 1.1, y]} anchor="left" size={sz} color={INK} opacity={opacity * grow * ((focus.length || litLines.size) && !lit && !typing_ ? 0.62 : 1) * (row.fold ? 0.7 : 1)}
					name={`${name} line ${n + 1 + base}`} means={kitMeans(means, lit)}>{row.fold ? <span style={{color: MUTED}}>{'▸ ' + row.text + ' …'}</span> : typedLine(line.text, insert && caretHere ? st.caret![1] : null)}</Txt>
				{caretHere && <Rect at={[left + 1.1 + st.caret![1] * adv + (insert ? 0.01 : adv / 2), y]} w={insert ? 0.03 : adv} h={lh * 0.72}
					fill={INK} opacity={opacity * blink * (insert ? 0.95 : 0.7)} name={`${name} caret`} />}
			</React.Fragment>;
		})}
		<Rect at={[at[0], at[1] - h / 2 + bar / 2 + 0.05]} w={w - 0.16} h={bar - 0.08} radius={0.08} fill={mix('#151B22', '#7FD18B', written * 0.25)}
			opacity={opacity} name={`${name} mode line`} />
		<Txt at={[left + 0.3, at[1] - h / 2 + bar / 2]} anchor="left" size={16} opacity={opacity} name={`${name} mode`}
			color={cmd !== null ? INK : msg ? '#7FD18B' : insert ? AMBER : MUTED}>{cmd !== null ? cmd : msg ?? (insert ? '-- INSERT --' : 'NORMAL')}</Txt>
	</>;
};

/**
 * A helper card from data/codeview.json: what a folded or external piece does, shown only between its
 * `from` and `to`, fading in and out. `id` picks the card.
 */
export const HelperCard: React.FC<{view: CodeView; id: string; at: XY; w: number; opacity?: number; name?: string}> =
({view, id, at, w, opacity = 1, name = 'helper'}) => {
	const {t, cue} = useClip();
	const h = view.helpers?.find((x) => x.id === id);
	if (!h) throw new Error(`no helper ${id} in data/codeview.json`);
	const a = whenAt(h.from, cue)!, b = whenAt(h.to, cue)!;
	const o = clamp((t - a) / 0.25) * clamp((b - t) / 0.25);
	if (o <= 0) return null;
	return <>
		<Panel at={at} w={w} h={1.5} opacity={opacity * o} name={name} />
		<Txt at={[at[0] - w / 2 + 0.3, at[1] + 0.4]} anchor="left" size={20} color={ICE} opacity={opacity * o} name={`${name} title`}>{h.title}</Txt>
		<Txt at={[at[0] - w / 2 + 0.3, at[1] - 0.2]} anchor="left" size={18} color={INK} opacity={opacity * o} name={`${name} text`}>{h.text}</Txt>
	</>;
};

/** The latest run of `ids` that has begun at clip time t, with its beat in clip seconds. */
export function runAt(typing: Typing, ids: string[], t: number, cue: (name: string) => number, fps: number) {
	let out: {id: string; up: number; enter: number; pop: number} | null = null;
	for (const id of ids) {
		const run = typing[id].run;
		if (!run) continue;
		const t0 = cue(typing[id].cue);
		if (t >= t0 + run.up / fps) out = {id, up: t0 + run.up / fps, enter: t0 + run.enter / fps, pop: t0 + run.pop / fps};
	}
	return out;
}

/**
 * The terminal under the editor: the build-and-run command recalled, Enter, the build's silence, then
 * the program's recorded output a line a frame. Each output line ticks in the soundtrack.
 */
export const RunTerminal: React.FC<{typing: Typing; ids: string[]; at: XY; w: number; rows?: number; size?: number; opacity?: number; name?: string}> =
({typing, ids, at, w, rows = 5, size = 17, opacity = 1, name = 'terminal'}) => {
	const s = useStage();
	const {t, cue, fps} = useClip();
	let lines: {text: string; color: string}[] = [];
	for (const id of ids) {
		const b = typing[id];
		if (!b.run) continue;
		const now = framesSince(t, cue, fps, b);
		if (now < b.run.up) continue;
		lines = [...lines.slice(-1), {text: b.run.cmd, color: INK}, ...b.run.log.filter(([f]) => now >= f).map(([, l]) => ({text: l, color: MUTED}))];
	}
	const r = runAt(typing, ids, t, cue, fps);
	const tail = lines.slice(-rows);
	const em = pt(s, size) / s.unit, lh = em * 1.5, h = rows * lh + 0.5;
	const blink = Math.floor(t / 0.53) % 2 === 0;
	return <>
		<Panel at={at} w={w} h={h} opacity={opacity} name={name} />
		{(tail.length ? tail : [{text: '$ ', color: INK}]).map((l, i) => <Txt key={i} at={[at[0] - w / 2 + 0.3, at[1] + h / 2 - 0.25 - (i + 0.5) * lh]}
			anchor="left" size={size} color={l.color} opacity={opacity} name={`${name} row ${i}`}>
			{l.text}{((r && t < r.enter && i === tail.length - 1) || !tail.length) && blink ? '▍' : ''}</Txt>)}
	</>;
};

/** A window's weight: it closes on the run's Enter and opens on its pop with a small overshoot and settle. */
export function windowMotion(t: number, enter: number | null, pop: number | null) {
	if (pop !== null && t >= pop) {
		const u = t - pop;
		const scale = u < 0.1 ? 0.9 + 0.125 * Math.sin(u / 0.1 * Math.PI / 2) : 1 + 0.025 * Math.exp(-(u - 0.1) / 0.09) * Math.cos((u - 0.1) / 0.2 * Math.PI * 1.5);
		return {scale, opacity: clamp(u / 0.07)};
	}
	if (enter !== null && t >= enter) {
		const u = clamp((t - enter) / 0.13);
		return {scale: 1 - 0.04 * u, opacity: 1 - u};
	}
	return {scale: 1, opacity: 1};
}

/**
 * The program's window, answering the run beat: it closes on Enter and opens with weight when the
 * program starts. `children(id, pop)` draws what the program shows for the run `id` (pop: when it
 * started, in clip seconds), a capture or a scene of its own; before any run, the window is empty.
 */
export const ProgramWindow: React.FC<{
	typing: Typing; ids: string[]; at: XY; w: number; h: number; children: (id: string, pop: number) => React.ReactNode; name?: string;
}> = ({typing, ids, at, w, h, children, name = 'program window'}) => {
	const s = useStage();
	const {t, cue, fps} = useClip();
	const r = runAt(typing, ids, t, cue, fps);
	if (!r) return null;
	const opened = t >= r.pop;
	const prev = ids.slice(0, ids.indexOf(r.id)).reverse().find((id) => typing[id].run);
	const id = opened ? r.id : prev;
	if (!id) return null;
	const m = opened ? windowMotion(t, null, r.pop) : windowMotion(t, r.enter, null);
	if (m.opacity <= 0) return null;
	const pop = opened ? r.pop : cue(typing[id].cue) + typing[id].run!.pop / fps;
	const [x, y] = toPx(s, [at[0] - w / 2, at[1] + h / 2]);
	return <div data-box={name} style={{position: 'absolute', left: x, top: y, width: w * s.unit, height: h * s.unit,
		transformOrigin: '50% 60%', transform: `scale(${m.scale})`, opacity: m.opacity, overflow: 'hidden'}}>
		{children(id, pop)}
	</div>;
};
