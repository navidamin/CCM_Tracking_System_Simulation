/**
 * Billet animation engine.
 *
 * Reads pre-computed event timestamps and interpolates billet positions
 * along the plant layout for each frame.
 */
import * as THREE from 'three';
import {
    STRAND_COLORS,
    X_TRANSPORT_START, X_TRANSPORT_END,
    X_DISCHARGE_START, X_DISCHARGE_END, X_INTERM_STOPPER,
    X_COOLBED_START, X_COOLBED_END,
    X_TABLE_START, X_TABLE_END,
    X_YARD_START, Z_COOLBED, Z_YARD,
    COOLBED_PITCH, COOLBED_PHASE_TIME, COOLBED_CYCLE_TIME,
    COOLBED_VERT_TRAVEL, COOLBED_HORIZ_TRAVEL,
    strandZ,
} from './equipment.js';

const BILLET_GEOM = new THREE.BoxGeometry(0.8, 0.15, 0.13);

export class AnimationEngine {
    constructor(scene) {
        this.scene = scene;
        this.billetMeshes = [];  // { mesh, billet } pairs
        this.billetGroup = new THREE.Group();
        scene.add(this.billetGroup);
        this.tcLog = [];
        this.coolbedLog = [];
        this.scenarioData = null;
        this.numStrands = 6;
    }

    /**
     * Load a scenario: create billet meshes and store event data.
     */
    load(data) {
        this.clear();
        this.scenarioData = data;
        this.numStrands = data.params.strands;
        this.tcLog = data.transfer_car_log || [];
        this.coolbedLog = data.coolbed_occupancy_log || [];

        for (const b of data.billets) {
            const colorIdx = (b.strand - 1) % STRAND_COLORS.length;
            const mat = new THREE.MeshStandardMaterial({
                color: STRAND_COLORS[colorIdx],
                roughness: 0.4,
                metalness: 0.2,
            });
            const mesh = new THREE.Mesh(BILLET_GEOM, mat);
            mesh.castShadow = true;
            mesh.visible = false;
            this.billetGroup.add(mesh);
            this.billetMeshes.push({ mesh, billet: b });
        }
    }

    clear() {
        for (const { mesh } of this.billetMeshes) {
            mesh.geometry !== BILLET_GEOM && mesh.geometry.dispose();
            mesh.material.dispose();
            this.billetGroup.remove(mesh);
        }
        this.billetMeshes = [];
        this.scenarioData = null;
    }

    /**
     * Update all billet positions for the given simulation time.
     * Returns live stats.
     */
    update(simTime, equipment) {
        let castCount = 0;
        let deliveredCount = 0;
        let activeBillets = 0;

        for (const { mesh, billet } of this.billetMeshes) {
            const pos = this.getBilletPosition(billet, simTime);
            if (pos === null) {
                mesh.visible = false;
                // Count stats even when not visible
                if (billet.events.torch_cut_start !== null &&
                    simTime >= billet.events.torch_cut_start) {
                    castCount++;
                }
                if (billet.events.crane_deliver !== null &&
                    simTime >= billet.events.crane_deliver) {
                    deliveredCount++;
                }
                continue;
            }

            mesh.visible = true;
            mesh.position.set(pos.x, pos.y, pos.z);
            mesh.rotation.y = pos.rotY || 0;
            activeBillets++;
            castCount++;
            if (billet.events.crane_deliver !== null &&
                simTime >= billet.events.crane_deliver) {
                deliveredCount++;
            }
        }

        // Update transfer car position
        if (equipment && equipment.tc) {
            const tcZ = this.getTCPosition(simTime);
            equipment.tc.position.z = tcZ;
        }

        // Get coolbed occupancy at this time
        let coolbedOcc = 0;
        for (const entry of this.coolbedLog) {
            if (entry.t <= simTime) coolbedOcc = entry.occupied;
            else break;
        }

        // TC status
        let tcStatus = 'idle';
        for (let i = this.tcLog.length - 1; i >= 0; i--) {
            if (this.tcLog[i].t <= simTime) {
                tcStatus = `${this.tcLog[i].action} S${this.tcLog[i].strand}`;
                break;
            }
        }

        return { castCount, deliveredCount, activeBillets, coolbedOcc, tcStatus };
    }

    /**
     * Compute the 3D position of a billet at the given sim time.
     * Returns null if the billet shouldn't be visible.
     */
    getBilletPosition(billet, t) {
        const e = billet.events;
        const strand = billet.strand;
        const ns = this.numStrands;
        const sz = strandZ(strand, ns);

        // Not yet cut
        if (e.torch_cut_start === null || t < e.torch_cut_start) return null;

        // Already delivered to yard — hide after a bit
        if (e.crane_deliver !== null && t > e.crane_deliver + 5) return null;

        // Stage 1: Torch cutting (at mold position)
        if (t < (e.transport_entry || Infinity)) {
            return { x: 1.0, y: 0.5, z: sz };
        }

        // Stage 2: Transport RT
        if (e.transport_entry !== null && t < (e.transport_exit || Infinity)) {
            const frac = (t - e.transport_entry) / ((e.transport_exit || e.transport_entry + 100) - e.transport_entry);
            const x = X_TRANSPORT_START + frac * (X_TRANSPORT_END - X_TRANSPORT_START);
            return { x, y: 0.25, z: sz };
        }

        // Stage 3: Waiting at security stopper / entering discharge
        if (e.transport_exit !== null && t < (e.discharge_entry || Infinity)) {
            return { x: X_TRANSPORT_END - 0.5, y: 0.25, z: sz };
        }

        // Stage 4: Discharge RT
        if (e.discharge_entry !== null && t < (e.discharge_buffer || Infinity)) {
            const dur = (e.discharge_buffer || e.discharge_entry + 50) - e.discharge_entry;
            const frac = (t - e.discharge_entry) / dur;
            // Determine stopper position
            let targetX;
            if (billet.stopper_role === 'second_at_intermediate') {
                targetX = X_INTERM_STOPPER;
            } else {
                targetX = X_DISCHARGE_END;
            }
            const x = X_DISCHARGE_START + frac * (targetX - X_DISCHARGE_START);
            return { x, y: 0.25, z: sz };
        }

        // Stage 5: Waiting at discharge stopper for pair
        if (e.discharge_buffer !== null && t < (e.transfer_pickup || Infinity)) {
            let x;
            if (billet.stopper_role === 'second_at_intermediate') {
                x = X_INTERM_STOPPER;
            } else {
                x = X_DISCHARGE_END - 0.3;
            }
            return { x, y: 0.25, z: sz };
        }

        // Stage 6: Transfer car moving to cooling bed
        if (e.transfer_pickup !== null && t < (e.coolbed_entry || Infinity)) {
            const dur = (e.coolbed_entry || e.transfer_pickup + 20) - e.transfer_pickup;
            const frac = Math.min(1, (t - e.transfer_pickup) / dur);
            // Interpolate from strand Z to coolbed Z, and X to coolbed entry
            const x = X_DISCHARGE_END + 1.5 + frac * (X_COOLBED_START - X_DISCHARGE_END - 1.5);
            const z = sz + frac * (Z_COOLBED - sz);
            const y = 0.25 + frac * 0.3; // slight lift during transfer
            return { x, y, z };
        }

        // Stage 7: On cooling bed (stepping through slots, rotated 90 degrees)
        if (e.coolbed_entry !== null && t < (e.coolbed_exit || Infinity)) {
            const dur = (e.coolbed_exit || e.coolbed_entry + 24) - e.coolbed_entry;
            const frac = Math.min(1, (t - e.coolbed_entry) / dur);
            const x = X_COOLBED_START + frac * (X_COOLBED_END - X_COOLBED_START);
            return { x, y: 0.35, z: Z_COOLBED, rotY: Math.PI / 2 };
        }

        // Stage 8: Collecting table
        if (e.coolbed_exit !== null && t < (e.crane_pickup || Infinity)) {
            const frac = Math.min(1,
                (t - e.coolbed_exit) / ((e.crane_pickup || e.coolbed_exit + 30) - e.coolbed_exit));
            const x = X_TABLE_START + frac * 6;
            return { x, y: 0.35, z: Z_COOLBED };
        }

        // Stage 9: Crane lifting to yard
        if (e.crane_pickup !== null && t < (e.crane_deliver || Infinity)) {
            const dur = (e.crane_deliver || e.crane_pickup + 60) - e.crane_pickup;
            const frac = Math.min(1, (t - e.crane_pickup) / dur);

            if (frac < 0.2) {
                // Lifting
                const liftFrac = frac / 0.2;
                return { x: X_TABLE_START + 6, y: 0.35 + liftFrac * 7, z: Z_COOLBED };
            } else if (frac < 0.7) {
                // Traversing
                const travFrac = (frac - 0.2) / 0.5;
                const x = X_TABLE_START + 6 + travFrac * (X_YARD_START + 15 - X_TABLE_START - 6);
                return { x, y: 7.5, z: Z_COOLBED };
            } else {
                // Lowering
                const lowFrac = (frac - 0.7) / 0.3;
                return {
                    x: X_YARD_START + 15,
                    y: 7.5 - lowFrac * 7,
                    z: Z_YARD
                };
            }
        }

        // Stage 10: In yard (briefly visible)
        if (e.crane_deliver !== null && t >= e.crane_deliver) {
            return { x: X_YARD_START + 15, y: 0.2, z: Z_YARD };
        }

        return null;
    }

    /**
     * Get transfer car Z position from the log.
     */
    getTCPosition(t) {
        let lastStrand = 1;
        let lastAction = 'idle';
        for (const entry of this.tcLog) {
            if (entry.t <= t) {
                lastStrand = entry.strand;
                lastAction = entry.action;
            } else break;
        }
        return strandZ(lastStrand, this.numStrands);
    }

    /**
     * Get TC hook height (Y) from the transfer car log.
     * Returns Y position for the hook mesh (0.15 = down at roller level, 1.25 = fully up).
     */
    getTCHookHeight(t) {
        const FULL_STROKE = 1.1;
        const Y_DOWN = 0.15;
        const Y_UP = Y_DOWN + FULL_STROKE; // 1.25
        const PLACE_EXTEND = 0.44; // partial lower for placement

        // Find the active TC log entry and compute hook position
        let hookY = Y_DOWN; // default: frame down
        for (let i = 0; i < this.tcLog.length; i++) {
            const entry = this.tcLog[i];
            const next = this.tcLog[i + 1];
            if (entry.t > t) break;
            const endT = next ? next.t : entry.t + (entry.duration || 0);

            if (t >= entry.t && t < entry.t + (entry.duration || 0.01)) {
                const frac = Math.min(1, (t - entry.t) / Math.max(entry.duration, 0.01));
                switch (entry.action) {
                    case 'hook_down_pickup':
                        // Lowering: from current to full down
                        hookY = Y_UP - frac * FULL_STROKE;
                        break;
                    case 'align_to_strand':
                        hookY = Y_DOWN; // stays down during alignment
                        break;
                    case 'hook_up_pickup':
                        // Lifting: from down to up
                        hookY = Y_DOWN + frac * FULL_STROKE;
                        break;
                    case 'travel_to_coolbed':
                        hookY = Y_UP; // carrying, fully up
                        break;
                    case 'hook_down_place':
                        // Partial lower for placement
                        hookY = Y_UP - frac * PLACE_EXTEND;
                        break;
                    case 'travel_to_strand':
                        // Traveling with partially lowered frame (after placement)
                        hookY = Y_UP - PLACE_EXTEND;
                        break;
                    default:
                        // Keep last position
                        break;
                }
                return hookY;
            }
        }
        return hookY;
    }

    /**
     * Update stopper states (color + height) based on billet events.
     * Computes stopper UP/DOWN from billet timestamps client-side.
     */
    updateStoppers(simTime, equipment) {
        if (!equipment || !equipment.stoppers || !this.scenarioData) return;
        const billets = this.scenarioData.billets;

        // For each strand, determine stopper states
        for (let s = 1; s <= this.numStrands; s++) {
            let secUp = false;
            let intUp = false;

            // Check each billet on this strand
            for (const b of billets) {
                if (b.strand !== s) continue;
                const e = b.events;

                // Intermediate stopper UP when first billet hits fixed stopper + 2s
                // (discharge_buffer for pair_pos=1 + 2s actuation)
                if (b.stopper_role === 'first_at_fixed' && e.discharge_buffer != null) {
                    const tUp = e.discharge_buffer + 2.0;
                    const tDown = e.transfer_pickup != null ? e.transfer_pickup + 2.0 : Infinity;
                    if (simTime >= tUp && simTime < tDown) intUp = true;
                }

                // Security stopper UP when second billet hits intermediate + 2s
                if (b.stopper_role === 'second_at_intermediate' && e.discharge_buffer != null) {
                    const tUp = e.discharge_buffer + 2.0;
                    const tDown = e.transfer_pickup != null ? e.transfer_pickup + 2.0 : Infinity;
                    if (simTime >= tUp && simTime < tDown) secUp = true;
                }
            }

            const ss = equipment.stoppers[s];
            if (!ss) continue;

            // Security stopper
            if (ss.security) {
                ss.security.material.color.setHex(secUp ? 0x33aa33 : 0xdd3333);
                ss.security.position.y = secUp ? 0.40 : 0.25;
            }
            // Intermediate stopper
            if (ss.intermediate) {
                ss.intermediate.material.color.setHex(intUp ? 0xddaa00 : 0xdd3333);
                ss.intermediate.position.y = intUp ? 0.37 : 0.22;
            }
        }
    }

    /**
     * Update cooling bed movable beam position (4-phase walking cycle).
     * Computes phase from coolbed_entry timestamps.
     */
    updateCoolingBed(simTime, equipment) {
        if (!equipment || !equipment.movableBeam || !this.scenarioData) return;
        const billets = this.scenarioData.billets;
        const beam = equipment.movableBeam;

        // Collect all coolbed entry times (each triggers a 24s cycle)
        if (!this._cbCycleTimes) {
            this._cbCycleTimes = [];
            for (const b of billets) {
                if (b.events.coolbed_entry != null) {
                    this._cbCycleTimes.push(b.events.coolbed_entry);
                }
            }
            // Remove near-duplicates (pairs enter at same time)
            this._cbCycleTimes.sort((a, b) => a - b);
            const unique = [this._cbCycleTimes[0]];
            for (let i = 1; i < this._cbCycleTimes.length; i++) {
                if (this._cbCycleTimes[i] - unique[unique.length - 1] > 1.0) {
                    unique.push(this._cbCycleTimes[i]);
                }
            }
            this._cbCycleTimes = unique;
        }

        // Find active cycle
        let offsetX = 0, offsetY = 0;
        for (const tStart of this._cbCycleTimes) {
            const elapsed = simTime - tStart;
            if (elapsed < 0 || elapsed >= COOLBED_CYCLE_TIME) continue;

            const phase = Math.floor(elapsed / COOLBED_PHASE_TIME);
            const phaseFrac = (elapsed % COOLBED_PHASE_TIME) / COOLBED_PHASE_TIME;

            if (phase === 0) {       // UP
                offsetY = phaseFrac * COOLBED_VERT_TRAVEL;
            } else if (phase === 1) { // FORWARD
                offsetY = COOLBED_VERT_TRAVEL;
                offsetX = phaseFrac * COOLBED_HORIZ_TRAVEL;
            } else if (phase === 2) { // DOWN
                offsetY = COOLBED_VERT_TRAVEL * (1 - phaseFrac);
                offsetX = COOLBED_HORIZ_TRAVEL;
            } else {                  // BACKWARD
                offsetX = COOLBED_HORIZ_TRAVEL * (1 - phaseFrac);
            }
            break; // only one cycle active at a time
        }

        // Base position (same as fixedBeam but at Y=0.05)
        const cbLength = 82 * COOLBED_PITCH;
        beam.position.set(
            X_COOLBED_START + cbLength / 2 + offsetX,
            0.05 + offsetY,
            Z_COOLBED
        );

        // Color tint by phase
        if (offsetY > 0 || offsetX > 0) {
            beam.material.color.setHex(0x44ddff); // active: bright cyan
            beam.material.opacity = 0.85;
        } else {
            beam.material.color.setHex(0x44aadd); // idle: default
            beam.material.opacity = 0.7;
        }
    }
}
