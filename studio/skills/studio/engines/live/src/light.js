// The live engine's light layer (c.L): tens of thousands of glowing points and lines on a WebGL2
// canvas under the SVG stage, for the big pictures of a network: traffic on the world's cables, a zoom
// from one home out to the planet, the dozens of requests behind one page. Light adds up, so crowded
// places glow; a soft bloom, a gentle shoulder and a fixed dither finish the frame so dark gradients
// survive a video encode.
//
// Like the other stages, a frame is whatever this frame drew. A scene calls L.point and L.line with
// world coordinates, the same ones its SVG uses, and the layer draws them through the camera the SVG
// stage ends the frame with (S.cam, c.camAt, shots, a match cut), so labels drawn in SVG sit on the
// lights. Light drawn inside a nested scene (a join's incoming chapter, a callback) follows that
// scene's camera, its inset and its opacity, and a join's dissolve fades this chapter's light with its
// SVG. The canvas is made on first use and hidden on a frame that draws no light.
//
// The layer paints the background itself (the theme's --bg, or L.look({ground})), because light can
// only add to something under it: a scene that uses it draws nothing opaque in the SVG's back layer.
// The 3D stage's canvas (c.G) is opaque and sits above it, so one frame uses one or the other.

const VS_POINT = `#version 300 es
layout(location=0) in vec2 corner;
layout(location=1) in vec2 pos;    // world
layout(location=2) in float size;  // radius, world units
layout(location=3) in vec4 col;    // rgb, alpha
uniform mat3 uM; uniform float uScale, uPx, uOp; uniform vec2 uRes;
out vec2 vUv; out vec4 vCol;
void main() {
  vec2 s = (uM * vec3(pos, 1.)).xy;
  float r = size * uScale;
  // A point smaller than a pixel or so keeps a visible size and loses brightness instead.
  float k = r < uPx ? r / uPx * 0.6 + 0.4 : 1.;
  vec2 p = s + corner * max(r, uPx);
  vUv = corner; vCol = vec4(col.rgb, col.a * k * uOp);
  gl_Position = vec4(p.x / uRes.x * 2. - 1., 1. - p.y / uRes.y * 2., 0., 1.);
}`
const FS_POINT = `#version 300 es
precision highp float;
in vec2 vUv; in vec4 vCol; out vec4 o;
uniform float uSoft;
void main() {
  float d = length(vUv); if (d > 1.) discard;
  float a = vCol.a * (1. - smoothstep(1. - uSoft - 0.08, 1., d));
  o = vec4(vCol.rgb * a, a);
}`
const VS_LINE = `#version 300 es
layout(location=0) in vec2 corner;   // x: 0..1 along, y: -1..1 across
layout(location=1) in vec4 ab;       // a.xy, b.xy, world
layout(location=2) in float width;   // pixels
layout(location=3) in vec4 col;
uniform mat3 uM; uniform float uOp; uniform vec2 uRes;
out vec4 vCol; out float vAcross;
void main() {
  vec2 a = (uM * vec3(ab.xy, 1.)).xy, b = (uM * vec3(ab.zw, 1.)).xy;
  vec2 d = b - a; float len = max(length(d), 1e-4); vec2 n = vec2(-d.y, d.x) / len, t = d / len;
  float w = width * 0.5 + 0.75;
  vec2 p = mix(a - t * w * 0.5, b + t * w * 0.5, corner.x) + n * corner.y * w;
  vCol = vec4(col.rgb, col.a * uOp); vAcross = corner.y * w / max(width * 0.5, 0.5);
  gl_Position = vec4(p.x / uRes.x * 2. - 1., 1. - p.y / uRes.y * 2., 0., 1.);
}`
const FS_LINE = `#version 300 es
precision highp float;
in vec4 vCol; in float vAcross; out vec4 o;
void main() { float a = vCol.a * (1. - smoothstep(0.6, 1.25, abs(vAcross))); o = vec4(vCol.rgb * a, a); }`
const VS_FULL = `#version 300 es
layout(location=0) in vec2 corner; out vec2 vUv;
void main() { vUv = corner * 0.5 + 0.5; gl_Position = vec4(corner, 0., 1.); }`
const FS_BLUR = `#version 300 es
precision highp float;
in vec2 vUv; out vec4 o; uniform sampler2D uT; uniform vec2 uDir;
void main() {
  vec4 s = texture(uT, vUv) * 0.227027;
  s += (texture(uT, vUv + uDir * 1.384615) + texture(uT, vUv - uDir * 1.384615)) * 0.316216;
  s += (texture(uT, vUv + uDir * 3.230769) + texture(uT, vUv - uDir * 3.230769)) * 0.070270;
  o = s;
}`
// The ground stays exactly its colour where there is no light (so a cut to an SVG-only frame shows no
// seam); light is added with a soft shoulder towards white, so bright cores never clip hard.
const FS_COMP = `#version 300 es
precision highp float;
in vec2 vUv; out vec4 o;
uniform sampler2D uScene, uB1, uB2; uniform vec3 uTop, uBot; uniform float uBloom;
float h(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
void main() {
  vec3 bg = mix(uBot, uTop, vUv.y);
  vec3 light = texture(uScene, vUv).rgb + (texture(uB1, vUv).rgb * 0.6 + texture(uB2, vUv).rgb * 0.9) * uBloom;
  vec3 col = bg + (1. - bg) * (1. - exp(-light * 1.25));
  if (dot(light, light) > 0.) col += (h(gl_FragCoord.xy) - 0.5) / 255. * 2.5;
  o = vec4(col, 1.);
}`

/** The look a frame starts with; L.look() changes it for this frame. */
const LOOK = { bloom: 1, soft: 0.85, minPx: 1.2, ground: 'var(--bg)' }

function program(gl, vs, fs) {
  const shader = (type, src) => {
    const s = gl.createShader(type)
    gl.shaderSource(s, src)
    gl.compileShader(s)
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(`L: ${gl.getShaderInfoLog(s)}`)
    return s
  }
  const p = gl.createProgram()
  gl.attachShader(p, shader(gl.VERTEX_SHADER, vs))
  gl.attachShader(p, shader(gl.FRAGMENT_SHADER, fs))
  gl.linkProgram(p)
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(`L: ${gl.getProgramInfoLog(p)}`)
  const u = {}
  return { p, u: n => u[n] ?? (u[n] = gl.getUniformLocation(p, n)) }
}

function target(gl, w, h) {
  const tex = gl.createTexture()
  gl.bindTexture(gl.TEXTURE_2D, tex)
  gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA16F, w, h, 0, gl.RGBA, gl.HALF_FLOAT, null)
  for (const [k, v] of [[gl.TEXTURE_MIN_FILTER, gl.LINEAR], [gl.TEXTURE_MAG_FILTER, gl.LINEAR],
    [gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE], [gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE]]) gl.texParameteri(gl.TEXTURE_2D, k, v)
  const fb = gl.createFramebuffer()
  gl.bindFramebuffer(gl.FRAMEBUFFER, fb)
  gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0)
  return { tex, fb, w, h }
}

/** A growing array of instances, `stride` floats each. */
class Batch {
  constructor(stride) { this.stride = stride; this.a = new Float32Array(stride * 1024); this.n = 0 }
  room() {
    if ((this.n + 1) * this.stride > this.a.length) {
      const b = new Float32Array(this.a.length * 2)
      b.set(this.a)
      this.a = b
    }
    return this.n++ * this.stride
  }
}

const colours = new Map()
let probe = null
/** A colour (a theme name such as 'cold', var(--name), #rrggbb or any CSS colour) as [r, g, b], 0..1. */
export function rgbOf(c) {
  if (Array.isArray(c)) return c
  let rgb = colours.get(c)
  if (rgb) return rgb
  let v = String(c).trim()
  const m = v.match(/^var\((--[\w-]+)\)$/) ?? (/^[a-z][\w-]*$/.test(v) && !CSS.supports('color', v) ? [null, `--${v}`] : null)
  if (m) v = getComputedStyle(document.documentElement).getPropertyValue(m[1]).trim()
  if (!v || !CSS.supports('color', v)) throw new Error(`L: no colour ${c} (a theme colour, var(--name) or #rrggbb)`)
  probe ??= document.createElement('canvas').getContext('2d')
  probe.fillStyle = '#000'
  probe.fillStyle = v
  const hex = probe.fillStyle            // a solid colour reads back as #rrggbb
  rgb = /^#[0-9a-f]{6}$/i.test(hex) ? [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255)
    : hex.match(/[\d.]+/g).slice(0, 3).map(x => Number(x) / 255)
  colours.set(c, rgb)
  return rgb
}

export class LightStage {
  /** canvas: the page's light canvas, under the 3D canvas and the SVG; stage: the SVG stage, whose cameras it follows. */
  constructor(canvas, stage, { width = 1920, height = 1080 } = {}) {
    this.canvas = canvas
    this.stage = stage
    this.W = width
    this.H = height
    canvas.width = width
    canvas.height = height
    const gl = canvas.getContext('webgl2', { antialias: true, preserveDrawingBuffer: true, premultipliedAlpha: false, alpha: false })
    if (!gl) throw new Error('L: this browser has no WebGL2, which the light layer needs (studio doctor names the renderer)')
    if (!gl.getExtension('EXT_color_buffer_float') && !gl.getExtension('EXT_color_buffer_half_float'))
      throw new Error('L: this browser cannot render to half-float textures, which the light layer needs for its glow')
    this.gl = gl
    this.P = program(gl, VS_POINT, FS_POINT)
    this.Ln = program(gl, VS_LINE, FS_LINE)
    this.B = program(gl, VS_FULL, FS_BLUR)
    this.C = program(gl, VS_FULL, FS_COMP)
    this.scene = target(gl, width, height)
    this.b1 = [target(gl, width >> 2, height >> 2), target(gl, width >> 2, height >> 2)]
    this.b2 = [target(gl, width >> 3, height >> 3), target(gl, width >> 3, height >> 3)]
    const buffer = data => {
      const b = gl.createBuffer()
      gl.bindBuffer(gl.ARRAY_BUFFER, b)
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(data), gl.STATIC_DRAW)
      return b
    }
    this.quad = buffer([-1, -1, 1, -1, -1, 1, 1, 1])
    this.strip = buffer([0, -1, 1, -1, 0, 1, 1, 1])
    this.inst = gl.createBuffer()
    this.vao = gl.createVertexArray()
    this.groups = new Map()       // the SVG camera group light was drawn under -> {points, lines}
    this.style = { ...LOOK }
    this.active = false
  }

  /** A new frame: no light yet, the default look. */
  begin() {
    for (const g of this.groups.values()) { g.points.n = 0; g.lines.n = 0 }
    this.groups.clear()
    this.style = { ...LOOK }
  }

  /** The batch for the camera in force: a nested scene's own camera group, or the frame's. */
  batch() {
    const group = this.stage.nested ?? this.stage.camera
    let b = this.groups.get(group)
    if (!b) this.groups.set(group, b = { points: new Batch(7), lines: new Batch(9) })
    return b
  }

  /**
   * A round light at world (x, y), `r` world units across its radius (it grows with a push-in; under
   * about a pixel it keeps its size and dims instead), in `colour` at opacity `op`. Lights add up.
   */
  point(x, y, r, colour, op = 1) {
    if (!(op > 0.002)) return
    const [cr, cg, cb] = rgbOf(colour), B = this.batch().points, o = B.room(), a = B.a
    a[o] = x; a[o + 1] = y; a[o + 2] = r; a[o + 3] = cr; a[o + 4] = cg; a[o + 5] = cb; a[o + 6] = op
  }

  /** A line of light from world (ax, ay) to (bx, by), `w` screen pixels wide whatever the zoom. */
  line(ax, ay, bx, by, w, colour, op = 1) {
    if (!(op > 0.002)) return
    const [cr, cg, cb] = rgbOf(colour), B = this.batch().lines, o = B.room(), a = B.a
    a[o] = ax; a[o + 1] = ay; a[o + 2] = bx; a[o + 3] = by; a[o + 4] = w; a[o + 5] = cr; a[o + 6] = cg; a[o + 7] = cb; a[o + 8] = op
  }

  /**
   * This frame's look: `bloom` (1; 0 is none), `soft` (0.85: how soft a point's edge is), `minPx` (1.2:
   * the smallest a point is drawn) and `ground` (a colour, or [top, bottom] for a vertical gradient).
   */
  look(o = {}) {
    for (const k of Object.keys(o)) if (!(k in LOOK)) throw new Error(`L.look: no option ${k} (${Object.keys(LOOK).join(', ')})`)
    Object.assign(this.style, o)
  }

  /** How many points and lines this frame drew. */
  count() {
    let points = 0, lines = 0
    for (const g of this.groups.values()) { points += g.points.n; lines += g.lines.n }
    return { points, lines }
  }

  /** The group's matrix from world to frame pixels, and its opacity with every group above it. */
  placement(group) {
    // Relative to the back layer, which no camera moves, so the frame's pixels whatever size the page shows it at.
    const ref = this.stage.layers.back.getCTM(), own = group.getCTM()
    if (!ref || !own) return null
    const m = ref.inverse().multiply(own)
    let op = 1
    for (let n = group; n && n !== this.stage.svg; n = n.parentNode) {
      const v = n.getAttribute?.('opacity')
      if (v != null && v !== '') op *= Number(v)
      if (n.style?.display === 'none') return null
    }
    return { m: [m.a, m.b, 0, m.c, m.d, 0, m.e, m.f, 1], scale: Math.sqrt(Math.abs(m.a * m.d - m.b * m.c)), op }
  }

  bind(stride, layout, corners) {
    const gl = this.gl
    gl.bindVertexArray(this.vao)
    gl.bindBuffer(gl.ARRAY_BUFFER, corners)
    gl.enableVertexAttribArray(0)
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0)
    gl.vertexAttribDivisor(0, 0)
    gl.bindBuffer(gl.ARRAY_BUFFER, this.inst)
    let off = 0
    layout.forEach((size, i) => {
      gl.enableVertexAttribArray(i + 1)
      gl.vertexAttribPointer(i + 1, size, gl.FLOAT, false, stride * 4, off * 4)
      gl.vertexAttribDivisor(i + 1, 1)
      off += size
    })
  }

  full(P) {
    const gl = this.gl
    gl.useProgram(P.p)
    gl.bindVertexArray(this.vao)
    gl.bindBuffer(gl.ARRAY_BUFFER, this.quad)
    gl.enableVertexAttribArray(0)
    gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0)
    gl.vertexAttribDivisor(0, 0)
    for (let i = 1; i < 4; i++) gl.disableVertexAttribArray(i)
    gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4)
  }

  blur(src, pair) {
    const gl = this.gl
    let from = src
    for (let pass = 0; pass < 2; pass++) for (const [k, dir] of [[0, [1, 0]], [1, [0, 1]]]) {
      const to = pair[k]
      gl.bindFramebuffer(gl.FRAMEBUFFER, to.fb)
      gl.viewport(0, 0, to.w, to.h)
      gl.useProgram(this.B.p)
      gl.activeTexture(gl.TEXTURE0)
      gl.bindTexture(gl.TEXTURE_2D, from.tex)
      gl.uniform1i(this.B.u('uT'), 0)
      gl.uniform2f(this.B.u('uDir'), dir[0] / to.w * (pass + 1), dir[1] / to.h * (pass + 1))
      this.full(this.B)
      from = to
    }
    return from
  }

  /** Render this frame's light through the cameras the SVG ended with; with no light, hide the canvas. */
  end() {
    const { gl, W, H, style } = this
    const drawn = [...this.groups.entries()].filter(([, b]) => b.points.n || b.lines.n)
    this.active = drawn.length > 0
    this.canvas.style.display = this.active ? 'block' : 'none'
    if (!this.active) return false
    gl.bindFramebuffer(gl.FRAMEBUFFER, this.scene.fb)
    gl.viewport(0, 0, W, H)
    gl.clearColor(0, 0, 0, 0)
    gl.clear(gl.COLOR_BUFFER_BIT)
    gl.enable(gl.BLEND)
    gl.blendFunc(gl.ONE, gl.ONE)
    for (const [group, b] of drawn) {
      const at = this.placement(group)
      if (!at || at.op <= 0.002) continue
      if (b.lines.n) {
        gl.useProgram(this.Ln.p)
        gl.bindBuffer(gl.ARRAY_BUFFER, this.inst)
        gl.bufferData(gl.ARRAY_BUFFER, b.lines.a.subarray(0, b.lines.n * 9), gl.DYNAMIC_DRAW)
        this.bind(9, [4, 1, 4], this.strip)
        gl.uniformMatrix3fv(this.Ln.u('uM'), false, at.m)
        gl.uniform1f(this.Ln.u('uOp'), at.op)
        gl.uniform2f(this.Ln.u('uRes'), W, H)
        gl.drawArraysInstanced(gl.TRIANGLE_STRIP, 0, 4, b.lines.n)
      }
      if (b.points.n) {
        gl.useProgram(this.P.p)
        gl.bindBuffer(gl.ARRAY_BUFFER, this.inst)
        gl.bufferData(gl.ARRAY_BUFFER, b.points.a.subarray(0, b.points.n * 7), gl.DYNAMIC_DRAW)
        this.bind(7, [2, 1, 4], this.quad)
        gl.uniformMatrix3fv(this.P.u('uM'), false, at.m)
        gl.uniform1f(this.P.u('uScale'), at.scale)
        gl.uniform1f(this.P.u('uPx'), style.minPx)
        gl.uniform1f(this.P.u('uSoft'), style.soft)
        gl.uniform1f(this.P.u('uOp'), at.op)
        gl.uniform2f(this.P.u('uRes'), W, H)
        gl.drawArraysInstanced(gl.TRIANGLE_STRIP, 0, 4, b.points.n)
      }
    }
    gl.disable(gl.BLEND)
    const b1 = this.blur(this.scene, this.b1), b2 = this.blur(b1, this.b2)
    gl.bindFramebuffer(gl.FRAMEBUFFER, null)
    gl.viewport(0, 0, W, H)
    gl.useProgram(this.C.p)
    ;[[this.scene, 'uScene'], [b1, 'uB1'], [b2, 'uB2']].forEach(([t, n], i) => {
      gl.activeTexture(gl.TEXTURE0 + i)
      gl.bindTexture(gl.TEXTURE_2D, t.tex)
      gl.uniform1i(this.C.u(n), i)
    })
    const [top, bottom] = Array.isArray(style.ground) ? style.ground : [style.ground, style.ground]
    gl.uniform3fv(this.C.u('uTop'), rgbOf(top))
    gl.uniform3fv(this.C.u('uBot'), rgbOf(bottom))
    gl.uniform1f(this.C.u('uBloom'), style.bloom)
    this.full(this.C)
    gl.finish()
    return true
  }
}
