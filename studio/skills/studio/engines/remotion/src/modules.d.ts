// Resolved per video by the bundler's aliases (see cli.mjs).
declare module '@video/index' {
	const scenes: Record<string, import('react').FC>;
	export default scenes;
}
declare module '@timeline' {
	const timeline: unknown;
	export default timeline;
}
declare module '@boards' {
	const boards: unknown;
	export default boards;
}
declare module '@board-notes' {
	const notes: unknown;
	export default notes;
}
declare module '@layout' {
	const layout: unknown;
	export default layout;
}
declare module '@video-config' {
	const config: unknown;
	export default config;
}
declare module '@look' {
	const pages: Record<string, import('react').FC>;
	export default pages;
}
