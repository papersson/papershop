// Resolved per video by the Vite aliases and defines (see cli.mjs).
declare module '@timeline' {
	const timeline: import('./kit').TimelineJson;
	export default timeline;
}
declare module '@layout' {
	const layout: import('./kit').LayoutJson;
	export default layout;
}
declare const __STUDIO_PROJECT__: string;
