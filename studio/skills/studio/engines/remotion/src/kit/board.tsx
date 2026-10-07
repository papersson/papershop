import React from 'react';
import timeline from '@timeline';
import {Arrow, Rect, Svg, Txt, useStage, type XY} from './stage';
import {FAINT, INK, MUTED, SANS} from './theme';
import {useClip} from './time';
import type {Timeline} from './types';

/**
 * A board: one rough frame per beat, drawn before a chapter's scene exists, so what the picture
 * shows (and where) is settled while it is cheap to change. The builder writes the frames in
 * boards/boards.json; each holds from the sentence it names until the next frame. The screen note of
 * the sentence being spoken runs along the bottom, and a chapter without frames shows its notes alone.
 * Deliberately rough: dashed outlines and plain text, never the final look.
 */
export type BoardElement =
	| {box: string; at: XY; w?: number; h?: number}
	| {text: string; at: XY; size?: number}
	| {arrow: [XY, XY]}
	| {line: [XY, XY]}
	| {dot: XY; r?: number};
export type BoardFrame = {from: string; elements: BoardElement[]};

const T = timeline as Timeline;

const Element: React.FC<{e: BoardElement}> = ({e}) => {
	if ('box' in e) {
		const w = e.w ?? 2.4;
		const h = e.h ?? 0.9;
		return (
			<>
				<Rect at={e.at} w={w} h={h} radius={0.08} stroke={MUTED} strokeWidth={2} dashed name={`board box ${e.box}`} />
				{e.box && <Txt at={e.at} size={18} color={INK} font="sans">{e.box}</Txt>}
			</>
		);
	}
	if ('text' in e) return <Txt at={e.at} size={e.size ?? 20} color={INK} font="sans" name={`board text ${e.text}`}>{e.text}</Txt>;
	if ('arrow' in e) return <Svg><Arrow from={e.arrow[0]} to={e.arrow[1]} color={MUTED} width={2} dash={0.07} /></Svg>;
	if ('line' in e) return <Svg><Arrow from={e.line[0]} to={e.line[1]} color={MUTED} width={2} tip={0} dash={0.07} /></Svg>;
	const r = e.r ?? 0.18;
	return <Rect at={e.dot} w={2 * r} h={2 * r} radius={r} stroke={MUTED} strokeWidth={2} dashed name="board dot" />;
};

export const Board: React.FC<{clip: string; frames?: BoardFrame[]; notes?: Record<string, string>}> = ({clip, frames = [], notes = {}}) => {
	const {t} = useClip();
	const s = useStage();
	const clipStart = T.tracks.scene.find((c) => c.id === clip)?.start ?? 0;
	const sentences = T.tracks.narration.filter((n) => n.clip === clip);
	const startOf = (id: string) => (sentences.find((n) => n.id === id)?.start ?? clipStart) - clipStart;
	const frame = [...frames].sort((a, b) => startOf(a.from) - startOf(b.from)).filter((f) => startOf(f.from) <= t).pop();
	// A screen note describes the picture until the next note, like a frame.
	const noted = [...sentences].reverse().find((n) => n.start - clipStart <= t && notes[n.id]);
	const note = noted ? notes[noted.id] : undefined;
	const alone = !frame;
	return (
		<>
			<Txt at={[s.width / 2 / s.unit - 0.45, 4 - 0.6]} anchor="right" size={16} color={FAINT} weight={500} name="board tag">BOARD</Txt>
			{frame?.elements.map((e, i) => <Element key={i} e={e} />)}
			{note && (
				<div data-box="board note" style={{
					position: 'absolute', left: s.width * 0.08, width: s.width * 0.84,
					top: alone ? s.height * 0.36 : s.height - s.unit * 1.25,
					color: alone ? INK : MUTED, fontFamily: SANS, fontSize: (alone ? 40 : 30) * s.unit / 115,
					lineHeight: 1.35, textAlign: alone ? 'center' : 'left',
				}}>
					{alone ? note : `${noted!.id}  ${note}`}
				</div>
			)}
		</>
	);
};
