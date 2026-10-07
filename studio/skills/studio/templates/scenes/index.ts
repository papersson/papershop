// One scene per chapter of SCRIPT.md, keyed by clip id (chapter N is sN). A chapter not listed here
// renders its board (boards/boards.json and the screen notes), so start from boards and register
// each chapter as its scene is built: import {S1} from './s1'; then {s1: S1}.
// example-chapter.tsx and example-map.tsx show the kit's building blocks and the map/close-up look.
export default {} as Record<string, import('react').FC>;
