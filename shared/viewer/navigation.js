/* EarthLink navigation: Rhino 8 for Mac gestures on a Cesium globe.

   Perspective / Two-Point   two fingers or right-drag   orbit about the point at the centre of the view
                             Shift + either               pan (the ground follows the fingers)
                             pinch, wheel, Ctrl+right     zoom (toward the cursor below 50 km)
   Parallel                  two fingers, right-drag      pan (Shift changes nothing)   pinch, wheel: zoom
   Walk                      two fingers or right-drag    look around

   Every gesture keeps the horizon level, picks its pivot when it starts and keeps one mode until its
   momentum ends. Movement is eased per frame. Pan and zoom scale with distance, orbit is angular, so
   one Sensitivity value feels the same from orbit to a single room. */
(function (root, factory) { const api = factory(); if (typeof module === "object" && module.exports) module.exports = api; else root.EarthLinkNavigation = api; })(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));

  // Per-feature rates at Sensitivity 100 %. Degrees per pixel unless noted.
  const RATE = {
    orbit: 0.144, tilt: 0.13,          // two fingers
    orbitMouse: 0.27, tiltMouse: 0.243, // right-drag
    pan: 1.1,                          // x the distance under the fingers (1 = exact follow)
    pinch: 0.0135, scroll: 0.0068,     // zoom: log-distance per wheel delta unit (trackpad)
    wheel: 0.0032, dragZoom: 0.0054,   // mouse wheel, Ctrl + right-drag
    hold: Math.LN2 / 0.61,             // +/- held: distance halves every 0.61 s
    look: 0.08, lookMouse: 0.15,       // walking
  };
  const GESTURE_GAP = 220;   // ms without wheel events that ends a gesture (momentum included)
  const EASE = 0.045;        // s: time constant of the per-frame easing

  /* Decide what a wheel event does. One decision per gesture: Shift released or pressed during the
     momentum tail cannot switch pan to orbit. Pinch (ctrlKey) is always zoom. */
  class WheelLatch {
    constructor() { this.last = -Infinity; this.mode = null; this.device = null; }
    read(e, projection, now) {
      const fresh = now - this.last > GESTURE_GAP; this.last = now;
      if (e.ctrlKey) { this.mode = fresh ? "zoom" : this.mode || "zoom"; return { mode: "zoom", pinch: true, start: fresh }; }
      if (fresh || !this.mode) {
        this.device = isMouseWheel(e) ? "mouse" : "trackpad";
        this.mode = this.device === "mouse" ? "zoom"
          : projection === "parallel" ? "pan"                // Rhino: Shift changes nothing in a parallel view
          : (e.shiftKey ? "pan" : "orbit");
      }
      return { mode: this.mode, device: this.device, start: fresh };
    }
  }
  // A notched mouse wheel starts a gesture with one large, purely vertical step; a trackpad starts small.
  function isMouseWheel(e) {
    if (e.deltaMode === 1 || e.deltaMode === 2) return true;
    if (e.deltaX !== 0) return false;
    const big = Math.abs(e.deltaY) >= 50, wd = e.wheelDeltaY;
    return big && (wd === undefined || wd === 0 || Math.abs(wd) % 120 === 0);
  }
  const wheelPx = e => (e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? 400 : 1);

  // Pending motion released gradually, frame by frame.
  class Ease {
    constructor() { this.v = { heading: 0, tilt: 0, px: 0, py: 0, zoom: 0 }; }
    add(k, x) { if (Number.isFinite(x)) this.v[k] += x; }
    take(dt) {
      const f = 1 - Math.exp(-Math.max(0, dt) / EASE), out = {};
      let any = false;
      for (const k in this.v) {
        out[k] = this.v[k] * f; this.v[k] -= out[k];
        if (Math.abs(this.v[k]) < 1e-4) { out[k] += this.v[k]; this.v[k] = 0; }
        if (out[k]) any = true;
      }
      return any ? out : null;
    }
    clear() { for (const k in this.v) this.v[k] = 0; }
    get busy() { return Object.values(this.v).some(Boolean); }
  }

  // Sunlight when the sun is off: from behind the viewer, a little above.
  function neutralDirection(direction, up) {
    const vertical = direction.reduce((s, n, i) => s + n * up[i], 0), h = direction.map((n, i) => n - up[i] * vertical), length = Math.hypot(...h) || 1;
    const d = h.map((n, i) => .5 * n / length - up[i]), norm = Math.hypot(...d); return d.map(n => n / norm);
  }

  /* The controller: binds input on the canvas and moves viewer.camera. `hooks`:
     projection() "perspective"|"two_point"|"parallel", pick(ray) nearest drawn surface or null,
     ground(ray) nearest map surface (your model excluded) or null,
     allowed() navigation permitted now,
     sensitivity() multiplier, moved() user took the camera (cancel flights / Follow Rhino),
     walking() true while walking, look(dHeading, dPitch) turn the walker. */
  function create(Cesium, viewer, hooks) {
    const C3 = Cesium.Cartesian3, scene = viewer.scene, cam = viewer.camera, canvas = scene.canvas;
    const E = Cesium.Ellipsoid.WGS84, latch = new WheelLatch(), ease = new Ease();
    const v3 = () => new C3();
    let pivot = null, anchor = null, pointer = null, hold = 0, holdStart = 0, last = 0, raf = 0, anim = null;
    scene.screenSpaceCameraController.enableInputs = false;   // one input path only

    const normal = p => E.geodeticSurfaceNormal(p, v3());
    const sens = () => clamp(+hooks.sensitivity() || 1, 0.2, 3);
    const ortho = () => cam.frustum instanceof Cesium.OrthographicFrustum;
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
    function centre() {
      const [w, h] = size();
      return pick(w / 2, h / 2) || C3.add(cam.positionWC, C3.multiplyByScalar(cam.directionWC, Math.max(50, height() * 2), v3()), v3());
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
    function setPose(pos, dir, up) {
      dir = C3.normalize(dir, v3());
      if (ortho()) { if (!pivot) pivot = centre(); pos = C3.subtract(pivot, C3.multiplyByScalar(dir, BACK, v3()), v3()); }
      else pos = aboveGround(pos);
      if (hooks.projection() === "two_point") {             // the axis stays level; framing is the lens shift
        const n = normal(pos); C3.subtract(dir, C3.multiplyByScalar(n, C3.dot(dir, n), v3()), dir); C3.normalize(dir, dir);
      }
      cam.setView({ destination: pos, orientation: { direction: dir, up: level(dir, up) } });
    }
    // Keep the camera above the drawn surface: under Google's mesh the map shows from behind as a jumble.
    function aboveGround(pos) {
      if (!hooks.ground || hooks.walking() || height() > 3000) return pos;
      const n = normal(pos), down = hooks.ground(new Cesium.Ray(pos, C3.negate(n, v3())));
      if (down) {                                          // standing above the map: keep 1.5 m clearance
        const above = C3.dot(C3.subtract(pos, down, v3()), n);
        return above >= 1.5 ? pos : C3.add(pos, C3.multiplyByScalar(n, 1.5 - above, v3()), v3());
      }
      const lid = hooks.ground(new Cesium.Ray(C3.add(pos, C3.multiplyByScalar(n, 300, v3()), v3()), C3.negate(n, v3())));
      return lid ? C3.add(lid, C3.multiplyByScalar(n, 1.5, v3()), v3()) : pos;   // nothing below: we are under the map
    }
    const rotate = (q, v) => Cesium.Matrix3.multiplyByVector(Cesium.Matrix3.fromQuaternion(q), v, v3());

    // ---- motions (all in world space, about a pivot latched when the gesture began)
    function orbit(dh, dt) {
      if (!pivot) pivot = centre();
      let pos = cam.positionWC, dir = cam.directionWC, up = cam.upWC;
      const n = normal(pivot);
      if (dh) {
        const q = Cesium.Quaternion.fromAxisAngle(n, -Cesium.Math.toRadians(dh));
        pos = C3.add(pivot, rotate(q, C3.subtract(pos, pivot, v3())), v3()); dir = rotate(q, dir); up = rotate(q, up);
      }
      if (dt && hooks.projection() === "two_point") {
        const f = cam.frustum, a = clamp(Math.atan(f._elShift || 0) - Cesium.Math.toRadians(dt), -1.4, 1.4);   // the frame follows the fingers
        f._elShift = Math.tan(a);
      } else if (dt) {
        const off = C3.subtract(pos, pivot, v3()), d = C3.magnitude(off);
        const elev = Math.asin(clamp(C3.dot(off, n) / (d || 1), -1, 1));
        const next = clamp(elev - Cesium.Math.toRadians(dt), Cesium.Math.toRadians(2), Cesium.Math.toRadians(89.9));
        if (Math.abs(next - elev) > 1e-9) {
          const right = C3.normalize(C3.cross(dir, up, v3()), v3());
          const q = Cesium.Quaternion.fromAxisAngle(right, elev - next);
          pos = C3.add(pivot, rotate(q, off), v3()); dir = rotate(q, dir); up = rotate(q, up);
        }
      }
      setPose(pos, dir, up);
    }
    function pan(fx, fy) {                                 // finger motion in CSS px; the scene follows it
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
      const down = clamp(-C3.dot(cam.directionWC, n), 0.25, 1);             // farther ground moves faster per pixel
      const D = C3.add(C3.multiplyByScalar(right, -fx * m, v3()), C3.multiplyByScalar(fwd, fy * m / down, v3()), v3());
      // move over the curved Earth: rotate camera and pivot about the Earth's centre
      const axis = C3.cross(pivot, D, v3()), ang = C3.magnitude(D) / C3.magnitude(pivot);
      if (!(ang > 0) || C3.magnitude(axis) === 0) return;
      const q = Cesium.Quaternion.fromAxisAngle(C3.normalize(axis, axis), ang);   // carries the camera along D
      pivot = rotate(q, pivot);
      setPose(rotate(q, cam.positionWC), rotate(q, cam.directionWC), rotate(q, cam.upWC));
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
      const A = anchor?.point || pivot || (pivot = centre());
      const off = C3.subtract(cam.positionWC, A, v3()), d = C3.magnitude(off);
      let nd = clamp(d * z, 0.4, 4e7);
      const pos = C3.add(A, C3.multiplyByScalar(off, nd / (d || 1), v3()), v3());
      if (Cesium.Cartographic.fromCartesian(pos)?.height > 4e7) return;
      cam.setView({ destination: pos, orientation: { direction: cam.directionWC, up: cam.upWC } });   // no re-levelling: the image never turns
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
    function begin() { hooks.moved(); cam.cancelFlight(); }

    // ---- input
    canvas.addEventListener("wheel", e => {
      e.preventDefault();
      if (!hooks.allowed() && !hooks.walking()) return;
      const g = latch.read(e, hooks.projection(), e.timeStamp || performance.now()), u = wheelPx(e), s = sens();   // event time: page stalls cannot split a gesture
      const fx = -e.deltaX * u, fy = -e.deltaY * u;        // finger motion (natural scrolling)
      if (hooks.walking()) { if (g.mode !== "zoom") { ease.add("heading", fx * RATE.look * s); ease.add("tilt", fy * RATE.look * s); kick(); } return; }
      if (g.start) { begin(); pivot = null; anchor = null; ease.clear(); }
      const proj = hooks.projection();
      if (g.mode === "zoom") {
        if (!anchor) anchor = zoomAnchor(e);
        const delta = g.pinch ? e.deltaY * u * RATE.pinch
          : g.device === "mouse" ? e.deltaY * u * RATE.wheel
          : (Math.abs(e.deltaY) >= Math.abs(e.deltaX) ? e.deltaY : e.deltaX) * u * RATE.scroll;
        ease.add("zoom", clamp(delta, -0.7, 0.7) * s);
      } else if (g.mode === "pan" || proj === "parallel") { ease.add("px", fx); ease.add("py", fy); }
      else { ease.add("heading", fx * RATE.orbit * s); ease.add("tilt", -fy * RATE.tilt * s); }
      kick();
    }, { passive: false });
    function zoomAnchor(e) {
      const r = canvas.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top;
      if (ortho()) return { screen: [x, y] };
      const p = pick(x, y);
      return p && C3.distance(p, cam.positionWC) < 5e4 ? { point: p } : null;   // globe scale: zoom to the centre
    }
    canvas.addEventListener("contextmenu", e => e.preventDefault());
    canvas.addEventListener("pointerdown", e => {
      if (![1, 2].includes(e.button)) return;
      if (!hooks.allowed() && !hooks.walking()) return;
      e.preventDefault(); canvas.setPointerCapture(e.pointerId);
      const proj = hooks.projection();
      const mode = hooks.walking() ? "look" : e.ctrlKey || e.metaKey ? "zoom" : e.shiftKey || e.button === 1 || proj === "parallel" ? "pan" : "orbit";
      if (mode !== "look") { begin(); pivot = null; anchor = mode === "zoom" ? zoomAnchor(e) : null; ease.clear(); }
      pointer = { id: e.pointerId, x: e.clientX, y: e.clientY, mode };
    });
    canvas.addEventListener("pointermove", e => {
      if (!pointer || pointer.id !== e.pointerId) return;
      const fx = e.clientX - pointer.x, fy = e.clientY - pointer.y, s = sens(); pointer.x = e.clientX; pointer.y = e.clientY;
      if (pointer.mode === "look") { ease.add("heading", fx * RATE.lookMouse * s); ease.add("tilt", fy * RATE.lookMouse * s); }
      else if (pointer.mode === "zoom") ease.add("zoom", fy * RATE.dragZoom * s);
      else if (pointer.mode === "pan") { ease.add("px", fx); ease.add("py", fy); }
      else { ease.add("heading", fx * RATE.orbitMouse * s); ease.add("tilt", -fy * RATE.tiltMouse * s); }
      kick();
    });
    const release = () => { pointer = null; hold = 0; };
    ["pointerup", "pointercancel", "lostpointercapture"].forEach(n => canvas.addEventListener(n, release));
    window.addEventListener("pointerup", release); window.addEventListener("blur", () => { release(); ease.clear(); });
    document.addEventListener("visibilitychange", () => { if (document.hidden) { release(); ease.clear(); } });

    // ---- public API (navigation menu, +/- buttons)
    function headingTilt() {
      const dir = cam.directionWC, n = normal(cam.positionWC), p = pivot || centre();
      const enu = Cesium.Transforms.eastNorthUpToFixedFrame(cam.positionWC), inv = Cesium.Matrix4.inverseTransformation(enu, new Cesium.Matrix4());
      const h = C3.dot(dir, n) < -0.999 ? cam.upWC : dir, l = Cesium.Matrix4.multiplyByPointAsVector(inv, h, v3());
      const heading = (Cesium.Math.toDegrees(Math.atan2(l.x, l.y)) + 360) % 360;
      const off = C3.subtract(cam.positionWC, p, v3());
      const tilt = hooks.projection() === "two_point" ? Cesium.Math.toDegrees(Math.atan(cam.frustum._elShift || 0))
        : 90 - Cesium.Math.toDegrees(Math.asin(clamp(C3.dot(C3.normalize(off, off), normal(p)), -1, 1)));
      return { heading, tilt };
    }
    let sliderAt = 0;
    const sliderPivot = () => { const now = performance.now(); if (now - sliderAt > 600) { begin(); pivot = centre(); } sliderAt = now; };
    const turn = d => ((d % 360) + 540) % 360 - 180;
    return {
      RATE,
      headingTilt,
      setHeading(h) { if (!hooks.allowed()) return; sliderPivot(); orbit(turn(h - headingTilt().heading), 0); scene.requestRender(); },
      setTilt(t) {
        if (!hooks.allowed()) return;
        if (hooks.projection() === "two_point") { begin(); cam.frustum._elShift = Math.tan(Cesium.Math.toRadians(clamp(t, -80, 80))); }
        else { sliderPivot(); orbit(0, t - headingTilt().tilt); }
        scene.requestRender();
      },
      north() {
        if (!hooks.allowed()) return; begin(); pivot = centre(); let left = -turn(headingTilt().heading), time = 0;
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
    };
  }

  return { RATE, WheelLatch, Ease, isMouseWheel, neutralDirection, create };
});
