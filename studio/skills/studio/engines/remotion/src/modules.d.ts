// Resolved per video by the bundler's aliases (see cli.mjs).
declare module '@video/index' {
	const scenes: Record<string, import('react').FC>;
	export default scenes;
}
declare module '@timeline' {
	const timeline: unknown;
	export default timeline;
}
declare module '@layout' {
	const layout: unknown;
	export default layout;
}
