// How an engine hands its result back to the kit. The kit names a file with --reply and reads the
// JSON from it: through a pipe, a reply larger than the pipe's buffer (64 KiB) was cut short when
// the engine exited before stdout drained. Without --reply (a person running the CLI by hand) the
// JSON goes to stdout, and the process exits only once it is written.
import { writeFileSync } from 'node:fs'

export function reply(file, result) {
  const json = JSON.stringify(result)
  if (file && file !== true) {
    writeFileSync(file, json)
    process.exit(0)
  }
  process.stdout.write(json + '\n', () => process.exit(0))
}
