import {makeProject} from '@motion-canvas/core';
import s1 from './s1?scene';

// One scene per clip in timeline.json, in order. Each scene must end at its clip's end (studioScene
// holds the frame until then), so the clips tile the video.
export default makeProject({scenes: [s1]});
