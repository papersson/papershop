export type Word = {w: string; start: number; end: number};
export type Sentence = {id: string; clip: string; text: string; caption: string; start: number; end: number; words: Word[]};
export type Caption = {start: number; end: number; lines: string[]};
export type SceneClip = {id: string; engine: string; title: string; start: number; end: number};
export type Beats = {bpm: number; beats: number[]; downbeats: number[]; hits: number[]};
export type FootageSegment = {id: string; file: string; in: number; out: number; start: number; end: number};
export type Timeline = {
	beats?: Beats;
	fps: number;
	duration: number;
	tracks: {scene: SceneClip[]; narration: Sentence[]; captions: Caption[]; footage?: FootageSegment[]};
	cues: Record<string, number>;
};
// band.font and band.chars: caption size in px and line width in characters (narrow formats need bigger type and shorter lines).
export type Layout = {width: number; height: number; fps: number; band: {height: number; style: 'opaque' | 'frosted'; font?: number; chars?: number}};
