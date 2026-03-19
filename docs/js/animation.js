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

        // Stage 7: On cooling bed (moving through slots)
        if (e.coolbed_entry !== null && t < (e.coolbed_exit || Infinity)) {
            const dur = (e.coolbed_exit || e.coolbed_entry + 24) - e.coolbed_entry;
            const frac = Math.min(1, (t - e.coolbed_entry) / dur);
            const x = X_COOLBED_START + frac * (X_COOLBED_END - X_COOLBED_START);
            return { x, y: 0.35, z: Z_COOLBED };
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
}
