import React, {useLayoutEffect, useState} from 'react';
import {AbsoluteFill, continueRender, delayRender, useCurrentFrame} from 'remotion';
import layout from '@layout';
import videoConfig from '@video-config';
import {Rect, Txt, pt, useStage, StageContext, type XY} from './stage';
import {Box, Card, Link, Term} from './blocks';
import {Chip} from './components';
import {CloseUp, GhostCard, MapView, Token, type MapNode, type TokenState} from './map';
import {CodePanel, RowTable, Terminal, legibleSize} from './explain';
import * as THEME from './theme';
import {AMBER, BAND, BG, CORAL, DIM, FAINT, ICE, INK, MUTED, PANEL, SANS, TRAY_EDGE, TRAY_FILL} from './theme';
import {CaptionBand, FONTS} from './Frame';
import type {Layout} from './types';

/**
 * The look sheet (`studio look-sheet VIDEO`): the model sheet a video's scenes are drawn to, rendered
 * with the kit's own components in the video's theme and layout, one page per frame of the
 * `studio-look` composition. Every element is shown in each of its states; the video's own elements
 * follow from scenes/look.tsx (templates/scenes/example-look.tsx), whose default export maps a page
 * title to a component drawn on the stage. A video that declares a colour legend (video.json legend)
 * gets a page of it after the built-in ones.
 */

const ROLES: [string, string, string][] = [
	['BG', BG, 'background'], ['BAND', BAND, 'caption band'], ['PANEL', PANEL, 'panel, close-up'],
	['TRAY_FILL', TRAY_FILL, 'box fill'], ['TRAY_EDGE', TRAY_EDGE, 'box outline'], ['DIM', DIM, 'guide line'],
	['INK', INK, 'text'], ['MUTED', MUTED, 'idle arrow, secondary text'], ['FAINT', FAINT, 'guide text'],
	['ICE', ICE, 'the thing explained, selection'], ['AMBER', AMBER, 'cost, a number to watch'], ['CORAL', CORAL, 'failure'],
];
const SIZES: [number, string][] = [[24, 'close-up header'], [20, 'map name, chapter label'], [18, 'box and card text'],
	[17, 'terminal line'], [16, 'panel title'], [14, 'sub-label, token label']];

/** The stage's width in units, and n x positions spread across it. */
function across(n: number, sw: number, margin = 0.8): number[] {
	return Array.from({length: n}, (_, i) => -sw / 2 + margin + ((sw - 2 * margin) * (i + 0.5)) / n);
}
const Note: React.FC<{at: XY; children: string}> = ({at, children}) => (
	<Txt at={at} size={14} color={MUTED} name={`look caption ${children}`}>{children}</Txt>
);

const Palette: React.FC = () => {
	const s = useStage();
	const sw = s.width / s.unit;
	const narrow = s.width < s.height;
	const left = -sw / 2 + 0.5;
	const lines = ROLES.map(([name, hex, role]) => `${name} ${hex} ${role}`);
	const colW = narrow ? sw - 1.6 : sw * 0.45;
	const size = legibleSize(s, 16, Math.max(...lines.map((l) => l.length)), colW);
	const step = narrow ? 0.34 : 0.5;
	const top = 4 - (s.header ?? 0) / s.unit - 0.9;
	return (
		<>
			{ROLES.map(([name, hex], i) => (
				<React.Fragment key={name}>
					<Rect at={[left + 0.18, top - i * step]} w={0.36} h={0.36 * (narrow ? 0.8 : 1)} radius={0.05} fill={hex} stroke={DIM} strokeWidth={1.5} name={`swatch ${name}`} />
					<Txt at={[left + 0.5, top - i * step]} anchor="left" size={size} name={`colour ${name}`}>{lines[i]}</Txt>
				</React.Fragment>
			))}
			{SIZES.map(([sz, role], i) => {
				const at: XY = narrow ? [left, top - ROLES.length * step - 0.3 - i * 0.42] : [1.2, top - i * 0.9];
				const text = narrow ? `${sz} pt: ${role}` : `${sz} pt, ${Math.round(pt(s, sz))} px: ${role}`;
				return <Txt key={sz} at={at} anchor="left" size={sz} name={`type ${sz}`}>{text}</Txt>;
			})}
		</>
	);
};

const TOKENS: TokenState[] = ['idle', 'ok', 'bad', 'wait'];

const Elements: React.FC = () => {
	const s = useStage();
	const sw = s.width / s.unit;
	const narrow = s.width < s.height;
	const top = 4 - (s.header ?? 0) / s.unit - 1.5;            // the first row, clear of the chapter label
	// A narrow stage (9:16) has room for the card alone on its row; the ghost and the terminal line share the last.
	const row = (i: number) => top + (narrow ? [0, 0.18, 0.36, 0.7, 1][i] * (-3.3 - top) : [0, 0.22, 0.42, 0.75, 1][i] * (-3.55 - top));
	const b = across(3, sw);
	const bw = Math.min(2.6, (sw - 1.6) / 3 - 0.3);
	const t = across(4, sw);
	const c = across(3, sw);
	const cw = Math.min(4, (sw - 1.6) / 3 - 0.3);
	const half = Math.min(1.2, bw / 2);
	const [cardAt, ghostAt, termAt]: XY[] = narrow ? [[0, row(3)], [-sw / 4, row(4)], [sw / 4, row(4)]] : [[c[0], row(3)], [c[1], row(3)], [c[2], row(3)]];
	const [cardW, smallW] = narrow ? [sw - 1.4, sw / 2 - 0.5] : [cw, cw];
	return (
		<>
			<Chip text="chapter label" opacity={1} />
			<Box at={[b[0], row(0)]} w={bw} text="server" name="box idle" />
			<Box at={[b[1], row(0)]} w={bw} text="server" lit={1} name="box lit" />
			<Box at={[b[2], row(0)]} w={bw} text="server" bad={1} name="box failed" />
			{['idle', 'lit', 'failed'].map((x, i) => <Note key={x} at={[b[i], row(0) - 0.65]}>{x}</Note>)}
			<Link from={[b[0] - half, row(1)]} to={[b[0] + half, row(1)]} />
			<Link from={[b[1] - half, row(1)]} to={[b[1] + half, row(1)]} color={ICE} width={3} />
			<Link from={[b[2] - half, row(1)]} to={[b[2] + half, row(1)]} opacity={0.3} />
			{['idle', 'active', 'muted'].map((x, i) => <Note key={x} at={[b[i], row(1) - 0.35]}>{x}</Note>)}
			{TOKENS.map((state, i) => <Token key={state} at={[t[i], row(2)]} state={state} label={state} />)}
			<Card at={cardAt} w={cardW} lines={['key: "a1"', 'state: open', 'retries: 3']} lit={[0, 1, 0]} bad={[0, 0, 1]} />
			<GhostCard at={ghostAt} w={smallW} h={narrow ? 1 : 1.2}><Txt at={ghostAt} size={18} color={ICE}>proposed</Txt></GhostCard>
			<Term at={termAt} w={smallW} text="make run" />
			{!narrow && ['card: lit and failed lines', 'ghost: a proposed change', 'terminal line'].map((x, i) => <Note key={x} at={[c[i], row(4)]}>{x}</Note>)}
		</>
	);
};

const NODES: MapNode[] = [
	{id: 'client', name: 'client', at: [-4.5, 0]},
	{id: 'server', name: 'server', at: [0, 0]},
	{id: 'db', name: 'database', at: [4.5, 0]},
];
const EDGES = [{from: 'client', to: 'server'}, {from: 'server', to: 'db'}];

const MapPage: React.FC = () => (
	<>
		<Chip text="the map" opacity={1} />
		<MapView nodes={NODES} edges={EDGES} visible={{client: 1, server: 1, db: 1}} lit={{server: 1}} litEdges={{'server>db': 1}}>
			<Token at={[-4.5, 1.1]} state="wait" />
		</MapView>
	</>
);

const Close: React.FC = () => {
	const s = useStage();
	const w = Math.min(6, s.width / s.unit - 1.2);
	const record = 'the record this chapter is about';
	const detail = 'a detail only this close-up needs';
	return (
		<CloseUp open={1} from={NODES[1]} name="server" nodes={NODES}>
			<GhostCard at={[0, 0.3]} w={w} h={1.6}>
				<Txt at={[0, 0.3]} size={legibleSize(s, 22, record.length, w - 0.4)} color={ICE}>{record}</Txt>
			</GhostCard>
			<Txt at={[0, -1.2]} size={legibleSize(s, 18, detail.length, w)} color={MUTED}>{detail}</Txt>
		</CloseUp>
	);
};

const SOURCE = {text: 'def total(rows):\n    out = 0\n    for row in rows:\n        out += row.price\n    return out\n', sha256: ''};

const Code: React.FC = () => {
	const s = useStage();
	const sw = s.width / s.unit;
	const narrow = s.width < s.height;
	const w = narrow ? sw - 1 : sw / 2 - 0.8;
	const [a, b]: [XY, XY] = narrow ? [[0, 2.0], [0, -0.92]] : [[-sw / 4, 0.6], [sw / 4, 0.6]];
	return (
		<>
			<CodePanel at={a} w={w} source={SOURCE} current={4} plumbing={[2]} tokens={[{line: 4, text: 'row.price', progress: 1}]} />
			<Terminal at={b} w={w} runs={[{argv: ['python', 'total.py'], stdout: '42\n', stderr: '', exit: 0}]} />
			<RowTable at={narrow ? [0, -2.97] : [0, -2.6]} w={Math.min(6, sw - 1)} columns={['id', 'price']} rows={[{id: 1, price: 30}, {id: 2, price: 12}]}
				highlight={[1, 'price']} />
		</>
	);
};

// The colour legend, meaning -> a theme colour's name (ice, AMBER, tray_fill) or #rrggbb.
const LEGEND = Object.entries((videoConfig as {legend?: Record<string, string>}).legend ?? {});
function themeColour(v: string): string {
	if (/^#[0-9a-f]{6}$/i.test(v)) return v;
	const hex = (THEME as Record<string, unknown>)[v.trim().toUpperCase().replace(/-/g, '_')];
	if (typeof hex !== 'string' || !hex.startsWith('#')) throw new Error(`video.json legend: ${JSON.stringify(v)} is not a theme colour (kit/theme.ts) or #rrggbb`);
	return hex;
}

/** Each meaning in its colour beside a swatch, its colour's name and value under it. */
const Legend: React.FC = () => {
	const s = useStage();
	const sw = s.width / s.unit;
	const left = -sw / 2 + 0.5;
	const top = 4 - (s.header ?? 0) / s.unit - 0.9;
	const step = Math.min(0.8, (top + 3.6) / Math.max(1, LEGEND.length));
	return (
		<>
			{LEGEND.map(([meaning, name], i) => {
				const hex = themeColour(name);
				const y = top - i * step;
				return (
					<React.Fragment key={meaning}>
						<Rect at={[left + 0.22, y]} w={0.44} h={0.44} radius={0.06} fill={hex} stroke={DIM} strokeWidth={1.5} name={`legend swatch ${meaning}`} means={meaning} />
						<Txt at={[left + 0.7, y + 0.11]} anchor="left" size={20} weight={600} font="sans" color={hex} name={`legend ${meaning}`} means={meaning}>{meaning}</Txt>
						<Txt at={[left + 0.7, y - 0.2]} anchor="left" size={14} color={MUTED} name={`legend colour ${meaning}`}>
							{name.startsWith('#') ? name : `${name}  ${hex}`}
						</Txt>
					</React.Fragment>
				);
			})}
		</>
	);
};

/** The built-in pages, in order (the legend's only when the video declares one); the video's own come after them. */
export const LOOK_PAGES: {title: string; Page: React.FC}[] = [
	{title: 'colour and type', Page: Palette},
	{title: 'elements and states', Page: Elements},
	{title: 'map', Page: MapPage},
	{title: 'close-up', Page: Close},
	{title: 'code', Page: Code},
	...(LEGEND.length ? [{title: 'colour legend', Page: Legend}] : []),
];

/** One page of the look sheet per frame: the built-in pages, then `own` (scenes/look.tsx); the band shows `caption`. */
export const LookSheet: React.FC<{pages: string[]; own: React.FC[]; caption?: string[]}> = ({pages, own, caption = []}) => {
	const l = layout as Layout;
	const [fontsHandle] = useState(() => delayRender('fonts'));
	const [ready, setReady] = useState(false);
	useLayoutEffect(() => {
		Promise.all(FONTS.map((f) => document.fonts.load(f))).then(() => {
			setReady(true);
			continueRender(fontsHandle);
		});
	}, [fontsHandle]);
	const n = useCurrentFrame();
	const stageH = l.height - l.band.height;
	const stage = {width: l.width, height: stageH, unit: stageH / 8, header: l.header?.height ?? 0};
	const Page = n < LOOK_PAGES.length ? LOOK_PAGES[n].Page : own[n - LOOK_PAGES.length];
	return (
		<AbsoluteFill style={{background: BG}}>
			{ready && (
				<StageContext.Provider value={stage}>
					<div style={{position: 'absolute', left: 0, top: 0, width: l.width, height: stageH}}>
						{Page && <Page />}
					</div>
				</StageContext.Provider>
			)}
			<CaptionBand top={stageH} height={l.band.height} font={l.band.font ?? 38} time={0} show={ready} given={caption} />
			{/* The page's name, in the band's corner: on the stage it would sit where a scene's header goes. */}
			<div data-box="look tag" style={{position: 'absolute', right: 24, bottom: 16, fontFamily: SANS, fontSize: 18, fontWeight: 600,
				color: FAINT, opacity: ready ? 1 : 0}}>{`LOOK ${n + 1}/${pages.length}  ${pages[n] ?? ''}`}</div>
		</AbsoluteFill>
	);
};

