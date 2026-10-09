import React from 'react';
import {Rect, Svg, Txt, pt, toPx, useStage, type Stage, type XY} from './stage';
import {Box, Link, Panel} from './blocks';
import {AMBER, CORAL, ICE, INK, MUTED, TRAY_EDGE, mix} from './theme';

const clamp = (n: number) => Math.max(0, Math.min(1, n));
const outputLines = (text: string) => text === '' ? [] : text.replace(/\r\n/g, '\n').replace(/\n$/, '').split('\n');
type Area = {at: XY; w: number; opacity?: number; size?: number; name?: string};

const MIN_TEXT_PX = 18;       // the legible check's floor: a text box at least 18 px tall at 1080p
const MONO_ADVANCE = 0.6;     // IBM Plex Mono's advance, in ems
/**
 * A mono text size in points: `size`, shrunk so `chars` characters fit `width` stage units, and never
 * under 18 px on this stage (a long line shrinks to fit before it clips, down to the floor).
 */
export function legibleSize(s: Stage, size: number, chars = 0, width = Infinity): number {
	const px = pt(s, 1);
	const fit = chars > 0 ? (width * s.unit) / (chars * MONO_ADVANCE * px) : Infinity;
	return Math.max(MIN_TEXT_PX / px, Math.min(size, fit));
}
const columns = (line: string) => line.replace(/\t/g, '        ').length;
/** An unmodified file from studio steps results.json. Line ranges are 1-based, inclusive. */
export type SourceFile = {text: string; sha256: string};

export const CodePanel: React.FC<Area & {
  source: SourceFile; range?: [number, number]; current?: number; plumbing?: number[];
  markers?: Record<number, string>; tokens?: {line: number; text: string; progress: number}[];
}> = ({at, w, source, range, current, plumbing = [], markers = {}, tokens = [], opacity = 1, size = 20, name = 'code'}) => {
  const s = useStage();
  const lines = source.text.replace(/\r\n/g, '\n').split('\n');
  if (lines.at(-1) === '') lines.pop();
  const first = range?.[0] ?? 1, last = range?.[1] ?? lines.length;
  const shown = lines.slice(first - 1, last);
  const sz = legibleSize(s, size, Math.max(0, ...shown.map(columns)), w - 1.2), lh = sz * 0.031;   // code starts 1 unit in
  return <>
    <Panel at={at} w={w} h={shown.length * lh + 0.6} opacity={opacity}/>
    {shown.map((line, i) => {
      const n = first + i, y = at[1] + (shown.length - 1) * lh / 2 - i * lh;
      const cues = tokens.filter(c => c.line === n && c.progress > 0);
      const color = current === n ? ICE : plumbing.includes(n) ? MUTED : INK;
      let offset = 0;
      const parts: React.ReactNode[] = [];
      for (const cue of cues) {
        const pos = line.indexOf(cue.text, offset);
        if (pos < 0) continue;
        parts.push(line.slice(offset, pos), <span key={pos} style={{color: mix(color, AMBER, clamp(cue.progress))}}>{cue.text}</span>);
        offset = pos + cue.text.length;
      }
      parts.push(line.slice(offset));
      return <React.Fragment key={n}>
        <Txt at={[at[0] - w / 2 + 0.2, y]} anchor="left" size={sz} color={current === n ? ICE : MUTED}
          opacity={opacity} name={`${name} line number ${n}`}>{markers[n] ?? String(n)}</Txt>
        <Txt at={[at[0] - w / 2 + 1, y]} anchor="left" size={sz} color={color}
          opacity={opacity} name={`${name} line ${n}`}>{parts}</Txt>
      </React.Fragment>;
    })}
  </>;
};

export type CapturedRun = {argv: string[]; stdout: string; stderr: string; exit: number | null};
export const Terminal: React.FC<Area & {runs: CapturedRun[]; progress?: number; maxLines?: number}> =
({at, w, runs, progress = 1, maxLines = 9, opacity = 1, size = 20, name = 'terminal'}) => {
  const lines = runs.flatMap(r => [{text: '$ ' + r.argv.join(' '), color: MUTED},
    ...outputLines(r.stdout).map(text => ({text, color: INK})),
    ...outputLines(r.stderr).map(text => ({text, color: r.exit ? CORAL : MUTED}))]);
  const shown = lines.slice(0, Math.floor(lines.length * clamp(progress))).slice(-maxLines);
  const s = useStage(), sz = legibleSize(s, size, Math.max(0, ...shown.map(l => columns(l.text))), w - 0.6), lh = sz * 0.031;
  return <><Panel at={at} w={w} h={Math.max(1, shown.length) * lh + 0.6} opacity={opacity}/>
    {shown.map((line, i) => <Txt key={i} at={[at[0] - w / 2 + 0.3, at[1] + (shown.length - 1) * lh / 2 - i * lh]}
      size={sz} anchor="left" color={line.color} opacity={opacity} name={`${name} row ${i}`}>{line.text}</Txt>)}
  </>;
};

export const RowTable: React.FC<Area & {columns: string[]; rows: Record<string, unknown>[]; highlight?: [number, string]; progress?: number}> =
({at, w, columns, rows, highlight, progress = 1, opacity = 1, size = 20, name = 'table'}) => {
  const shown = rows.slice(0, Math.ceil(rows.length * clamp(progress))), cw = w / Math.max(1, columns.length), lh = 0.65;
  // The table's outline (2.5) is heavier than the dividers between its cells (1.5); a selected cell is outlined in ice.
  return <><Rect at={at} w={cw * columns.length} h={(shown.length + 1) * lh} stroke={TRAY_EDGE} strokeWidth={2.5} opacity={opacity} name={name}/>
  {[Object.fromEntries(columns.map(c => [c, c])), ...shown].map((row, i) => columns.map((c, j) => {
    const pos: XY = [at[0] - w / 2 + (j + 0.5) * cw, at[1] + shown.length * lh / 2 - i * lh];
    const selected = highlight?.[0] === i - 1 && highlight[1] === c;
    return <React.Fragment key={`${i}-${c}`}>
      <Rect at={pos} w={cw} h={lh} stroke={selected ? ICE : TRAY_EDGE} strokeWidth={selected ? 2.5 : 1.5} opacity={opacity}/>
      <Txt at={pos} size={Math.max(18, size)} color={selected ? ICE : i ? INK : MUTED} opacity={opacity}
        name={`${name} ${i ? `row ${i}` : 'header'} ${c}`}>{typeof row[c] === 'object' ? JSON.stringify(row[c]) : String(row[c] ?? '')}</Txt>
    </React.Fragment>;
  }))}</>;
};

/** Flatten actual JSON values while retaining their key path for a deterministic cursor. */
export function jsonRows(value: unknown, path: string[] = []): {path: string[]; text: string}[] {
  if (value !== null && typeof value === 'object') {
    return [{path, text: Array.isArray(value) ? '[' : '{'}, ...Object.entries(value).flatMap(([key, v]) => jsonRows(v, [...path, key]))];
  }
  return [{path, text: JSON.stringify(value) ?? 'null'}];
}
export const JsonTree: React.FC<Area & {value: unknown; cursor?: string[]; progress?: number}> =
({at, w, value, cursor = [], progress = 1, opacity = 1, size = 20, name = 'json'}) => {
  const all = jsonRows(value), rows = all.slice(0, Math.ceil(all.length * clamp(progress))), lh = 0.55;
  return <>{rows.map((r, i) => <Txt key={JSON.stringify(r.path)} at={[at[0] - w / 2 + r.path.length * 0.3, at[1] + (all.length - 1) * lh / 2 - i * lh]}
    anchor="left" size={Math.max(18, size)} color={JSON.stringify(r.path) === JSON.stringify(cursor) ? ICE : INK}
    opacity={opacity} name={`${name} ${r.path.join('.') || 'root'}`}>{(r.path.length ? r.path.at(-1) + ': ' : '') + r.text}</Txt>)}</>;
};

export const ColumnStrips: React.FC<Area & {columns: {name: string; bytes: number; groups?: number[]}[]; h?: number; open?: number}> =
({at, w, columns, h = 3, open = 0, opacity = 1, size = 20}) => {
  const total = columns.reduce((sum, c) => sum + Math.max(0, c.bytes), 0);
  let x = at[0] - w / 2;
  return <>{columns.map(c => {
    const width = total ? w * Math.max(0, c.bytes) / total : 0, center = x + width / 2; x += width;
    let y = at[1] + h / 2;
    const groups = c.groups ?? [c.bytes], denom = groups.reduce((a, b) => a + b, 0) || 1;
    return <React.Fragment key={c.name}>
      <Txt at={[center, at[1] + h / 2 + 0.35]} size={Math.max(18, size)} opacity={opacity} name={`column ${c.name}`}>{c.name}</Txt>
      {groups.map((bytes, i) => {const gh = h * bytes / denom, cy = y - gh / 2; y -= gh;
        return <Rect key={i} at={[center + clamp(open) * i * 0.12, cy]} w={width} h={gh} stroke={ICE} opacity={opacity} name={`${c.name} group ${i}`}/>;
      })}
    </React.Fragment>;
  })}</>;
};

export const VarCard: React.FC<Area & {label: string; value: string; type: string; focus?: number}> =
({at, w, label, value, type, focus = 0, opacity = 1, size = 20}) => <>
  <Box at={at} w={w} h={1.5} text={value} lit={focus} opacity={opacity} size={Math.max(18, size)} name={`variable ${label}`}/>
  <Txt at={[at[0] - w / 2 + 0.2, at[1] + 0.52]} anchor="left" size={18} opacity={opacity} name={`${label} type`}>{label + ': ' + type}</Txt>
</>;

/** A reference relationship, not a travelling data token. */
export const Thread: React.FC<{from: XY; to: XY; progress?: number; opacity?: number}> = props => <Link {...props} tip={0} color={ICE}/>;

export type Geometry = {type: 'Point'; coordinates: XY} | {type: 'LineString' | 'MultiPoint'; coordinates: XY[]} |
  {type: 'Polygon' | 'MultiLineString'; coordinates: XY[][]} | {type: 'MultiPolygon'; coordinates: XY[][][]};
export type GeoFeature = {id: string | number; geometry: Geometry};
function paths(g: Geometry): XY[][] {
  if (g.type === 'Point') return [[g.coordinates]];
  if (g.type === 'LineString') return [g.coordinates];
  if (g.type === 'MultiPoint') return g.coordinates.map(p => [p]);
  if (g.type === 'MultiPolygon') return g.coordinates.flat();
  return g.coordinates as XY[][];
}
/** Normalized GeoJSON only. Convert WKT in sims/; coordinate units/projection belong in the evidence. */
export const GeoMap: React.FC<Area & {features: GeoFeature[]; h?: number; selected?: string | number; halo?: number; grid?: number}> =
({at, w, features, h = 5, selected, halo = 0, grid = 0, opacity = 1}) => {
  const stage = useStage(), pts = features.flatMap(f => paths(f.geometry).flat());
  if (!pts.length) return null;
  const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
  const scale = Math.min(w / (maxX - minX || 1), h / (maxY - minY || 1));
  const point = (p: XY) => toPx(stage, [at[0] + (p[0] - (minX + maxX) / 2) * scale, at[1] + (p[1] - (minY + maxY) / 2) * scale]);
  return <><Svg opacity={opacity}>{features.map(f => {
    const color = selected === f.id ? ICE : MUTED;
    const d = paths(f.geometry).map(path => path.map((p, i) => `${i ? 'L' : 'M'}${point(p).join(',')}`).join(' ') +
      (f.geometry.type.includes('Polygon') ? ' Z' : '')).join(' ');
    return <g key={f.id}>{halo > 0 && selected === f.id && <path d={d} fill="none" stroke={ICE} strokeWidth={14 * clamp(halo)} opacity={0.2}/>}
      {f.geometry.type === 'Point' || f.geometry.type === 'MultiPoint' ? paths(f.geometry).flat().map((p, i) => <circle key={i} cx={point(p)[0]} cy={point(p)[1]} r={4} fill={color}/>) :
        <path d={d} fill="none" stroke={color} strokeWidth={2}/>}</g>;
  })}</Svg>{Array.from({length: Math.max(0, Math.floor(grid)) + 1}, (_, i) => grid > 0 && <React.Fragment key={i}>
    <Link from={[at[0] - w / 2 + i * w / grid, at[1] - h / 2]} to={[at[0] - w / 2 + i * w / grid, at[1] + h / 2]} opacity={opacity * 0.4} tip={0}/>
    <Link from={[at[0] - w / 2, at[1] - h / 2 + i * h / grid]} to={[at[0] + w / 2, at[1] - h / 2 + i * h / grid]} opacity={opacity * 0.4} tip={0}/>
  </React.Fragment>)}</>;
};
