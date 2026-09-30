import React from 'react';
import {Beats, Chapter, Chip, CloseUp, GhostCard, MapView, Token, Txt, MUTED, ICE, ramp, useClip, type MapNode} from '@studio';

// A map and one close-up, the explainer's default look. The map shows component names and state
// only; the detail lives in a close-up opened from its box, and closing it returns the same map.
const NODES: MapNode[] = [
	{id: 'client', name: 'client', at: [-4.5, 0]},
	{id: 'server', name: 'server', at: [0, 0]},
	{id: 'db', name: 'database', at: [4.5, 0]},
];
const EDGES = [{from: 'client', to: 'server'}, {from: 'server', to: 'db'}];

export const MapScene: React.FC = () => {
	const {t, at} = useClip();
	const b = new Beats();
	const a = b.at(at('01'), 0.5);
	const s = b.at(at('02'), 0.5);
	const d = b.at(at('03'), 0.5);
	const light = b.at(at('04'), 0.4);            // the source box lights just before the zoom
	const zoomIn = b.play(0.9);
	const zoomOut = b.at(at('05'), 0.7);
	const visible = {client: ramp(t, a, 0.5), server: ramp(t, s, 0.5), db: ramp(t, d, 0.5)};
	const open = ramp(t, zoomIn, 0.9) * (1 - ramp(t, zoomOut, 0.7));
	const lit = {server: ramp(t, light, 0.4) * (1 - ramp(t, zoomOut + 0.3, 0.4))};
	const token = 1 - ramp(t, zoomIn, 0.4) * (1 - ramp(t, zoomOut + 0.4, 0.4));
	return (
		<Chapter>
			<Chip text="The map" opacity={ramp(t, a, 0.5)} />
			<MapView nodes={NODES} edges={EDGES} visible={visible} lit={lit} opacity={1 - open}>
				<Token at={[-4.5, 1.1]} state="wait" opacity={visible.client * token} />
			</MapView>
			<CloseUp open={open} from={NODES[1]} name="server" nodes={NODES}>
				<GhostCard at={[0, 0.3]} w={6} h={1.6}>
					<Txt at={[0, 0.3]} size={22} color={ICE}>{'{{the record this chapter is about}}'}</Txt>
				</GhostCard>
				<Txt at={[0, -1.2]} size={18} color={MUTED}>{'{{a detail only this close-up needs}}'}</Txt>
			</CloseUp>
		</Chapter>
	);
};
