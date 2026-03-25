/**
 * Entry point — ties scene, equipment, animation, and UI together.
 */
import { createScene } from './scene.js';
import { buildEquipment, STRAND_COLORS } from './equipment.js';
import { AnimationEngine } from './animation.js';
import { UIController } from './ui.js';

const DATA_DIR = 'data/';

async function init() {
    // 1. Scene
    const { scene, camera, renderer, controls } = createScene();

    // 2. UI
    const ui = new UIController();

    // 3. Load manifest
    const manifestResp = await fetch(DATA_DIR + 'manifest.json');
    const manifest = await manifestResp.json();
    ui.populateScenarios(manifest);

    // 4. Equipment & animation (will be rebuilt per scenario)
    let equipment = null;
    const engine = new AnimationEngine(scene);

    // 5. Scenario loader
    async function loadScenario(filename) {
        const resp = await fetch(DATA_DIR + filename);
        const data = await resp.json();

        // Rebuild equipment if strand count changed
        const ns = data.params.strands;
        if (!equipment || equipment.numStrands !== ns) {
            // Remove old equipment
            // Simple approach: we keep equipment static for 6 strands
            // and just reload billets
        }
        if (!equipment) {
            equipment = buildEquipment(scene, ns);
        }

        engine.load(data);
        ui.buildLegend(ns, STRAND_COLORS);
        ui.setScenarioInfo(data.stats);
        ui.simTime = data.params.warmup;
        ui.duration = data.params.duration;
        ui.timeSlider.max = data.params.duration;
        ui.timeSlider.value = ui.simTime;

        // Reset playback
        ui.playing = false;
        ui.btnPlay.textContent = '\u25B6';
    }

    ui.onScenarioChange((file) => loadScenario(file));

    // Load first scenario
    if (manifest.length > 0) {
        await loadScenario(manifest[0].file);
    }

    // 6. Render loop
    let lastTime = performance.now();

    function animate(now) {
        requestAnimationFrame(animate);

        const delta = (now - lastTime) / 1000; // seconds
        lastTime = now;

        // Advance sim time
        ui.tick(delta);

        // Update billets
        const stats = engine.update(ui.simTime, equipment);
        ui.updateStats(stats);

        // Update TC hook vertical position
        if (equipment && equipment.tcHook) {
            const hookY = engine.getTCHookHeight(ui.simTime);
            equipment.tcHook.position.y = hookY;
            // Rod connects frame (Y=1.4) to hook
            equipment.tcRod.position.y = (1.4 + hookY) / 2;
            equipment.tcRod.scale.y = (1.4 - hookY) / 1.1;
        }

        // Update stopper states (color + height)
        engine.updateStoppers(ui.simTime, equipment);

        // Update cooling bed walking beam
        engine.updateCoolingBed(ui.simTime, equipment);

        // Controls
        controls.update();

        renderer.render(scene, camera);
    }

    requestAnimationFrame(animate);
}

init().catch(console.error);
