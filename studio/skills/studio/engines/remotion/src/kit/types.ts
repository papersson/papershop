export type Word = {w: string; start: number; end: number};
export type Sentence = {id: string; clip: string; text: string; caption: string; start: number; end: number; words: Word[]};
// lines: the 16:9 lines; wrapped: every other format's, keyed by format (the kit wraps them all).
export type Caption = {start: number; end: number; lines: string[]; wrapped?: Record<string, string[]>};
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
// band.font and band.chars: caption size in px and the line width in characters the kit wraps captions to (narrow formats need bigger type and shorter lines).
// format: set on a format's generated layout (absent for the video's own, 16:9).
export type Layout = {width: number; height: number; fps: number; format?: string; band: {height: number; style: 'opaque' | 'frosted'; font?: number; chars?: number}};
