/**
 * 3D models of the CCM plant equipment.
 *
 * Coordinate system:
 *   X = longitudinal (along roller tables, billet flow direction)
 *   Z = transverse (across strands, strand 1 is furthest from coolbed)
 *   Y = up
 *
 * Scale: 1 unit = 1 meter.
 *
 * Layout (top-down view):
 *
 *   Strands (left) → Transport RT → Discharge RT → TC pickup zone
 *        ↓ (TC moves transversely)
 *   Cooling bed (below) → Collecting table → Crane zone → Yard
 */
import * as THREE from 'three';

// Strand colors
export const STRAND_COLORS = [
    0xff4444, // S1 red
    0x44bb44, // S2 green
    0x4488ff, // S3 blue
    0xffaa22, // S4 orange
    0xcc44cc, // S5 purple
    0x44dddd, // S6 cyan
];

// Layout constants (derived from config.py)
const STRAND_PITCH = 1.3;
const TRANSPORT_LENGTH = 25.2;
const DISCHARGE_LENGTH = 13.375;
const INTERM_STOPPER_POS = 7.175;
const COOLBED_SLOTS = 84;
const COOLBED_PITCH = 0.375;
const RT_WIDTH = 0.4;
const BILLET_LEN = 6.0;

// X offsets for each stage
export const X_STRAND = 0;
export const X_TRANSPORT_START = 2;
export const X_TRANSPORT_END = X_TRANSPORT_START + TRANSPORT_LENGTH;
export const X_DISCHARGE_START = X_TRANSPORT_END + 1.5;
export const X_DISCHARGE_END = X_DISCHARGE_START + DISCHARGE_LENGTH;
export const X_INTERM_STOPPER = X_DISCHARGE_START + INTERM_STOPPER_POS;

// Z positions for strands (strand 1 at top, strand 6 near coolbed)
export function strandZ(strandId, numStrands = 6) {
    return (numStrands - strandId) * STRAND_PITCH;
}

// Cooling bed runs along X axis, positioned below the strands in Z
export const Z_COOLBED = -3.0;
export const X_COOLBED_START = X_DISCHARGE_END + 3;
export const X_COOLBED_END = X_COOLBED_START + COOLBED_SLOTS * COOLBED_PITCH;

// Collecting table
export const X_TABLE_START = X_COOLBED_END + 2;
export const X_TABLE_END = X_TABLE_START + 8;

// Yard
export const X_YARD_START = X_TABLE_END + 5;
export const X_YARD_END = X_YARD_START + 40;
export const Z_YARD = Z_COOLBED;

/**
 * Build all static equipment meshes and add to scene.
 * Returns an object with references to dynamic elements (TC, cranes).
 */
export function buildEquipment(scene, numStrands = 6) {
    const group = new THREE.Group();
    const materials = {
        rt: new THREE.MeshStandardMaterial({ color: 0x555566, roughness: 0.6 }),
        rtDark: new THREE.MeshStandardMaterial({ color: 0x444455, roughness: 0.7 }),
        stopper: new THREE.MeshStandardMaterial({ color: 0xdd3333, roughness: 0.4 }),
        stopperGreen: new THREE.MeshStandardMaterial({ color: 0x33aa33, roughness: 0.4 }),
        tc: new THREE.MeshStandardMaterial({ color: 0xddaa22, roughness: 0.3, metalness: 0.4 }),
        coolbed: new THREE.MeshStandardMaterial({ color: 0x3355aa, roughness: 0.5, transparent: true, opacity: 0.6 }),
        table: new THREE.MeshStandardMaterial({ color: 0x22aa88, roughness: 0.5 }),
        crane: new THREE.MeshStandardMaterial({ color: 0xee8822, roughness: 0.3, metalness: 0.5 }),
        yard: new THREE.MeshStandardMaterial({ color: 0x665544, roughness: 0.8 }),
        label: new THREE.MeshBasicMaterial({ color: 0xffffff }),
    };

    // --- Strands (mold exits) ---
    for (let s = 1; s <= numStrands; s++) {
        const z = strandZ(s, numStrands);
        // Mold marker
        const mold = new THREE.Mesh(
            new THREE.BoxGeometry(1.5, 0.8, 0.5),
            new THREE.MeshStandardMaterial({ color: STRAND_COLORS[s - 1], roughness: 0.4 })
        );
        mold.position.set(X_STRAND, 0.4, z);
        mold.castShadow = true;
        group.add(mold);

        // Transport roller table
        const trt = new THREE.Mesh(
            new THREE.BoxGeometry(TRANSPORT_LENGTH, 0.15, RT_WIDTH),
            materials.rt
        );
        trt.position.set(X_TRANSPORT_START + TRANSPORT_LENGTH / 2, 0.08, z);
        trt.receiveShadow = true;
        group.add(trt);

        // Security stopper (at end of transport RT)
        const secStop = new THREE.Mesh(
            new THREE.BoxGeometry(0.3, 0.5, 0.5),
            materials.stopper
        );
        secStop.position.set(X_TRANSPORT_END, 0.25, z);
        group.add(secStop);

        // Discharge roller table
        const drt = new THREE.Mesh(
            new THREE.BoxGeometry(DISCHARGE_LENGTH, 0.15, RT_WIDTH),
            materials.rtDark
        );
        drt.position.set(X_DISCHARGE_START + DISCHARGE_LENGTH / 2, 0.08, z);
        drt.receiveShadow = true;
        group.add(drt);

        // Intermediate stopper
        const intStop = new THREE.Mesh(
            new THREE.BoxGeometry(0.25, 0.45, 0.45),
            materials.stopper
        );
        intStop.position.set(X_INTERM_STOPPER, 0.22, z);
        group.add(intStop);

        // Fixed stopper (end of discharge)
        const fixStop = new THREE.Mesh(
            new THREE.BoxGeometry(0.25, 0.45, 0.45),
            materials.stopper
        );
        fixStop.position.set(X_DISCHARGE_END, 0.22, z);
        group.add(fixStop);
    }

    // --- Transfer car ---
    const tcWidth = (numStrands + 1) * STRAND_PITCH;
    const tc = new THREE.Mesh(
        new THREE.BoxGeometry(2.0, 0.3, 0.8),
        materials.tc
    );
    tc.position.set(X_DISCHARGE_END + 1.5, 0.15, strandZ(1, numStrands));
    tc.castShadow = true;
    group.add(tc);

    // TC rail
    const tcRail = new THREE.Mesh(
        new THREE.BoxGeometry(0.1, 0.05, tcWidth + 6),
        new THREE.MeshStandardMaterial({ color: 0x888855, roughness: 0.5 })
    );
    tcRail.position.set(X_DISCHARGE_END + 1.5, 0.02,
        (strandZ(1, numStrands) + strandZ(numStrands, numStrands)) / 2);
    group.add(tcRail);

    // --- Cooling bed ---
    const cbLength = COOLBED_SLOTS * COOLBED_PITCH;
    const coolbed = new THREE.Mesh(
        new THREE.BoxGeometry(cbLength, 0.2, 4),
        materials.coolbed
    );
    coolbed.position.set(X_COOLBED_START + cbLength / 2, 0.1, Z_COOLBED);
    coolbed.receiveShadow = true;
    group.add(coolbed);

    // Slot lines on cooling bed
    for (let i = 0; i <= COOLBED_SLOTS; i += 4) {
        const line = new THREE.Mesh(
            new THREE.BoxGeometry(0.02, 0.22, 4),
            new THREE.MeshBasicMaterial({ color: 0x4466cc })
        );
        line.position.set(X_COOLBED_START + i * COOLBED_PITCH, 0.11, Z_COOLBED);
        group.add(line);
    }

    // --- Collecting table ---
    const table = new THREE.Mesh(
        new THREE.BoxGeometry(8, 0.25, 5),
        materials.table
    );
    table.position.set(X_TABLE_START + 4, 0.12, Z_COOLBED);
    table.receiveShadow = true;
    group.add(table);

    // --- Crane gantries (2 cranes) ---
    const cranes = [];
    for (let c = 0; c < 2; c++) {
        const craneGroup = new THREE.Group();

        // Bridge beam
        const bridge = new THREE.Mesh(
            new THREE.BoxGeometry(1.0, 0.4, 20),
            materials.crane
        );
        bridge.position.set(0, 8, Z_COOLBED);
        craneGroup.add(bridge);

        // Two legs
        for (const side of [-9, 9]) {
            const leg = new THREE.Mesh(
                new THREE.BoxGeometry(0.3, 8, 0.3),
                materials.crane
            );
            leg.position.set(0, 4, Z_COOLBED + side);
            craneGroup.add(leg);
        }

        // Hook (hanging line)
        const hook = new THREE.Mesh(
            new THREE.CylinderGeometry(0.08, 0.08, 4, 8),
            new THREE.MeshStandardMaterial({ color: 0xcccccc })
        );
        hook.position.set(0, 5.5, Z_COOLBED);
        craneGroup.add(hook);

        craneGroup.position.x = X_TABLE_START + 5 + c * 15;
        cranes.push(craneGroup);
        group.add(craneGroup);
    }

    // --- Billet yard (simplified) ---
    const yard = new THREE.Mesh(
        new THREE.BoxGeometry(40, 0.1, 14),
        materials.yard
    );
    yard.position.set(X_YARD_START + 20, 0.05, Z_YARD);
    yard.receiveShadow = true;
    group.add(yard);

    // Yard row markers
    for (let r = 0; r < 3; r++) {
        const row = new THREE.Mesh(
            new THREE.BoxGeometry(38, 0.12, 3),
            new THREE.MeshStandardMaterial({ color: 0x776655, roughness: 0.7 })
        );
        row.position.set(X_YARD_START + 20, 0.06, Z_YARD - 5 + r * 5);
        group.add(row);
    }

    // --- Labels (using sprite-based text) ---
    addLabel(group, "MOLDS", X_STRAND, 2.0, strandZ(3, numStrands));
    addLabel(group, "TRANSPORT RT", X_TRANSPORT_START + TRANSPORT_LENGTH / 2, 1.5, strandZ(numStrands, numStrands) - 1.5);
    addLabel(group, "DISCHARGE RT", X_DISCHARGE_START + DISCHARGE_LENGTH / 2, 1.5, strandZ(numStrands, numStrands) - 1.5);
    addLabel(group, "TRANSFER CAR", X_DISCHARGE_END + 1.5, 1.5, strandZ(numStrands, numStrands) - 2);
    addLabel(group, "COOLING BED", X_COOLBED_START + cbLength / 2, 2.0, Z_COOLBED + 3);
    addLabel(group, "COLLECTING TABLE", X_TABLE_START + 4, 2.0, Z_COOLBED + 4);
    addLabel(group, "CRANES", X_TABLE_START + 12, 10, Z_COOLBED);
    addLabel(group, "BILLET YARD", X_YARD_START + 20, 2.0, Z_YARD + 8);

    scene.add(group);

    return { tc, cranes, numStrands };
}


function addLabel(parent, text, x, y, z) {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    canvas.width = 512;
    canvas.height = 64;
    ctx.fillStyle = 'rgba(0,0,0,0)';
    ctx.fillRect(0, 0, 512, 64);
    ctx.font = 'bold 32px sans-serif';
    ctx.fillStyle = '#aaaacc';
    ctx.textAlign = 'center';
    ctx.fillText(text, 256, 42);

    const texture = new THREE.CanvasTexture(canvas);
    const sprite = new THREE.Sprite(
        new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false })
    );
    sprite.position.set(x, y, z);
    sprite.scale.set(10, 1.25, 1);
    parent.add(sprite);
}
