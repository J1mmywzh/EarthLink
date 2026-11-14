/* EarthLink navigation: Rhino 8 view controls on a Cesium globe (McNeel's documented defaults).

   Mouse (Mac and Windows; Mod = Cmd on Mac, Ctrl on Windows; Alt = Option on Mac)
     right-drag                 rotate (perspective) / pan (parallel)
     Shift + right-drag         pan; press Shift during a drag to lock it to one direction
     Mod + right-drag           zoom (drag up = in)          wheel: zoom toward the cursor
     Alt + right-drag           dolly: move in / out          Mod + Shift + right-drag: rotate, also in parallel
     Mod + Alt + right-drag     turn the camera in place      Mod + Shift + Alt + right-drag: lens length
     middle-drag                pan (Mac default; Alt/Option + middle: rotate on Mac, dolly on Windows)
   Mac trackpad                 two fingers rotate (pan in parallel), Shift + two fingers pan, pinch zooms
   Windows touchpad             two-finger scroll zooms, like Rhino for Windows; pinch zooms; rotate with right-drag
   Keys                         arrows rotate (pan in parallel), Shift + arrows pan, Page Up / Page Down zoom
   Walk                         two fingers, right-drag or arrows look around

   Every gesture keeps the horizon level, picks its pivot when it starts and keeps one mode until its
   momentum ends. Movement is eased per frame. Pan and zoom scale with distance, orbit is angular, so
   one Sensitivity value feels the same from orbit to a single room.

   The pivot is Rhino's camera target: what is at the centre of the view when you start turning. It stays the
   same from one rotation to the next (a tree passing in front does not move it) until you pan, zoom or fly;
   while your model reaches the middle of the view the pivot is kept within the model's depth; at the horizon
   or in the sky it is your model's depth, or a limited distance (see pivotDistance).
   A gesture does one thing from start to finish: the small pinches a trackpad sends while two fingers scroll or
   rest are dropped; a pinch has to be meant (see WheelLatch).
   Two-Point is the same camera drawn with a level axis and a shifted lens, so every gesture works the same.
   Nothing but this module moves the camera: Cesium's own collision is off. The camera passes through trees
   and buildings; it only comes to rest when it descends onto a surface from above, and follows gently rising
   ground (see Floor). */
(function (root, factory) { const api = factory(); if (typeof module === "object" && module.exports) module.exports = api; else root.EarthLinkNavigation = api; })(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

  // Per-feature rates at Sensitivity 100 %. Degrees per pixel unless noted.
  const RATE = {
    orbit: 0.117, tilt: 0.105,         // two fingers
    orbitMouse: 0.219, tiltMouse: 0.197, // right-drag
    pan: 0.89,                         // x the distance under the fingers (1 = exact follow)
    // zoom: 10 % and then 15 % faster than beta.12 (the author, 2026-11-14); turning and panning are as they like them
    pinch: 0.01383, scroll: 0.00696,   // zoom: log-distance per wheel delta unit (trackpad)
    wheel: 0.00329, dragZoom: 0.00557, // mouse wheel, Ctrl + right-drag
    hold: Math.LN2 / 0.60,             // +/- held: distance halves every 0.60 s
    look: 0.072, lookMouse: 0.135,     // walking
  };
  /* How far the view may tilt from straight down at a height (m): freely near the ground, less and less higher up,
     not at all from space (as in Apple Maps and Google Earth: the globe stays on the screen). */
  const GLOBE = { low: 30e3, high: 2500e3, spin: 600e3 };   // spin: above it two fingers (or a drag) turn the globe instead of orbiting
  function maxTilt(h) {
    if (!(h > GLOBE.low)) return 180;
    if (h >= GLOBE.high) return 0;
    return 90 * (1 - Math.log(h / GLOBE.low) / Math.log(GLOBE.high / GLOBE.low));
  }
  const STEP = { degrees: 6, pan: 1 / 8 };   // arrow keys: Rhino's 60 steps per turn; pan an eighth of the view
  const GESTURE_GAP = 220;   // ms without wheel events that ends a gesture (momentum included)
  const TAKEOVER = 120;      // ms a pinch must be quiet before scrolling takes over
  const PINCH_START = 3, PINCH_OVER = 10, PINCH_WINDOW = 250;   // wheel units of pinch (1 = 1 % of magnification) that begin a zoom
  const TWO_POINT_MAX = 65 * Math.PI / 180;   // steeper than this a shifted lens stretches the picture badly
  const EASE = 0.045;        // s: time constant of the per-frame easing
  const wheelPx = e => (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? 400 : 1);

  /* Decide what a wheel event does. One decision per gesture: Shift released or pressed during the momentum
     tail cannot switch pan to orbit. macOS sends small pinch events whenever two scrolling or resting fingers drift
     apart or together, and a burst of them when the fingers lift, so a pinch has to be meant: it begins only once
     PINCH_START units of it arrive within PINCH_WINDOW ms (PINCH_OVER, and more than the scrolling itself, within
     GESTURE_GAP of a scroll), and until then its events are dropped. During a
     pinch, scroll events are dropped until the pinch has been quiet for TAKEOVER ms. The device is corrected if
     later events prove the first guess wrong, and remembered. */
  class WheelLatch {
    constructor() { this.last = -Infinity; this.mode = null; this.device = null; this.prior = null; this.kind = null; this.n = 0; this.sure = 0; this.pend = []; this.flow = []; }
    read(e, projection, now, mac = true) {
      const kind = e.ctrlKey ? "pinch" : "scroll";
      if (this.kind && now - this.last > GESTURE_GAP) { this.kind = null; this.pend = []; }   // the fingers lifted or rest: the gesture is over
      let fresh = !this.kind;
      if (kind === "pinch" && this.kind !== "pinch") {
        // Counted with its sign: drift goes back and forth and cancels, a pinch keeps one direction. During a scroll
        // only the last PINCH_WINDOW ms count; with the fingers otherwise still, the whole run does, so a slow pinch
        // starts too (a run ends after GESTURE_GAP without pinch events).
        const from = this.kind === "scroll" ? PINCH_WINDOW : this.pend.length && now - this.pend[this.pend.length - 1][0] > GESTURE_GAP ? 0 : Infinity;
        this.pend = this.pend.filter(q => now - q[0] <= from); this.pend.push([now, e.deltaY * wheelPx(e)]);
        // while the fingers are scrolling, the pinch must also outweigh the scroll (1 % of pinch is about 6 px of travel)
        this.flow = this.flow.filter(q => now - q[0] <= PINCH_WINDOW);
        const need = this.kind === "scroll" ? Math.max(PINCH_OVER, this.flow.reduce((a, q) => a + q[1], 0) / 3) : PINCH_START;   // lifting fingers also sends a burst of pinch
        if (Math.abs(this.pend.reduce((a, q) => a + q[1], 0)) < need) return { mode: "none", skip: true, start: false };
        fresh = true;
      } else if (kind === "scroll" && this.kind === "pinch") {
        if (now - this.last <= TAKEOVER) return { mode: "none", skip: true, start: false };
        fresh = true;
      }
      if (fresh) { this.kind = kind; this.n = 0; this.sure = 0; this.pend = []; this.flow = []; }
      this.last = now; this.n++;
      if (kind === "scroll") this.flow.push([now, (Math.abs(e.deltaX) + Math.abs(e.deltaY)) * wheelPx(e)]);
      if (kind === "pinch") { this.mode = "zoom"; return { mode: "zoom", pinch: true, start: fresh, gain: 1 }; }
      const ev = wheelEvidence(e), choose = device => {
        this.device = device;
        this.mode = device === "mouse" || !mac ? "zoom"      // Rhino for Windows: two-finger scrolling zooms
          : projection === "parallel" ? "pan"                // Rhino: Shift changes nothing in a parallel view
          : (e.shiftKey ? "pan" : "orbit");
      };
      let start = fresh;
      if (fresh || !this.mode) choose(ev.device || this.prior || "trackpad");
      else if (ev.sure && ev.device !== this.device) {     // the first event misled: a trackpad shows at once, a wheel after two notches
        this.sure = ev.device === "mouse" ? this.sure + 1 : 2;
        if (this.sure >= 2 && (ev.device === "trackpad" || this.n <= 4)) { choose(ev.device); start = true; }
      } else if (ev.sure) this.sure = 0;
      if (ev.sure && ev.device === this.device) this.prior = ev.device;
      return { mode: this.mode, device: this.device, start, gain: 1 };   // gain: the system's glide counts in full (it is what brings a turn to rest)
    }
  }
  /* What a wheel event says about its device: {device: "mouse" | "trackpad" | null, sure}. Chrome and Safari
     report a trackpad's legacy wheelDeltaY as -3 x deltaY (other than a multiple of 120 unless the step is exactly
     40, 80, ...) and a notched wheel's as a multiple of 120 whatever deltaY is (on a Mac a slow notch is only about
     4 px). Sideways motion is a trackpad. Where the legacy field is missing, a large vertical first step suggests
     a wheel. A Magic Mouse cannot be told from a trackpad by a web page. */
  function wheelEvidence(e) {
    if (e.deltaMode === 1 || e.deltaMode === 2) return { device: "mouse", sure: true };
    if (e.deltaX !== 0) return e.shiftKey && !e.deltaY ? { device: null, sure: false } : { device: "trackpad", sure: true };   // Shift + wheel scrolls sideways
    if (!e.deltaY) return { device: null, sure: false };
    const wd = e.wheelDeltaY;
    if (wd === undefined || wd === 0) return Math.abs(e.deltaY) >= 50 ? { device: "mouse", sure: false } : { device: null, sure: false };
    if (Math.abs(wd) % 120 !== 0) return { device: "trackpad", sure: true };
    if (Math.abs(wd + 3 * e.deltaY) <= 0.5) return { device: null, sure: false };      // a trackpad step of exactly 40, or a wheel that moved as far
    return { device: "mouse", sure: true };
  }
  const isMouseWheel = e => wheelEvidence(e).device === "mouse";
  /* Pending motion released gradually, frame by frame. Zoom is released more slowly: a wheel has no glide of its own.

     Coming to rest. A two-finger turn, pan or pinch often ends while the view is still moving: the fingers lift, or
     the next stroke touches down and cuts the system's glide short (measured on a MacBook: strokes follow each
     other every 0.3 s and the stream stops at 20 to 30 px per event). Released as it is, the view would stop dead
     within EASE. Motion added as `soft` therefore never slows faster than RELEASE allows: the view runs on and comes
     to rest. What it runs ahead is a loan: while the fingers keep moving the same way the next events pay it back
     (the view stays exactly under the fingers, and uneven events are evened out); when nothing follows for FORGIVE
     s, or the fingers turn back, it is forgiven and is the little the view glided. Slow motion (below the first
     speed of SOFT, per second) stops as precisely as before; from the second speed on the release is in full. */
  const EASE_OF = { zoom: 0.085 }, RELEASE = 0.12, FORGIVE = 0.04;
  const SOFT = { heading: [14, 56], tilt: [14, 56], lh: [14, 56], lt: [14, 56], px: [150, 600], py: [150, 600], zoom: [0.3, 1.2] };
  class Ease {
    constructor() { this.v = { heading: 0, tilt: 0, px: 0, py: 0, zoom: 0, lh: 0, lt: 0 }; this.u = {}; this.c = {}; this.loan = {}; this.idle = {}; this.soft = {}; this.clear(); }
    add(k, x, soft = false) {
      if (!Number.isFinite(x) || !x) return;
      const loan = this.loan[k];
      if (loan) {
        if (Math.sign(x) === Math.sign(loan)) { const pay = Math.sign(x) * Math.min(Math.abs(x), Math.abs(loan)); x -= pay; this.loan[k] -= pay; }
        else this.loan[k] = 0;
      }
      this.v[k] += x; this.idle[k] = 0; this.soft[k] = !!soft;
    }
    take(dt) {
      dt = Math.max(0, dt);
      const out = {};
      let any = false;
      for (const k in this.v) {
        const f = 1 - Math.exp(-dt / (EASE_OF[k] || EASE));
        let q = this.v[k] * f; this.v[k] -= q;
        if (Math.abs(this.v[k]) < 1e-4) { q += this.v[k]; this.v[k] = 0; }
        this.idle[k] += dt; if (this.idle[k] > FORGIVE) this.loan[k] = 0;
        let o = q;
        const lim = SOFT[k];
        if (lim && this.soft[k] && dt > 0 && (this.u[k] || this.c[k])) {
          const from = this.c[k] || this.u[k];                                             // per second: what is fading, or the speed of the last frame
          const env = from * dt * Math.exp(-dt / RELEASE), s = Math.sign(env);             // the slowest it may get this frame
          const w = clamp((Math.abs(from) - lim[0]) / (lim[1] - lim[0]), 0, 1);
          if (w && Math.sign(q) === -s) { this.c[k] = env / dt; o = q + env * w; }          // turning back: the old motion fades under the new one
          else {
            this.c[k] = 0;
            if (w && s * (env - q) > 0) { const extra = (env - q) * w; o = q + extra; this.loan[k] += extra; }
          }
        } else this.c[k] = 0;
        this.u[k] = dt > 0 ? o / dt : 0;
        if (Math.abs(o) < 1e-7) { o = 0; this.u[k] = 0; }
        out[k] = o;
        if (o) any = true;
      }
      return any ? out : null;
    }
    drop(k) { this.v[k] = 0; this.u[k] = 0; this.c[k] = 0; this.loan[k] = 0; }
    clear() { for (const k in this.v) { this.drop(k); this.idle[k] = 1; this.soft[k] = false; } }
    get busy() { return Object.values(this.v).some(Boolean) || Object.values(this.u).some(Boolean); }
  }

  /* How far along the centre of the view the pivot is. pick: distance to the surface there (null: none).
     focus: depth of the visible model when it is in view (null: none). limit: the farthest surface that still
     counts as what you are looking at (a shallow view reaches the horizon). The pivot is what you see at the
     centre of the view; it is never a remembered distance and never a point behind the surface you are looking
     at: turning about anything else makes the picture rush in and out. */
  function pivotDistance(pick, focus, limit = Infinity) {
    if (pick != null && pick <= limit) return pick;
    if (focus != null) return focus;
    return pick != null ? limit : null;
  }

  /* The ground rule, in heights above the ellipsoid. `top` is the map's upper surface at the camera's position and
     `below` the first surface under the camera (null: none), needed only when the camera is under `top`.
     - A gesture never starts by lifting the camera, and a surface that appears beside it (a wall, a tree) is entered.
     - The camera rests on a surface it descends onto, and rides up ground that rises no faster than it moves.
     - Under a tree it rests on the ground beneath. Inside something solid (a building, a hillside) it can move
       sideways and up, not further down: there is no way deep under the map.
     - `base` (set by the controller): the camera came down into something that stands out of its surroundings
       (a tree, a pole); it may go down to the height around it. */
  class Floor {
    constructor(clear = 0.3) { this.clear = clear; this.reset(); }
    reset() { this.known = false; this.inside = false; this.top = null; this.h = null; this.base = null; }
    step(h, top, moved = 0, below = null) {
      const was = this.h;
      const out = v => (this.h = v);
      if (top == null) { this.known = false; return out(h); }
      const before = this.top, first = !this.known;
      this.known = true; this.top = top;
      if (h >= top + this.clear) { this.inside = false; this.base = null; return out(h); }
      if (first) this.inside = true;
      else if (!this.inside) {
        if (top - before > Math.max(0.5, moved)) this.inside = true;
        else return out(top + this.clear);
      }
      if (below != null) return out(Math.max(h, below + this.clear));
      if (this.base != null) return out(Math.max(h, this.base + this.clear));   // inside a tree or the like: down to the ground around it
      return out(was == null ? h : Math.max(h, was));
    }
  }

  // Sunlight when the sun is off: from behind the viewer, a little above.
  function neutralDirection(direction, up) {
    const vertical = direction.reduce((s, n, i) => s + n * up[i], 0), h = direction.map((n, i) => n - up[i] * vertical), length = Math.hypot(...h) || 1;
    const d = h.map((n, i) => .5 * n / length - up[i]), norm = Math.hypot(...d); return d.map(n => n / norm);
  }

  /* The light at a sun height `e` (degrees above the horizon), for a scene whose map is a daytime photograph.
     tint: what the map's colours are multiplied by (white by day, warm near sunset, dark blue at night);
     night 0..1 (full 8 degrees under the horizon); shadow 0..1: how strong cast shadows are (a sun on or under
     the horizon casts none); sky: the colour overhead. */
  function daylight(e) {
    const ss = (a, b, x) => { const t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); };
    const mix = (a, b, t) => a.map((v, i) => v + (b[i] - v) * t);
    const night = 1 - ss(-8, 0, e), warm = (1 - ss(1, 12, e)) * (1 - night);
    return { night, warm, shadow: ss(0.5, 6, e),
      tint: mix(mix([1, 1, 1], [1, 0.82, 0.66], warm), [0.1, 0.13, 0.23], night),
      sky: mix(mix([0.22, 0.45, 0.82], [0.4, 0.44, 0.62], warm), [0.008, 0.012, 0.035], night) };
  }

  /* The controller: binds input on the canvas and moves viewer.camera. `hooks`:
     projection() "perspective"|"two_point"|"parallel", pick(ray) nearest drawn surface or null,
     ground(ray) nearest map surface (your model excluded) or null,
     allowed() navigation permitted now,
     sensitivity() multiplier, moved() user took the camera (cancel flights / Follow Rhino),
     focus() bounding sphere {center, radius} of the visible models or null,
     walking() true while walking, look(dHeading, dPitch) turn the walker,
     lens(k) multiply the perspective field of view by k (optional), mac() Mac controls (default: detected). */
  function create(Cesium, viewer, hooks) {
    const C3 = Cesium.Cartesian3, scene = viewer.scene, cam = viewer.camera, canvas = scene.canvas;
    const E = Cesium.Ellipsoid.WGS84, latch = new WheelLatch(), ease = new Ease();
    const v3 = () => new C3();
    let pivot = null, anchor = null, pointer = null, hold = 0, holdStart = 0, last = 0, raf = 0, anim = null;
    let grounded_ = false;                               // this gesture's tilt has reached the ground
    let held = null, groundAt = null, rec = null;        // the pivot kept between rotations; last ground check; input recording
    const floor = new Floor();
    const ssc = scene.screenSpaceCameraController;
    // One input path only. Cesium switches its own controls back on at the end of every camera flight (CameraFlightPath
    // sets enableInputs = true on complete and on cancel): after a search, Fit or a saved view, every two-finger scroll
    // then also zoomed the camera with Cesium's own wheel zoom, so a tilt pulled the view in and out (found in a
    // recording from the author's trackpad, 2026-11-14). The switch is pinned off for good.
    Object.defineProperty(ssc, "enableInputs", { configurable: true, get: () => false, set: () => {} });
    ssc.enableCollisionDetection = false;    // and one thing that moves the camera: Cesium's collision lifts it by itself
    const mac = () => (hooks.mac ? !!hooks.mac() : isMac());

    const normal = p => E.geodeticSurfaceNormal(p, v3()) || (C3.magnitude(p) > 1 ? C3.normalize(p, v3()) : C3.clone(C3.UNIT_Z));
    const sens = () => clamp(+hooks.sensitivity() || 1, 0.2, 3);
    const ortho = () => cam.frustum instanceof Cesium.OrthographicFrustum;
    const twoPoint = () => hooks.projection() === "two_point" && !ortho();
    // The camera as the gestures see it. Two-Point draws it with a level axis and a shifted lens: the shift is the pitch.
    function pose() {
      const pos = cam.positionWC.clone(), k = twoPoint() ? cam.frustum._elShift || 0 : 0;
      if (!k) return { pos, dir: cam.directionWC.clone(), up: cam.upWC.clone() };
      const dir = C3.normalize(C3.add(cam.directionWC, C3.multiplyByScalar(cam.upWC, k, v3()), v3()), v3());
      return { pos, dir, up: level(dir, cam.upWC) };
    }
    const size = () => [Math.max(1, canvas.clientWidth), Math.max(1, canvas.clientHeight)];

    function pick(x, y) {                                // the drawn surface under a screen point
      const s = new Cesium.Cartesian2(x, y), ray = cam.getPickRay(s);
      const ok = p => p && Number.isFinite(p.x) && C3.dot(C3.subtract(p, cam.positionWC, v3()), ray.direction) > 0 &&
        Math.abs((Cesium.Cartographic.fromCartesian(p)?.height ?? 1e9)) < 2e4;
      const p = hooks.pick && hooks.pick(ray);              // CPU ray test on the model and the map
      if (ok(p)) return p;
      const hit = Cesium.IntersectionTests.rayEllipsoid(ray, E);
      return hit ? Cesium.Ray.getPoint(ray, hit.start, v3()) : null;
    }
    function centre() {                                  // what is at the centre of the view
      const [w, h] = size(), ray = cam.getPickRay(new Cesium.Cartesian2(w / 2, h / 2));
      const p = pick(w / 2, h / 2), dp = p ? C3.dot(C3.subtract(p, ray.origin, v3()), ray.direction) : null;
      const f = hooks.focus && hooks.focus();
      let depth = null, within = null;                     // the visible model's depth, when it is in view
      if (f) {
        const to = C3.subtract(f.center, ray.origin, v3()), d = C3.dot(to, ray.direction), far = C3.magnitude(to);
        const side = Math.sqrt(Math.max(0, far * far - d * d));
        if (ortho()) { if (side <= Math.max(f.radius, cam.frustum.width)) depth = d; }
        // in view from outside: within the lens plus half the model's own angular size. Inside or beside the
        // model its centre says nothing about what you are looking at.
        else if (d > 0 && far > 1.5 * f.radius) {
          const off = Math.atan2(side, d), wide = Math.asin(f.radius / far), fov = cam.frustum.fovy || 0.8;
          if (off <= fov / 2 + 0.5 * wide) depth = d;
          // The model reaches the middle of the view: it is what you are turning around. The centre of the view
          // often passes it (through a gap, over a roof) and lands on ground far behind; turning about that makes
          // the model rush towards you and away. The pivot is then no farther than the model's far side.
          if (off <= fov / 4 + wide) within = [Math.max(0.4, d - f.radius), d + f.radius];
        }
      }
      let d;
      if (ortho()) {                                       // distances start far behind the scene: compare depths
        const span = f ? 3 * Math.max(f.radius, cam.frustum.width) : Infinity;
        d = dp != null && (depth == null || Math.abs(dp - depth) <= span) ? dp : depth ?? dp;
      } else {
        // The ground under the camera where it is known: a far hit on map detail that has not loaded yet lies deep
        // below the real ground and must not stretch the limit.
        const under = floor.known && floor.top != null ? floor.top : (p ? Cesium.Cartographic.fromCartesian(p)?.height ?? 0 : 0);
        d = pivotDistance(dp, depth, Math.max(300, 8 * Math.max(0, height() - under)));
        // Only ever nearer: the surface you see in front of the model (a hill, a tree, the map over a model that
        // sits too low) stays the pivot. A point behind what is seen is the one thing a pivot must not be.
        if (within) d = d == null ? depth : Math.min(d, within[1]);
      }
      if (d == null) d = Math.max(50, height() * 2);
      const at = Cesium.Ray.getPoint(ray, d, v3());
      // From high up, looking past the Earth: nothing sensible to turn around but the Earth itself. The point of
      // the Earth under the camera, so that a turn or a zoom brings the planet back, never a point in space or
      // deep inside the Earth (both lost the planet off the screen and then stuck the camera).
      if (height() > GLOBE.low && (C3.magnitude(at) < 0.9 * E.minimumRadius || C3.distance(at, cam.positionWC) > 1.2 * C3.magnitude(cam.positionWC)))
        return E.scaleToGeodeticSurface(cam.positionWC, v3()) || at;
      return at;
    }
    // The pivot of a rotation: the one the last rotation used while nothing else has moved the camera since.
    function turnPivot() {
      if (held && C3.distance(held.at, cam.positionWC) < 0.01 && held.proj === hooks.projection()) return held.pivot;
      return centre();
    }
    const height = () => { const c = Cesium.Cartographic.fromCartesian(cam.positionWC); return c ? c.height : 1e7; };

    // Re-derive "up" so the horizon is level (no roll); direction is untouched.
    function level(dir, up) {
      const n = normal(cam.positionWC);
      let right = C3.cross(dir, n, v3());
      if (C3.magnitude(right) < 0.05) {                    // within 3 deg of straight down: keep the current right (no flip)
        right = C3.cross(dir, up, v3());
        C3.subtract(right, C3.multiplyByScalar(n, C3.dot(right, n), v3()), right);
      }
      C3.normalize(right, right);
      return C3.normalize(C3.cross(right, dir, v3()), v3());
    }
    // Parallel: the image does not depend on how far back the camera is, but anything nearer than the camera is
    // cut away (black half, tile seams). Keep it far back along its axis, behind the point at the centre.
    const BACK = 20000;
    function setPose(pos, dir, up, onGround) {
      dir = C3.normalize(dir, v3());
      if (ortho()) { if (!pivot) pivot = centre(); pos = C3.subtract(pivot, C3.multiplyByScalar(dir, BACK, v3()), v3()); }
      else { const g = grounded(pos); pos = g.pos; if (g.rests && onGround) onGround(); }
      if (twoPoint()) {                                     // the axis stays level; the pitch becomes the lens shift
        const n = normal(pos), pitch = clamp(Math.asin(clamp(C3.dot(dir, n), -1, 1)), -TWO_POINT_MAX, TWO_POINT_MAX);
        let flat = C3.subtract(dir, C3.multiplyByScalar(n, C3.dot(dir, n), v3()), v3());
        if (C3.magnitude(flat) < 1e-6) flat = C3.subtract(cam.directionWC, C3.multiplyByScalar(n, C3.dot(cam.directionWC, n), v3()), v3());
        cam.frustum._elShift = Math.tan(pitch);
        cam.setView({ destination: pos, orientation: { direction: C3.normalize(flat, flat), up: n } });
      } else cam.setView({ destination: pos, orientation: { direction: dir, up: level(dir, up) } });
    }
    // The ground rule (Floor): one ray down onto the map's upper surface where the camera is going.
    function grounded(pos) {
      const c = hooks.ground && !hooks.walking() ? Cesium.Cartographic.fromCartesian(pos) : null;
      if (!c || c.height > 3000) { floor.reset(); groundAt = null; return { pos, rests: false }; }
      const n = normal(pos), hit = hooks.ground(new Cesium.Ray(C3.add(pos, C3.multiplyByScalar(n, 1000, v3()), v3()), C3.negate(n, v3())));
      const top = hit ? Cesium.Cartographic.fromCartesian(hit)?.height ?? null : null;
      let moved = 0;
      if (groundAt) { const d = C3.subtract(pos, groundAt, v3()); moved = C3.magnitude(C3.subtract(d, C3.multiplyByScalar(n, C3.dot(d, n), v3()), d)); }
      groundAt = C3.clone(pos);
      let below = null;                                    // only matters under the upper surface
      if (top != null && c.height < top + floor.clear) {
        const u = hooks.ground(new Cesium.Ray(pos, C3.negate(n, v3()))); below = u ? Cesium.Cartographic.fromCartesian(u)?.height ?? null : null;
        // Coming down onto something that stands out of its surroundings (a tree, a pole, a chimney): the camera
        // passes through it, as it does when it meets one from the side. Only ground and broad roofs carry it.
        if (floor.known && !floor.inside && c.height >= top - 1) { const around = bump(pos, n, top); if (around != null) { floor.inside = true; floor.base = around; } }
      }
      const h = floor.step(c.height, top, moved, below);
      return h === c.height ? { pos, rests: false } : { pos: C3.add(pos, C3.multiplyByScalar(n, h - c.height, v3()), v3()), rests: true };
    }
    // Does the map's surface at `pos` stand at least BUMP m above most of what is around it (BUMP_R m away)?
    // Returns the height around it, or null.
    const BUMP = 2.5, BUMP_R = 8;
    function bump(pos, n, top) {
      let e = C3.cross(C3.UNIT_Z, n, v3()); if (C3.magnitude(e) < 1e-6) e = C3.cross(C3.UNIT_X, n, v3()); C3.normalize(e, e);
      const f = C3.cross(n, e, v3()), hs = [];
      for (let k = 0; k < 6; k++) {
        const a = k * Math.PI / 3, o = C3.add(C3.multiplyByScalar(e, BUMP_R * Math.cos(a), v3()), C3.multiplyByScalar(f, BUMP_R * Math.sin(a), v3()), v3());
        const hit = hooks.ground(new Cesium.Ray(C3.add(C3.add(pos, o, v3()), C3.multiplyByScalar(n, 1000, v3()), v3()), C3.negate(n, v3())));
        const h = hit ? Cesium.Cartographic.fromCartesian(hit)?.height : null;
        if (h != null) hs.push(h);
      }
      if (hs.length < 4) return false;
      hs.sort((x, y) => x - y);
      const around = hs[Math.floor(hs.length / 2)];           // the upper middle: more than half lie lower
      return top - around >= BUMP ? around : null;
    }
    const rotate = (q, v) => Cesium.Matrix3.multiplyByVector(Cesium.Matrix3.fromQuaternion(q), v, v3());

    // ---- motions (all in world space, about a pivot latched when the gesture began)
    function orbit(dh, dt) {
      if (!pivot) pivot = turnPivot();
      let { pos, dir, up } = pose();
      const n = normal(pivot), keep = () => { held = { pivot, at: cam.positionWC.clone(), proj: hooks.projection() }; };
      if (dh) {
        const q = Cesium.Quaternion.fromAxisAngle(n, -Cesium.Math.toRadians(dh));
        pos = C3.add(pivot, rotate(q, C3.subtract(pos, pivot, v3())), v3()); dir = rotate(q, dir); up = rotate(q, up);
      }
      if (dt) {
        const off = C3.subtract(pos, pivot, v3()), d = C3.magnitude(off);
        const elev = Math.asin(clamp(C3.dot(off, n) / (d || 1), -1, 1));
        // from straight down to straight up: below the pivot is fine (looking up at a facade), as in Rhino
        const lim = twoPoint() ? TWO_POINT_MAX : Cesium.Math.toRadians(89.9);
        // Without a map under the camera (not loaded yet, or none) nothing would stop it going under the ground:
        // it then comes down no lower than what it turns around.
        const low = floor.known ? -lim : 0;
        // From high up the view tilts less and less, and not at all from space: the planet stays on the screen.
        const top = Cesium.Math.toRadians(90 - maxTilt(height()));
        const next = clamp(elev - Cesium.Math.toRadians(dt), Math.min(elev, Math.max(low, top)), Math.max(elev, lim));
        if (next > elev) grounded_ = false;                // tilting up again
        if (Math.abs(next - elev) > 1e-9 && !(next < elev && grounded_)) {
          const right = C3.normalize(C3.cross(dir, up, v3()), v3());
          const q = Cesium.Quaternion.fromAxisAngle(right, elev - next);
          const flat = [pos, dir, up];                     // the pose without the tilt
          pos = C3.add(pivot, rotate(q, off), v3()); dir = rotate(q, dir); up = rotate(q, up);
          if (next < elev) {                               // tilting down: stop at the ground, do not slide along it
            let rests = false; setPose(pos, dir, up, () => { rests = true; });
            // The ground stopped the tilt: it stays stopped for the rest of this gesture. Tilting on wherever the
            // ground dips makes the camera follow every bump while it turns, and the picture jumps in and out.
            if (rests) { grounded_ = true; setPose(...flat); }
            return keep();
          }
        }
      }
      setPose(pos, dir, up); keep();
    }
    // From space a pan turns the globe about its own axis, as Apple Maps and Google Earth do: sideways along the
    // parallels, up and down along the meridians, north stays where it is and the poles are not crossed. (Moving
    // the camera along great circles instead, as near the ground, slid the globe diagonally and turned it.)
    function globePan(fx, fy) {
      const [, h] = size(), c = Cesium.Cartographic.fromCartesian(cam.positionWC); if (!c) return;
      const R = E.maximumRadius, dist = Math.max(1, c.height), m = 2 * dist * Math.tan((cam.frustum.fovy || 0.8) / 2) / h * RATE.pan * sens();
      const H = cam.heading, de = -fx * m * Math.cos(H) + fy * m * Math.sin(H), dn = fx * m * Math.sin(H) + fy * m * Math.cos(H);
      const lat = clamp(c.latitude + dn / R, -Cesium.Math.toRadians(85), Cesium.Math.toRadians(85));
      const lon = Cesium.Math.negativePiToPi(c.longitude + de / R);
      pivot = null; held = null;
      cam.setView({ destination: Cesium.Cartesian3.fromRadians(lon, lat, c.height), orientation: { heading: H, pitch: cam.pitch, roll: 0 } });
    }
    function pan(fx, fy) {                                 // finger motion in CSS px; the scene follows it
      if (!ortho() && !twoPoint() && height() > GLOBE.spin) return globePan(fx, fy);
      const [w, h] = size(), k = RATE.pan * sens();
      if (ortho()) {
        const m = cam.frustum.width / w * k, d = C3.add(C3.multiplyByScalar(cam.rightWC, -fx * m, v3()), C3.multiplyByScalar(cam.upWC, fy * m, v3()), v3());
        if (!pivot) pivot = centre();
        pivot = C3.add(pivot, d, v3());
        setPose(C3.add(cam.positionWC, d, v3()), cam.directionWC, cam.upWC); return;
      }
      if (!pivot) pivot = centre();
      const n = normal(pivot), dist = C3.distance(cam.positionWC, pivot);
      const m = 2 * dist * Math.tan((cam.frustum.fovy || 0.8) / 2) / h * k;
      const right = C3.subtract(cam.rightWC, C3.multiplyByScalar(n, C3.dot(cam.rightWC, n), v3()), v3()); C3.normalize(right, right);
      const fwd = C3.normalize(C3.cross(n, right, v3()), v3());
      const P = pose(), down = clamp(-C3.dot(P.dir, n), 0.25, 1);          // farther ground moves faster per pixel
      const D = C3.add(C3.multiplyByScalar(right, -fx * m, v3()), C3.multiplyByScalar(fwd, fy * m / down, v3()), v3());
      // move over the curved Earth: rotate camera and pivot about the Earth's centre
      const axis = C3.cross(pivot, D, v3()), ang = C3.magnitude(D) / C3.magnitude(pivot);
      if (!(ang > 0) || C3.magnitude(axis) === 0) return;
      const q = Cesium.Quaternion.fromAxisAngle(C3.normalize(axis, axis), ang);   // carries the camera along D
      pivot = rotate(q, pivot);
      setPose(rotate(q, P.pos), rotate(q, P.dir), rotate(q, P.up));
    }
    function lookAround(dh, dt) {                          // turn the camera where it stands (Rhino: RotateCamera)
      const P = pose(), n = normal(P.pos);
      let dir = rotate(Cesium.Quaternion.fromAxisAngle(n, -Cesium.Math.toRadians(dh)), P.dir);
      const lim = twoPoint() ? TWO_POINT_MAX : 1.55;
      const pitch = Math.asin(clamp(C3.dot(dir, n), -1, 1)), next = clamp(pitch + Cesium.Math.toRadians(dt), Math.min(pitch, -lim), Math.max(pitch, lim));
      const right = C3.normalize(C3.cross(dir, n, v3()), v3());
      dir = rotate(Cesium.Quaternion.fromAxisAngle(right, next - pitch), dir);
      pivot = null; held = null;                           // the view turned where it stands: the old turning point is no longer ahead
      setPose(P.pos, dir, P.up);
    }
    function zoom(logFactor) {                             // > 0 zooms out
      const z = Math.exp(logFactor);
      if (ortho()) {
        const f = cam.frustum, w0 = f.width, w1 = clamp(w0 * z, 0.5, 4e7), [w, h] = size();
        if (anchor && anchor.screen) {                     // keep the point under the cursor fixed
          const m = w0 / w, ox = (anchor.screen[0] - w / 2) * m, oy = -(anchor.screen[1] - h / 2) * m, s = 1 - w1 / w0;
          const d = C3.add(C3.multiplyByScalar(cam.rightWC, ox * s, v3()), C3.multiplyByScalar(cam.upWC, oy * s, v3()), v3());
          if (!pivot) pivot = centre();
          pivot = C3.add(pivot, d, v3());
          setPose(C3.add(cam.positionWC, d, v3()), cam.directionWC, cam.upWC);
        }
        f.width = w1; return;
      }
      let A = anchor?.point || pivot || (pivot = centre());
      if (height() > GLOBE.low && C3.magnitude(A) < 0.9 * E.minimumRadius) A = pivot = E.scaleToGeodeticSurface(cam.positionWC, v3()) || A;
      const off = C3.subtract(cam.positionWC, A, v3()), d = C3.magnitude(off);
      const nd = clamp(d * z, 0.4, 4e7);
      let pos = C3.add(A, C3.multiplyByScalar(off, nd / (d || 1), v3()), v3());
      if (Cesium.Cartographic.fromCartesian(pos)?.height > 4e7) return;
      pos = grounded(pos).pos;
      cam.setView({ destination: pos, orientation: { direction: cam.directionWC, up: cam.upWC } });   // no re-levelling: the image never turns
      if (logFactor > 0) straighten();
    }
    // Higher up the view may tilt less (maxTilt): turned down towards the Earth where it stands, the planet in view.
    function straighten() {
      if (ortho() || twoPoint() || hooks.walking()) return;
      const h = height(); if (h <= GLOBE.low) return;
      const n = normal(cam.positionWC), dir = cam.directionWC, pitch = Math.asin(clamp(C3.dot(dir, n), -1, 1));
      const most = -Cesium.Math.toRadians(90 - maxTilt(h));
      if (pitch <= most + 1e-6) return;
      let right = C3.cross(dir, n, v3()); if (C3.magnitude(right) < 1e-6) return; C3.normalize(right, right);
      const q = Cesium.Quaternion.fromAxisAngle(right, most - pitch);
      const nd = rotate(q, dir), nu = rotate(q, cam.upWC);
      pivot = null; held = null;
      cam.setView({ destination: cam.positionWC.clone(), orientation: { direction: nd, up: level(nd, nu) } });
    }

    // ---- frame loop: ease pending motion, continuous zoom, short animations
    function frame(t) {
      raf = 0;
      const real = last ? (t - last) / 1000 : 1 / 60, dt = Math.min(0.05, real); last = t;
      if (!hooks.allowed() && !hooks.walking()) { ease.clear(); hold = 0; anim = null; }
      const m = ease.take(dt);
      if (m) {
        if (hooks.walking()) hooks.look(m.heading, -m.tilt);
        else {
          if (m.heading || m.tilt) orbit(m.heading, m.tilt);
          if (m.px || m.py) pan(m.px, m.py);
          if (m.zoom) zoom(m.zoom);
          if (m.lh || m.lt) lookAround(m.lh, m.lt);
        }
      }
      if (hold) {
        const ramp = clamp((t - holdStart) / 180, 0, 1);
        zoom(hold * RATE.hold * sens() * ramp * Math.min(0.25, real));   // follows real time while held
      }
      if (anim) { const done = anim(dt); if (done) anim = null; }
      if (m || hold || anim || ease.busy) { scene.requestRender(); raf = requestAnimationFrame(frame); } else last = 0;
    }
    const kick = () => { if (!raf) raf = requestAnimationFrame(frame); };
    function begin() {
      hooks.moved(); cam.cancelFlight();
      floor.reset(); groundAt = null;                      // a new gesture never starts by lifting the camera
      grounded_ = false;
      const c0 = Cesium.Cartographic.fromCartesian(cam.positionWC); if (c0) floor.h = c0.height;
    }

    // ---- input
    canvas.addEventListener("wheel", e => {
      e.preventDefault();
      if (!hooks.allowed() && !hooks.walking()) return;
      // scrollZooms: the person's choice that scrolling zooms (a smooth-scrolling mouse or a Magic Mouse looks like a trackpad to a web page)
      const g = latch.read(e, hooks.projection(), e.timeStamp || performance.now(), mac() && !(hooks.scrollZooms && hooks.scrollZooms())), u = wheelPx(e), s = sens();   // event time: page stalls cannot split a gesture
      if (rec) rec.push(["wheel", Math.round(e.timeStamp), e.deltaX, e.deltaY, e.deltaMode, e.wheelDeltaY ?? null, +e.ctrlKey, +e.shiftKey, g.mode, g.device || "", +(g.gain ?? 1).toFixed(3)]);
      if (g.skip) return;
      const fx = -e.deltaX * u * g.gain, fy = -e.deltaY * u * g.gain;   // finger motion (natural scrolling)
      const soft = g.device !== "mouse";                   // fingers on a trackpad: comes to rest (see Ease); a wheel notch is exact
      if (hooks.walking()) { if (g.mode !== "zoom") { ease.add("heading", fx * RATE.look * s, soft); ease.add("tilt", fy * RATE.look * s, soft); kick(); } return; }
      if (g.start) {                                       // the next stroke: what is still gliding from the last one fades by itself
        begin(); pivot = null; anchor = null;
        if (g.device === "mouse") ease.clear(); else if (g.mode !== "zoom") ease.drop("zoom");
      }
      const proj = hooks.projection();
      if (g.mode === "zoom") {
        if (!anchor) anchor = zoomAnchor(e);
        const notch = g.pinch && wheelEvidence(e).device === "mouse";       // Ctrl + mouse wheel: a wheel step, not a 100 % pinch
        const delta = notch ? e.deltaY * u * RATE.wheel : g.pinch ? e.deltaY * u * RATE.pinch
          : g.device === "mouse" ? e.deltaY * u * RATE.wheel
          : (Math.abs(e.deltaY) >= Math.abs(e.deltaX) ? e.deltaY : e.deltaX) * u * RATE.scroll;
        ease.add("zoom", clamp(delta, -0.7, 0.7) * s, !!g.pinch && !notch);
      } else if (g.mode === "pan" || proj === "parallel" || height() > GLOBE.spin) { ease.add("px", fx, soft); ease.add("py", fy, soft); }   // from space two fingers turn the globe
      else { ease.add("heading", fx * RATE.orbit * s, soft); ease.add("tilt", -fy * RATE.tilt * s, soft); }
      kick();
    }, { passive: false });
    // Safari reports a trackpad pinch as gesture events, not as wheel events (it would zoom the whole page).
    let gesture = null;
    canvas.addEventListener("gesturestart", e => {
      e.preventDefault();
      if (!hooks.allowed() || hooks.walking()) return;
      begin(); pivot = null; ease.clear(); anchor = zoomAnchor(e); gesture = { scale: e.scale || 1 };
      latch.kind = "pinch"; latch.last = e.timeStamp || performance.now();      // scrolling waits until the pinch is over
    });
    canvas.addEventListener("gesturechange", e => {
      e.preventDefault();
      if (!gesture || !(e.scale > 0)) return;
      ease.add("zoom", clamp(-Math.log(e.scale / gesture.scale) * 100 * RATE.pinch, -0.7, 0.7) * sens(), true); gesture.scale = e.scale;
      latch.last = e.timeStamp || performance.now(); kick();
    });
    canvas.addEventListener("gestureend", e => { e.preventDefault(); gesture = null; });
    function zoomAnchor(e) {
      const r = canvas.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
      if (ortho()) return { screen: [x, y] };
      const p = pick(x, y);
      return p && C3.distance(p, cam.positionWC) < 5e4 ? { point: p } : null;   // globe scale: zoom to the centre
    }
    canvas.addEventListener("contextmenu", e => e.preventDefault());
    // Rhino's mouse: the button and modifiers held when the drag starts choose what it does.
    function dragMode(e) {
      const proj = hooks.projection(), mod = mac() ? e.metaKey : e.ctrlKey, alt = e.altKey, shift = e.shiftKey;
      if (hooks.walking()) return "look";
      if (e.button === 1) return mod ? "zoom" : alt ? (mac() ? "orbit" : "dolly") : "pan";   // middle button
      if (mod && shift && alt) return "lens";
      if (mod && alt) return "lookAround";
      if (shift && alt) return "none";                    // Rhino tilts (rolls) the view; EarthLink keeps the horizon level
      if (mod && shift) return "orbit";                   // rotate, also a parallel view
      if (mod) return "zoom";
      if (alt) return "dolly";
      if (shift) return "pan";
      return proj === "parallel" ? "pan" : "orbit";
    }
    canvas.addEventListener("pointerdown", e => {
      if (![1, 2].includes(e.button)) return;
      if (!hooks.allowed() && !hooks.walking()) return;
      e.preventDefault(); canvas.setPointerCapture(e.pointerId);
      const mode = dragMode(e);
      if (mode !== "look") { begin(); pivot = null; anchor = mode === "zoom" ? zoomAnchor(e) : null; ease.clear(); }
      pointer = { id: e.pointerId, x: e.clientX, y: e.clientY, mode, shift: e.shiftKey, sx: 0, sy: 0, lock: null };
      if (rec) rec.push(["down", Math.round(e.timeStamp), e.button, mode, e.pointerType]);
    });
    canvas.addEventListener("pointermove", e => {
      if (!pointer || pointer.id !== e.pointerId) return;
      let fx = e.clientX - pointer.x, fy = e.clientY - pointer.y; const s = sens(); pointer.x = e.clientX; pointer.y = e.clientY;
      pointer.sx += fx; pointer.sy += fy;
      if (e.shiftKey && !pointer.shift && !pointer.lock) pointer.lock = Math.abs(pointer.sx) >= Math.abs(pointer.sy) ? "x" : "y";   // Shift pressed mid-drag
      if (!e.shiftKey && !pointer.shift) pointer.lock = null;
      if (pointer.lock === "x") fy = 0; else if (pointer.lock === "y") fx = 0;
      const m = pointer.mode;
      if (rec) rec.push(["move", Math.round(e.timeStamp), fx, fy]);
      if (m === "look") { ease.add("heading", fx * RATE.lookMouse * s); ease.add("tilt", fy * RATE.lookMouse * s); }
      else if (m === "zoom") ease.add("zoom", fy * RATE.dragZoom * s);
      else if (m === "dolly") { if (!anchor) anchor = { point: pivot || (pivot = centre()) }; ease.add("zoom", fy * RATE.dragZoom * s); }
      else if (m === "pan") { ease.add("px", fx); ease.add("py", fy); }
      else if (m === "lookAround") { ease.add("lh", fx * RATE.lookMouse * s); ease.add("lt", -fy * RATE.lookMouse * s); }
      else if (m === "lens") { if (hooks.lens) hooks.lens(Math.exp(fy * 0.004)); }
      else if (m === "orbit" && height() > GLOBE.spin) { ease.add("px", fx); ease.add("py", fy); }   // from space a drag turns the globe
      else if (m === "orbit") { ease.add("heading", fx * RATE.orbitMouse * s); ease.add("tilt", -fy * RATE.tiltMouse * s); }
      kick();
    });
    // Rhino's keys: arrows rotate (pan in parallel), Shift + arrows pan, Page Up / Page Down zoom.
    document.addEventListener("keydown", e => {
      if (hooks.walking() || !hooks.allowed() || e.defaultPrevented || e.target.closest?.("input,textarea,select,[contenteditable=true]")) return;
      const arrow = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[e.key];
      if (arrow && !(mac() ? e.metaKey : e.ctrlKey)) {
        e.preventDefault(); if (!e.repeat) { begin(); pivot = null; anchor = null; }
        const [w, h] = size(), [dx, dy] = arrow;
        if (e.shiftKey || hooks.projection() === "parallel") { ease.add("px", -dx * w * STEP.pan); ease.add("py", -dy * h * STEP.pan); }
        else { ease.add("heading", dx * STEP.degrees); ease.add("tilt", -dy * STEP.degrees); }
        kick();
      } else if (e.key === "PageUp" || e.key === "PageDown") {
        e.preventDefault(); if (!e.repeat) { begin(); pivot = null; anchor = null; }
        if (e.shiftKey && hooks.lens) hooks.lens(e.key === "PageUp" ? 0.9 : 1 / 0.9);   // Shift: lens length
        else api.zoomStep(e.key === "PageUp" ? -1 : 1);
      }
    });
    const release = () => { pointer = null; hold = 0; };
    ["pointerup", "pointercancel", "lostpointercapture"].forEach(n => canvas.addEventListener(n, release));
    window.addEventListener("pointerup", release); window.addEventListener("blur", () => { release(); ease.clear(); });
    document.addEventListener("visibilitychange", () => { if (document.hidden) { release(); ease.clear(); } });

    // ---- public API (navigation menu, +/- buttons)
    function headingTilt() {
      const dir = cam.directionWC, n = normal(cam.positionWC), p = pivot || turnPivot();
      const enu = Cesium.Transforms.eastNorthUpToFixedFrame(cam.positionWC), inv = Cesium.Matrix4.inverseTransformation(enu, new Cesium.Matrix4());
      const h = C3.dot(dir, n) < -0.999 ? cam.upWC : dir, l = Cesium.Matrix4.multiplyByPointAsVector(inv, h, v3());
      const heading = (Cesium.Math.toDegrees(Math.atan2(l.x, l.y)) + 360) % 360;
      const off = C3.subtract(cam.positionWC, p, v3());
      const tilt = 90 - Cesium.Math.toDegrees(Math.asin(clamp(C3.dot(C3.normalize(off, off), normal(p)), -1, 1)));
      return { heading, tilt };
    }
    const turn = d => ((d % 360) + 540) % 360 - 180;
    const api = {
      RATE,
      headingTilt,
      // Turn (degrees clockwise) and tilt about the pivot, from a control such as the compass. start: a new gesture.
      turn(dh, dt, start) {
        if (!hooks.allowed()) return;
        if (start) { begin(); pivot = turnPivot(); ease.clear(); }
        if (dh || dt) { orbit(dh, dt); scene.requestRender(); }
      },
      north() {
        if (!hooks.allowed()) return; begin(); pivot = turnPivot(); let left = -turn(headingTilt().heading), time = 0;
        const total = left, dur = 0.35;
        anim = dt => {
          time += dt; const k = clamp(time / dur, 0, 1), eased = 1 - Math.pow(1 - k, 3), step = total * eased - (total - left); left -= step; orbit(step, 0);
          if (k < 1) return false;
          for (let i = 0; i < 3; i++) { const off = turn(headingTilt().heading); if (Math.abs(off) < 0.01) break; orbit(-off, 0); }   // a distant pivot's vertical differs slightly from the camera's
          return true;
        };
        kick();
      },
      zoomStep(sign) {                                     // click: a short eased zoom
        if (!hooks.allowed()) return; begin(); pivot = centre(); anchor = null; ease.add("zoom", sign * 0.5 * sens()); kick();
      },
      hold(sign) { if (!hooks.allowed()) return; if (!hold) { begin(); pivot = centre(); anchor = null; holdStart = performance.now(); } hold = sign; kick(); },
      release() { hold = 0; },
      stop() { ease.clear(); hold = 0; anim = null; pointer = null; },
      settleParallel() { if (!ortho()) return; pivot = centre(); setPose(cam.positionWC, cam.directionWC, cam.upWC); pivot = null; scene.requestRender(); },
      get pivot() { return pivot; },
      // Record raw input for `ms` (trackpad, wheel and drags; no page content), to see what a device really sends.
      record(ms = 10000) { rec = []; const out = rec; return new Promise(done => setTimeout(() => { if (rec === out) rec = null; done({ ua: navigator.userAgent, dpr: window.devicePixelRatio, mac: mac(), events: out }); }, ms)); },
    };
    return api;
  }

  // Rhino's Mac and Windows controls differ (Cmd vs Ctrl, two-finger scrolling). Detected from the browser.
  function isMac() {
    const n = typeof navigator !== "undefined" ? navigator : {};
    return /mac|iphone|ipad/i.test((n.userAgentData && n.userAgentData.platform) || n.platform || "");
  }
  return { RATE, STEP, GLOBE, maxTilt, WheelLatch, Ease, Floor, pivotDistance, isMouseWheel, wheelEvidence, isMac, neutralDirection, daylight, create };
});
