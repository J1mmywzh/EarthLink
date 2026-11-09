/* EarthLink walking: a 1.80 m person on whatever is drawn (Google's map or your model).

   Coordinates are metres east/north/up in a frame centred where the walk began. The browser supplies
   probe(origin, direction, maxDistance) -> distance to the first drawn surface, or null. Each frame the
   walker probes the ground below, walls ahead at knee and head height, and the ceiling when jumping. */
(function (root, factory) { const api = factory(); if (typeof module === "object" && module.exports) module.exports = api; else root.EarthLinkWalk = api; })(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const W = {
    eye: 1.65, head: 1.8, radius: 0.3, step: 0.45,      // stairs up to 45 cm are climbed
    walk: 3.5, sprint: 9.5, accel: 0.12,                // m/s; s to reach speed
    gravity: 9.81, jump: 0.5, snapDown: 0.5,            // m jump height; m followed down stairs
  };

  class Walker {
    constructor(probe, feet = [0, 0, 0]) {
      this.probe = probe; this.feet = feet.slice(); this.vel = [0, 0]; this.vz = 0;
      this.grounded = true; this.airborne = 0;
    }
    get eye() { return [this.feet[0], this.feet[1], this.feet[2] + W.eye]; }

    blocked(x, y, dx, dy) {
      const len = Math.hypot(dx, dy); if (!len) return false;
      const d = [dx / len, dy / len, 0], reach = len + W.radius;
      for (const h of [W.step + 0.05, W.head - 0.2]) {   // knee and head height
        const t = this.probe([x, y, this.feet[2] + h], d, reach);
        if (t != null && t < reach) return true;
      }
      return false;
    }
    ground(x, y, from) {                                // height of the surface below, or null
      const top = this.feet[2] + from, t = this.probe([x, y, top], [0, 0, -1], from + 60);
      return t == null ? null : top - t;
    }

    /* input: {x, y} desired direction in the walk frame (length <= 1), sprint, jump */
    step(input, dt) {
      if (!(dt > 0)) return this.feet;
      dt = Math.min(dt, 0.05);
      const len = Math.hypot(input.x || 0, input.y || 0), speed = input.sprint ? W.sprint : W.walk;
      const target = len ? [input.x / Math.max(1, len) * speed, input.y / Math.max(1, len) * speed] : [0, 0];
      const k = 1 - Math.exp(-dt / W.accel);
      this.vel = this.vel.map((v, i) => v + (target[i] - v) * k);
      if (Math.hypot(...this.vel) < 0.01 && !len) this.vel = [0, 0];

      // horizontal: each axis separately, so walls stop you and you slide along them
      let [dx, dy] = [this.vel[0] * dt, this.vel[1] * dt];
      const [x, y] = this.feet;
      if (dx && this.blocked(x, y, dx, 0)) { dx = 0; this.vel[0] = 0; }
      if (dy && this.blocked(x + dx, y, 0, dy)) { dy = 0; this.vel[1] = 0; }
      this.feet[0] += dx; this.feet[1] += dy;

      // vertical: stand, climb a step, follow stairs down, jump, fall
      if (input.jump && this.grounded) { this.vz = Math.sqrt(2 * W.gravity * W.jump); this.grounded = false; }
      let g = this.ground(this.feet[0], this.feet[1], W.step);
      if (g == null) {                                  // under a refined map surface (or nothing yet): rise onto it
        const high = this.ground(this.feet[0], this.feet[1], 3);
        if (high != null && (g == null || high > g + 0.01) && high > this.feet[2]) g = high;
      }
      if (this.grounded) {
        if (g == null) return this.feet;                // nothing drawn below yet: hold
        if (g >= this.feet[2] - W.snapDown) { this.feet[2] = g; return this.feet; }
        this.grounded = false; this.vz = 0;              // walked off an edge
      }
      if (this.vz > 0) {
        const t = this.probe([this.feet[0], this.feet[1], this.feet[2] + W.head - 0.05], [0, 0, 1], this.vz * dt + 0.1);
        if (t != null) this.vz = 0;
      }
      this.vz -= W.gravity * dt; this.airborne += dt;
      const z = this.feet[2] + this.vz * dt;
      if (g != null && z <= g) { this.feet[2] = g; this.vz = 0; this.grounded = true; this.airborne = 0; }
      else if (g == null && this.airborne > 3) { this.vz = 0; }   // nothing below for 3 s: stop falling
      else this.feet[2] = z;
      return this.feet;
    }
  }
  return { W, Walker };
});
