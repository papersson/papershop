export type Shot = {
  /** 1-based number, stable for the session. */
  n: number
  /** The copy this mod keeps, so a later screenshot to the same path can't change it. */
  path: string
  /** Where Claude wrote it. */
  origin: string
  /** When it was noticed, milliseconds since the epoch. */
  at: number
  /** Pixel size; a 16:10 guess when the header could not be read. */
  width: number
  height: number
  /** True for a PNG the terminal can draw. */
  isPng: boolean
  /** What produced it. */
  source: 'agent-browser' | 'screencapture' | 'read'
  /** The page the browser was on, when known. */
  page?: string
  /** The subagent that took it; absent for the main conversation. */
  agent?: string
}

declare module 'claude-code' {
  interface PluginState {
    'screenshot-pane': {
      /** Every screenshot noticed this session, oldest first, capped. */
      shots: Shot[]
      /** Which one the pane shows: an index, or -1 to follow the newest. */
      index: number
      /** True once the person closed the pane; new shots then toast instead. */
      dismissed: boolean
      /** True while the pane shows the previous shot of the same page. */
      compare: boolean
    }
  }
}
