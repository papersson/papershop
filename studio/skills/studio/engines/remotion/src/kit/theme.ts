// The studio's default palette: one meaning per colour. Amber is cost or a number to watch, ice the
// thing being explained, coral failure; muted, faint and dim are text and guide greys.
export const BG = '#0F1318';
export const BAND = '#0A0D11';
export const INK = '#E6EBF0';
export const MUTED = '#8C97A4';
export const FAINT = '#56606B';
export const DIM = '#2B333C';
export const PANEL = '#151B22';
export const TRAY_FILL = '#17202A';
export const TRAY_EDGE = '#C9D3DD';
export const AMBER = '#F2A93B';
export const ICE = '#8FD3FF';
export const CORAL = '#E4715F';

export const SANS = '"IBM Plex Sans", sans-serif';
export const MONO = '"IBM Plex Mono", monospace';

/** Linear blend of two #rrggbb colours, k in 0..1. */
export function mix(a: string, b: string, k: number): string {
	const p = (c: string, i: number) => parseInt(c.slice(1 + 2 * i, 3 + 2 * i), 16);
	const ch = (i: number) => Math.round(p(a, i) + (p(b, i) - p(a, i)) * Math.min(1, Math.max(0, k)));
	return '#' + [0, 1, 2].map((i) => ch(i).toString(16).padStart(2, '0')).join('');
}
