/* EarthLink walking: a 1.80 m person on whatever is drawn (Google's map or your model), who can also fly
   like Minecraft's creative mode: double-tap Space to take off, Space rises, Shift sinks, double-tap Space
   again to drop. Flying has no collision: it passes through buildings, trees, your model and the ground.

   Coordinates are metres east/north/up in a frame centred where the walk began. The browser supplies
   probe(origin, direction, maxDistance) -> distance to the first drawn surface, or null. Each frame the
   walker probes the ground below, walls ahead at knee and head height, and the ceiling when jumping. */
(function (root, factory) { const api = factory(); if (typeof module === "object" && module.exports) module.exports = api; else root.EarthLinkWalk = api; })(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const W = {
    eye: 1.65, head: 1.8, radius: 0.3, step: 0.45,      // stairs up to 45 cm are climbed
    walk: 4.4, sprint: 11.9, sneak: 1.3, accel: 0.12,    // m/s; s to reach speed
    gravity: 9.81, jump: 0.5, snapDown: 0.5,            // m jump height; m followed down stairs
    fly: 13.6, flySprint: 27, flyUp: 9.4, flyAccel: 0.25,   // Minecraft creative flight, m/s; s to reach speed (it glides)
  };

  class Walker {
    constructor(probe, feet = [0, 0, 0]) {
      this.probe = probe; this.feet = feet.slice(); this.vel = [0, 0]; this.vz = 0;
      this.grounded = true; this.airborne = 0; this.flying = false;
    }
    toggleFly() {                                        // double-tap Space
      this.flying = !this.flying; this.vz = 0;
      if (this.flying) this.grounded = false; else this.airborne = 0;   // stop flying: fall
      return this.flying;
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
    ground(x, y, from, reach = 60) {                    // height of the surface below, or null
      const top = this.feet[2] + from, t = this.probe([x, y, top], [0, 0, -1], from + reach);
      return t == null ? null : top - t;
    }

    /* input: {x, y} desired direction in the walk frame (length <= 1), sprint, sneak (Shift), jump (Space held) */
    step(input, dt) {
      if (!(dt > 0)) return this.feet;
      dt = Math.min(dt, 0.05);
      const fly = this.flying;
      const len = Math.hypot(input.x || 0, input.y || 0);
      const speed = fly ? (input.sprint ? W.flySprint : W.fly) : input.sprint ? W.sprint : input.sneak ? W.sneak : W.walk;
      const target = len ? [input.x / Math.max(1, len) * speed, input.y / Math.max(1, len) * speed] : [0, 0];
      const k = 1 - Math.exp(-dt / (fly ? W.flyAccel : W.accel));
      this.vel = this.vel.map((v, i) => v + (target[i] - v) * k);
      if (Math.hypot(...this.vel) < 0.01 && !len) this.vel = [0, 0];

      // horizontal: each axis separately, so walls stop you and you slide along them
      let [dx, dy] = [this.vel[0] * dt, this.vel[1] * dt];
      const [x, y] = this.feet;
      if (!fly && dx && this.blocked(x, y, dx, 0)) { dx = 0; this.vel[0] = 0; }
      if (!fly && dy && this.blocked(x + dx, y, 0, dy)) { dy = 0; this.vel[1] = 0; }
      this.feet[0] += dx; this.feet[1] += dy;
      if (fly) return this.flyVertical(input, dt, k);

      // vertical: stand, climb a step, follow stairs down, jump, fall
      if (input.jump && this.grounded) { this.vz = Math.sqrt(2 * W.gravity * W.jump); this.grounded = false; }
      let g = this.ground(this.feet[0], this.feet[1], W.step, this.grounded ? 60 : 2000);   // falling from a flight: look far down
      if (g == null) {                                  // under a refined map surface (or nothing yet): rise onto it
        const high = this.ground(this.feet[0], this.feet[1], 3);
        if (high != null && (g == null || high > g + 0.01) && high > this.feet[2]) g = high;
      }
      if (g == null && !this.grounded) {                // dropped out of a flight under the map: stand on what is above
        const above = this.ground(this.feet[0], this.feet[1], 3000, 0);
        if (above != null) { this.feet[2] = above; this.vz = 0; this.grounded = true; this.airborne = 0; return this.feet; }
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
  Walker.prototype.flyVertical = function (input, dt, k) {   // Space rises, Shift sinks; nothing is in the way
    const want = ((input.jump ? 1 : 0) - (input.sneak ? 1 : 0)) * W.flyUp;
    this.vz += (want - this.vz) * k;
    if (Math.abs(this.vz) < 0.01 && !want) this.vz = 0;
    this.feet[2] += this.vz * dt;
    return this.feet;
  };
  return { W, Walker };
});
