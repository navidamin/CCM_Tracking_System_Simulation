/**
 * Three.js scene setup: camera, lights, renderer, controls.
 */
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export function createScene() {
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x1a1a2e);
    renderer.shadowMap.enabled = true;
    document.body.prepend(renderer.domElement);

    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x1a1a2e, 0.003);

    // Camera — isometric-ish perspective
    const camera = new THREE.PerspectiveCamera(
        45, window.innerWidth / window.innerHeight, 0.5, 500
    );
    camera.position.set(30, 35, 45);
    camera.lookAt(15, 0, 5);

    // Controls
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(15, 0, 5);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.maxPolarAngle = Math.PI / 2.1;
    controls.update();

    // Lights
    const ambient = new THREE.AmbientLight(0x404060, 1.2);
    scene.add(ambient);

    const dirLight = new THREE.DirectionalLight(0xfff0e0, 1.5);
    dirLight.position.set(40, 60, 30);
    dirLight.castShadow = true;
    dirLight.shadow.camera.left = -60;
    dirLight.shadow.camera.right = 60;
    dirLight.shadow.camera.top = 40;
    dirLight.shadow.camera.bottom = -40;
    scene.add(dirLight);

    const fillLight = new THREE.DirectionalLight(0x6080ff, 0.3);
    fillLight.position.set(-20, 30, -10);
    scene.add(fillLight);

    // Ground plane
    const ground = new THREE.Mesh(
        new THREE.PlaneGeometry(300, 200),
        new THREE.MeshStandardMaterial({ color: 0x222233, roughness: 0.9 })
    );
    ground.rotation.x = -Math.PI / 2;
    ground.position.set(0, -0.05, 0);
    ground.receiveShadow = true;
    scene.add(ground);

    // Grid helper
    const grid = new THREE.GridHelper(200, 100, 0x333355, 0x2a2a44);
    grid.position.y = -0.04;
    scene.add(grid);

    // Resize handler
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });

    return { scene, camera, renderer, controls };
}
