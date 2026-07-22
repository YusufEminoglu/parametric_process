/* app.js - Parametric Process Studio */
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

// Application State
let scene, camera, renderer, controls, composer;
let raycaster, mouse;
let parcelFeatures = []; // Array of { fid, properties, outerRing, parcelMesh, buildingMesh, setbackMesh, sidewalkMesh, zoningMesh, area, params }
let selectedParcel = null;
let skyDome = null;
let skyUniforms = null;
let pedestrians = []; // Array of { mesh, path, speed, progress, direction }

// Traffic State
let trafficCars = []; // Array of { carMesh, path, speed, progress, laneOffset }
let roadMeshes = []; // Inferred road corridor surfaces/markings between urban blocks
let intersectionMeshes = []; // Roundabouts, crossings, and signal hardware at inferred junctions

// Time Animation State
let isTimeAnimating = false;
let timeAnimationId = null;

// Cinematic Tour State
let isCinematicTour = false;

// 3D Ruler / Measurement Tool State
let isMeasurementMode = false;
let measurementPoints = [];
let tempMeasureLine = null;
let tempMeasureLabel = null;
let savedMeasurements = [];

// Height Dragging State
let heightHandleMesh = null;
let isDraggingHeight = false;
let dragStartHeight = 0;
let dragStartFloors = 0;
let dragIntersectionPlane = null;

// Setback Dragging State
let setbackHandleMesh = null;
let isDraggingSetback = false;
let scaleXHandleMesh = null;
let scaleYHandleMesh = null;
let isDraggingScaleAxis = null;
let dragStartScale = 1;
let dragStartScaleDistance = 1;
let dragScaleCenter = null;
let dragScaleAxis = null;

// Light references
let dirLight, ambientLight;

// Projection variables (local offset)
let centerX = 0;
let centerY = 0;
let groundMesh = null;
let groundTexture = null;

const LARGE_EXTENT_FOCUS_THRESHOLD = 1200;
const DEFAULT_CAMERA_DISTANCE = 320;

// Setup UI Element references
const loadingEl = document.getElementById('loading');
const placeholderEl = document.getElementById('selection-placeholder');
const controlsEl = document.getElementById('editor-controls');
const btnSync = document.getElementById('btn-sync');
const btnCapture = document.getElementById('btn-capture');
const btnExportCsv = document.getElementById('btn-export-csv');
const btnSolveSelected = document.getElementById('btn-solve-selected');
const btnSolveCity = document.getElementById('btn-solve-city');
const btnReload = document.getElementById('btn-reload');
const btnTour = document.getElementById('btn-tour');
const btnMeasure = document.getElementById('btn-measure');
const btnClearMeasure = document.getElementById('hud-btn-clear-measure');
const crsWarningBannerEl = document.getElementById('crs-warning-banner');
const btnGuide = document.getElementById('btn-guide');
const btnGuideInline = document.getElementById('btn-guide-inline');
const btnGuideClose = document.getElementById('btn-guide-close');
const guidePanelEl = document.getElementById('guide-panel');
const guideScrimEl = document.getElementById('guide-scrim');
const inScenarioPreset = document.getElementById('input-scenario-preset');
const btnApplyPreset = document.getElementById('btn-apply-preset');
const scenarioNoteEl = document.getElementById('scenario-note');
const inHeatmapMode = document.getElementById('input-heatmap-mode');
const cityScoreEl = document.getElementById('city-score');
const cityComplianceRateEl = document.getElementById('city-compliance-rate');
const cityGfaEl = document.getElementById('city-gfa');
const cityPopulationEl = document.getElementById('city-population');
const cityCarbonEl = document.getElementById('city-carbon');
const legendTitleEl = document.getElementById('legend-title');
const legendNoteEl = document.getElementById('legend-note');
const toastContainerEl = document.getElementById('toast-container');

// View settings checkbox controls
const toggleBuildingsEl = document.getElementById('toggle-buildings');
const toggleZoningEl = document.getElementById('toggle-zoning');
const toggleSetbacksEl = document.getElementById('toggle-setbacks');
const toggleSidewalksEl = document.getElementById('toggle-sidewalks');
const togglePedestriansEl = document.getElementById('toggle-pedestrians');
const toggleTrafficEl = document.getElementById('toggle-traffic');
const toggleGridEl = document.getElementById('toggle-grid');
const toggleHeightLabelsEl = document.getElementById('toggle-height-labels');

// Input controls
const inTypology = document.getElementById('input-typology');
const inUsage = document.getElementById('input-usage');
const inRoofStyle = document.getElementById('input-roof-style');
const inSetback = document.getElementById('input-setback');
const inFloors = document.getElementById('input-floors');
const inFloorHeight = document.getElementById('input-floorheight');
const inScaleX = document.getElementById('input-scale-x');
const inScaleY = document.getElementById('input-scale-y');
const inMaxBcr = document.getElementById('input-max-bcr');
const inMaxFar = document.getElementById('input-max-far');
const inMaxHeight = document.getElementById('input-max-height');
const inTime = document.getElementById('input-time');
const btnPlayTime = document.getElementById('btn-play-time');

// Stepped Tower Controls
const steppedTowerControlsEl = document.getElementById('stepped-tower-controls');
const inStepbackInterval = document.getElementById('input-stepback-interval');
const inStepbackDepth = document.getElementById('input-stepback-depth');
const lblStepbackInterval = document.getElementById('val-stepback-interval');
const lblStepbackDepth = document.getElementById('val-stepback-depth');

// Label values
const lblSetback = document.getElementById('val-setback');
const lblFloors = document.getElementById('val-floors');
const lblFloorHeight = document.getElementById('val-floorheight');
const lblScaleX = document.getElementById('val-scale-x');
const lblScaleY = document.getElementById('val-scale-y');
const lblMaxBcr = document.getElementById('val-max-bcr');
const lblMaxFar = document.getElementById('val-max-far');
const lblMaxHeight = document.getElementById('val-max-height');
const lblTime = document.getElementById('val-time');

// Metrics
const metFid = document.getElementById('prop-fid');
const metArea = document.getElementById('prop-area');
const metFootprint = document.getElementById('metric-footprint');
const metGfa = document.getElementById('metric-gfa');
const metHeight = document.getElementById('metric-height');
const metZRange = document.getElementById('metric-z-range');
const metBcrLabel = document.getElementById('metric-bcr-label');
const metFarLabel = document.getElementById('metric-far-label');
const metStatus = document.getElementById('metric-status');

// Gauge elements
const bcrFillEl = document.getElementById('gauge-bcr-fill');
const farFillEl = document.getElementById('gauge-far-fill');

// Population Estimator elements
const metUnits = document.getElementById('metric-units');
const metPopulation = document.getElementById('metric-population');
const metDensity = document.getElementById('metric-density');

// Sustainability Indicators elements
const metOsr = document.getElementById('metric-osr');
const metOpenSpace = document.getElementById('metric-open-space');
const metCarbon = document.getElementById('metric-carbon');
const metRunoff = document.getElementById('metric-runoff');
const metPlanScore = document.getElementById('metric-plan-score');
const metConstraintLoad = document.getElementById('metric-constraint-load');

// Apply All button
const btnApplyAll = document.getElementById('btn-apply-all');

// HUD
const hudTotalParcels = document.getElementById('hud-total-parcels');
const hudCrs = document.getElementById('hud-crs');
const hudMaxZ = document.getElementById('hud-max-z');

// Grid reference for toggle
let gridHelper = null;
let heatmapMode = 'score';

const SCENARIO_PRESETS = {
    balanced: {
        label: 'Balanced Growth',
        note: 'Balanced Growth keeps a compact footprint while using most available FAR.',
        apply(item) {
            const area = item.area;
            const usage = area > 1400 ? 'MixedUse' : 'Residential';
            const typology = defaultTypologyForBlock(area, usage, item.outerRing);
            return {
                usage,
                typology,
                roofStyle: defaultRoofStyleFor(usage, typology),
                setback: area > 1200 ? 3.5 : 3.0,
                floors: Math.min(12, Math.max(4, defaultFloorCountForBlock(area, usage) + 1)),
                floorHeight: usage === 'MixedUse' ? 3.2 : 3.0,
                maxBcr: 0.45,
                maxFar: area > 1600 ? 3.2 : 2.5,
                maxHeight: area > 1600 ? 36 : 24
            };
        }
    },
    transit: {
        label: 'Transit-Oriented Mix',
        note: 'Transit-Oriented Mix prioritizes mixed-use podiums, taller massing, and strong FAR utilization.',
        apply(item) {
            const isLarge = item.area >= 1200;
            const typology = isLarge ? 'PodiumTower' : 'SteppedTower';
            return {
                usage: 'MixedUse',
                typology,
                roofStyle: 'Mansard',
                setback: isLarge ? 3.0 : 2.5,
                floors: isLarge ? 14 : 9,
                floorHeight: 3.2,
                maxBcr: 0.60,
                maxFar: isLarge ? 5.5 : 4.0,
                maxHeight: isLarge ? 62 : 42,
                stepbackInterval: 4,
                stepbackDepth: 1.5
            };
        }
    },
    affordable: {
        label: 'Affordable Mid-Rise',
        note: 'Affordable Mid-Rise favors repeatable residential blocks with efficient GFA and stable height limits.',
        apply(item) {
            const typology = item.area >= 1400 ? 'MultiBuildingBlock' : 'Courtyard';
            return {
                usage: 'Residential',
                typology,
                roofStyle: defaultRoofStyleFor('Residential', typology),
                setback: 3.0,
                floors: item.area >= 1400 ? 8 : 6,
                floorHeight: 3.0,
                maxBcr: 0.50,
                maxFar: item.area >= 1400 ? 3.2 : 2.6,
                maxHeight: item.area >= 1400 ? 30 : 24
            };
        }
    },
    green: {
        label: 'Low-Carbon Campus',
        note: 'Low-Carbon Campus lowers height, increases setbacks, and keeps runoff and open-space pressure visible.',
        apply(item) {
            const typology = item.area >= 900 ? 'Courtyard' : 'Slab';
            return {
                usage: 'Civic',
                typology,
                roofStyle: 'Gable',
                setback: 6.0,
                floors: item.area >= 1400 ? 4 : 3,
                floorHeight: 3.4,
                maxBcr: 0.35,
                maxFar: 1.6,
                maxHeight: 18
            };
        }
    },
    park: {
        label: 'Public Realm Upgrade',
        note: 'Public Realm Upgrade converts the selected parcel into open space for civic review scenarios.',
        apply() {
            return {
                usage: 'Park',
                typology: 'Tower',
                roofStyle: 'Hipped',
                setback: 2.0,
                floors: 1,
                floorHeight: 3.0,
                maxBcr: 0.10,
                maxFar: 0.10,
                maxHeight: 4
            };
        }
    }
};

const VALID_USAGES = ['Residential', 'Commercial', 'MixedUse', 'Civic', 'Park'];
const VALID_TYPOLOGIES = ['Tower', 'Slab', 'Courtyard', 'LShape', 'UShape', 'PodiumTower', 'SteppedTower', 'MultiBuildingBlock'];
const VALID_ROOF_STYLES = ['Hipped', 'Gable', 'Mansard', 'Flat'];

// Initialize the 3D scene
function init() {
    // 1. Scene setup
    scene = new THREE.Scene();
    scene.background = new THREE.Color(0xe9f7ff);

    // 2. Sky gradient dome: procedural shader sphere replacing flat background
    const skyGeom = new THREE.SphereGeometry(2000, 32, 32);
    const skyVertShader = `
        varying vec3 vWorldPosition;
        void main() {
            vec4 worldPos = modelMatrix * vec4(position, 1.0);
            vWorldPosition = worldPos.xyz;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
    `;
    const skyFragShader = `
        uniform vec3 uHorizonColor;
        uniform vec3 uZenithColor;
        uniform float uStarIntensity;
        varying vec3 vWorldPosition;

        // Simple pseudo-random for stars
        float hash(vec2 p) {
            return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
        }

        void main() {
            float h = normalize(vWorldPosition).y;
            float t = clamp(h, 0.0, 1.0);
            vec3 sky = mix(uHorizonColor, uZenithColor, t);

            // Star field: tiny bright dots at high elevation
            if (uStarIntensity > 0.01) {
                vec3 dir = normalize(vWorldPosition);
                vec2 starUV = dir.xz / (dir.y + 1.0) * 200.0;
                float star = hash(floor(starUV));
                float brightness = step(0.997, star) * uStarIntensity;
                sky += vec3(brightness);
            }

            gl_FragColor = vec4(sky, 1.0);
        }
    `;
    skyUniforms = {
        uHorizonColor: { value: new THREE.Color(0xf6fbff) },
        uZenithColor:  { value: new THREE.Color(0x9ed8ff) },
        uStarIntensity: { value: 0.0 }
    };
    const skyMat = new THREE.ShaderMaterial({
        vertexShader: skyVertShader,
        fragmentShader: skyFragShader,
        uniforms: skyUniforms,
        side: THREE.BackSide,
        depthWrite: false
    });
    skyDome = new THREE.Mesh(skyGeom, skyMat);
    scene.add(skyDome);

    // 3. Camera setup
    camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 1, 10000);
    camera.position.set(0, 180, 280);

    // 4. Renderer setup
    renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    renderer.setClearColor(0xe9f7ff, 1);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.32;
    document.getElementById('viewport').appendChild(renderer.domElement);

    // 5. Post-Processing Bloom
    composer = new EffectComposer(renderer);
    const renderPass = new RenderPass(scene, camera);
    composer.addPass(renderPass);
    const bloomPass = new UnrealBloomPass(
        new THREE.Vector2(window.innerWidth, window.innerHeight),
        0.3,   // strength
        0.4,   // radius
        0.85   // threshold
    );
    composer.addPass(bloomPass);
    const outputPass = new OutputPass();
    composer.addPass(outputPass);

    // 6. OrbitControls
    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.maxPolarAngle = Math.PI / 2 - 0.02;
    controls.addEventListener('start', () => {
        if (isCinematicTour) {
            isCinematicTour = false;
            if (btnTour) btnTour.classList.remove('active');
        }
    });

    // 7. Lighting
    ambientLight = new THREE.AmbientLight(0xffffff, 1.18);
    scene.add(ambientLight);

    dirLight = new THREE.DirectionalLight(0xffffff, 1.38);
    dirLight.position.set(200, 450, 150);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 2048;
    dirLight.shadow.mapSize.height = 2048;
    dirLight.shadow.camera.near = 0.5;
    dirLight.shadow.camera.far = 1200;
    
    const d = 600;
    dirLight.shadow.camera.left = -d;
    dirLight.shadow.camera.right = d;
    dirLight.shadow.camera.top = d;
    dirLight.shadow.camera.bottom = -d;
    scene.add(dirLight);

    // 8. Ground Terrain Plane with subtle grid texture
    const groundCanvas = document.createElement('canvas');
    groundCanvas.width = 512;
    groundCanvas.height = 512;
    const gCtx = groundCanvas.getContext('2d');
    gCtx.fillStyle = '#d8e6ef';
    gCtx.fillRect(0, 0, 512, 512);
    // Draw subtle grid lines. Each cell is about 10 m.
    gCtx.strokeStyle = 'rgba(15, 23, 42, 0.04)';
    gCtx.lineWidth = 0.5;
    const cellSize = 512 / 24;
    for (let i = 0; i <= 24; i++) {
        const p = i * cellSize;
        gCtx.beginPath(); gCtx.moveTo(p, 0); gCtx.lineTo(p, 512); gCtx.stroke();
        gCtx.beginPath(); gCtx.moveTo(0, p); gCtx.lineTo(512, p); gCtx.stroke();
    }
    groundTexture = new THREE.CanvasTexture(groundCanvas);
    groundTexture.wrapS = THREE.RepeatWrapping;
    groundTexture.wrapT = THREE.RepeatWrapping;
    groundTexture.repeat.set(10, 10);

    const groundGeom = new THREE.PlaneGeometry(2400, 2400);
    groundGeom.rotateX(-Math.PI / 2);
    const groundMat = new THREE.MeshStandardMaterial({
        map: groundTexture,
        color: 0xf1f7fb,
        roughness: 0.95,
        metalness: 0.05
    });
    groundMesh = new THREE.Mesh(groundGeom, groundMat);
    groundMesh.receiveShadow = true;
    groundMesh.position.y = -0.1;
    scene.add(groundMesh);

    // Subtle overlay grid (kept for fine detail but semi-transparent)
    const grid = new THREE.GridHelper(1200, 120, 0xb6c6d8, 0x7a8ba1);
    grid.position.y = -0.05;
    grid.material.opacity = 0.12;
    grid.material.transparent = true;
    grid.visible = toggleGridEl ? toggleGridEl.checked : false;
    scene.add(grid);
    gridHelper = grid;

    // 9. Clear city air: no fog by default.
    scene.fog = null;

    // Build Solar Orbit Arc high in celestial sky
    const arcPoints = [];
    const radius = 3500;
    const segments = 64;
    for (let i = 0; i <= segments; i++) {
        const theta = (i / segments) * Math.PI; // 0 to 180 degrees
        const x = Math.cos(theta + Math.PI) * radius;
        const y = Math.max(100, Math.sin(theta) * radius);
        const z = 800;
        arcPoints.push(new THREE.Vector3(x, y, z));
    }
    const arcGeom = new THREE.BufferGeometry().setFromPoints(arcPoints);
    const arcMat = new THREE.LineDashedMaterial({
        color: 0xeab308,
        dashSize: 40,
        gapSize: 20,
        transparent: true,
        opacity: 0.25
    });
    const solarArc = new THREE.Line(arcGeom, arcMat);
    solarArc.computeLineDistances();
    scene.add(solarArc);
    window.solarArc = solarArc;

    // Build Celestial Sun/Moon Sphere high above ground
    const sunSphereGeom = new THREE.SphereGeometry(35, 16, 16);
    const sunSphereMat = new THREE.MeshBasicMaterial({ color: 0xfef08a });
    const sunSphere = new THREE.Mesh(sunSphereGeom, sunSphereMat);
    sunSphere.position.set(0, 3500, 0); // Position celestial sun high in sky
    scene.add(sunSphere);
    window.sunSphere = sunSphere;
    updateSolarPhysics((inTime && inTime.value) ? parseFloat(inTime.value) : 12.0);

    // 10. Interaction
    raycaster = new THREE.Raycaster();
    mouse = new THREE.Vector2();
    window.addEventListener('click', onDocumentClick);
    window.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
    window.addEventListener('resize', onWindowResize);

    setupInputListeners();

    // 11. Load Data
    loadGeoJSON();

    animate();
}

// Render loop
function animate() {
    requestAnimationFrame(animate);
    
    // Auto orbit camera for Cinematic Tour
    if (isCinematicTour) {
        const offset = new THREE.Vector3().subVectors(camera.position, controls.target);
        const radius = Math.sqrt(offset.x * offset.x + offset.z * offset.z);
        let angle = Math.atan2(offset.z, offset.x);
        angle += 0.002; // slow orbit speed
        camera.position.x = controls.target.x + radius * Math.cos(angle);
        camera.position.z = controls.target.z + radius * Math.sin(angle);
    }
    
    // Update controls
    controls.update();

    // Update traffic cars positions
    updateTraffic();

    // Update pedestrian positions
    updatePedestrians();

    // Update 3D ruler tool labels screen positions
    updateMeasurementLabels();
    updateHeightLabels();

    composer.render();
}

// Resize handler
function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
    composer.setSize(window.innerWidth, window.innerHeight);
}

// Set up UI input controls event handlers
function setupInputListeners() {
    const triggerUpdate = () => {
        if (!selectedParcel) return;
        
        selectedParcel.modified = true;

        // Read slider values
        if (inSetback) selectedParcel.params.setback = parseFloat(inSetback.value);
        if (inFloors) selectedParcel.params.floors = parseInt(inFloors.value);
        if (inFloorHeight) selectedParcel.params.floorHeight = parseFloat(inFloorHeight.value);
        if (inScaleX) selectedParcel.params.scaleX = parseFloat(inScaleX.value);
        if (inScaleY) selectedParcel.params.scaleY = parseFloat(inScaleY.value);
        if (inTypology) selectedParcel.params.typology = inTypology.value;
        if (inUsage) selectedParcel.params.usage = inUsage.value;
        if (inRoofStyle) selectedParcel.params.roofStyle = inRoofStyle.value;
        
        if (inStepbackInterval) selectedParcel.params.stepbackInterval = parseInt(inStepbackInterval.value);
        if (inStepbackDepth) selectedParcel.params.stepbackDepth = parseFloat(inStepbackDepth.value);

        // Zoning limits
        if (inMaxBcr) selectedParcel.params.maxBcr = parseFloat(inMaxBcr.value);
        if (inMaxFar) selectedParcel.params.maxFar = parseFloat(inMaxFar.value);
        if (inMaxHeight) selectedParcel.params.maxHeight = parseFloat(inMaxHeight.value);
        selectedParcel.params = sanitizeParcelParams(selectedParcel.params, selectedParcel.area, selectedParcel.outerRing);

        // Update labels
        if (lblSetback) lblSetback.textContent = selectedParcel.params.setback.toFixed(1);
        if (lblFloors) lblFloors.textContent = selectedParcel.params.floors;
        if (lblFloorHeight) lblFloorHeight.textContent = selectedParcel.params.floorHeight.toFixed(1);
        if (lblScaleX && selectedParcel.params.scaleX != null) lblScaleX.textContent = selectedParcel.params.scaleX.toFixed(2);
        if (lblScaleY && selectedParcel.params.scaleY != null) lblScaleY.textContent = selectedParcel.params.scaleY.toFixed(2);
        if (lblMaxBcr && selectedParcel.params.maxBcr != null) lblMaxBcr.textContent = selectedParcel.params.maxBcr.toFixed(2);
        if (lblMaxFar && selectedParcel.params.maxFar != null) lblMaxFar.textContent = selectedParcel.params.maxFar.toFixed(1);
        if (lblMaxHeight && selectedParcel.params.maxHeight != null) lblMaxHeight.textContent = selectedParcel.params.maxHeight.toFixed(1);
        
        if (lblStepbackInterval && selectedParcel.params.stepbackInterval != null) lblStepbackInterval.textContent = selectedParcel.params.stepbackInterval;
        if (lblStepbackDepth && selectedParcel.params.stepbackDepth != null) lblStepbackDepth.textContent = selectedParcel.params.stepbackDepth.toFixed(1);

        // Show/hide stepped tower controls
        if (steppedTowerControlsEl) {
            if (selectedParcel.params.typology === 'SteppedTower') {
                steppedTowerControlsEl.classList.remove('hidden');
            } else {
                steppedTowerControlsEl.classList.add('hidden');
            }
        }

        // Rebuild meshes
        rebuildParcel3D(selectedParcel);
        updateDashboard(selectedParcel);
        updateCitySummary();
        updateScaleHandles();

        // Update height handle position or remove it if park
        if (selectedParcel.params.usage !== 'Park') {
            if (heightHandleMesh) {
                updateHeightHandle();
            } else {
                let cx = 0, cy = 0;
                const ring = selectedParcel.outerRing;
                ring.forEach(pt => { cx += pt.x; cy += pt.y; });
                cx /= ring.length;
                cy /= ring.length;
                const height = selectedParcel.params.floors * selectedParcel.params.floorHeight;
                spawnHeightHandle(cx, cy, height);
            }
        } else {
            removeHeightHandle();
        }
    };

    const triggerTimeUpdate = () => {
        if (isTimeAnimating) {
            toggleTimeAnimation(); // Stop playing if user manually drags slider
        }
        const tVal = (inTime && inTime.value) ? parseFloat(inTime.value) : 12.0;
        const hours = Math.floor(tVal);
        const mins = Math.floor((tVal % 1) * 60).toString().padStart(2, '0');
        if (lblTime) lblTime.textContent = `${hours}:${mins}`;

        updateSolarPhysics(tVal);
    };

    if (inSetback) inSetback.addEventListener('input', triggerUpdate);
    if (inFloors) inFloors.addEventListener('input', triggerUpdate);
    if (inFloorHeight) inFloorHeight.addEventListener('input', triggerUpdate);
    if (inScaleX) inScaleX.addEventListener('input', triggerUpdate);
    if (inScaleY) inScaleY.addEventListener('input', triggerUpdate);
    if (inTypology) inTypology.addEventListener('change', triggerUpdate);
    if (inUsage) inUsage.addEventListener('change', triggerUpdate);
    if (inRoofStyle) inRoofStyle.addEventListener('change', triggerUpdate);
    
    if (inStepbackInterval) inStepbackInterval.addEventListener('input', triggerUpdate);
    if (inStepbackDepth) inStepbackDepth.addEventListener('input', triggerUpdate);
    
    if (inMaxBcr) inMaxBcr.addEventListener('input', triggerUpdate);
    if (inMaxFar) inMaxFar.addEventListener('input', triggerUpdate);
    if (inMaxHeight) inMaxHeight.addEventListener('input', triggerUpdate);

    if (inTime) inTime.addEventListener('input', triggerTimeUpdate);

    // Play Solar animation button
    if (btnPlayTime) {
        btnPlayTime.addEventListener('click', toggleTimeAnimation);
    }

    btnSync.addEventListener('click', syncToQGIS);
    btnCapture.addEventListener('click', captureViewport);
    if (btnExportCsv) {
        btnExportCsv.addEventListener('click', exportPlanningReport);
    }
    if (btnSolveSelected) {
        btnSolveSelected.addEventListener('click', () => {
            if (selectedParcel) {
                optimizeParcelZoning(selectedParcel);
                rebuildParcel3D(selectedParcel);
                selectParcel(selectedParcel);
                updateDashboard(selectedParcel);
                updateCitySummary();
                showToast("Selected parcel optimized against its active zoning limits.", "success");
            } else {
                showToast("Select a parcel first, then run Auto-Solve Selected Parcel.", "warning");
            }
        });
    }
    if (btnSolveCity) {
        btnSolveCity.addEventListener('click', solveCityLayout);
    }

    const btnPpud = document.getElementById('btn-ppud');
    if (btnPpud) {
        btnPpud.addEventListener('click', runPpudPipeline);
    }

    // Cinematic Tour Toggle
    if (btnTour) {
        btnTour.addEventListener('click', () => {
            isCinematicTour = !isCinematicTour;
            btnTour.classList.toggle('active', isCinematicTour);
        });
    }

    // Toggle 3D Ruler / Measurement Mode
    if (btnMeasure) {
        btnMeasure.addEventListener('click', () => {
            isMeasurementMode = !isMeasurementMode;
            btnMeasure.classList.toggle('active', isMeasurementMode);
            
            if (isMeasurementMode) {
                // De-select active parcel to prevent interference
                deselectParcel();
                // Ensure cinematic tour is off
                if (isCinematicTour) {
                    isCinematicTour = false;
                    if (btnTour) btnTour.classList.remove('active');
                }
                
                // Initialize temp lines/labels if they don't exist yet
                initTemporaryMeasurementAssets();
            } else {
                // Disable measurement mode
                document.body.style.cursor = 'default';
                if (tempMeasureLine) tempMeasureLine.visible = false;
                if (tempMeasureLabel) tempMeasureLabel.style.display = 'none';
                measurementPoints = [];
            }
        });
    }

    // Clear Measurements
    if (btnClearMeasure) {
        btnClearMeasure.addEventListener('click', clearAllMeasurements);
    }

    const btnGuideTop = document.getElementById('btn-guide-top');
    if (btnGuide) {
        btnGuide.addEventListener('click', openGuidePanel);
    }
    if (btnGuideTop) {
        btnGuideTop.addEventListener('click', openGuidePanel);
    }
    if (btnGuideInline) {
        btnGuideInline.addEventListener('click', openGuidePanel);
    }
    if (btnGuideClose) {
        btnGuideClose.addEventListener('click', closeGuidePanel);
    }
    if (guideScrimEl) {
        guideScrimEl.addEventListener('click', closeGuidePanel);
    }

    if (inScenarioPreset) {
        inScenarioPreset.addEventListener('change', () => {
            const preset = SCENARIO_PRESETS[inScenarioPreset.value] || SCENARIO_PRESETS.balanced;
            if (scenarioNoteEl) scenarioNoteEl.textContent = preset.note;
        });
    }
    if (btnApplyPreset) {
        btnApplyPreset.addEventListener('click', () => {
            if (!selectedParcel) {
                showToast("Select a parcel before applying a scenario preset.", "warning");
                return;
            }
            applyScenarioPreset(selectedParcel, inScenarioPreset ? inScenarioPreset.value : 'balanced');
        });
    }
    if (inHeatmapMode) {
        inHeatmapMode.addEventListener('change', () => {
            heatmapMode = inHeatmapMode.value;
            updateHeatmapLegend();
            refreshParcelHeatmap();
        });
    }

    // Reload Data button
    if (btnReload) {
        btnReload.addEventListener('click', reloadData);
    }

    // View toggles listeners
    const onVisibilityChange = () => {
        updateLayersVisibility();
    };

    if (toggleBuildingsEl) toggleBuildingsEl.addEventListener('change', onVisibilityChange);
    if (toggleZoningEl) toggleZoningEl.addEventListener('change', onVisibilityChange);
    if (toggleSetbacksEl) toggleSetbacksEl.addEventListener('change', onVisibilityChange);
    if (toggleSidewalksEl) toggleSidewalksEl.addEventListener('change', onVisibilityChange);
    if (togglePedestriansEl) togglePedestriansEl.addEventListener('change', onVisibilityChange);
    if (toggleTrafficEl) toggleTrafficEl.addEventListener('change', onVisibilityChange);
    if (toggleGridEl) toggleGridEl.addEventListener('change', onVisibilityChange);
    if (toggleHeightLabelsEl) toggleHeightLabelsEl.addEventListener('change', updateHeightLabels);

    // Apply All button
    if (btnApplyAll) {
        btnApplyAll.addEventListener('click', applyToAllParcels);
    }

    // Keyboard shortcuts
    window.addEventListener('keydown', handleKeyboardShortcuts);
}

function isUiEventTarget(target) {
    return !!(
        target.closest('#control-dock') ||
        target.closest('.hud-bar') ||
        target.closest('.loading-screen') ||
        target.closest('#guide-panel') ||
        target.closest('#guide-scrim')
    );
}

function openGuidePanel() {
    if (!guidePanelEl) return;
    guidePanelEl.classList.remove('hidden');
    if (guideScrimEl) {
        guideScrimEl.classList.remove('hidden');
    }
}

function closeGuidePanel() {
    if (guidePanelEl) {
        guidePanelEl.classList.add('hidden');
    }
    if (guideScrimEl) {
        guideScrimEl.classList.add('hidden');
    }
}

function showToast(message, tone = 'success') {
    if (!toastContainerEl) {
        console.log(message);
        return;
    }
    const toast = document.createElement('div');
    toast.className = `toast ${tone}`;
    toast.textContent = message;
    toastContainerEl.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(8px)';
        setTimeout(() => toast.remove(), 220);
    }, 3600);
}

function clamp01(value) {
    if (!Number.isFinite(value)) return 0;
    return Math.max(0, Math.min(1, value));
}

function clampNumber(value, min, max, fallback) {
    const parsed = Number.isFinite(value) ? value : fallback;
    return Math.max(min, Math.min(max, parsed));
}

function readProp(props, names) {
    if (!props) return undefined;
    for (const name of names) {
        if (Object.prototype.hasOwnProperty.call(props, name)) {
            const value = props[name];
            if (value !== null && value !== undefined && String(value).trim() !== '' && String(value).toLowerCase() !== 'null') {
                return value;
            }
        }
    }

    const lowerNames = names.map(name => name.toLowerCase());
    for (const [key, value] of Object.entries(props)) {
        if (!lowerNames.includes(key.toLowerCase())) continue;
        if (value !== null && value !== undefined && String(value).trim() !== '' && String(value).toLowerCase() !== 'null') {
            return value;
        }
    }
    return undefined;
}

function parseFiniteNumber(value, fallback) {
    if (value === null || value === undefined) return fallback;
    if (typeof value === 'string') {
        const trimmed = value.trim();
        if (!trimmed || trimmed.toLowerCase() === 'null') return fallback;
        value = trimmed.replace(',', '.');
    }
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
}

function parseNumberProp(props, names, fallback) {
    return parseFiniteNumber(readProp(props, names), fallback);
}

function parseIntegerProp(props, names, fallback) {
    const parsed = parseFiniteNumber(readProp(props, names), fallback);
    return Number.isFinite(parsed) ? Math.round(parsed) : fallback;
}

function normalizeUsage(value, fallback = 'Residential') {
    if (value === null || value === undefined || String(value).trim() === '') return fallback;
    const raw = String(value).trim();
    const compact = raw.toLowerCase().replace(/[\s_\-]+/g, '');
    const exact = VALID_USAGES.find(usage => usage.toLowerCase() === compact);
    if (exact) return exact;
    const usageMap = {
        residential: 'Residential',
        housing: 'Residential',
        konut: 'Residential',
        commercial: 'Commercial',
        retail: 'Commercial',
        office: 'Commercial',
        ticaret: 'Commercial',
        mixed: 'MixedUse',
        mixeduse: 'MixedUse',
        karma: 'MixedUse',
        civic: 'Civic',
        institutional: 'Civic',
        public: 'Civic',
        donati: 'Civic',
        park: 'Park',
        greenspace: 'Park',
        yesilalan: 'Park',
        open: 'Park',
        openspace: 'Park'
    };
    return usageMap[compact] || fallback;
}

function normalizeTypology(value, fallback = 'Tower') {
    if (value === null || value === undefined || String(value).trim() === '') return fallback;
    const compact = String(value).trim().toLowerCase().replace(/[\s_\-\/]+/g, '');
    const exact = VALID_TYPOLOGIES.find(typology => typology.toLowerCase() === compact);
    if (exact) return exact;
    const typologyMap = {
        tower: 'Tower',
        slab: 'Slab',
        row: 'Slab',
        courtyard: 'Courtyard',
        avlu: 'Courtyard',
        l: 'LShape',
        lshape: 'LShape',
        u: 'UShape',
        ushape: 'UShape',
        podium: 'PodiumTower',
        podiumtower: 'PodiumTower',
        stepped: 'SteppedTower',
        steppedtower: 'SteppedTower',
        multibuilding: 'MultiBuildingBlock',
        multibuildingblock: 'MultiBuildingBlock',
        block: 'MultiBuildingBlock'
    };
    return typologyMap[compact] || fallback;
}

function normalizeRoofStyle(value, fallback = 'Hipped') {
    if (value === null || value === undefined || String(value).trim() === '') return fallback;
    const compact = String(value).trim().toLowerCase().replace(/[\s_\-]+/g, '');
    const exact = VALID_ROOF_STYLES.find(style => style.toLowerCase() === compact);
    return exact || fallback;
}

function sanitizeParcelParams(params, area, ring) {
    const usage = normalizeUsage(params.usage, 'Residential');
    const defaultTypology = defaultTypologyForBlock(area, usage, ring);
    const typology = normalizeTypology(params.typology, defaultTypology);
    const floorHeight = clampNumber(parseFiniteNumber(params.floorHeight, 3.0), 2.5, 6.0, 3.0);
    const defaultFloors = defaultFloorCountForBlock(area, usage);
    const floors = usage === 'Park'
        ? 1
        : clampNumber(Math.round(parseFiniteNumber(params.floors, defaultFloors)), 1, 30, defaultFloors);
    const roofStyle = normalizeRoofStyle(params.roofStyle, defaultRoofStyleFor(usage, typology));

    return {
        setback: clampNumber(parseFiniteNumber(params.setback, 3.0), 0, 15, 3.0),
        floors,
        floorHeight,
        typology,
        usage,
        roofStyle,
        scaleX: clampNumber(parseFiniteNumber(params.scaleX, 1.0), 0.35, 1.60, 1.0),
        scaleY: clampNumber(parseFiniteNumber(params.scaleY, 1.0), 0.35, 1.60, 1.0),
        stepbackInterval: clampNumber(Math.round(parseFiniteNumber(params.stepbackInterval, 4)), 2, 10, 4),
        stepbackDepth: clampNumber(parseFiniteNumber(params.stepbackDepth, 1.5), 0.5, 5.0, 1.5),
        maxBcr: clampNumber(parseFiniteNumber(params.maxBcr, 0.45), 0.1, 0.9, 0.45),
        maxFar: clampNumber(parseFiniteNumber(params.maxFar, 2.5), 0.5, 8.0, 2.5),
        maxHeight: clampNumber(parseFiniteNumber(params.maxHeight, 18.0), 3.0, 120.0, 18.0)
    };
}

function scoreClass(score) {
    if (score >= 76) return 'score-good';
    if (score >= 55) return 'score-watch';
    return 'score-poor';
}

function calculateConstraintLoad(metrics, item) {
    const maxBcr = Math.max(0.01, item.params.maxBcr || 0.45);
    const maxFar = Math.max(0.01, item.params.maxFar || 2.5);
    const maxHeight = Math.max(0.01, item.params.maxHeight || 18);
    const heightLoad = metrics.usage === 'Park' ? 0 : metrics.height / maxHeight;
    return Math.max(metrics.bcr / maxBcr, metrics.far / maxFar, heightLoad);
}

function calculatePlanScore(metrics, item) {
    const maxBcr = Math.max(0.01, item.params.maxBcr || 0.45);
    const maxFar = Math.max(0.01, item.params.maxFar || 2.5);
    const maxHeight = Math.max(0.01, item.params.maxHeight || 18);
    const farUtilization = clamp01(metrics.far / maxFar);
    const openSpaceShare = clamp01(metrics.openSpaceArea / Math.max(1, item.area));
    const runoffScore = clamp01(1 - metrics.runoff);
    const densityScore = metrics.usage === 'Park'
        ? 0.82
        : clamp01(metrics.densityPpHa / 650);

    const bcrExcess = Math.max(0, (metrics.bcr - maxBcr) / maxBcr);
    const farExcess = Math.max(0, (metrics.far - maxFar) / maxFar);
    const heightExcess = metrics.usage === 'Park' ? 0 : Math.max(0, (metrics.height - maxHeight) / maxHeight);
    const zeroFootprintPenalty = metrics.usage !== 'Park' && metrics.footprintArea <= 0 ? 28 : 0;
    const violationPenalty = Math.min(55, bcrExcess * 28 + farExcess * 34 + heightExcess * 26 + zeroFootprintPenalty);

    const score = 42
        + farUtilization * 24
        + openSpaceShare * 16
        + runoffScore * 10
        + densityScore * 8
        - violationPenalty;

    return Math.round(Math.max(0, Math.min(100, score)));
}

function formatCompactNumber(value, unit = '') {
    const abs = Math.abs(value);
    let text;
    if (abs >= 1000000) text = `${(value / 1000000).toFixed(1)}M`;
    else if (abs >= 10000) text = `${Math.round(value / 1000)}k`;
    else if (abs >= 1000) text = `${(value / 1000).toFixed(1)}k`;
    else text = Math.round(value).toLocaleString();
    return unit ? `${text} ${unit}` : text;
}

function lerpColorHex(colorA, colorB, t) {
    const a = new THREE.Color(colorA);
    const b = new THREE.Color(colorB);
    return a.lerp(b, clamp01(t)).getHex();
}

// High-Divergence Multi-Stop Color Scale (7 vibrant stops from Deep Indigo to Crimson Red)
function getDivergentHeatmapColor(t) {
    const clampT = Math.max(0, Math.min(1, t));
    if (clampT < 0.16) return lerpColorHex(0x1e1b4b, 0x06b6d4, clampT / 0.16);         // Navy Blue -> Cyan
    if (clampT < 0.33) return lerpColorHex(0x06b6d4, 0x10b981, (clampT - 0.16) / 0.17);  // Cyan -> Emerald Green
    if (clampT < 0.50) return lerpColorHex(0x10b981, 0x84cc16, (clampT - 0.33) / 0.17);  // Emerald -> Lime Yellow
    if (clampT < 0.66) return lerpColorHex(0x84cc16, 0xf59e0b, (clampT - 0.50) / 0.16);  // Lime -> Amber Gold
    if (clampT < 0.83) return lerpColorHex(0xf59e0b, 0xf97316, (clampT - 0.66) / 0.17);  // Amber -> Neon Orange
    return lerpColorHex(0xf97316, 0xdc2626, (clampT - 0.83) / 0.17);                    // Orange -> Crimson Red
}

// Spatial Inverse Distance Weighting (IDW) Kernel Interpolation Engine
function computeIdwHeatmapValue(targetItem, extractorFn, powerExp = 2.0, radiusMax = 120.0) {
    if (!parcelFeatures || parcelFeatures.length <= 1) return extractorFn(targetItem);
    
    const targetPt = getParcelCentroid(targetItem);
    let sumWeightedValue = 0.0;
    let sumWeights = 0.0;
    
    for (let i = 0; i < parcelFeatures.length; i++) {
        const neighbor = parcelFeatures[i];
        const rawVal = extractorFn(neighbor);
        
        if (neighbor === targetItem) {
            // Local building weight (primary 1m height impact)
            const selfWeight = 4.0;
            sumWeightedValue += selfWeight * rawVal;
            sumWeights += selfWeight;
            continue;
        }
        
        const nPt = getParcelCentroid(neighbor);
        const dist = Math.hypot(targetPt.x - nPt.x, targetPt.y - nPt.y);
        
        if (dist <= radiusMax) {
            const weight = 1.0 / Math.pow(Math.max(1.0, dist), powerExp);
            sumWeightedValue += weight * rawVal;
            sumWeights += weight;
        }
    }
    
    return sumWeights > 0 ? (sumWeightedValue / sumWeights) : extractorFn(targetItem);
}

function getRawParcelHeight(item) {
    const fl = item.params?.floors || 4;
    const fh = item.params?.floorHeight || 3.0;
    const setback = item.params?.setback || 0;
    return (fl * fh) + (setback * 0.2); // Meter-precise total building height
}

function colorForParcel(item) {
    const metrics = calculateParcelMetrics(item);
    if (selectedParcel === item && heatmapMode === 'compliance') {
        return metrics.violated ? 0xb91c1c : 0x0d9488;
    }
    
    const isPark = item.params?.usage === 'Park' || item.params?.usage === 'Tree' || item.params?.usage === 'GreenSpace';
    const isAsphalt = item.params?.usage === 'Asphalt' || item.params?.usage === 'Road' || item.params?.usage === 'Parking';
    const isGreenRoof = item.params?.roofStyle === 'Flat' || isPark;

    if (isPark && heatmapMode !== 'density' && heatmapMode !== 'carbon' && heatmapMode !== 'solair' && heatmapMode !== 'solar' && heatmapMode !== 'utci' && heatmapMode !== 'svf' && heatmapMode !== 'uhi') {
        return 0x047857; // Rich Emerald Green for Parks/Trees
    }

    if (heatmapMode === 'svf') {
        // IDW Kernel Sky View Factor (SVF) Simulation with 1m height & canopy shade sensitivity
        const idwSvf = computeIdwHeatmapValue(item, (target) => {
            const tPark = target.params?.usage === 'Park' || target.params?.usage === 'Tree';
            if (tPark) return 0.88; // Open tree canopy sky view
            const h = getRawParcelHeight(target);
            const w = Math.sqrt(target.area || 500);
            const canyonRatio = h / Math.max(4, w * 0.35);
            return Math.max(0.10, Math.min(0.96, 1.0 / Math.sqrt(1 + canyonRatio * canyonRatio)));
        });
        return getDivergentHeatmapColor(1.0 - idwSvf); // Deep Indigo for canyon (low SVF), Sky Teal for open plaza/park
    }

    if (heatmapMode === 'uhi') {
        // IDW Kernel UHI Simulation: Asphalt Heat Trap (+6.8°C) vs Park Evapotranspirative Cooling (-8.5°C)
        const idwUhi = computeIdwHeatmapValue(item, (target) => {
            const tPark = target.params?.usage === 'Park' || target.params?.usage === 'Tree';
            const tAsphalt = target.params?.usage === 'Asphalt' || target.params?.usage === 'Road' || target.params?.usage === 'Parking';
            const tGreenRoof = target.params?.roofStyle === 'Flat' || tPark;
            
            const h = getRawParcelHeight(target);
            const bcr = (target.params?.footprintArea || 200) / Math.max(1, target.area || 500);
            
            // Material Evapotranspiration vs Solar Heat Sink Delta
            const matDelta = tPark ? -8.5 : (tAsphalt ? +6.8 : (tGreenRoof ? -3.5 : 0.0));
            return 26.0 + 1.2 + (h * 0.35) + (bcr * 4.5) + matDelta;
        });
        return getDivergentHeatmapColor((idwUhi - 22.0) / 24.0); // Cooled Sage (22°C) to Severe UHI Crimson (46°C)
    }

    if (heatmapMode === 'solair') {
        // IDW Kernel Sol-Air Surface Temp (°C): Asphalt (58°C Crimson) vs Park/Tree (22°C Emerald)
        const idwSolAir = computeIdwHeatmapValue(item, (target) => {
            const tPark = target.params?.usage === 'Park' || target.params?.usage === 'Tree';
            const tAsphalt = target.params?.usage === 'Asphalt' || target.params?.usage === 'Road' || target.params?.usage === 'Parking';
            
            if (tPark) return 22.5; // Cool evapotranspirative tree canopy
            if (tAsphalt) return 56.5; // Black asphalt solar thermal absorption surge (56.5°C Crimson)
            
            const h = getRawParcelHeight(target);
            const bcr = (target.params?.footprintArea || 200) / Math.max(1, target.area || 500);
            return 22.0 + (h * 0.65) + (bcr * 18.0); // 1m height adds 0.65°C radiant temp
        });
        return getDivergentHeatmapColor((idwSolAir - 22.0) / 36.0); // 22°C (Park) to 58°C (Asphalt/Tower)
    }

    if (heatmapMode === 'solar') {
        // IDW Kernel Solar Irradiance (kWh/m²) Simulation
        const idwSolar = computeIdwHeatmapValue(item, (target) => {
            const tPark = target.params?.usage === 'Park' || target.params?.usage === 'Tree';
            if (tPark) return 320; // Filtered canopy irradiance
            const h = getRawParcelHeight(target);
            return 200 + (h * 28.0) + ((target.params?.floors || 4) * 15.0); // Sensitive to 1m height increment
        });
        return getDivergentHeatmapColor((idwSolar - 200) / 1300); // 200 to 1500 kWh/m²
    }

    if (heatmapMode === 'utci') {
        // IDW Kernel UTCI Outdoor Thermal Stress Index (°C)
        const idwUtci = computeIdwHeatmapValue(item, (target) => {
            const tPark = target.params?.usage === 'Park' || target.params?.usage === 'Tree';
            const tAsphalt = target.params?.usage === 'Asphalt' || target.params?.usage === 'Road' || target.params?.usage === 'Parking';
            if (tPark) return 19.2; // Comfortable outdoor shade
            if (tAsphalt) return 44.5; // Extreme asphalt heat stress
            
            const h = getRawParcelHeight(target);
            const bcr = (target.params?.footprintArea || 200) / Math.max(1, target.area || 500);
            return 18.0 + (h * 0.52) + (bcr * 12.0);
        });
        return getDivergentHeatmapColor((idwUtci - 18.0) / 28.0); // 18°C (Park) to 46°C (Asphalt)
    }

    if (heatmapMode === 'density') {
        const idwDensity = computeIdwHeatmapValue(item, (target) => {
            const targetMetrics = calculateParcelMetrics(target);
            return targetMetrics.densityPpHa;
        });
        return getDivergentHeatmapColor(idwDensity / 800);
    }

    if (heatmapMode === 'carbon') {
        const idwCarbon = computeIdwHeatmapValue(item, (target) => {
            const targetMetrics = calculateParcelMetrics(target);
            return targetMetrics.gfa > 0 ? targetMetrics.carbon / targetMetrics.gfa : 0;
        });
        return getDivergentHeatmapColor(idwCarbon / 0.08);
    }

    if (heatmapMode === 'compliance') {
        return metrics.violated ? 0x7f1d1d : 0x334155;
    }

    // Default Score Heatmap with IDW Spatial Height & Density Influence
    const idwScore = computeIdwHeatmapValue(item, (target) => {
        const targetMetrics = calculateParcelMetrics(target);
        return targetMetrics.planScore !== undefined ? targetMetrics.planScore : calculatePlanScore(targetMetrics, target);
    });
    return getDivergentHeatmapColor(idwScore / 100);
}

function refreshParcelHeatmap() {
    parcelFeatures.forEach(item => {
        // Tint the ground parcel mesh
        if (item.parcelMesh && item.parcelMesh.material) {
            item.parcelMesh.material.color.setHex(colorForParcel(item));
        }
        // Tint the 3D building massing
        const heatColor = new THREE.Color(colorForParcel(item));
        if (item.buildingMesh) {
            item.buildingMesh.traverse(child => {
                if (child.isMesh && child.material) {
                    const mats = Array.isArray(child.material) ? child.material : [child.material];
                    mats.forEach(m => {
                        if (m.isRoofMesh) return; // Preserve pitched roof material style
                        if (m.color && !m.emissiveMap) {
                            // Tint solid-color materials (courtyard, base, etc.)
                            m.color.copy(heatColor).multiplyScalar(0.7);
                        } else if (m.color && m.emissiveMap) {
                            // Blend heatmap tint into wall material
                            m.color.lerp(heatColor, 0.5);
                        }
                    });
                }
            });
        }
    });
}

function updateHeatmapLegend() {
    if (!legendTitleEl || !legendNoteEl) return;
    const labels = {
        score: ['PlanX Performance Score', 'Red underperforms (<55), amber is watchlist, green is optimal (85+).'],
        svf: ['🌌 Sky View Factor (SVF)', 'Indigo/Violet is enclosed street canyon (low SVF < 0.3), sky blue is open plaza (high SVF > 0.85).'],
        uhi: ['🌿 Urban Heat Island & Vegetation Cooling', 'Emerald/Sage is vegetation cooled (-3.5°C), yellow/amber is moderate, crimson is severe UHI heat island trap.'],
        solair: ['🔥 Sol-Air Heat Surface Temp (°C)', 'Deep cyan is cool (22°C), yellow is warm (34°C), crimson is peak radiant heat (48°C).'],
        solar: ['☀️ Annual Solar Irradiance (kWh/m²)', 'Dark blue is shaded courtyard, yellow/amber is high PV solar exposure.'],
        utci: ['🌡️ UTCI Microclimate Heat Stress (°C)', 'Green is neutral thermal comfort, orange/red is severe outdoor heat stress.'],
        compliance: ['Zoning Compliance Map', 'Slate is fully compliant, red indicates active BCR/FAR/Height conflict.'],
        density: ['Urban Density (PpHa)', 'Blue is low-density, amber is mid-rise, violet is high-density tower.'],
        carbon: ['Embodied & Operational Carbon', 'Emerald is low-carbon timber/green roof, red is heavy carbon footprint.']
    };
    const selected = labels[heatmapMode] || labels.score;
    legendTitleEl.textContent = selected[0];
    legendNoteEl.textContent = selected[1];
}

function updateCitySummary() {
    if (!parcelFeatures || parcelFeatures.length === 0) {
        if (cityScoreEl) cityScoreEl.textContent = '-';
        return;
    }

    const metricsList = parcelFeatures.map(item => calculateParcelMetrics(item));
    const compliantCount = metricsList.filter(metrics => !metrics.violated).length;
    const totalGfa = metricsList.reduce((sum, metrics) => sum + metrics.gfa, 0);
    const totalPopulation = metricsList.reduce((sum, metrics) => sum + metrics.population, 0);
    const totalCarbon = metricsList.reduce((sum, metrics) => sum + metrics.carbon, 0);
    const totalOpenSpace = metricsList.reduce((sum, metrics) => sum + metrics.openSpaceArea, 0);
    const maxZ = metricsList.reduce((max, metrics) => Math.max(max, metrics.height || 0), 0);
    const avgScore = Math.round(metricsList.reduce((sum, metrics) => sum + metrics.planScore, 0) / metricsList.length);
    const complianceRate = Math.round((compliantCount / metricsList.length) * 100);

    if (cityScoreEl) {
        cityScoreEl.textContent = String(avgScore);
        cityScoreEl.className = scoreClass(avgScore);
    }
    if (cityComplianceRateEl) cityComplianceRateEl.textContent = `${complianceRate}%`;
    if (cityGfaEl) cityGfaEl.textContent = formatCompactNumber(totalGfa, 'sqm');
    if (cityPopulationEl) cityPopulationEl.textContent = formatCompactNumber(totalPopulation);
    if (cityCarbonEl) cityCarbonEl.textContent = formatCompactNumber(totalCarbon, 't');
    if (hudMaxZ) hudMaxZ.textContent = `${maxZ.toFixed(1)} m`;

    window.planxCitySummary = {
        score: avgScore,
        compliantCount,
        parcelCount: parcelFeatures.length,
        complianceRate,
        totalGfa,
        totalPopulation,
        totalCarbon,
        totalOpenSpace,
        maxZ
    };
    refreshParcelHeatmap();
}

function applyScenarioPreset(item, presetKey) {
    const preset = SCENARIO_PRESETS[presetKey] || SCENARIO_PRESETS.balanced;
    const updates = preset.apply(item);
    item.params = {
        ...item.params,
        ...updates
    };
    item.modified = true;
    rebuildParcel3D(item);
    selectParcel(item);
    updateDashboard(item);
    updateCitySummary();
    showToast(`${preset.label} applied to parcel ${item.fid}.`, "success");
}

function focusParcelCamera(item, options = {}) {
    if (!item || !camera || !controls) return;
    const metrics = calculateParcelMetrics(item);
    const bounds = getRingBounds(item.outerRing);
    const maxDim = Math.max(bounds.width, bounds.depth, 18);
    const height = Math.max(metrics.height, 8);
    const target = new THREE.Vector3(bounds.cx, Math.min(height * 0.45, 32), -bounds.cy);
    const distance = Math.max(55, Math.min(420, maxDim * 2.2 + height * 1.8));
    const currentDir = new THREE.Vector3().subVectors(camera.position, controls.target);
    if (currentDir.lengthSq() < 0.001) currentDir.set(0.55, 0.42, 0.95);
    currentDir.normalize();
    currentDir.y = Math.max(0.34, currentDir.y);
    currentDir.normalize();

    controls.target.copy(target);
    camera.position.copy(target).add(currentDir.multiplyScalar(distance));
    controls.update();

    if (options.toast) {
        showToast(`Focused parcel ${item.fid}: Z top ${metrics.height.toFixed(1)} m.`, "success");
    }
}

// Update lights and sky theme based on solar time of day
function updateSolarPhysics(timeVal) {
    // Math model of sun orbit path
    const angle = ((timeVal - 6) / 16) * Math.PI; // map 6:00-22:00 to 0-180 degrees
    const isNight = timeVal < 7.5 || timeVal > 19.5;

    // Celestial Dome Orbit position (far out in the sky, offset by site center)
    const radius = 3500;
    const sunX = Math.cos(angle + Math.PI) * radius;
    const sunY = Math.sin(angle) * radius;
    const sunZ = 800;

    dirLight.position.set(sunX, Math.max(100, sunY), sunZ);

    // Update Sun/Moon sphere mesh high in celestial sky dome
    if (window.sunSphere) {
        if (isNight || sunY < 20) {
            window.sunSphere.visible = false;
        } else {
            window.sunSphere.visible = true;
            window.sunSphere.position.set(sunX, sunY, sunZ);
            window.sunSphere.material.color.setHex(0xfef08a); // glowing yellow celestial sun
            window.sunSphere.scale.setScalar(1.5);
        }
    }

    // Update sky dome gradient and stars
    if (skyUniforms) {
        if (isNight) {
            scene.background = new THREE.Color(0x020617);
            if (renderer) renderer.setClearColor(0x020617, 1);
            skyUniforms.uHorizonColor.value.setHex(0x020208);
            skyUniforms.uZenithColor.value.setHex(0x000005);
            skyUniforms.uStarIntensity.value = 0.9;
        } else {
            scene.background = new THREE.Color(0xfaf6f0);
            if (renderer) renderer.setClearColor(0xfaf6f0, 1);
            skyUniforms.uHorizonColor.value.setHex(0xf3ece2);
            skyUniforms.uZenithColor.value.setHex(0xe2f2ef);
            skyUniforms.uStarIntensity.value = 0.0;
        }
    }

    if (isNight) {
        ambientLight.color.setHex(0x1e1b4b); // Dim indigo light
        ambientLight.intensity = 0.25;
        dirLight.intensity = 0.05; // Dim moon-like sun
    } else {
        // Daylight Mode
        ambientLight.color.setHex(0xffffff);
        ambientLight.intensity = 1.18;
        
        // Solar intensity peaks at noon
        const peakFactor = Math.sin(angle);
        dirLight.intensity = 0.92 + peakFactor * 0.7;
    }

    // Update active building emission light and streetlights visibility
    parcelFeatures.forEach(item => {
        // Toggle building window glow at night
        if (item.buildingMesh) {
            item.buildingMesh.traverse(child => {
                if (child.isMesh && Array.isArray(child.material)) {
                    const wallMaterial = child.material[1];
                    if (wallMaterial && wallMaterial.emissiveMap) {
                        wallMaterial.emissiveIntensity = isNight ? 1.0 : 0.0;
                    }
                }
            });
        }

        // Toggle streetlight bulb visibility
        if (item.sidewalkMesh) {
            item.sidewalkMesh.traverse(child => {
                if (child.userData && child.userData.isStreetlightBulb) {
                    child.visible = isNight;
                }
            });
        }
    });

    // Toggle headlights on traffic cars
    trafficCars.forEach(car => {
        car.carMesh.traverse(child => {
            if (child.userData && (child.userData.isHeadlight || child.userData.isTaillight)) {
                child.visible = isNight;
            }
        });
    });
}

function defaultTypologyForBlock(area, usage = 'Residential', ring = null) {
    if (usage === 'Park') return 'Tower';
    let aspect = 1;
    if (ring && ring.length >= 3) {
        const ob = getOrientedBounds(ring);
        const minDim = Math.max(1, Math.min(ob.W, ob.H));
        const maxDim = Math.max(ob.W, ob.H);
        aspect = maxDim / minDim;
    }
    if (area >= 1800) return 'MultiBuildingBlock';
    if (area >= 1100) return aspect > 2.0 ? 'Slab' : 'Courtyard';
    if (area >= 650) return aspect > 1.8 ? 'Slab' : 'LShape';
    return 'Tower';
}

function defaultFloorCountForBlock(area, usage = 'Residential') {
    if (usage === 'Park') return 1;
    if (usage === 'Commercial') return area >= 1600 ? 8 : 6;
    if (usage === 'MixedUse') return area >= 1800 ? 7 : 5;
    if (usage === 'Civic') return 4;
    if (area >= 2400) return 6;
    if (area >= 1200) return 5;
    return 4;
}

function defaultRoofStyleFor(usage = 'Residential', typology = 'Tower') {
    if (usage === 'Park') return 'Hipped';
    if (typology === 'Slab') return 'Gable';
    if (typology === 'Courtyard' || typology === 'LShape' || typology === 'UShape') return 'Hipped';
    if (typology === 'PodiumTower' || typology === 'SteppedTower' || typology === 'MultiBuildingBlock') return 'Mansard';
    if (usage === 'Commercial' || usage === 'MixedUse') return 'Mansard';
    if (usage === 'Civic') return 'Gable';
    return 'Hipped';
}

function roofStyleForItem(item) {
    const params = item.params || {};
    return params.roofStyle || defaultRoofStyleFor(params.usage, params.typology);
}

// Mockup GeoJSON for Offline Demo Mode
const mockupGeoJSON = {
    type: "FeatureCollection",
    crs_is_geographic: false,
    crs: {
        properties: {
            name: "EPSG:3857"
        }
    },
    features: [
        {
            type: "Feature",
            id: 1,
            properties: {
                fid: 1,
                setback: 3.0,
                floors: 6,
                floor_h: 3.2,
                typology: "MultiBuildingBlock",
                usage: "MixedUse",
                roof_style: "Mansard",
                stepback_i: 3,
                stepback_d: 1.5,
                max_bcr: 0.5,
                max_far: 3.0,
                max_height: 25.0
            },
            geometry: {
                type: "Polygon",
                coordinates: [[
                    [-30, -30],
                    [30, -30],
                    [30, 30],
                    [-30, 30],
                    [-30, -30]
                ]]
            }
        },
        {
            type: "Feature",
            id: 2,
            properties: {
                fid: 2,
                setback: 2.0,
                floors: 3,
                floor_h: 3.0,
                typology: "Courtyard",
                usage: "Residential",
                roof_style: "Hipped",
                max_bcr: 0.4,
                max_far: 1.5,
                max_height: 12.0
            },
            geometry: {
                type: "Polygon",
                coordinates: [[
                    [50, -50],
                    [110, -50],
                    [110, 10],
                    [50, 10],
                    [50, -50]
                ]]
            }
        },
        {
            type: "Feature",
            id: 3,
            properties: {
                fid: 3,
                setback: 4.0,
                floors: 1,
                floor_h: 3.5,
                typology: "Tower",
                usage: "Park",
                roof_style: "Hipped",
                max_bcr: 0.1,
                max_far: 0.1,
                max_height: 4.0
            },
            geometry: {
                type: "Polygon",
                coordinates: [[
                    [-110, -50],
                    [-50, -50],
                    [-50, 10],
                    [-110, 10],
                    [-110, -50]
                ]]
            }
        },
        {
            type: "Feature",
            id: 4,
            properties: {
                fid: 4,
                setback: 3.0,
                floors: 10,
                floor_h: 3.0,
                typology: "PodiumTower",
                usage: "Commercial",
                roof_style: "Mansard",
                max_bcr: 0.6,
                max_far: 5.0,
                max_height: 35.0
            },
            geometry: {
                type: "Polygon",
                coordinates: [[
                    [-30, 50],
                    [30, 50],
                    [30, 110],
                    [-30, 110],
                    [-30, 50]
                ]]
            }
        }
    ]
};

// Fetch exported layer GeoJSON from local Python server
async function loadGeoJSON() {
    try {
        const response = await fetch('/data.geojson');
        if (!response.ok) throw new Error("Could not load data");
        
        const data = await response.json();
        parseGeoJSON(data);
        
        loadingEl.style.opacity = 0;
        setTimeout(() => loadingEl.classList.add('hidden'), 500);
    } catch (e) {
        console.warn("Could not reach QGIS server, falling back to Demo Mockup layer.", e);
        
        showFallbackScene('Offline Demo Mode: Loaded procedural mockup parcels. Start the plugin server in QGIS to connect live.');
        
        loadingEl.style.opacity = 0;
        setTimeout(() => loadingEl.classList.add('hidden'), 500);
    }
}

function showDataWarning(message, tone = 'warning') {
    if (!crsWarningBannerEl) return;
    crsWarningBannerEl.className = 'warning-banner';
    crsWarningBannerEl.style.background = tone === 'error'
        ? 'linear-gradient(135deg, #dc2626, #991b1b)'
        : 'linear-gradient(135deg, #d97706, #b45309)';
    crsWarningBannerEl.classList.remove('hidden');
    const warningText = crsWarningBannerEl.querySelector('.warning-text');
    if (warningText) {
        warningText.innerHTML = `<strong>${message}</strong>`;
    }
}

function showFallbackScene(reason) {
    console.warn(`PlanX fallback city loaded: ${reason}`);
    parseGeoJSON(mockupGeoJSON, { allowFallback: false, fallbackReason: reason });
    showDataWarning(reason);
    if (window.planxDebug) {
        window.planxDebug.fallbackReason = reason;
    }
    return false;
}

function normalizePlanRing(points) {
    const clean = [];
    points.forEach(pt => {
        if (!Number.isFinite(pt.x) || !Number.isFinite(pt.y)) return;
        const prev = clean[clean.length - 1];
        if (!prev || Math.hypot(pt.x - prev.x, pt.y - prev.y) > 0.001) {
            clean.push(pt);
        }
    });

    if (clean.length > 2) {
        const first = clean[0];
        const last = clean[clean.length - 1];
        if (Math.hypot(first.x - last.x, first.y - last.y) <= 0.001) {
            clean.pop();
        }
    }
    return clean;
}

function buildFeatureMeshesSafely(item) {
    try {
        buildParcelGround(item);
        buildSidewalk(item);
        rebuildParcel3D(item);
        return;
    } catch (err) {
        console.error("PlanX feature build failed; retrying with safe tower fallback.", item.fid, err);
    }

    try {
        item.params.typology = 'Tower';
        item.params.roofStyle = 'Flat';
        item.params.setback = Math.min(item.params.setback || 3.0, 2.0);
        if (!item.parcelMesh) buildParcelGround(item);
        rebuildParcel3D(item);
    } catch (fallbackErr) {
        console.error("PlanX fallback build failed; keeping parcel ground only.", item.fid, fallbackErr);
    }
}

function extractOuterRingCoordinates(feature) {
    if (!feature || !feature.geometry) return null;
    const geometry = feature.geometry;

    if (geometry.type === 'Polygon') {
        return Array.isArray(geometry.coordinates) ? geometry.coordinates[0] : null;
    }

    if (geometry.type === 'MultiPolygon' && Array.isArray(geometry.coordinates)) {
        let bestRing = null;
        let bestArea = 0;
        geometry.coordinates.forEach(poly => {
            const ring = poly && poly[0];
            if (!Array.isArray(ring) || ring.length < 4) return;
            const area = Math.abs(calculatePolygonArea(ring.map(coord => ({
                x: Array.isArray(coord) ? Number(coord[0]) : NaN,
                y: Array.isArray(coord) ? Number(coord[1]) : NaN
            }))));
            if (area > bestArea) {
                bestArea = area;
                bestRing = ring;
            }
        });
        return bestRing;
    }

    return null;
}

function collectRenderableFeatures(data) {
    if (!data || !Array.isArray(data.features)) return [];

    return data.features
        .map((feature, index) => {
            const coords = extractOuterRingCoordinates(feature);
            if (!Array.isArray(coords) || coords.length < 4) return null;

            const cleanCoords = coords
                .map(coord => Array.isArray(coord) ? [Number(coord[0]), Number(coord[1])] : [NaN, NaN])
                .filter(coord => Number.isFinite(coord[0]) && Number.isFinite(coord[1]));

            if (cleanCoords.length < 4) return null;
            return { feature, index, coords: cleanCoords };
        })
        .filter(Boolean);
}

function calculateCoordinateBounds(renderableFeatures) {
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;

    renderableFeatures.forEach(entry => {
        entry.coords.forEach(coord => {
            minX = Math.min(minX, coord[0]);
            maxX = Math.max(maxX, coord[0]);
            minY = Math.min(minY, coord[1]);
            maxY = Math.max(maxY, coord[1]);
        });
    });

    if (![minX, maxX, minY, maxY].every(Number.isFinite)) return null;
    if (Math.abs(maxX - minX) < 0.001 || Math.abs(maxY - minY) < 0.001) return null;

    return { minX, maxX, minY, maxY };
}

function getRingBounds(ring) {
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    ring.forEach(pt => {
        minX = Math.min(minX, pt.x);
        maxX = Math.max(maxX, pt.x);
        minY = Math.min(minY, pt.y);
        maxY = Math.max(maxY, pt.y);
    });
    return {
        minX,
        maxX,
        minY,
        maxY,
        width: maxX - minX,
        depth: maxY - minY,
        cx: (minX + maxX) / 2,
        cy: (minY + maxY) / 2
    };
}

function buildFallbackFootprintRing(ring, requestedSetback = 0) {
    if (!ring || ring.length < 3) return null;
    const ob = getOrientedBounds(ring);
    if (!Number.isFinite(ob.W) || !Number.isFinite(ob.H) || ob.W <= 0.2 || ob.H <= 0.2) return null;

    const minDim = Math.min(ob.W, ob.H);
    const safeMargin = Math.max(0, Math.min(parseFiniteNumber(requestedSetback, 0), minDim * 0.28));
    let halfW = (ob.W / 2) - safeMargin;
    let halfH = (ob.H / 2) - safeMargin;

    if (!Number.isFinite(halfW) || halfW < 0.35) halfW = Math.max(0.35, ob.W * 0.34);
    if (!Number.isFinite(halfH) || halfH < 0.35) halfH = Math.max(0.35, ob.H * 0.34);

    halfW = Math.min(halfW, ob.W * 0.46);
    halfH = Math.min(halfH, ob.H * 0.46);

    const localCorners = [
        { x: -halfW, y: -halfH },
        { x: halfW, y: -halfH },
        { x: halfW, y: halfH },
        { x: -halfW, y: halfH }
    ];

    return localCorners.map(pt => ({
        x: ob.cx + pt.x * ob.ux + pt.y * ob.nx,
        y: ob.cy + pt.x * ob.uy + pt.y * ob.ny
    }));
}

function resolveBuildableRing(item, requestedSetback) {
    const setback = Math.max(0, parseFiniteNumber(requestedSetback, 0));
    const candidates = [setback, setback * 0.75, setback * 0.5, setback * 0.25, Math.min(1.0, setback), 0];
    const seen = new Set();

    for (const candidate of candidates) {
        const rounded = Math.max(0, Math.round(candidate * 100) / 100);
        if (seen.has(rounded)) continue;
        seen.add(rounded);
        const ring = offsetPolygonRing(item.outerRing, rounded);
        if (ring && ring.length >= 3 && calculatePolygonArea(ring) > 0.05) {
            return {
                ring,
                effectiveSetback: rounded,
                usedFallback: rounded !== setback
            };
        }
    }

    const fallbackRing = buildFallbackFootprintRing(item.outerRing, setback);
    if (fallbackRing && fallbackRing.length >= 3 && calculatePolygonArea(fallbackRing) > 0.05) {
        return {
            ring: fallbackRing,
            effectiveSetback: 0,
            usedFallback: true
        };
    }

    return {
        ring: null,
        effectiveSetback: setback,
        usedFallback: true
    };
}

function scaleRingInLocalAxes(ring, scaleX = 1, scaleY = 1) {
    if (!ring || ring.length < 3) return ring;
    const sx = clampNumber(parseFiniteNumber(scaleX, 1), 0.35, 1.60, 1);
    const sy = clampNumber(parseFiniteNumber(scaleY, 1), 0.35, 1.60, 1);
    if (Math.abs(sx - 1) < 0.001 && Math.abs(sy - 1) < 0.001) return ring;

    const ob = getOrientedBounds(ring);
    return ring.map(pt => {
        const rx = pt.x - ob.cx;
        const ry = pt.y - ob.cy;
        const lx = rx * ob.ux + ry * ob.uy;
        const ly = rx * ob.nx + ry * ob.ny;
        return {
            x: ob.cx + (lx * sx) * ob.ux + (ly * sy) * ob.nx,
            y: ob.cy + (lx * sx) * ob.uy + (ly * sy) * ob.ny
        };
    });
}

function resizeGroundForCity(maxDim) {
    const groundSize = Math.max(2400, Math.min(80000, maxDim * 2.4));
    if (groundMesh) {
        const scale = groundSize / 2400;
        groundMesh.scale.set(scale, 1, scale);
    }
    if (groundTexture) {
        const repeats = Math.max(10, groundSize / 240);
        groundTexture.repeat.set(repeats, repeats);
        groundTexture.needsUpdate = true;
    }
    if (gridHelper) {
        const gridScale = groundSize / 1200;
        gridHelper.scale.set(gridScale, 1, gridScale);
    }
}

function chooseCameraFocus(maxDim) {
    if (parcelFeatures.length === 0) {
        return {
            target: new THREE.Vector3(0, 0, 0),
            focusDim: DEFAULT_CAMERA_DISTANCE
        };
    }

    if (maxDim <= LARGE_EXTENT_FOCUS_THRESHOLD) {
        return {
            target: new THREE.Vector3(0, 0, 0),
            focusDim: Math.max(160, maxDim)
        };
    }

    const focusItem = parcelFeatures
        .slice()
        .sort((a, b) => {
            const ba = getRingBounds(a.outerRing);
            const bb = getRingBounds(b.outerRing);
            const da = Math.hypot(ba.cx, ba.cy);
            const db = Math.hypot(bb.cx, bb.cy);
            return da - db || b.area - a.area;
        })[0];
    const bounds = getRingBounds(focusItem.outerRing);
    return {
        target: new THREE.Vector3(bounds.cx, 0, -bounds.cy),
        focusDim: Math.max(120, bounds.width, bounds.depth)
    };
}

function fitCameraToCity(bounds) {
    const maxDim = Math.max(bounds.maxX - bounds.minX, bounds.maxY - bounds.minY, 1);
    const focus = chooseCameraFocus(maxDim);
    const focusDim = Math.max(120, focus.focusDim);
    const distance = Math.max(220, Math.min(Math.max(focusDim * 2.4, DEFAULT_CAMERA_DISTANCE), 1800));

    camera.near = 0.5;
    camera.far = Math.max(10000, maxDim * 5, distance * 8);
    camera.updateProjectionMatrix();
    camera.position.set(
        focus.target.x + distance * 0.55,
        distance * 0.62,
        focus.target.z + distance * 0.95
    );

    controls.target.copy(focus.target);
    controls.maxDistance = Math.max(2000, maxDim * 3);
    controls.update();

    resizeGroundForCity(maxDim);

    if (dirLight) {
        dirLight.position.set(focus.target.x + 200, Math.max(450, distance * 1.5), focus.target.z + 150);
        dirLight.shadow.camera.far = Math.max(1200, maxDim * 3, distance * 4);
        const shadowExtent = Math.max(600, Math.min(5000, Math.max(maxDim, focusDim) * 1.2));
        dirLight.shadow.camera.left = -shadowExtent;
        dirLight.shadow.camera.right = shadowExtent;
        dirLight.shadow.camera.top = shadowExtent;
        dirLight.shadow.camera.bottom = -shadowExtent;
        dirLight.shadow.camera.updateProjectionMatrix();
    }

    return { maxDim, focusDim, distance };
}

function updateSceneDebug(bounds, fallbackReason = null) {
    const buildingCount = parcelFeatures.filter(item => !!item.buildingMesh).length;
    const parcelGroundCount = parcelFeatures.filter(item => !!item.parcelMesh).length;
    const buildingHeights = parcelFeatures.map(item => {
        const params = sanitizeParcelParams(item.params || {}, item.area || 0, item.outerRing || []);
        return params.usage === 'Park' ? 0 : params.floors * params.floorHeight;
    });
    window.planxDebug = {
        ...(window.planxDebug || {}),
        parcelFeatures: parcelFeatures.length,
        parcelGroundCount,
        buildingCount,
        maxBuildingHeight: buildingHeights.length ? Math.max(...buildingHeights) : 0,
        fallbackFootprints: parcelFeatures.filter(item => item.usedFootprintFallback).length,
        roadMeshes: roadMeshes.length,
        intersectionMeshes: intersectionMeshes.length,
        trafficCars: trafficCars.length,
        bounds,
        camera: {
            position: camera ? camera.position.toArray() : null,
            target: controls ? controls.target.toArray() : null,
            far: camera ? camera.far : null
        },
        fallbackReason
    };
}

// Parse GeoJSON geometries and center coordinates
function parseGeoJSON(data, options = {}) {
    const allowFallback = options.allowFallback !== false;
    const renderableFeatures = collectRenderableFeatures(data);
    const bounds = calculateCoordinateBounds(renderableFeatures);

    if (renderableFeatures.length === 0 || !bounds) {
        if (allowFallback) {
            return showFallbackScene('QGIS returned no renderable polygon features, so a demo city was loaded instead of a blank grid.');
        }
        clearScene();
        hudTotalParcels.textContent = "0";
        if (placeholderEl) {
            placeholderEl.innerHTML = "<strong>No features found in the active layer.</strong><br><br>Please draw polygon features (parcels/building blocks) in QGIS first, then click <strong>Reload Data from QGIS</strong>.";
        }
        updateSceneDebug(null, options.fallbackReason || 'No renderable polygon features');
        return false;
    }

    // Clear existing scene elements and memory/resources
    clearScene();

    // Reset default placeholder message
    if (placeholderEl) {
        placeholderEl.innerHTML = "Click a parcel in the 3D scene to inspect it, tune planning controls, and send the result back to QGIS.";
    }

    // Check if layer CRS is geographic
    const isGeographic = !!data.crs_is_geographic;
    if (crsWarningBannerEl) {
        if (isGeographic) {
            crsWarningBannerEl.classList.remove('hidden');
        } else {
            crsWarningBannerEl.classList.add('hidden');
        }
    }

    hudTotalParcels.textContent = renderableFeatures.length;
    if (data.crs && data.crs.properties && data.crs.properties.name) {
        const crsName = data.crs.properties.name.split("::").pop();
        if (hudCrs) {
            hudCrs.textContent = crsName;
        }
    }

    centerX = (bounds.minX + bounds.maxX) / 2;
    centerY = (bounds.minY + bounds.maxY) / 2;

    // 2. Parse features
    renderableFeatures.forEach(entry => {
        const f = entry.feature;
        const fid = f.id !== undefined ? f.id : entry.index;
        const props = f.properties || {};

        // Convert coordinates to local meters
        const localPoints = normalizePlanRing(entry.coords.map(pt => {
            return { x: pt[0] - centerX, y: pt[1] - centerY };
        }));

        if (localPoints.length < 3) return;

        // Calculate parcel area
        const area = calculatePolygonArea(localPoints);
        if (!Number.isFinite(area) || area <= 0.01) return;
        const usage = normalizeUsage(readProp(props, ['usage', 'use', 'landuse', 'land_use', 'kullanim', 'fonksiyon']), 'Residential');
        const typology = normalizeTypology(readProp(props, ['typology', 'type', 'building_type', 'form']), defaultTypologyForBlock(area, usage, localPoints));
        const floorHeight = parseNumberProp(props, ['floor_h', 'floor_height', 'floorheight', 'kat_yuk', 'kat_yuksekligi'], 3.0);
        const heightMeters = parseNumberProp(props, ['height_m', 'height', 'z_top', 'yukseklik', 'hmax'], null);
        const defaultFloors = Number.isFinite(heightMeters) && heightMeters > 0
            ? Math.max(1, Math.round(heightMeters / Math.max(2.5, floorHeight)))
            : defaultFloorCountForBlock(area, usage);

        // Initial params (fall back to layer attributes if existing)
        const params = sanitizeParcelParams({
            setback: parseNumberProp(props, ['setback', 'setback_m', 'cekme'], 3.0),
            floors: parseIntegerProp(props, ['floors', 'floor_count', 'kat', 'kat_adedi', 'kat_sayisi', 'n_kat'], defaultFloors),
            floorHeight,
            typology,
            usage,
            roofStyle: readProp(props, ['roof_style', 'roof', 'roofstyle']),
            scaleX: parseNumberProp(props, ['scale_x', 'mass_x', 'x_scale', 'width_scale'], 1.0),
            scaleY: parseNumberProp(props, ['scale_y', 'mass_y', 'y_scale', 'depth_scale'], 1.0),
            stepbackInterval: parseIntegerProp(props, ['stepback_i', 'stepback_interval'], 4),
            stepbackDepth: parseNumberProp(props, ['stepback_d', 'stepback_depth'], 1.5),
            // Zoning constraints
            maxBcr: parseNumberProp(props, ['max_bcr', 'bcr_max', 'emsal_taban'], 0.45),
            maxFar: parseNumberProp(props, ['max_far', 'far_max', 'emsal', 'kaks'], 2.5),
            maxHeight: parseNumberProp(props, ['max_height', 'height_limit', 'hmax', 'z_limit'], 18.0)
        }, area, localPoints);

        const item = {
            fid,
            properties: props,
            outerRing: localPoints,
            area,
            params,
            modified: false,
            parcelMesh: null,
            buildingMesh: null,
            setbackMesh: null,
            sidewalkMesh: null,
            zoningMesh: null
        };

        parcelFeatures.push(item);
        buildFeatureMeshesSafely(item);
    });

    if (parcelFeatures.length === 0) {
        if (allowFallback) {
            return showFallbackScene('QGIS polygons could not be converted into valid 3D footprints, so a demo city was loaded instead of a blank grid.');
        }
        updateSceneDebug(bounds, options.fallbackReason || 'No valid footprints after parsing');
        return false;
    }

    // Generate Animated Traffic on road tracks (minimal default)
    try {
        generateTrafficCars();
        // Keep only first 4 cars for minimal default
        if (trafficCars.length > 4) {
            for (let i = 4; i < trafficCars.length; i++) {
                if (trafficCars[i].carMesh) {
                    scene.remove(trafficCars[i].carMesh);
                    disposeObject3D(trafficCars[i].carMesh);
                }
            }
            trafficCars = trafficCars.slice(0, 4);
        }
    } catch (err) {
        console.error("PlanX traffic/intersection generation failed; keeping buildings visible.", err);
        window.planxDebug = { roadCorridors: [], intersections: [], trafficCars: 0, trafficError: String(err) };
    }

    const fit = fitCameraToCity(bounds);
    updateSceneDebug({ ...bounds, maxDim: fit.maxDim, focusDim: fit.focusDim }, options.fallbackReason || null);
    updateHeatmapLegend();
    updateCitySummary();
    return true;
}

// Dynamic color updates for parcel grounds representing zoning compliance
function updateParcelGroundColor(item, hasViolation) {
    if (!item.parcelMesh || !item.parcelMesh.material) return;

    if (heatmapMode !== 'compliance') {
        item.parcelMesh.material.color.setHex(colorForParcel(item));
        return;
    }

    let colorHex = 0x334155;

    if (item.params.usage === 'Park') {
        colorHex = 0x064e3b; // soft forest green for public parks
    } else if (selectedParcel === item) {
        colorHex = hasViolation ? 0xb91c1c : 0x0d9488; // active selection: bright red vs bright teal
    } else {
        colorHex = hasViolation ? 0x7f1d1d : 0x334155; // inactive: burgundy vs default slate
    }
    
    item.parcelMesh.material.color.setHex(colorHex);
}

// Render parcel boundary lines and ground surface
function buildParcelGround(item) {
    const shape = new THREE.Shape();
    item.outerRing.forEach((pt, i) => {
        if (i === 0) shape.moveTo(pt.x, pt.y);
        else shape.lineTo(pt.x, pt.y);
    });

    const geom = new THREE.ShapeGeometry(shape);
    geom.rotateX(-Math.PI / 2);

    const mat = new THREE.MeshStandardMaterial({
        color: 0x334155,
        roughness: 0.9,
        polygonOffset: true,
        polygonOffsetFactor: 1,
        polygonOffsetUnits: 1
    });

    const mesh = new THREE.Mesh(geom, mat);
    mesh.receiveShadow = true;
    mesh.userData = { parcelItem: item };
    scene.add(mesh);
    item.parcelMesh = mesh;

    // Draw boundary line
    const borderPoints = item.outerRing.map(pt => new THREE.Vector3(pt.x, 0.05, -pt.y));
    borderPoints.push(borderPoints[0].clone());
    
    const lineGeom = new THREE.BufferGeometry().setFromPoints(borderPoints);
    const lineMat = new THREE.LineBasicMaterial({ color: 0x475569, linewidth: 2 });
    const line = new THREE.Line(lineGeom, lineMat);
    scene.add(line);
}

// Build concrete sidewalk and place procedural streetlights along curbs
function buildSidewalk(item) {
    if (item.sidewalkMesh) {
        scene.remove(item.sidewalkMesh);
        item.sidewalkMesh.geometry.dispose();
    }

    // Outer sidewalk polygon (shifted 2.0 meters outward)
    const outerSidewalk = offsetPolygonRing(item.outerRing, -2.0);
    if (!outerSidewalk) return;

    const shape = new THREE.Shape();
    outerSidewalk.forEach((pt, i) => {
        if (i === 0) shape.moveTo(pt.x, pt.y);
        else shape.lineTo(pt.x, pt.y);
    });

    // Subtract parcel shape to make a frame
    const hole = new THREE.Path();
    item.outerRing.forEach((pt, i) => {
        if (i === 0) hole.moveTo(pt.x, pt.y);
        else hole.lineTo(pt.x, pt.y);
    });
    shape.holes.push(hole);

    // Extrude sidewalk by 0.15m height
    const geom = new THREE.ExtrudeGeometry(shape, { depth: 0.15, bevelEnabled: false });
    geom.rotateX(-Math.PI / 2);

    const mat = new THREE.MeshStandardMaterial({
        color: 0x52525b, // concrete grey
        roughness: 0.8
    });

    const mesh = new THREE.Mesh(geom, mat);
    mesh.receiveShadow = true;
    mesh.position.y = -0.05;
    scene.add(mesh);
    item.sidewalkMesh = mesh;

    // Place Procedural Streetlights along curb corners
    const numLights = Math.max(2, Math.floor(item.outerRing.length / 2));
    const step = Math.floor(item.outerRing.length / numLights);

    for (let i = 0; i < numLights; i++) {
        const idx = (i * step) % item.outerRing.length;
        const pt = item.outerRing[idx];
        
        // Offset light/tree slightly outwards onto sidewalk
        const ptNext = item.outerRing[(idx + 1) % item.outerRing.length];
        const dx = ptNext.x - pt.x;
        const dy = ptNext.y - pt.y;
        const len = Math.sqrt(dx*dx + dy*dy);
        if (len < 0.01) continue;
        const nx = -dy / len;
        const ny = dx / len;

        const lx = pt.x + nx * 1.0;
        const lz = - (pt.y + ny * 1.0);

        if (i % 2 === 0) {
            // Build streetlight pole
            const poleGeom = new THREE.CylinderGeometry(0.1, 0.15, 6, 8);
            const poleMat = new THREE.MeshStandardMaterial({ color: 0x3f3f46, metalness: 0.8 });
            const pole = new THREE.Mesh(poleGeom, poleMat);
            pole.position.set(lx, 3, lz);
            pole.castShadow = true;
            mesh.add(pole);

            // Lamp head Arm
            const armGeom = new THREE.BoxGeometry(0.2, 0.2, 1.5);
            const arm = new THREE.Mesh(armGeom, poleMat);
            arm.position.set(0, 3, 0.5);
            pole.add(arm);

            // Glowing light bulb (only visible at night)
            const bulbGeom = new THREE.SphereGeometry(0.3, 16, 16);
            const bulbMat = new THREE.MeshBasicMaterial({ color: 0xfef08a });
            const bulb = new THREE.Mesh(bulbGeom, bulbMat);
            bulb.position.set(0, 2.8, 1.2);
            bulb.userData = { isStreetlightBulb: true };
            bulb.visible = false; // off by default (daylight)
            pole.add(bulb);

            // Spot light source casting downward
            const spotLight = new THREE.SpotLight(0xfef08a, 4, 15, Math.PI / 4, 0.5, 1);
            spotLight.position.set(0, 2.7, 1.2);
            spotLight.target.position.set(0, 0, 1.2);
            bulb.add(spotLight);
            bulb.add(spotLight.target);
        } else {
            // Plant a beautiful sidewalk tree with random style variety
            const treeStyles = ['conifer', 'deciduous', 'palm'];
            const style = treeStyles[Math.floor(Math.random() * treeStyles.length)];
            const tree = buildLowPolyTree(lx, 0.15, lz, 4 + Math.random() * 2, style);
            mesh.add(tree);
        }
    }

    // Spawn animated pedestrians on the sidewalk
    spawnSidewalkPedestrians(item, outerSidewalk);
}

// Rebuild building massing, zoning envelopes, and setback lines based on params
function rebuildParcel3D(item) {
    item.params = sanitizeParcelParams(item.params || {}, item.area, item.outerRing);

    // 1. Clear old models
    if (item.buildingMesh) {
        scene.remove(item.buildingMesh);
        item.buildingMesh.traverse(child => {
            if (child.isMesh) {
                child.geometry.dispose();
                if (Array.isArray(child.material)) {
                    child.material.forEach(m => m.dispose());
                } else if (child.material) {
                    child.material.dispose();
                }
            }
        });
        item.buildingMesh = null;
    }
    if (item.setbackMesh) {
        scene.remove(item.setbackMesh);
        item.setbackMesh.geometry.dispose();
        item.setbackMesh = null;
    }
    if (item.zoningMesh) {
        scene.remove(item.zoningMesh);
        item.zoningMesh.geometry.dispose();
        item.zoningMesh = null;
    }

    const setback = item.params.setback;
    const floors = item.params.floors;
    const floorH = item.params.floorHeight;
    const height = floors * floorH;
    const typology = item.params.typology;
    const usage = item.params.usage;

    // 2. Generate Inset Setback Shape. If the requested setback eats the parcel,
    // keep rendering a safe 3D massing footprint instead of leaving a flat plan.
    const requestedInsetRing = offsetPolygonRing(item.outerRing, setback);
    const buildable = resolveBuildableRing(item, setback);
    const insetRing = scaleRingInLocalAxes(buildable.ring, item.params.scaleX, item.params.scaleY);
    item.usedFootprintFallback = !!buildable.usedFallback;
    if (!insetRing || insetRing.length < 3) {
        drawSetbackErrorLine(item);
        removeHeightLabel(item);
        return;
    }

    if (requestedInsetRing && requestedInsetRing.length >= 3) {
        // Draw requested setback guideline
        const setbackPoints = requestedInsetRing.map(pt => new THREE.Vector3(pt.x, 0.1, -pt.y));
        setbackPoints.push(setbackPoints[0].clone());
        const sbGeom = new THREE.BufferGeometry().setFromPoints(setbackPoints);
        const sbMat = new THREE.LineDashedMaterial({ color: 0x14b8a6, dashSize: 2, gapSize: 1.5 });
        const sbLine = new THREE.Line(sbGeom, sbMat);
        sbLine.computeLineDistances();
        scene.add(sbLine);
        item.setbackMesh = sbLine;
    } else {
        drawSetbackErrorLine(item);
    }

    const buildingGroup = new THREE.Group();
    buildingGroup.userData = { parcelItem: item };

    // Calculate footprint area and construct shape/geometry
    let footprintArea = 0;
    let gfa = 0;
    let bldGeom = null;
    let bldMesh = null;
    let footprintPoints = [];

    // Check if usage is Park
    if (usage === 'Park') {
        const parkGroup = new THREE.Group();
        parkGroup.userData = { parcelItem: item };
        scene.add(parkGroup);
        item.buildingMesh = parkGroup;

        // Draw green turf shape
        const turfShape = new THREE.Shape();
        insetRing.forEach((pt, i) => {
            if (i === 0) turfShape.moveTo(pt.x, pt.y);
            else turfShape.lineTo(pt.x, pt.y);
        });
        const turfGeom = new THREE.ExtrudeGeometry(turfShape, { depth: 0.1, bevelEnabled: false });
        turfGeom.rotateX(-Math.PI / 2);
        const turfMat = new THREE.MeshStandardMaterial({ color: 0x15803d, roughness: 0.9 });
        const turfMesh = new THREE.Mesh(turfGeom, turfMat);
        turfMesh.receiveShadow = true;
        turfMesh.position.y = 0.02;
        parkGroup.add(turfMesh);

        // Add walking path: a gravel circle or oval in the center
        let cx = 0, cy = 0;
        insetRing.forEach(pt => { cx += pt.x; cy += pt.y; });
        cx /= insetRing.length;
        cy /= insetRing.length;

        const pathGeom = new THREE.TorusGeometry(8, 1.5, 8, 24);
        pathGeom.rotateX(Math.PI / 2);
        const pathMat = new THREE.MeshStandardMaterial({ color: 0xd4d4d8, roughness: 0.8 });
        const pathMesh = new THREE.Mesh(pathGeom, pathMat);
        pathMesh.position.set(cx, 0.13, -cy);
        pathMesh.receiveShadow = true;
        parkGroup.add(pathMesh);

        // Add 2 wooden benches around path
        const benchGeom = new THREE.BoxGeometry(2.5, 0.4, 0.6);
        const benchMat = new THREE.MeshStandardMaterial({ color: 0x78350f, roughness: 0.7 });
        const legGeom = new THREE.BoxGeometry(0.2, 0.4, 0.6);
        const legMat = new THREE.MeshStandardMaterial({ color: 0x18181b, metalness: 0.8 });

        const benchOffsets = [
            { x: cx - 6, z: -cy - 6, rot: Math.PI / 4 },
            { x: cx + 6, z: -cy + 6, rot: 5 * Math.PI / 4 }
        ];

        benchOffsets.forEach(offset => {
            const bench = new THREE.Group();
            bench.position.set(offset.x, 0.2, offset.z);
            bench.rotation.y = offset.rot;
            
            const seat = new THREE.Mesh(benchGeom, benchMat);
            seat.position.y = 0.2;
            seat.castShadow = true;
            bench.add(seat);

            const leg1 = new THREE.Mesh(legGeom, legMat);
            leg1.position.set(-1.0, 0, 0);
            leg1.castShadow = true;
            bench.add(leg1);

            const leg2 = new THREE.Mesh(legGeom, legMat);
            leg2.position.set(1.0, 0, 0);
            leg2.castShadow = true;
            bench.add(leg2);

            parkGroup.add(bench);
        });

        // Add clustered park trees
        const numParkTrees = Math.min(6, Math.max(3, Math.floor(item.area / 200)));
        for (let i = 0; i < numParkTrees; i++) {
            const angle = Math.random() * Math.PI * 2;
            const dist = 3 + Math.random() * 8;
            const tx = cx + Math.cos(angle) * dist;
            const tz = -cy + Math.sin(angle) * dist;
            
            const parkStyles = ['conifer', 'deciduous', 'deciduous', 'palm'];
            const style = parkStyles[Math.floor(Math.random() * parkStyles.length)];
            const tree = buildLowPolyTree(tx, 0.1, tz, 4 + Math.random() * 3, style);
            parkGroup.add(tree);
        }

        buildZoningEnvelope(item, insetRing, item.params.maxHeight, false);
        removeHeightLabel(item);
        return;
    }

    // Otherwise, generate building based on Typology
    if (typology === 'Courtyard') {
        const innerSetback = 8;
        const innerRing = offsetPolygonRing(insetRing, innerSetback);
        const outerArea = calculatePolygonArea(insetRing);
        const innerArea = innerRing ? calculatePolygonArea(innerRing) : 0;
        footprintArea = Math.max(0, outerArea - innerArea);
        gfa = footprintArea * floors;

        const bldShape = new THREE.Shape();
        insetRing.forEach((pt, i) => {
            if (i === 0) bldShape.moveTo(pt.x, pt.y);
            else bldShape.lineTo(pt.x, pt.y);
        });
        if (innerRing && innerRing.length >= 3) {
            const hole = new THREE.Path();
            innerRing.forEach((pt, i) => {
                if (i === 0) hole.moveTo(pt.x, pt.y);
                else hole.lineTo(pt.x, pt.y);
            });
            bldShape.holes.push(hole);
        }
        bldGeom = new THREE.ExtrudeGeometry(bldShape, { depth: height, bevelEnabled: false });
        bldGeom.rotateX(-Math.PI / 2);

        footprintPoints = insetRing; // approximate pitched roof edge
    } else if (typology === 'Slab') {
        const slabShape = buildSlabShape(insetRing, 12);
        footprintArea = calculateShapeArea(slabShape);
        gfa = footprintArea * floors;

        bldGeom = new THREE.ExtrudeGeometry(slabShape, { depth: height, bevelEnabled: false });
        bldGeom.rotateX(-Math.PI / 2);

        footprintPoints = slabShape.getPoints().map(pt => { return { x: pt.x, y: pt.y }; });
    } else if (typology === 'LShape') {
        const lShape = buildLShape(insetRing, 12);
        footprintArea = calculateShapeArea(lShape);
        gfa = footprintArea * floors;

        bldGeom = new THREE.ExtrudeGeometry(lShape, { depth: height, bevelEnabled: false });
        bldGeom.rotateX(-Math.PI / 2);

        footprintPoints = lShape.getPoints().map(pt => { return { x: pt.x, y: pt.y }; });
    } else if (typology === 'UShape') {
        const uShape = buildUShape(insetRing, 12);
        footprintArea = calculateShapeArea(uShape);
        gfa = footprintArea * floors;

        bldGeom = new THREE.ExtrudeGeometry(uShape, { depth: height, bevelEnabled: false });
        bldGeom.rotateX(-Math.PI / 2);

        footprintPoints = uShape.getPoints().map(pt => { return { x: pt.x, y: pt.y }; });
    } else if (typology === 'PodiumTower') {
        const podiumH = Math.min(height, 2 * floorH);
        const towerH = Math.max(0, height - podiumH);

        const podiumArea = calculatePolygonArea(insetRing);
        const towerRing = offsetPolygonRing(insetRing, 3.5) || insetRing;
        const towerArea = calculatePolygonArea(towerRing);

        const podiumFloors = Math.round(podiumH / floorH);
        const towerFloors = Math.round(towerH / floorH);

        footprintArea = podiumArea;
        gfa = (podiumArea * podiumFloors) + (towerArea * towerFloors);

        // Build Podium Mesh
        const podiumShape = new THREE.Shape();
        insetRing.forEach((pt, i) => {
            if (i === 0) podiumShape.moveTo(pt.x, pt.y);
            else podiumShape.lineTo(pt.x, pt.y);
        });
        const podiumGeom = new THREE.ExtrudeGeometry(podiumShape, { depth: podiumH, bevelEnabled: false });
        podiumGeom.rotateX(-Math.PI / 2);

        const matsPodium = getBuildingMaterials(usage, podiumFloors);
        const podiumMesh = new THREE.Mesh(podiumGeom, matsPodium);
        podiumMesh.castShadow = true;
        podiumMesh.receiveShadow = true;

        // Build Tower Mesh
        let towerMesh = null;
        if (towerH > 0) {
            const towerShape = new THREE.Shape();
            towerRing.forEach((pt, i) => {
                if (i === 0) towerShape.moveTo(pt.x, pt.y);
                else towerShape.lineTo(pt.x, pt.y);
            });
            const towerGeom = new THREE.ExtrudeGeometry(towerShape, { depth: towerH, bevelEnabled: false });
            towerGeom.rotateX(-Math.PI / 2);
            towerGeom.translate(0, podiumH, 0);

            const matsTower = getBuildingMaterials(usage, towerFloors);
            towerMesh = new THREE.Mesh(towerGeom, matsTower);
            towerMesh.castShadow = true;
            towerMesh.receiveShadow = true;
        }

        const group = new THREE.Group();
        group.userData = { parcelItem: item };
        group.add(podiumMesh);
        if (towerMesh) group.add(towerMesh);
        buildingGroup.add(group);

        // Add roof details on top based on roof style selection
        const topMesh = towerMesh || podiumMesh;
        const roofStyle = roofStyleForItem(item);
        if (roofStyle === 'Hipped') {
            buildHippedRoof(topMesh, towerRing, height);
        } else if (roofStyle === 'Gable') {
            buildGableRoof(topMesh, towerRing, height);
        } else if (roofStyle === 'Mansard') {
            buildMansardRoof(topMesh, towerRing, height);
        } else {
            addRooftopDetails(topMesh, towerRing, height, usage);
        }

        footprintPoints = towerRing; // for compliance envelope
    } else if (typology === 'SteppedTower') {
        const group = new THREE.Group();
        group.userData = { parcelItem: item };

        const stepInterval = item.params.stepbackInterval || 4;
        const stepDepth = item.params.stepbackDepth || 1.5;

        let baseHeight = 0;
        let remainingFloors = floors;
        let segmentIndex = 0;
        let lastRing = insetRing;
        let lastHeight = 0;
        let topMesh = null;

        footprintArea = calculatePolygonArea(insetRing);
        gfa = 0;

        while (remainingFloors > 0) {
            const currentSetback = setback + segmentIndex * stepDepth;
            const segmentRing = offsetPolygonRing(item.outerRing, currentSetback);
            
            if (!segmentRing || segmentRing.length < 3) {
                break;
            }

            lastRing = segmentRing;

            const segFloors = Math.min(stepInterval, remainingFloors);
            const segHeight = segFloors * floorH;
            const segArea = calculatePolygonArea(segmentRing);
            gfa += segArea * segFloors;

            const segShape = new THREE.Shape();
            segmentRing.forEach((pt, i) => {
                if (i === 0) segShape.moveTo(pt.x, pt.y);
                else segShape.lineTo(pt.x, pt.y);
            });

            const segGeom = new THREE.ExtrudeGeometry(segShape, { depth: segHeight, bevelEnabled: false });
            segGeom.rotateX(-Math.PI / 2);
            segGeom.translate(0, baseHeight, 0);

            const mats = getBuildingMaterials(usage, segFloors);
            const segMesh = new THREE.Mesh(segGeom, mats);
            segMesh.castShadow = true;
            segMesh.receiveShadow = true;

            group.add(segMesh);
            topMesh = segMesh;

            baseHeight += segHeight;
            lastHeight = baseHeight;
            remainingFloors -= segFloors;
            segmentIndex++;
        }

        buildingGroup.add(group);

        // Add roof details on top based on roof style selection
        if (topMesh && lastRing) {
            const roofStyle = roofStyleForItem(item);
            if (roofStyle === 'Hipped') {
                buildHippedRoof(topMesh, lastRing, lastHeight);
            } else if (roofStyle === 'Gable') {
                buildGableRoof(topMesh, lastRing, lastHeight);
            } else if (roofStyle === 'Mansard') {
                buildMansardRoof(topMesh, lastRing, lastHeight);
            } else {
                addRooftopDetails(topMesh, lastRing, lastHeight, usage);
            }
        }

        footprintPoints = lastRing; // for compliance envelope
    } else if (typology === 'MultiBuildingBlock') {
        const group = new THREE.Group();
        group.userData = { parcelItem: item };

        const ob = getOrientedBounds(insetRing);
        const W = ob.W;

        const localRing = insetRing.map(pt => {
            const rx = pt.x - ob.cx;
            const ry = pt.y - ob.cy;
            return {
                x: rx * ob.ux + ry * ob.uy,
                y: rx * ob.nx + ry * ob.ny
            };
        });

        const floorsA = Math.round(floors * 1.3);
        const floorsB = Math.round(floors * 0.7);
        const heightA = floorsA * floorH;
        const heightB = floorsB * floorH;

        footprintArea = 0;
        gfa = 0;

        let insetPoly1 = null;
        let insetPoly3 = null;

        if (W >= 40) {
            const localPoly1 = clipConvexPolygonVertical(localRing, ob.minX, ob.minX + W * 0.38);
            const localPoly2 = clipConvexPolygonVertical(localRing, ob.minX + W * 0.38, ob.minX + W * 0.62);
            const localPoly3 = clipConvexPolygonVertical(localRing, ob.minX + W * 0.62, ob.maxX);

            if (localPoly1 && localPoly1.length >= 3) {
                const globalPoly1 = localPoly1.map(pt => ({
                    x: ob.cx + pt.x * ob.ux + pt.y * ob.nx,
                    y: ob.cy + pt.x * ob.uy + pt.y * ob.ny
                }));
                insetPoly1 = offsetPolygonRing(globalPoly1, 1.2);
                if (insetPoly1 && insetPoly1.length >= 3) {
                    const a1 = calculatePolygonArea(insetPoly1);
                    footprintArea += a1;
                    gfa += a1 * floorsA;

                    const shapeA = new THREE.Shape();
                    insetPoly1.forEach((pt, i) => {
                        if (i === 0) shapeA.moveTo(pt.x, pt.y);
                        else shapeA.lineTo(pt.x, pt.y);
                    });
                    const geomA = new THREE.ExtrudeGeometry(shapeA, { depth: heightA, bevelEnabled: false });
                    geomA.rotateX(-Math.PI / 2);

                    const matsA = getBuildingMaterials(usage, floorsA);
                    const meshA = new THREE.Mesh(geomA, matsA);
                    meshA.castShadow = true;
                    meshA.receiveShadow = true;
                    meshA.userData = { parcelItem: item };
                    group.add(meshA);

                    addRooftopDetails(meshA, insetPoly1, heightA, usage);
                    addBuildingBalconies(group, insetPoly1, floorsA, floorH);
                }
            }

            if (localPoly2 && localPoly2.length >= 3) {
                const globalPoly2 = localPoly2.map(pt => ({
                    x: ob.cx + pt.x * ob.ux + pt.y * ob.nx,
                    y: ob.cy + pt.x * ob.uy + pt.y * ob.ny
                }));

                const shapeP = new THREE.Shape();
                globalPoly2.forEach((pt, i) => {
                    if (i === 0) shapeP.moveTo(pt.x, pt.y);
                    else shapeP.lineTo(pt.x, pt.y);
                });
                const geomP = new THREE.ExtrudeGeometry(shapeP, { depth: 0.05, bevelEnabled: false });
                geomP.rotateX(-Math.PI / 2);
                geomP.translate(0, 0.03, 0);

                const matP = new THREE.MeshStandardMaterial({ color: 0xe2e8f0, roughness: 0.8 });
                const meshP = new THREE.Mesh(geomP, matP);
                meshP.receiveShadow = true;
                group.add(meshP);

                let px = 0, py = 0;
                globalPoly2.forEach(pt => { px += pt.x; py += pt.y; });
                px /= globalPoly2.length;
                py /= globalPoly2.length;

                const fountainGroup = new THREE.Group();
                fountainGroup.position.set(px, 0.06, -py);

                const rimGeom = new THREE.TorusGeometry(3.5, 0.4, 8, 16);
                rimGeom.rotateX(Math.PI / 2);
                const rimMat = new THREE.MeshStandardMaterial({ color: 0x64748b, roughness: 0.5 });
                const rimMesh = new THREE.Mesh(rimGeom, rimMat);
                rimMesh.castShadow = true;
                rimMesh.receiveShadow = true;
                fountainGroup.add(rimMesh);

                const waterGeom = new THREE.CylinderGeometry(3.3, 3.3, 0.1, 16);
                const waterMat = new THREE.MeshStandardMaterial({
                    color: 0x38bdf8,
                    metalness: 0.9,
                    roughness: 0.1,
                    transparent: true,
                    opacity: 0.8
                });
                const waterMesh = new THREE.Mesh(waterGeom, waterMat);
                waterMesh.position.y = 0.1;
                fountainGroup.add(waterMesh);

                const jetGeom = new THREE.CylinderGeometry(0.05, 0.15, 1.8, 8);
                const jetMat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.7 });
                const jet = new THREE.Mesh(jetGeom, jetMat);
                jet.position.y = 0.9;
                fountainGroup.add(jet);

                group.add(fountainGroup);

                const benchGeom = new THREE.BoxGeometry(1.6, 0.3, 0.4);
                const benchMat = new THREE.MeshStandardMaterial({ color: 0x7c2d12, roughness: 0.6 });
                const legGeom = new THREE.BoxGeometry(0.15, 0.3, 0.4);
                const legMat = new THREE.MeshStandardMaterial({ color: 0x334155, metalness: 0.8 });

                const benchOffsets = [
                    { dx: -4.8, dz: 0, rot: Math.PI / 2 },
                    { dx: 4.8, dz: 0, rot: -Math.PI / 2 },
                    { dx: 0, dz: 4.8, rot: 0 }
                ];
                benchOffsets.forEach(offset => {
                    const bench = new THREE.Group();
                    bench.position.set(px + offset.dx, 0.05, -py + offset.dz);
                    bench.rotation.y = offset.rot;
                    
                    const seat = new THREE.Mesh(benchGeom, benchMat);
                    seat.position.y = 0.15;
                    seat.castShadow = true;
                    bench.add(seat);

                    const l1 = new THREE.Mesh(legGeom, legMat);
                    l1.position.set(-0.7, 0, 0);
                    bench.add(l1);

                    const l2 = new THREE.Mesh(legGeom, legMat);
                    l2.position.set(0.7, 0, 0);
                    bench.add(l2);

                    group.add(bench);
                });

                const treePositions = [
                    { dx: -3, dz: -7 },
                    { dx: 3, dz: -7 },
                    { dx: -7, dz: 3 },
                    { dx: 7, dz: 3 }
                ];
                treePositions.forEach(tPos => {
                    const t = buildLowPolyTree(px + tPos.dx, 0.06, -py + tPos.dz, 4.5 + Math.random() * 1.5, 'deciduous');
                    group.add(t);
                });

                const pL = new THREE.Group();
                pL.position.set(px + 4, 0.06, -py - 6);
                pL.rotation.y = Math.PI / 6;

                const stripeMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
                const stripeGeom = new THREE.BoxGeometry(0.1, 0.01, 3.5);
                for (let k = -1.5; k <= 1.5; k += 1.5) {
                    const stripe = new THREE.Mesh(stripeGeom, stripeMat);
                    stripe.position.set(k * 2.2, 0.01, 0);
                    pL.add(stripe);
                }

                const colors = [0xd97706, 0x2563eb, 0xdc2626];
                for (let cIdx = 0; cIdx < 2; cIdx++) {
                    const carMesh = buildDetailedCar(colors[cIdx % colors.length], 1.0);
                    carMesh.position.set((-0.75 + cIdx * 1.5) * 2.2, 0.35, 0);
                    carMesh.rotation.y = Math.PI / 2;
                    pL.add(carMesh);
                }
                group.add(pL);
            }

            if (localPoly3 && localPoly3.length >= 3) {
                const globalPoly3 = localPoly3.map(pt => ({
                    x: ob.cx + pt.x * ob.ux + pt.y * ob.nx,
                    y: ob.cy + pt.x * ob.uy + pt.y * ob.ny
                }));
                insetPoly3 = offsetPolygonRing(globalPoly3, 1.2);
                if (insetPoly3 && insetPoly3.length >= 3) {
                    const a3 = calculatePolygonArea(insetPoly3);
                    footprintArea += a3;
                    gfa += a3 * floorsB;

                    const shapeB = new THREE.Shape();
                    insetPoly3.forEach((pt, i) => {
                        if (i === 0) shapeB.moveTo(pt.x, pt.y);
                        else shapeB.lineTo(pt.x, pt.y);
                    });
                    const geomB = new THREE.ExtrudeGeometry(shapeB, { depth: heightB, bevelEnabled: false });
                    geomB.rotateX(-Math.PI / 2);

                    const matsB = getBuildingMaterials('Residential', floorsB);
                    const meshB = new THREE.Mesh(geomB, matsB);
                    meshB.castShadow = true;
                    meshB.receiveShadow = true;
                    meshB.userData = { parcelItem: item };
                    group.add(meshB);

                    buildGableRoof(meshB, insetPoly3, heightB);
                    addBuildingBalconies(group, insetPoly3, floorsB, floorH);
                }
            }

            footprintPoints = insetPoly1 || insetPoly3 || insetRing;
        } else {
            const localPoly1 = clipConvexPolygonVertical(localRing, ob.minX, ob.minX + W * 0.5);
            const localPoly2 = clipConvexPolygonVertical(localRing, ob.minX + W * 0.5, ob.maxX);

            if (localPoly1 && localPoly1.length >= 3) {
                const globalPoly1 = localPoly1.map(pt => ({
                    x: ob.cx + pt.x * ob.ux + pt.y * ob.nx,
                    y: ob.cy + pt.x * ob.uy + pt.y * ob.ny
                }));
                insetPoly1 = offsetPolygonRing(globalPoly1, 1.2);
                if (insetPoly1 && insetPoly1.length >= 3) {
                    const a1 = calculatePolygonArea(insetPoly1);
                    footprintArea += a1;
                    gfa += a1 * floors;

                    const shapeA = new THREE.Shape();
                    insetPoly1.forEach((pt, i) => {
                        if (i === 0) shapeA.moveTo(pt.x, pt.y);
                        else shapeA.lineTo(pt.x, pt.y);
                    });
                    const geomA = new THREE.ExtrudeGeometry(shapeA, { depth: height, bevelEnabled: false });
                    geomA.rotateX(-Math.PI / 2);

                    const matsA = getBuildingMaterials(usage, floors);
                    const meshA = new THREE.Mesh(geomA, matsA);
                    meshA.castShadow = true;
                    meshA.receiveShadow = true;
                    meshA.userData = { parcelItem: item };
                    group.add(meshA);

                    const roofStyle = roofStyleForItem(item);
                    if (roofStyle === 'Hipped') {
                        buildHippedRoof(meshA, insetPoly1, height);
                    } else if (roofStyle === 'Gable') {
                        buildGableRoof(meshA, insetPoly1, height);
                    } else if (roofStyle === 'Mansard') {
                        buildMansardRoof(meshA, insetPoly1, height);
                    } else {
                        addRooftopDetails(meshA, insetPoly1, height, usage);
                    }

                    addBuildingBalconies(group, insetPoly1, floors, floorH);
                }
            }

            if (localPoly2 && localPoly2.length >= 3) {
                const globalPoly2 = localPoly2.map(pt => ({
                    x: ob.cx + pt.x * ob.ux + pt.y * ob.nx,
                    y: ob.cy + pt.x * ob.uy + pt.y * ob.ny
                }));

                const shapeP = new THREE.Shape();
                globalPoly2.forEach((pt, i) => {
                    if (i === 0) shapeP.moveTo(pt.x, pt.y);
                    else shapeP.lineTo(pt.x, pt.y);
                });
                const geomP = new THREE.ExtrudeGeometry(shapeP, { depth: 0.05, bevelEnabled: false });
                geomP.rotateX(-Math.PI / 2);
                geomP.translate(0, 0.03, 0);

                const matP = new THREE.MeshStandardMaterial({ color: 0x166534, roughness: 0.95 });
                const meshP = new THREE.Mesh(geomP, matP);
                meshP.receiveShadow = true;
                group.add(meshP);

                let px = 0, py = 0;
                globalPoly2.forEach(pt => { px += pt.x; py += pt.y; });
                px /= globalPoly2.length;
                py /= globalPoly2.length;

                const pathGeom = new THREE.BoxGeometry(4.5, 0.02, 1.2);
                const pathMat = new THREE.MeshStandardMaterial({ color: 0xd4d4d8, roughness: 0.8 });
                const path = new THREE.Mesh(pathGeom, pathMat);
                path.position.set(px, 0.09, -py);
                group.add(path);

                const bench = new THREE.Group();
                bench.position.set(px, 0.05, -py + 1.2);
                const seat = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.3, 0.4), new THREE.MeshStandardMaterial({ color: 0x78350f }));
                seat.position.y = 0.15;
                bench.add(seat);
                group.add(bench);

                const carStripe = new THREE.Group();
                carStripe.position.set(px + 4, 0.06, -py - 4);
                carStripe.rotation.y = Math.PI / 4;
                const parkedCar = buildDetailedCar(0x0ea5e9, 1.0);
                parkedCar.position.set(0, 0.35, 0);
                carStripe.add(parkedCar);
                group.add(carStripe);

                for (let k = 0; k < 4; k++) {
                    const tree = buildLowPolyTree(px - 3 + Math.random() * 6, 0.06, -py - 3 + Math.random() * 6, 4 + Math.random() * 2);
                    group.add(tree);
                }
            }

            footprintPoints = insetPoly1 || insetRing;
        }

        buildingGroup.add(group);
    } else { // Tower
        footprintArea = calculatePolygonArea(insetRing);
        gfa = footprintArea * floors;

        const bldShape = new THREE.Shape();
        insetRing.forEach((pt, i) => {
            if (i === 0) bldShape.moveTo(pt.x, pt.y);
            else bldShape.lineTo(pt.x, pt.y);
        });
        bldGeom = new THREE.ExtrudeGeometry(bldShape, { depth: height, bevelEnabled: false });
        bldGeom.rotateX(-Math.PI / 2);

        footprintPoints = insetRing;
    }

    if (typology !== 'PodiumTower' && typology !== 'SteppedTower' && typology !== 'MultiBuildingBlock') {
        const mats = getBuildingMaterials(usage, floors);
        bldMesh = new THREE.Mesh(bldGeom, mats);
        bldMesh.castShadow = true;
        bldMesh.receiveShadow = true;
        bldMesh.userData = { parcelItem: item };
        buildingGroup.add(bldMesh);

        // Add Rooftop based on Roof Style parameter
        const roofStyle = roofStyleForItem(item);
        if (roofStyle === 'Hipped') {
            buildHippedRoof(bldMesh, footprintPoints, height);
        } else if (roofStyle === 'Gable') {
            buildGableRoof(bldMesh, footprintPoints, height);
        } else if (roofStyle === 'Mansard') {
            buildMansardRoof(bldMesh, footprintPoints, height);
        } else {
            addRooftopDetails(bldMesh, footprintPoints, height, usage);
        }

        // Add Courtyard/Inner garden trees for specific typologies
        if (typology === 'Courtyard') {
            let cx = 0, cy = 0;
            insetRing.forEach(pt => { cx += pt.x; cy += pt.y; });
            cx /= insetRing.length;
            cy /= insetRing.length;
            
            const courtTree = buildLowPolyTree(cx, 0.05, -cy, 6);
            bldMesh.add(courtTree);
        } else if (typology === 'LShape') {
            const ob = getOrientedBounds(insetRing);
            const w = Math.min(12, ob.W * 0.5);
            const h = Math.min(12, ob.H * 0.5);
            const px = ob.maxX - (ob.W - w) / 2;
            const py = ob.maxY - (ob.H - h) / 2;
            const gx = ob.cx + px * ob.ux + py * ob.nx;
            const gy = ob.cy + px * ob.uy + py * ob.ny;
            
            const courtTree = buildLowPolyTree(gx, 0.05, -gy, 5);
            bldMesh.add(courtTree);
        } else if (typology === 'UShape') {
            const ob = getOrientedBounds(insetRing);
            const w = Math.min(12, ob.W * 0.4);
            const h = Math.min(12, ob.H * 0.4);
            const px = (ob.minX + ob.maxX) / 2;
            const py = ob.maxY - (ob.H - h) / 2;
            const gx = ob.cx + px * ob.ux + py * ob.nx;
            const gy = ob.cy + px * ob.uy + py * ob.ny;
            
            const courtTree = buildLowPolyTree(gx, 0.05, -gy, 5);
            bldMesh.add(courtTree);
        }
    }

    if (usage !== 'Park') {
        // Add balconies to standard building typologies
        if (typology !== 'PodiumTower' && typology !== 'SteppedTower' && typology !== 'MultiBuildingBlock') {
            addBuildingBalconies(buildingGroup, insetRing, floors, floorH);
        }

        const lawn = buildSetbackLawn(item, insetRing);
        if (lawn) buildingGroup.add(lawn);
        addSidewalkTreesAndAssets(buildingGroup, item, insetRing);

        scene.add(buildingGroup);
        item.buildingMesh = buildingGroup;
        ensureHeightLabel(item, height);
    }

    const bcr = item.area > 0 ? (footprintArea / item.area) : 0;
    const far = item.area > 0 ? (gfa / item.area) : 0;

    // Check violations
    const heightViolation = height > item.params.maxHeight;
    const bcrViolation = bcr > item.params.maxBcr;
    const farViolation = far > item.params.maxFar;
    const hasViolation = heightViolation || bcrViolation || farViolation;

    // 3. Build Zoning Envelope
    buildZoningEnvelope(item, insetRing, item.params.maxHeight, hasViolation);

    // Update ground color dynamically matching compliance status
    updateParcelGroundColor(item, hasViolation);
}

// Low poly procedural vegetation
function buildLowPolyTree(x, y, z, height, style) {
    style = style || 'conifer';
    const treeGroup = new THREE.Group();
    treeGroup.position.set(x, y, z);

    const trunkMat = new THREE.MeshStandardMaterial({ color: 0x78350f, roughness: 0.9 });

    if (style === 'deciduous') {
        // Deciduous: thicker trunk + noisy sphere canopy
        const trunkH = height * 0.4;
        const trunkR = trunkH * 0.1;
        const trunkGeom = new THREE.CylinderGeometry(trunkR * 0.8, trunkR, trunkH, 8);
        const trunk = new THREE.Mesh(trunkGeom, trunkMat);
        trunk.position.y = trunkH / 2;
        trunk.castShadow = true;
        treeGroup.add(trunk);

        // Sphere canopy with vertex noise displacement for organic look
        const canopyRadius = height * 0.38;
        const canopyGeom = new THREE.IcosahedronGeometry(canopyRadius, 2);
        const posAttr = canopyGeom.getAttribute('position');
        for (let i = 0; i < posAttr.count; i++) {
            const nx = posAttr.getX(i);
            const ny = posAttr.getY(i);
            const nz = posAttr.getZ(i);
            const noise = 1.0 + (Math.random() - 0.5) * 0.3;
            posAttr.setXYZ(i, nx * noise, ny * noise, nz * noise);
        }
        canopyGeom.computeVertexNormals();

        // Varied green hues for deciduous
        const greens = [0x16a34a, 0x15803d, 0x22c55e, 0x166534];
        const greenColor = greens[Math.floor(Math.random() * greens.length)];
        const foliageMat = new THREE.MeshStandardMaterial({ color: greenColor, roughness: 0.85, flatShading: true });
        const canopy = new THREE.Mesh(canopyGeom, foliageMat);
        canopy.position.y = trunkH + canopyRadius * 0.7;
        canopy.castShadow = true;
        treeGroup.add(canopy);

    } else if (style === 'palm') {
        // Palm: tall thin trunk + fan leaves radiating from top
        const trunkH = height * 0.7;
        const trunkR = height * 0.035;
        const trunkGeom = new THREE.CylinderGeometry(trunkR * 0.6, trunkR, trunkH, 6);
        const trunk = new THREE.Mesh(trunkGeom, trunkMat);
        trunk.position.y = trunkH / 2;
        trunk.castShadow = true;
        treeGroup.add(trunk);

        // Fan leaves: elongated flattened cones radiating outward
        const leafCount = 7;
        const leafLength = height * 0.45;
        const leafMat = new THREE.MeshStandardMaterial({ color: 0x22c55e, roughness: 0.8, side: THREE.DoubleSide });
        for (let i = 0; i < leafCount; i++) {
            const leafGeom = new THREE.ConeGeometry(leafLength * 0.18, leafLength, 4);
            const leaf = new THREE.Mesh(leafGeom, leafMat);
            const angle = (i / leafCount) * Math.PI * 2;
            leaf.position.set(
                Math.cos(angle) * leafLength * 0.35,
                trunkH + leafLength * 0.1,
                Math.sin(angle) * leafLength * 0.35
            );
            leaf.rotation.z = Math.cos(angle) * 0.8;
            leaf.rotation.x = Math.sin(angle) * 0.8;
            leaf.castShadow = true;
            treeGroup.add(leaf);
        }

    } else {
        // Conifer (default): stacked cones for the classic procedural look
        const trunkHeight = height * 0.35;
        const trunkRadius = trunkHeight * 0.12;
        const trunkGeom = new THREE.CylinderGeometry(trunkRadius * 0.7, trunkRadius, trunkHeight, 8);
        const trunk = new THREE.Mesh(trunkGeom, trunkMat);
        trunk.position.y = trunkHeight / 2;
        trunk.castShadow = true;
        treeGroup.add(trunk);

        const foliageHeight = height * 0.65;
        // Vary conifer greens slightly
        const coniferGreens = [0x16a34a, 0x166534, 0x14532d];
        const greenColor = coniferGreens[Math.floor(Math.random() * coniferGreens.length)];
        const foliageMat = new THREE.MeshStandardMaterial({ color: greenColor, roughness: 0.8 });
        
        const numLayers = 3;
        for (let l = 0; l < numLayers; l++) {
            const radius = foliageHeight * 0.5 * (1 - l * 0.25);
            const coneGeom = new THREE.ConeGeometry(radius, foliageHeight * 0.5, 8);
            const cone = new THREE.Mesh(coneGeom, foliageMat);
            cone.position.y = trunkHeight + (l * foliageHeight * 0.22) + (foliageHeight * 0.25);
            cone.castShadow = true;
            treeGroup.add(cone);
        }
    }

    return treeGroup;
}

// Animated pedestrians
function spawnSidewalkPedestrians(item, sidewalkRing) {
    if (!sidewalkRing || sidewalkRing.length < 3) return;

    // Build a 3D path from the sidewalk ring midpoints (between parcel and outer edge)
    const pathPoints = [];
    for (let i = 0; i < sidewalkRing.length; i++) {
        const outer = sidewalkRing[i];
        const inner = item.outerRing[i % item.outerRing.length];
        // Midpoint of the sidewalk width
        pathPoints.push({
            x: (outer.x + inner.x) / 2,
            z: -((outer.y + inner.y) / 2)
        });
    }

    // Spawn 1 pedestrian per parcel sidewalk (minimal default)
    const numPeds = 1;
    const clothingColors = [0x3b82f6, 0xef4444, 0xf59e0b, 0x8b5cf6, 0x06b6d4, 0xe11d48, 0x84cc16, 0xf97316];

    for (let i = 0; i < numPeds; i++) {
        const pedGroup = new THREE.Group();

        // Body: capsule approximation (cylinder + hemispheres)
        const bodyColor = clothingColors[Math.floor(Math.random() * clothingColors.length)];
        const bodyMat = new THREE.MeshStandardMaterial({ color: bodyColor, roughness: 0.7 });
        const bodyGeom = new THREE.CapsuleGeometry(0.2, 0.7, 4, 8);
        const body = new THREE.Mesh(bodyGeom, bodyMat);
        body.position.y = 0.75;
        body.castShadow = true;
        pedGroup.add(body);

        // Head: small sphere
        const headGeom = new THREE.SphereGeometry(0.15, 8, 8);
        const skinColors = [0xf5d6c8, 0xd4a574, 0x8d5524, 0xc68642];
        const headMat = new THREE.MeshStandardMaterial({ color: skinColors[Math.floor(Math.random() * skinColors.length)], roughness: 0.6 });
        const head = new THREE.Mesh(headGeom, headMat);
        head.position.y = 1.3;
        head.castShadow = true;
        pedGroup.add(head);

        // Legs: two thin cylinders
        const legMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, roughness: 0.8 });
        for (let s = -1; s <= 1; s += 2) {
            const legGeom = new THREE.CylinderGeometry(0.06, 0.06, 0.4, 6);
            const leg = new THREE.Mesh(legGeom, legMat);
            leg.position.set(s * 0.1, 0.2, 0);
            leg.castShadow = true;
            pedGroup.add(leg);
        }

        scene.add(pedGroup);

        pedestrians.push({
            mesh: pedGroup,
            path: pathPoints,
            speed: 0.002 + Math.random() * 0.003,
            progress: Math.random() * pathPoints.length,
            direction: Math.random() > 0.5 ? 1 : -1
        });
    }
}

// Update pedestrian positions each frame
function updatePedestrians() {
    pedestrians.forEach(ped => {
        const ring = ped.path;
        if (!ring || ring.length < 2) return;

        ped.progress += ped.speed * ped.direction;
        if (ped.progress >= ring.length) ped.progress -= ring.length;
        if (ped.progress < 0) ped.progress += ring.length;

        const idx1 = Math.floor(ped.progress) % ring.length;
        const idx2 = (idx1 + 1) % ring.length;
        const t = ped.progress % 1.0;

        const pt1 = ring[idx1];
        const pt2 = ring[idx2];

        const x = pt1.x + (pt2.x - pt1.x) * t;
        const z = pt1.z + (pt2.z - pt1.z) * t;

        ped.mesh.position.set(x, 0.15, z);

        // Face direction of travel
        const dx = pt2.x - pt1.x;
        const dz = pt2.z - pt1.z;
        if (Math.abs(dx) > 0.001 || Math.abs(dz) > 0.001) {
            ped.mesh.rotation.y = Math.atan2(dx * ped.direction, dz * ped.direction);
        }

        // Subtle walking bob
        const bobPhase = Date.now() * 0.008 + ped.progress * 10;
        ped.mesh.position.y = 0.15 + Math.abs(Math.sin(bobPhase)) * 0.05;
    });
}

// Oriented bounding box helpers
function getOrientedBounds(ring) {
    let maxLen = -1;
    let bestStart = null, bestEnd = null;
    const N = ring.length;
    for (let i = 0; i < N; i++) {
        const p1 = ring[i];
        const p2 = ring[(i + 1) % N];
        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        const len = Math.sqrt(dx*dx + dy*dy);
        if (len > maxLen) {
            maxLen = len;
            bestStart = p1;
            bestEnd = p2;
        }
    }

    let cx = 0, cy = 0;
    ring.forEach(pt => { cx += pt.x; cy += pt.y; });
    cx /= N;
    cy /= N;

    const dx = bestEnd.x - bestStart.x;
    const dy = bestEnd.y - bestStart.y;
    const len = Math.sqrt(dx*dx + dy*dy);
    const ux = dx / len;
    const uy = dy / len;

    const nx = -uy;
    const ny = ux;

    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;

    ring.forEach(pt => {
        const rx = pt.x - cx;
        const ry = pt.y - cy;
        const projX = rx * ux + ry * uy;
        const projY = rx * nx + ry * ny;
        if (projX < minX) minX = projX;
        if (projX > maxX) maxX = projX;
        if (projY < minY) minY = projY;
        if (projY > maxY) maxY = projY;
    });

    return {
        cx, cy,
        ux, uy,
        nx, ny,
        minX, maxX,
        minY, maxY,
        W: maxX - minX,
        H: maxY - minY
    };
}

function buildLShape(ring, width) {
    const ob = getOrientedBounds(ring);
    
    const w = Math.min(width, ob.W * 0.5);
    const h = Math.min(width, ob.H * 0.5);

    const shape = new THREE.Shape();
    
    const ptsLocal = [
        { x: ob.minX, y: ob.minY },
        { x: ob.maxX, y: ob.minY },
        { x: ob.maxX, y: ob.minY + h },
        { x: ob.minX + w, y: ob.minY + h },
        { x: ob.minX + w, y: ob.maxY },
        { x: ob.minX, y: ob.maxY }
    ];

    ptsLocal.forEach((pt, i) => {
        const gx = ob.cx + pt.x * ob.ux + pt.y * ob.nx;
        const gy = ob.cy + pt.x * ob.uy + pt.y * ob.ny;
        if (i === 0) shape.moveTo(gx, gy);
        else shape.lineTo(gx, gy);
    });

    return shape;
}

function buildUShape(ring, width) {
    const ob = getOrientedBounds(ring);
    
    const w = Math.min(width, ob.W * 0.4);
    const h = Math.min(width, ob.H * 0.4);

    const shape = new THREE.Shape();

    const ptsLocal = [
        { x: ob.minX, y: ob.maxY },
        { x: ob.minX, y: ob.minY },
        { x: ob.maxX, y: ob.minY },
        { x: ob.maxX, y: ob.maxY },
        { x: ob.maxX - w, y: ob.maxY },
        { x: ob.maxX - w, y: ob.minY + h },
        { x: ob.minX + w, y: ob.minY + h },
        { x: ob.minX + w, y: ob.maxY }
    ];

    ptsLocal.forEach((pt, i) => {
        const gx = ob.cx + pt.x * ob.ux + pt.y * ob.nx;
        const gy = ob.cy + pt.x * ob.uy + pt.y * ob.ny;
        if (i === 0) shape.moveTo(gx, gy);
        else shape.lineTo(gx, gy);
    });

    return shape;
}

// Generate textured building materials with window grids dynamically
function getBuildingMaterials(usage, floors) {
    let colorHex = '#e2e8f0';
    if (usage === 'Residential') {
        colorHex = '#d97706'; // warm amber facade, bright enough for first view
    } else if (usage === 'Commercial') {
        colorHex = '#64748b'; // steel facade without disappearing into the ground
    } else if (usage === 'MixedUse') {
        colorHex = '#256d85'; // teal-blue mixed-use facade
    } else if (usage === 'Civic') {
        colorHex = '#7c8da0'; // professional slate civic facade
    }

    const textures = createFacadeTextures(colorHex, usage, floors);
    textures.map.repeat.set(6, 1);
    textures.emissiveMap.repeat.set(6, 1);

    const tVal = (inTime && inTime.value) ? parseFloat(inTime.value) : 12.0;
    const isNight = tVal < 7.5 || tVal > 19.5;

    const wallMat = new THREE.MeshStandardMaterial({
        map: textures.map,
        emissiveMap: textures.emissiveMap,
        emissive: new THREE.Color(0xffffff),
        emissiveIntensity: isNight ? 1.0 : 0.0,
        roughness: 0.4,
        metalness: 0.08,
        transparent: true,
        opacity: 1.0
    });

    const roofMat = new THREE.MeshStandardMaterial({
        color: 0x6b7280, // concrete grey roof
        roughness: 0.8
    });

    return [roofMat, wallMat];
}

// Canvas-drawn texture mapping for realistic windows with randomized emissive maps
function createFacadeTextures(wallColor, usage, floors) {
    const canvas = document.createElement('canvas');
    canvas.width = 256;
    canvas.height = 512;
    const ctx = canvas.getContext('2d');

    const emCanvas = document.createElement('canvas');
    emCanvas.width = 256;
    emCanvas.height = 512;
    const emCtx = emCanvas.getContext('2d');

    // Draw base wall
    ctx.fillStyle = wallColor;
    ctx.fillRect(0, 0, 256, 512);

    // Emissive base is black (no glow on walls)
    emCtx.fillStyle = '#000000';
    emCtx.fillRect(0, 0, 256, 512);

    const isCommercial = usage === 'Commercial';
    const isMixedUse = usage === 'MixedUse';
    const isCivic = usage === 'Civic';
    
    // Window design details
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1.5;

    const cols = 4;
    const sliceH = 512 / floors;

    for (let f = 0; f < floors; f++) {
        const isGroundFloor = (f === floors - 1);
        const yStart = f * sliceH;
        
        // Window dimensions
        const winW = 32;
        const winH = Math.min(sliceH * 0.7, 40);
        const gapX = (256 - cols * winW) / (cols + 1);
        const gapY = (sliceH - winH) / 2;

        for (let c = 0; c < cols; c++) {
            const x = gapX + c * (winW + gapX);
            const y = yStart + gapY;

            if (isGroundFloor) {
                // Ground floor: retail shopfronts for MixedUse/Commercial, doors for others
                if (isMixedUse || isCommercial) {
                    // Glass shopfront (large windows)
                    ctx.fillStyle = '#7dd3fc'; // light sky blue glass
                    ctx.fillRect(x, yStart + 2, winW, sliceH - 4);
                    ctx.strokeRect(x, yStart + 2, winW, sliceH - 4);
                    
                    // Lit up shop window at night
                    const isLit = Math.random() < 0.8;
                    if (isLit) {
                        ctx.fillStyle = '#bae6fd';
                        ctx.fillRect(x + 2, yStart + 4, winW - 4, sliceH - 8);
                        emCtx.fillStyle = '#bae6fd';
                        emCtx.fillRect(x + 2, yStart + 4, winW - 4, sliceH - 8);
                    }
                } else {
                    // Entrance doors in center columns
                    if (c === 1 || c === 2) {
                        ctx.fillStyle = '#3f220f'; // dark wood
                        ctx.fillRect(x, yStart + 2, winW, sliceH - 2);
                        ctx.strokeRect(x, yStart + 2, winW, sliceH - 2);
                        
                        ctx.fillStyle = '#fef08a';
                        ctx.fillRect(x + 6, yStart + 8, winW - 12, sliceH * 0.3);
                        
                        const isLit = Math.random() < 0.7;
                        if (isLit) {
                            emCtx.fillStyle = '#fef08a';
                            emCtx.fillRect(x + 6, yStart + 8, winW - 12, sliceH * 0.3);
                        }
                    } else {
                        // Ground floor side window
                        ctx.fillStyle = '#1e293b';
                        ctx.fillRect(x, y, winW, winH);
                        ctx.strokeRect(x, y, winW, winH);
                        
                        const isLit = Math.random() < 0.45;
                        if (isLit) {
                            ctx.fillStyle = '#fef08a';
                            ctx.fillRect(x + 2, y + 2, winW - 4, winH - 4);
                            emCtx.fillStyle = '#fef08a';
                            emCtx.fillRect(x + 2, y + 2, winW - 4, winH - 4);
                        }
                    }
                }
            } else {
                // Upper floors
                ctx.fillStyle = (isCommercial || isMixedUse) ? '#1e3a8a' : (isCivic ? '#115e59' : '#3f3f46');
                ctx.fillRect(x, y, winW, winH);
                ctx.strokeRect(x, y, winW, winH);

                ctx.beginPath();
                ctx.moveTo(x + winW / 2, y);
                ctx.lineTo(x + winW / 2, y + winH);
                ctx.moveTo(x, y + winH / 2);
                ctx.lineTo(x + winW, y + winH / 2);
                ctx.stroke();

                const isLit = Math.random() < 0.48;
                if (isLit) {
                    const colorChoices = [
                        { lit: '#fef08a', em: '#eab308' }, // warm gold
                        { lit: '#ffedd5', em: '#f97316' }, // amber/orange
                        { lit: '#e0f2fe', em: '#0ea5e9' }, // cool blue
                        { lit: '#ccfbf1', em: '#0d9488' }  // soft teal
                    ];
                    
                    let idx = 0;
                    const rand = Math.random();
                    if (isCommercial) {
                        idx = rand < 0.5 ? 2 : (rand < 0.8 ? 3 : (rand < 0.9 ? 1 : 0));
                    } else if (usage === 'Residential') {
                        idx = rand < 0.5 ? 0 : (rand < 0.8 ? 1 : (rand < 0.9 ? 2 : 3));
                    } else {
                        idx = Math.floor(rand * 4);
                    }
                    
                    const choice = colorChoices[idx];
                    
                    ctx.fillStyle = choice.lit;
                    ctx.fillRect(x + 2, y + 2, winW - 4, winH - 4);
                    emCtx.fillStyle = choice.em;
                    emCtx.fillRect(x + 2, y + 2, winW - 4, winH - 4);
                }
            }
        }
    }

    const diffuseTex = new THREE.CanvasTexture(canvas);
    diffuseTex.wrapS = THREE.RepeatWrapping;
    diffuseTex.wrapT = THREE.RepeatWrapping;

    const emissiveTex = new THREE.CanvasTexture(emCanvas);
    emissiveTex.wrapS = THREE.RepeatWrapping;
    emissiveTex.wrapT = THREE.RepeatWrapping;

    return { map: diffuseTex, emissiveMap: emissiveTex };
}

// Hipped pitched roof generator with clay tiles
function buildHippedRoof(parentMesh, footprintPoints, height) {
    const topVerts = footprintPoints.map(pt => new THREE.Vector3(pt.x, height, -pt.y));
    const N = topVerts.length;

    let cx = 0, cz = 0;
    topVerts.forEach(v => { cx += v.x; cz += v.z; });
    cx /= N;
    cz /= N;
    const topCentroid = new THREE.Vector3(cx, height + 3.5, cz); // Ridge elevated by 3.5m

    const vertices = [];
    for (let i = 0; i < N; i++) {
        const v1 = topVerts[i];
        const v2 = topVerts[(i + 1) % N];

        vertices.push(v1.x, v1.y, v1.z);
        vertices.push(v2.x, v2.y, v2.z);
        vertices.push(topCentroid.x, topCentroid.y, topCentroid.z);
    }

    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    geom.computeVertexNormals();

    const mat = new THREE.MeshStandardMaterial({
        color: 0x991b1b, // red clay tiles
        roughness: 0.7,
        side: THREE.DoubleSide
    });
    mat.isRoofMesh = true;

    const mesh = new THREE.Mesh(geom, mat);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    parentMesh.add(mesh);
}

// Gable roof generator aligned with OBB longitudinal axis
function buildGableRoof(parentMesh, footprintPoints, height) {
    const ob = getOrientedBounds(footprintPoints);
    const N = footprintPoints.length;

    const midY = (ob.minY + ob.maxY) / 2;
    const ridgeH = 4.5; // height of the ridge above building roof height

    const topVerts = footprintPoints.map(pt => new THREE.Vector3(pt.x, height, -pt.y));

    // For each footprint vertex, project it onto the ridge line
    const ridgeVerts = footprintPoints.map(pt => {
        const rx = pt.x - ob.cx;
        const ry = pt.y - ob.cy;
        const lx = rx * ob.ux + ry * ob.uy;
        // Project to the center line of the OBB along local Y
        const rx_proj = lx * ob.ux + midY * ob.nx;
        const ry_proj = lx * ob.uy + midY * ob.ny;
        return new THREE.Vector3(ob.cx + rx_proj, height + ridgeH, -(ob.cy + ry_proj));
    });

    const vertices = [];
    for (let i = 0; i < N; i++) {
        const v1 = topVerts[i];
        const v2 = topVerts[(i + 1) % N];
        const vr1 = ridgeVerts[i];
        const vr2 = ridgeVerts[(i + 1) % N];

        // Triangle 1
        vertices.push(v1.x, v1.y, v1.z);
        vertices.push(v2.x, v2.y, v2.z);
        vertices.push(vr2.x, vr2.y, vr2.z);

        // Triangle 2
        vertices.push(v1.x, v1.y, v1.z);
        vertices.push(vr2.x, vr2.y, vr2.z);
        vertices.push(vr1.x, vr1.y, vr1.z);
    }

    const geom = new THREE.BufferGeometry();
    geom.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    geom.computeVertexNormals();

    const mat = new THREE.MeshStandardMaterial({
        color: 0x2563eb, // royal blue slate
        roughness: 0.65,
        side: THREE.DoubleSide
    });
    mat.isRoofMesh = true;

    const mesh = new THREE.Mesh(geom, mat);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    parentMesh.add(mesh);
}

// Mansard roof generator with steep sides and a flat top cap
function buildMansardRoof(parentMesh, footprintPoints, height) {
    const slopeH = 3.0; // Height of the steep slope
    const topH = height + slopeH;
    const insetVal = 1.8; // Inset distance for the top flat cap

    // Calculate inset points using offsetPolygonRing
    const innerRing = offsetPolygonRing(footprintPoints, insetVal);
    if (!innerRing || innerRing.length < 3) {
        // Fallback to hipped if offset fails
        buildHippedRoof(parentMesh, footprintPoints, height);
        return;
    }

    const N = footprintPoints.length;
    const topVerts = footprintPoints.map(pt => new THREE.Vector3(pt.x, height, -pt.y));
    const innerVerts = innerRing.map(pt => new THREE.Vector3(pt.x, topH, -pt.y));

    // 1. Build the steep outer sloped facets
    const vertices = [];
    for (let i = 0; i < N; i++) {
        const v1 = topVerts[i];
        const v2 = topVerts[(i + 1) % N];
        const vi1 = innerVerts[i % innerRing.length];
        const vi2 = innerVerts[(i + 1) % innerRing.length];

        // Triangle 1: v1, v2, vi2
        vertices.push(v1.x, v1.y, v1.z);
        vertices.push(v2.x, v2.y, v2.z);
        vertices.push(vi2.x, vi2.y, vi2.z);

        // Triangle 2: v1, vi2, vi1
        vertices.push(v1.x, v1.y, v1.z);
        vertices.push(vi2.x, vi2.y, vi2.z);
        vertices.push(vi1.x, vi1.y, vi1.z);
    }

    const slopeGeom = new THREE.BufferGeometry();
    slopeGeom.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
    slopeGeom.computeVertexNormals();

    const mat = new THREE.MeshStandardMaterial({
        color: 0xd97706, // copper amber mansard tile
        roughness: 0.7,
        side: THREE.DoubleSide
    });
    mat.isRoofMesh = true;

    const slopeMesh = new THREE.Mesh(slopeGeom, mat);
    slopeMesh.castShadow = true;
    slopeMesh.receiveShadow = true;
    parentMesh.add(slopeMesh);

    // 2. Build the flat top cap
    const capShape = new THREE.Shape();
    innerRing.forEach((pt, i) => {
        if (i === 0) capShape.moveTo(pt.x, pt.y);
        else capShape.lineTo(pt.x, pt.y);
    });

    const capGeom = new THREE.ShapeGeometry(capShape);
    capGeom.rotateX(-Math.PI / 2);
    capGeom.translate(0, topH, 0);

    const capMat = new THREE.MeshStandardMaterial({
        color: 0x1e293b, // dark flat cap roof
        roughness: 0.8
    });
    capMat.isRoofMesh = true;

    const capMesh = new THREE.Mesh(capGeom, capMat);
    capMesh.castShadow = true;
    capMesh.receiveShadow = true;
    parentMesh.add(capMesh);
}

// Flat roof details (helipad, HVAC boxes, solar panels)
function addRooftopDetails(parentMesh, insetRing, height, usage) {
    let cx = 0, cy = 0;
    insetRing.forEach(pt => { cx += pt.x; cy += pt.y; });
    cx /= insetRing.length;
    cy /= insetRing.length;

    // Penthouse/elevator shaft
    const pentGeom = new THREE.BoxGeometry(6, 3, 6);
    const pentMat = new THREE.MeshStandardMaterial({ color: 0x475569 });
    const penthouse = new THREE.Mesh(pentGeom, pentMat);
    penthouse.position.set(cx, height + 1.5, -cy);
    penthouse.castShadow = true;
    parentMesh.add(penthouse);

    // HVAC boxes
    const hvacGeom = new THREE.BoxGeometry(2, 1.2, 2);
    const hvacMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.9, roughness: 0.2 });
    for (let i = 0; i < 2; i++) {
        const hvac = new THREE.Mesh(hvacGeom, hvacMat);
        hvac.position.set(cx - 6 + i * 12, height + 0.6, -cy + 6);
        hvac.castShadow = true;
        parentMesh.add(hvac);
    }

    // Commercial Helipad painting
    if (usage === 'Commercial' || usage === 'MixedUse') {
        const padGeom = new THREE.CylinderGeometry(5, 5, 0.1, 32);
        
        // Draw Helipad letter canvas texture
        const padCanvas = document.createElement('canvas');
        padCanvas.width = 128;
        padCanvas.height = 128;
        const padCtx = padCanvas.getContext('2d');
        padCtx.fillStyle = '#4b5563'; // concrete pad
        padCtx.fillRect(0, 0, 128, 128);
        
        // Draw white circle
        padCtx.strokeStyle = '#ffffff';
        padCtx.lineWidth = 6;
        padCtx.beginPath();
        padCtx.arc(64, 64, 40, 0, Math.PI * 2);
        padCtx.stroke();
        
        // Draw H letter
        padCtx.fillStyle = '#ffffff';
        padCtx.font = 'bold 50px Arial';
        padCtx.textAlign = 'center';
        padCtx.textBaseline = 'middle';
        padCtx.fillText('H', 64, 64);
        
        const padTex = new THREE.CanvasTexture(padCanvas);
        const padMat = new THREE.MeshStandardMaterial({ map: padTex, roughness: 0.7 });
        const pad = new THREE.Mesh(padGeom, padMat);
        pad.position.set(cx, height + 0.05, -cy - 5);
        pad.receiveShadow = true;
        parentMesh.add(pad);
    }

    // Solar panels for Civic/Institutional
    if (usage === 'Civic') {
        const panelGeom = new THREE.BoxGeometry(3, 0.1, 1.6);
        const panelMat = new THREE.MeshStandardMaterial({ color: 0x1d4ed8, roughness: 0.1 });
        for (let i = -1; i <= 1; i++) {
            const panel = new THREE.Mesh(panelGeom, panelMat);
            panel.rotation.x = -Math.PI / 6;
            panel.position.set(cx + i * 5, height + 0.5, -cy - 6);
            panel.castShadow = true;
            parentMesh.add(panel);
        }
    }
}

// 3D Semi-transparent Wireframe Zoning Envelope
function buildZoningEnvelope(item, insetRing, maxHeight, isViolated) {
    const envShape = new THREE.Shape();
    insetRing.forEach((pt, i) => {
        if (i === 0) envShape.moveTo(pt.x, pt.y);
        else envShape.lineTo(pt.x, pt.y);
    });

    const envGeom = new THREE.ExtrudeGeometry(envShape, { depth: maxHeight, bevelEnabled: false });
    envGeom.rotateX(-Math.PI / 2);

    const envColor = isViolated ? 0xef4444 : 0x06b6d4; // Holographic cyan glow for compliance
    const envMat = new THREE.MeshStandardMaterial({
        color: envColor,
        transparent: true,
        opacity: isViolated ? 0.22 : 0.05,
        side: THREE.DoubleSide,
        depthWrite: false
    });

    const envMesh = new THREE.Mesh(envGeom, envMat);
    envMesh.visible = toggleZoningEl ? toggleZoningEl.checked : false;
    scene.add(envMesh);
    item.zoningMesh = envMesh;

    const edges = new THREE.EdgesGeometry(envGeom);
    const lineMat = new THREE.LineBasicMaterial({
        color: envColor,
        linewidth: 2.0,
        transparent: true,
        opacity: isViolated ? 0.8 : 0.45
    });
    const line = new THREE.LineSegments(edges, lineMat);
    envMesh.add(line);

    // Add dashed vertical column tracks at each corner of the zoning volume
    const colMat = new THREE.LineDashedMaterial({
        color: envColor,
        dashSize: 1.2,
        gapSize: 0.8,
        transparent: true,
        opacity: isViolated ? 0.85 : 0.55
    });

    insetRing.forEach(pt => {
        const points = [
            new THREE.Vector3(pt.x, 0.05, -pt.y),
            new THREE.Vector3(pt.x, maxHeight, -pt.y)
        ];
        const colGeom = new THREE.BufferGeometry().setFromPoints(points);
        const colLine = new THREE.Line(colGeom, colMat);
        colLine.computeLineDistances();
        envMesh.add(colLine);
    });
}

// Draw a red guideline if setback is too large to fit a building footprint
function drawSetbackErrorLine(item) {
    const borderPoints = item.outerRing.map(pt => new THREE.Vector3(pt.x, 0.15, -pt.y));
    borderPoints.push(borderPoints[0].clone());
    const errorGeom = new THREE.BufferGeometry().setFromPoints(borderPoints);
    const errorMat = new THREE.LineBasicMaterial({ color: 0xef4444, linewidth: 3 });
    const errorLine = new THREE.Line(errorGeom, errorMat);
    scene.add(errorLine);
    item.setbackMesh = errorLine;
}

function makePlanPoint(x, y) {
    return { x, y };
}

function planToVector3(pt, y = 0.02) {
    return new THREE.Vector3(pt.x, y, -pt.y);
}

function addPlanQuad(group, start, end, nx, ny, halfWidth, y, material) {
    const p1 = makePlanPoint(start.x + nx * halfWidth, start.y + ny * halfWidth);
    const p2 = makePlanPoint(end.x + nx * halfWidth, end.y + ny * halfWidth);
    const p3 = makePlanPoint(end.x - nx * halfWidth, end.y - ny * halfWidth);
    const p4 = makePlanPoint(start.x - nx * halfWidth, start.y - ny * halfWidth);
    const geom = new THREE.BufferGeometry();
    geom.setFromPoints([
        planToVector3(p1, y),
        planToVector3(p2, y),
        planToVector3(p3, y),
        planToVector3(p4, y)
    ]);
    geom.setIndex([0, 1, 2, 0, 2, 3]);
    geom.computeVertexNormals();
    const mesh = new THREE.Mesh(geom, material);
    mesh.receiveShadow = true;
    group.add(mesh);
    return mesh;
}

function addOffsetLine(group, start, end, nx, ny, offset, y, material, dashed = false) {
    const a = makePlanPoint(start.x + nx * offset, start.y + ny * offset);
    const b = makePlanPoint(end.x + nx * offset, end.y + ny * offset);
    const geom = new THREE.BufferGeometry().setFromPoints([planToVector3(a, y), planToVector3(b, y)]);
    const line = new THREE.Line(geom, material);
    if (dashed && line.computeLineDistances) line.computeLineDistances();
    group.add(line);
    return line;
}

function classifyRoadWidth(width) {
    if (width >= 32) {
        return { label: "Boulevard + Tram", lanesPerDirection: 2, laneWidth: 3.25, bikeWidth: 1.8, medianWidth: 4.0, sidewalkWidth: Math.min(4.5, Math.max(3.0, width * 0.12)), transit: "tram" };
    }
    if (width >= 24) {
        return { label: "Urban Avenue", lanesPerDirection: 2, laneWidth: 3.25, bikeWidth: 1.5, medianWidth: 2.4, sidewalkWidth: Math.min(4.0, Math.max(2.5, width * 0.12)), transit: null };
    }
    if (width >= 15) {
        return { label: "Collector Street", lanesPerDirection: 1, laneWidth: 3.2, bikeWidth: 1.4, medianWidth: 1.0, sidewalkWidth: Math.min(3.2, Math.max(2.0, width * 0.13)), transit: null };
    }
    if (width >= 10) {
        return { label: "Two-Way Local Street", lanesPerDirection: 1, laneWidth: 3.0, bikeWidth: 0, medianWidth: 0, sidewalkWidth: Math.min(2.4, Math.max(1.6, width * 0.15)), transit: null };
    }
    return { label: "Shared Slow Street", lanesPerDirection: 1, laneWidth: Math.max(2.7, width - 3.2), bikeWidth: 0, medianWidth: 0, sidewalkWidth: Math.min(1.6, Math.max(1.0, width * 0.14)), transit: null };
}

function getParcelSegments(item) {
    const ring = item.outerRing || [];
    const segments = [];
    for (let i = 0; i < ring.length; i++) {
        const p1 = ring[i];
        const p2 = ring[(i + 1) % ring.length];
        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        const len = Math.sqrt(dx * dx + dy * dy);
        if (len < 6) continue;
        const ux = dx / len;
        const uy = dy / len;
        segments.push({ item, index: i, p1, p2, len, ux, uy, nx: -uy, ny: ux });
    }
    return segments;
}

function inferRoadCorridors() {
    const allSegments = parcelFeatures.flatMap(getParcelSegments);
    const candidates = [];

    for (let i = 0; i < allSegments.length; i++) {
        for (let j = i + 1; j < allSegments.length; j++) {
            const a = allSegments[i];
            const b = allSegments[j];
            if (a.item === b.item) continue;

            const dot = a.ux * b.ux + a.uy * b.uy;
            if (Math.abs(dot) < 0.94) continue;

            const axis = { x: a.ux, y: a.uy };
            const normal = { x: a.nx, y: a.ny };
            const a0 = a.p1.x * axis.x + a.p1.y * axis.y;
            const a1 = a.p2.x * axis.x + a.p2.y * axis.y;
            const b0 = b.p1.x * axis.x + b.p1.y * axis.y;
            const b1 = b.p2.x * axis.x + b.p2.y * axis.y;
            const aMin = Math.min(a0, a1);
            const aMax = Math.max(a0, a1);
            const bMin = Math.min(b0, b1);
            const bMax = Math.max(b0, b1);
            let overlapStart = Math.max(aMin, bMin);
            let overlapEnd = Math.min(aMax, bMax);
            const overlapLength = overlapEnd - overlapStart;
            if (overlapLength < 8) continue;

            const d0 = (b.p1.x - a.p1.x) * normal.x + (b.p1.y - a.p1.y) * normal.y;
            const d1 = (b.p2.x - a.p1.x) * normal.x + (b.p2.y - a.p1.y) * normal.y;
            if (Math.abs(d0 - d1) > 3.0) continue;

            const signedWidth = (d0 + d1) / 2;
            const width = Math.abs(signedWidth);
            if (width < 6 || width > 70) continue;

            const trim = Math.min(4, overlapLength * 0.18);
            overlapStart += trim;
            overlapEnd -= trim;
            if (overlapEnd <= overlapStart) continue;

            const baseOffset = a.p1.x * normal.x + a.p1.y * normal.y;
            const centerOffset = baseOffset + signedWidth / 2;
            const start = makePlanPoint(axis.x * overlapStart + normal.x * centerOffset, axis.y * overlapStart + normal.y * centerOffset);
            const end = makePlanPoint(axis.x * overlapEnd + normal.x * centerOffset, axis.y * overlapEnd + normal.y * centerOffset);

            candidates.push({ start, end, ux: axis.x, uy: axis.y, nx: normal.x, ny: normal.y, width, length: overlapEnd - overlapStart });
        }
    }

    candidates.sort((a, b) => (a.width - b.width) || (b.length - a.length));
    const accepted = [];
    candidates.forEach(candidate => {
        const midA = makePlanPoint((candidate.start.x + candidate.end.x) / 2, (candidate.start.y + candidate.end.y) / 2);
        const tooSimilar = accepted.some(existing => {
            const midB = makePlanPoint((existing.start.x + existing.end.x) / 2, (existing.start.y + existing.end.y) / 2);
            const dist = Math.hypot(midA.x - midB.x, midA.y - midB.y);
            const dirDot = Math.abs(candidate.ux * existing.ux + candidate.uy * existing.uy);
            return dirDot > 0.96 && dist < Math.min(candidate.width, existing.width) * 0.5;
        });
        if (!tooSimilar) accepted.push(candidate);
    });
    return accepted;
}

function renderRoadCorridor(corridor) {
    const profile = classifyRoadWidth(corridor.width);
    const group = new THREE.Group();
    group.userData = { isRoadCorridor: true, profile };

    const asphaltWidth = Math.min(
        Math.max(3.2, corridor.width - profile.sidewalkWidth * 2),
        profile.laneWidth * profile.lanesPerDirection * 2 + profile.medianWidth + profile.bikeWidth * 2
    );

    const asphaltMat = new THREE.MeshStandardMaterial({ color: 0x1f2933, roughness: 0.92, metalness: 0.02, polygonOffset: true, polygonOffsetFactor: -1, polygonOffsetUnits: -1 });
    addPlanQuad(group, corridor.start, corridor.end, corridor.nx, corridor.ny, asphaltWidth / 2, 0.018, asphaltMat);

    if (profile.bikeWidth > 0) {
        const bikeMat = new THREE.MeshStandardMaterial({ color: 0x0f766e, roughness: 0.85 });
        const bikeCenter = asphaltWidth / 2 - profile.bikeWidth / 2;
        addPlanQuad(group, corridor.start, corridor.end, corridor.nx, corridor.ny, profile.bikeWidth / 2, 0.024, bikeMat).position.set(corridor.nx * bikeCenter, 0, -corridor.ny * bikeCenter);
        addPlanQuad(group, corridor.start, corridor.end, corridor.nx, corridor.ny, profile.bikeWidth / 2, 0.024, bikeMat).position.set(-corridor.nx * bikeCenter, 0, corridor.ny * bikeCenter);
    }

    if (profile.medianWidth > 0) {
        const medianMat = new THREE.MeshStandardMaterial({ color: 0x166534, roughness: 0.95 });
        addPlanQuad(group, corridor.start, corridor.end, corridor.nx, corridor.ny, profile.medianWidth / 2, 0.035, medianMat);
    }

    if (profile.medianWidth === 0) {
        const centerLineMat = new THREE.LineDashedMaterial({ color: 0xf8fafc, dashSize: 2.5, gapSize: 2.0, transparent: true, opacity: 0.8 });
        addOffsetLine(group, corridor.start, corridor.end, corridor.nx, corridor.ny, 0, 0.05, centerLineMat, true);
    }

    const laneLineMat = new THREE.LineDashedMaterial({ color: 0xe5e7eb, dashSize: 3.0, gapSize: 3.5, transparent: true, opacity: 0.55 });
    for (let side = -1; side <= 1; side += 2) {
        for (let lane = 1; lane < profile.lanesPerDirection; lane++) {
            const offset = side * (profile.medianWidth / 2 + lane * profile.laneWidth);
            addOffsetLine(group, corridor.start, corridor.end, corridor.nx, corridor.ny, offset, 0.052, laneLineMat, true);
        }
    }

    if (profile.transit === "tram") {
        const railMat = new THREE.LineBasicMaterial({ color: 0xcbd5e1, transparent: true, opacity: 0.9 });
        addOffsetLine(group, corridor.start, corridor.end, corridor.nx, corridor.ny, -0.75, 0.065, railMat);
        addOffsetLine(group, corridor.start, corridor.end, corridor.nx, corridor.ny, 0.75, 0.065, railMat);
    }

    corridor.profile = profile;
    corridor.asphaltWidth = asphaltWidth;
    scene.add(group);
    roadMeshes.push(group);
    return { group, profile, asphaltWidth };
}

function cross2D(ax, ay, bx, by) {
    return ax * by - ay * bx;
}

function lineIntersection2D(a0, a1, b0, b1) {
    const rx = a1.x - a0.x;
    const ry = a1.y - a0.y;
    const sx = b1.x - b0.x;
    const sy = b1.y - b0.y;
    const denom = cross2D(rx, ry, sx, sy);
    if (Math.abs(denom) < 0.0001) return null;

    const qpx = b0.x - a0.x;
    const qpy = b0.y - a0.y;
    const t = cross2D(qpx, qpy, sx, sy) / denom;
    const u = cross2D(qpx, qpy, rx, ry) / denom;
    if (t < -0.02 || t > 1.02 || u < -0.02 || u > 1.02) return null;
    return {
        point: makePlanPoint(a0.x + rx * t, a0.y + ry * t),
        t,
        u
    };
}

function getCorridorJunctionReach(corridor) {
    return Math.max(18, Math.min(56, corridor.width * 1.8 + 10));
}

function getExtendedCorridorSegment(corridor) {
    const reach = getCorridorJunctionReach(corridor);
    return {
        start: makePlanPoint(corridor.start.x - corridor.ux * reach, corridor.start.y - corridor.uy * reach),
        end: makePlanPoint(corridor.end.x + corridor.ux * reach, corridor.end.y + corridor.uy * reach),
        reach
    };
}

function closestPointOnSegment(pt, a, b) {
    const vx = b.x - a.x;
    const vy = b.y - a.y;
    const wx = pt.x - a.x;
    const wy = pt.y - a.y;
    const lenSq = vx * vx + vy * vy;
    if (lenSq <= 0.0001) return makePlanPoint(a.x, a.y);
    const t = Math.max(0, Math.min(1, (wx * vx + wy * vy) / lenSq));
    return makePlanPoint(a.x + vx * t, a.y + vy * t);
}

function distancePointToSegment(pt, a, b) {
    const closest = closestPointOnSegment(pt, a, b);
    return Math.hypot(pt.x - closest.x, pt.y - closest.y);
}

function shouldRenderRoundabout(connected) {
    if (connected.length >= 3) return true;
    if (connected.length !== 2) return false;
    const a = connected[0].corridor;
    const b = connected[1].corridor;
    const dirDot = Math.abs(a.ux * b.ux + a.uy * b.uy);
    const maxWidth = Math.max(a.width, b.width);
    return dirDot < 0.45 && maxWidth >= 12;
}

function inferRoadIntersections(corridors) {
    const nodes = [];

    const addOrMergeNode = (point, corridorIndices, strength = 1) => {
        const maxWidth = corridorIndices.reduce((acc, idx) => Math.max(acc, corridors[idx]?.width || 0), 0);
        const mergeDistance = Math.max(8, Math.min(28, maxWidth * 0.55 + 5));
        let node = nodes.find(existing => Math.hypot(existing.point.x - point.x, existing.point.y - point.y) < Math.max(existing.mergeDistance, mergeDistance));
        if (!node) {
            node = { point: makePlanPoint(point.x, point.y), corridorIndices: new Set(), hits: 0, mergeDistance };
            nodes.push(node);
        } else {
            const weight = Math.max(1, node.hits);
            node.point.x = (node.point.x * weight + point.x * strength) / (weight + strength);
            node.point.y = (node.point.y * weight + point.y * strength) / (weight + strength);
            node.mergeDistance = Math.max(node.mergeDistance, mergeDistance);
        }
        corridorIndices.forEach(idx => node.corridorIndices.add(idx));
        node.hits += strength;
    };

    for (let i = 0; i < corridors.length; i++) {
        for (let j = i + 1; j < corridors.length; j++) {
            const a = corridors[i];
            const b = corridors[j];
            const dirDot = Math.abs(a.ux * b.ux + a.uy * b.uy);
            if (dirDot > 0.86) continue;
            const hit = lineIntersection2D(a.start, a.end, b.start, b.end);
            if (hit) {
                addOrMergeNode(hit.point, [i, j], 2);
            }

            const extA = getExtendedCorridorSegment(a);
            const extB = getExtendedCorridorSegment(b);
            const extendedHit = lineIntersection2D(extA.start, extA.end, extB.start, extB.end);
            if (extendedHit) {
                const actualDistA = distancePointToSegment(extendedHit.point, a.start, a.end);
                const actualDistB = distancePointToSegment(extendedHit.point, b.start, b.end);
                if (actualDistA <= extA.reach + a.width * 0.5 && actualDistB <= extB.reach + b.width * 0.5) {
                    addOrMergeNode(extendedHit.point, [i, j], 1);
                }
            }
        }
    }

    const endpoints = [];
    corridors.forEach((corridor, idx) => {
        endpoints.push({ point: corridor.start, idx });
        endpoints.push({ point: corridor.end, idx });
    });

    endpoints.forEach(endpoint => {
        const nearby = endpoints.filter(other => {
            if (other.idx === endpoint.idx) return false;
            const width = Math.max(corridors[endpoint.idx].width, corridors[other.idx].width);
            const threshold = Math.max(10, Math.min(34, width * 0.55 + 8));
            return Math.hypot(endpoint.point.x - other.point.x, endpoint.point.y - other.point.y) <= threshold;
        });
        if (nearby.length > 0) {
            const all = [endpoint, ...nearby];
            const avg = all.reduce((acc, item) => {
                acc.x += item.point.x;
                acc.y += item.point.y;
                return acc;
            }, { x: 0, y: 0 });
            avg.x /= all.length;
            avg.y /= all.length;
            addOrMergeNode(makePlanPoint(avg.x, avg.y), [...new Set(all.map(item => item.idx))], 1);
        }
    });

    return nodes.map(node => {
        const connected = corridors
            .map((corridor, idx) => ({ corridor, idx }))
            .filter(({ corridor, idx }) => {
                if (node.corridorIndices.has(idx)) return true;
                const tolerance = Math.max(7, corridor.width * 0.45);
                return distancePointToSegment(node.point, corridor.start, corridor.end) <= tolerance;
            });
        const maxWidth = connected.reduce((acc, item) => Math.max(acc, item.corridor.width), 0);
        const radius = Math.max(6, Math.min(18, maxWidth * 0.32 + connected.length * 1.1));
        const kind = shouldRenderRoundabout(connected) ? 'roundabout' : 'signalized';
        return {
            point: node.point,
            connected,
            radius,
            kind
        };
    }).filter(node => node.connected.length >= 2);
}

function addCrosswalk(group, node, corridor) {
    const profile = corridor.profile || classifyRoadWidth(corridor.width);
    const asphaltWidth = corridor.asphaltWidth || Math.max(4, corridor.width - profile.sidewalkWidth * 2);
    const center = node.point;
    const mid = makePlanPoint((corridor.start.x + corridor.end.x) / 2, (corridor.start.y + corridor.end.y) / 2);
    const awaySign = ((mid.x - center.x) * corridor.ux + (mid.y - center.y) * corridor.uy) >= 0 ? 1 : -1;
    const stripeMat = new THREE.MeshStandardMaterial({ color: 0xf8fafc, roughness: 0.75, transparent: true, opacity: 0.92 });
    const halfCross = Math.min(asphaltWidth * 0.5 + 0.8, corridor.width * 0.5 - 0.6);
    const baseOffset = node.radius + 2.4;
    const stripeCount = 5;
    const stripeGap = 0.82;

    for (let i = 0; i < stripeCount; i++) {
        const alongOffset = baseOffset + (i - (stripeCount - 1) / 2) * stripeGap;
        const stripeCenter = makePlanPoint(
            center.x + corridor.ux * awaySign * alongOffset,
            center.y + corridor.uy * awaySign * alongOffset
        );
        const a = makePlanPoint(stripeCenter.x - corridor.nx * halfCross, stripeCenter.y - corridor.ny * halfCross);
        const b = makePlanPoint(stripeCenter.x + corridor.nx * halfCross, stripeCenter.y + corridor.ny * halfCross);
        addPlanQuad(group, a, b, corridor.ux * awaySign, corridor.uy * awaySign, 0.22, 0.085, stripeMat);
    }
}

function addIntersectionApproach(group, node, corridor, material) {
    const profile = corridor.profile || classifyRoadWidth(corridor.width);
    const asphaltWidth = corridor.asphaltWidth || Math.max(4, corridor.width - profile.sidewalkWidth * 2);
    const center = node.point;
    const closest = closestPointOnSegment(center, corridor.start, corridor.end);
    const dist = Math.hypot(center.x - closest.x, center.y - closest.y);
    if (dist < node.radius * 0.6) return;

    const from = makePlanPoint(
        center.x + ((closest.x - center.x) / dist) * node.radius * 0.25,
        center.y + ((closest.y - center.y) / dist) * node.radius * 0.25
    );
    addPlanQuad(group, from, closest, corridor.nx, corridor.ny, asphaltWidth / 2, 0.062, material);
}

function addRoundaboutDirectionMarkings(group, node, material) {
    const ringRadius = node.radius * 0.76;
    const markerGeom = new THREE.BoxGeometry(1.9, 0.035, 0.42);
    for (let i = 0; i < 8; i++) {
        const angle = (i / 8) * Math.PI * 2;
        const marker = new THREE.Mesh(markerGeom, material);
        marker.position.set(
            node.point.x + Math.cos(angle) * ringRadius,
            0.14,
            -node.point.y - Math.sin(angle) * ringRadius
        );
        marker.rotation.y = -angle + Math.PI * 0.5;
        marker.receiveShadow = true;
        group.add(marker);
    }
}

function buildTrafficSignal(x, z, heading) {
    const group = new THREE.Group();
    group.position.set(x, 0, z);
    group.rotation.y = heading;

    const poleMat = new THREE.MeshStandardMaterial({ color: 0x334155, roughness: 0.65, metalness: 0.2 });
    const housingMat = new THREE.MeshStandardMaterial({ color: 0x111827, roughness: 0.7 });
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.08, 3.2, 10), poleMat);
    pole.position.y = 1.6;
    pole.castShadow = true;
    group.add(pole);

    const arm = new THREE.Mesh(new THREE.BoxGeometry(1.15, 0.08, 0.08), poleMat);
    arm.position.set(0.5, 3.05, 0);
    arm.castShadow = true;
    group.add(arm);

    const housing = new THREE.Mesh(new THREE.BoxGeometry(0.34, 1.0, 0.24), housingMat);
    housing.position.set(1.05, 2.75, -0.04);
    housing.castShadow = true;
    group.add(housing);

    const lampColors = [0xef4444, 0xfacc15, 0x22c55e];
    lampColors.forEach((color, idx) => {
        const lampMat = new THREE.MeshStandardMaterial({
            color,
            emissive: color,
            emissiveIntensity: idx === 2 ? 0.85 : 0.25,
            roughness: 0.35
        });
        const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.095, 12, 12), lampMat);
        lamp.position.set(1.05, 3.06 - idx * 0.28, -0.18);
        group.add(lamp);
    });

    return group;
}

function addIntersectionSignals(group, node, corridor) {
    const profile = corridor.profile || classifyRoadWidth(corridor.width);
    const asphaltWidth = corridor.asphaltWidth || Math.max(4, corridor.width - profile.sidewalkWidth * 2);
    const center = node.point;
    const mid = makePlanPoint((corridor.start.x + corridor.end.x) / 2, (corridor.start.y + corridor.end.y) / 2);
    const awaySign = ((mid.x - center.x) * corridor.ux + (mid.y - center.y) * corridor.uy) >= 0 ? 1 : -1;
    const signalDistance = node.radius + 5.0;
    const sideOffset = asphaltWidth * 0.5 + 1.2;
    const heading = Math.atan2(-corridor.uy * awaySign, corridor.ux * awaySign);

    [-1, 1].forEach(side => {
        const x = center.x + corridor.ux * awaySign * signalDistance + corridor.nx * side * sideOffset;
        const y = center.y + corridor.uy * awaySign * signalDistance + corridor.ny * side * sideOffset;
        group.add(buildTrafficSignal(x, -y, heading));
    });
}

function renderRoadIntersections(corridors) {
    const nodes = inferRoadIntersections(corridors);
    const asphaltMat = new THREE.MeshStandardMaterial({ color: 0x202a33, roughness: 0.94, metalness: 0.02, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -2 });
    const approachMat = new THREE.MeshStandardMaterial({ color: 0x202a33, roughness: 0.94, metalness: 0.02, polygonOffset: true, polygonOffsetFactor: -3, polygonOffsetUnits: -3 });
    const islandMat = new THREE.MeshStandardMaterial({ color: 0x166534, roughness: 0.95 });
    const curbMat = new THREE.MeshStandardMaterial({ color: 0xe5e7eb, roughness: 0.8 });
    const markingMat = new THREE.MeshStandardMaterial({ color: 0xf8fafc, roughness: 0.8, transparent: true, opacity: 0.85 });

    nodes.forEach(node => {
        const group = new THREE.Group();
        group.userData = { isRoadIntersection: true, kind: node.kind };

        const asphalt = new THREE.Mesh(new THREE.CircleGeometry(node.radius + 2.8, 48), asphaltMat);
        asphalt.rotation.x = -Math.PI / 2;
        asphalt.position.set(node.point.x, 0.055, -node.point.y);
        asphalt.receiveShadow = true;
        group.add(asphalt);

        if (node.kind === 'roundabout') {
            const islandRadius = Math.max(2.4, node.radius * 0.42);
            const island = new THREE.Mesh(new THREE.CircleGeometry(islandRadius, 40), islandMat);
            island.rotation.x = -Math.PI / 2;
            island.position.set(node.point.x, 0.095, -node.point.y);
            island.receiveShadow = true;
            group.add(island);

            const curb = new THREE.Mesh(new THREE.TorusGeometry(islandRadius + 0.18, 0.08, 8, 48), curbMat);
            curb.rotation.x = Math.PI / 2;
            curb.position.set(node.point.x, 0.16, -node.point.y);
            curb.castShadow = true;
            group.add(curb);

            const laneRing = new THREE.Mesh(new THREE.TorusGeometry(node.radius * 0.72, 0.035, 6, 56), markingMat);
            laneRing.rotation.x = Math.PI / 2;
            laneRing.position.set(node.point.x, 0.12, -node.point.y);
            group.add(laneRing);

            addRoundaboutDirectionMarkings(group, node, markingMat);
        }

        node.connected.forEach(({ corridor }) => {
            addIntersectionApproach(group, node, corridor, approachMat);
            addCrosswalk(group, node, corridor);
            addIntersectionSignals(group, node, corridor);
        });

        scene.add(group);
        intersectionMeshes.push(group);
    });

    return nodes;
}

// Generate animated low-poly traffic cars on inferred road corridors between parcel blocks
function generateTrafficCars() {
    // Clear old traffic cars
    trafficCars.forEach(car => {
        if (car.carMesh) {
            scene.remove(car.carMesh);
            disposeObject3D(car.carMesh);
        }
    });
    trafficCars = [];

    roadMeshes.forEach(mesh => {
        scene.remove(mesh);
        disposeObject3D(mesh);
    });
    roadMeshes = [];

    intersectionMeshes.forEach(mesh => {
        scene.remove(mesh);
        disposeObject3D(mesh);
    });
    intersectionMeshes = [];

    const corridors = inferRoadCorridors();
    const colors = [0xef4444, 0x3b82f6, 0xf59e0b, 0x10b981, 0xf8fafc, 0x8b5cf6];

    corridors.forEach(corridor => {
        const rendered = renderRoadCorridor(corridor);
        const profile = rendered.profile;
        const baseOffset = profile.medianWidth / 2 + profile.laneWidth / 2;
        const laneOffsets = [-baseOffset, baseOffset];

        if (profile.lanesPerDirection > 1) {
            laneOffsets.push(-(baseOffset + profile.laneWidth), baseOffset + profile.laneWidth);
        }

        laneOffsets.forEach((laneOffset, idx) => {
            const carColor = colors[(idx + Math.floor(Math.random() * colors.length)) % colors.length];
            const carMesh = buildDetailedCar(carColor, 1.35);
            scene.add(carMesh);

            trafficCars.push({
                carMesh,
                path: [corridor.start, corridor.end],
                nx: corridor.nx,
                ny: corridor.ny,
                laneOffset,
                direction: laneOffset < 0 ? 1 : -1,
                speed: 0.0015 + Math.random() * 0.0012,
                progress: Math.random()
            });
        });
    });

    const intersections = renderRoadIntersections(corridors);
    updateLayersVisibility();

    window.planxDebug = {
        roadCorridors: corridors.map(corridor => ({
            width: Number(corridor.width.toFixed(2)),
            length: Number(corridor.length.toFixed(2)),
            profile: classifyRoadWidth(corridor.width).label
        })),
        intersections: intersections.map(node => ({
            kind: node.kind,
            arms: node.connected.length,
            radius: Number(node.radius.toFixed(1))
        })),
        trafficCars: trafficCars.length
    };

    // Make sure headlights match current slider value immediately
    updateSolarPhysics((inTime && inTime.value) ? parseFloat(inTime.value) : 12.0);
}

// Drive cars along inferred road centerlines
function updateTraffic() {
    let maxHeadingError = 0;
    let headingChecks = 0;

    trafficCars.forEach(car => {
        if (car.path && car.path.length === 2) {
            car.progress += car.speed * car.direction;
            if (car.progress > 1) car.progress -= 1;
            if (car.progress < 0) car.progress += 1;

            const pt1 = car.path[0];
            const pt2 = car.path[1];
            const t = car.progress;
            const x = pt1.x + (pt2.x - pt1.x) * t + car.nx * car.laneOffset;
            const y = pt1.y + (pt2.y - pt1.y) * t + car.ny * car.laneOffset;

            car.carMesh.position.set(x, 0.05, -y);
            const dx = pt2.x - pt1.x;
            const dy = pt2.y - pt1.y;
            const heading = Math.atan2(dy, dx) + (car.direction < 0 ? Math.PI : 0);
            car.carMesh.rotation.y = heading;
            maxHeadingError = Math.max(maxHeadingError, Math.abs(normalizeAngleDelta(car.carMesh.rotation.y - heading)));
            headingChecks++;
            return;
        }

        const ring = car.roadRing;
        if (!ring || ring.length < 2) return;
        car.progress += car.speed;
        
        // Find segment indices based on progress
        const idx1 = Math.floor(car.progress) % ring.length;
        const idx2 = (idx1 + 1) % ring.length;
        const segmentProgress = car.progress % 1.0;

        const pt1 = ring[idx1];
        const pt2 = ring[idx2];

        // Interpolate position
        const x = pt1.x + (pt2.x - pt1.x) * segmentProgress;
        const z = - (pt1.y + (pt2.y - pt1.y) * segmentProgress);

        car.carMesh.position.set(x, 0.05, z);

        // Calculate heading rotation
        const dx = pt2.x - pt1.x;
        const dy = pt2.y - pt1.y;
        const heading = Math.atan2(dy, dx);
        car.carMesh.rotation.y = heading;
        maxHeadingError = Math.max(maxHeadingError, Math.abs(normalizeAngleDelta(car.carMesh.rotation.y - heading)));
        headingChecks++;
    });

    if (window.planxDebug) {
        window.planxDebug.trafficHeadingMaxError = headingChecks > 0 ? Number(maxHeadingError.toFixed(6)) : 0;
    }
}

function normalizeAngleDelta(angle) {
    return Math.atan2(Math.sin(angle), Math.cos(angle));
}

// Helper to traverse up the parent chain to find the associated parcel item
function getParcelItemFromObject(obj) {
    let current = obj;
    while (current) {
        if (current.userData && current.userData.parcelItem) {
            return current.userData.parcelItem;
        }
        current = current.parent;
    }
    return null;
}

// Click listener to select building and open panel details
function onDocumentClick(event) {
    if (isUiEventTarget(event.target)) return;

    mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);

    // Intercept click if in 3D Ruler Measurement mode
    if (isMeasurementMode) {
        const allIntersects = raycaster.intersectObjects(scene.children, true);
        const filtered = allIntersects.filter(hit => {
            return hit.object.type === 'Mesh' && 
                   !hit.object.userData?.isHeightHandle && 
                   !hit.object.userData?.isSetbackHandle && 
                   !hit.object.userData?.isMeasurementElement;
        });

        if (filtered.length > 0) {
            const hitPoint = filtered[0].point;
            handleMeasurementClick(hitPoint);
        }
        return;
    }

    if (heightHandleMesh) {
        const handleIntersects = raycaster.intersectObject(heightHandleMesh, true);
        if (handleIntersects.length > 0) return;
    }

    if (setbackHandleMesh) {
        const handleIntersects = raycaster.intersectObject(setbackHandleMesh, true);
        if (handleIntersects.length > 0) return;
    }

    const meshes = [];
    parcelFeatures.forEach(item => {
        if (item.parcelMesh) meshes.push(item.parcelMesh);
        if (item.buildingMesh) meshes.push(item.buildingMesh);
    });

    const intersects = raycaster.intersectObjects(meshes);

    if (intersects.length > 0) {
        const hitObject = intersects[0].object;
        const item = getParcelItemFromObject(hitObject);
        if (item) {
            selectParcel(item);
        }
    } else {
        deselectParcel();
    }
}

// Handle parcel selection, loading values to sliders
function selectParcel(item) {
    item.params = sanitizeParcelParams(item.params || {}, item.area, item.outerRing);

    if (selectedParcel) {
        setBuildingHighlight(selectedParcel.buildingMesh, false);
    }

    selectedParcel = item;
    setBuildingHighlight(item.buildingMesh, true);

    // Populate sliders
    if (inSetback) inSetback.value = item.params.setback;
    if (inFloors) inFloors.value = item.params.floors;
    if (inFloorHeight) inFloorHeight.value = item.params.floorHeight;
    if (inScaleX) inScaleX.value = item.params.scaleX || 1.0;
    if (inScaleY) inScaleY.value = item.params.scaleY || 1.0;
    if (inTypology) inTypology.value = item.params.typology;
    if (inUsage) inUsage.value = item.params.usage;
    if (inRoofStyle) inRoofStyle.value = roofStyleForItem(item);
    
    if (inStepbackInterval) inStepbackInterval.value = item.params.stepbackInterval || 4;
    if (inStepbackDepth) inStepbackDepth.value = item.params.stepbackDepth || 1.5;
    
    // Zoning sliders
    if (inMaxBcr) inMaxBcr.value = item.params.maxBcr;
    if (inMaxFar) inMaxFar.value = item.params.maxFar;
    if (inMaxHeight) inMaxHeight.value = item.params.maxHeight;

    // Populate labels
    if (lblSetback) lblSetback.textContent = item.params.setback.toFixed(1);
    if (lblFloors) lblFloors.textContent = item.params.floors;
    if (lblFloorHeight) lblFloorHeight.textContent = item.params.floorHeight.toFixed(1);
    if (lblScaleX) lblScaleX.textContent = (item.params.scaleX || 1.0).toFixed(2);
    if (lblScaleY) lblScaleY.textContent = (item.params.scaleY || 1.0).toFixed(2);
    if (lblMaxBcr) lblMaxBcr.textContent = item.params.maxBcr.toFixed(2);
    if (lblMaxFar) lblMaxFar.textContent = item.params.maxFar.toFixed(1);
    if (lblMaxHeight) lblMaxHeight.textContent = item.params.maxHeight.toFixed(1);
    
    if (lblStepbackInterval) lblStepbackInterval.textContent = item.params.stepbackInterval || 4;
    if (lblStepbackDepth) lblStepbackDepth.textContent = (item.params.stepbackDepth || 1.5).toFixed(1);

    // Show/hide stepped tower controls
    if (steppedTowerControlsEl) {
        if (item.params.typology === 'SteppedTower') {
            steppedTowerControlsEl.classList.remove('hidden');
        } else {
            steppedTowerControlsEl.classList.add('hidden');
        }
    }

    if (metFid) metFid.textContent = item.fid;
    if (metArea) metArea.textContent = Math.round(item.area).toLocaleString() + " sq m";

    placeholderEl.classList.add('hidden');
    controlsEl.classList.remove('hidden');

    updateDashboard(item);
    updateHeightLabels();
    focusParcelCamera(item);

    // Spawn 3D arrow height handle on top of building and setback handle on ground
    if (item.params.usage !== 'Park') {
        let cx = 0, cy = 0;
        const ring = item.outerRing;
        ring.forEach(pt => { cx += pt.x; cy += pt.y; });
        cx /= ring.length;
        cy /= ring.length;

        const height = item.params.floors * item.params.floorHeight;
        spawnHeightHandle(cx, cy, height);

        // Spawn setback handle on first segment midpoint
        const insetRing = offsetPolygonRing(item.outerRing, item.params.setback);
        if (insetRing && insetRing.length >= 2) {
            const pt1 = insetRing[0];
            const pt2 = insetRing[1];
            spawnSetbackHandle((pt1.x + pt2.x) / 2, (pt1.y + pt2.y) / 2);
            spawnScaleHandles(item);
        } else {
            removeSetbackHandle();
            removeScaleHandles();
        }
    } else {
        removeHeightHandle();
        removeSetbackHandle();
        removeScaleHandles();
    }
}

// Deselect selected parcel and hide controls panel
function deselectParcel() {
    if (selectedParcel) {
        const prevSelected = selectedParcel;
        setBuildingHighlight(prevSelected.buildingMesh, false);
        selectedParcel = null;
        removeHeightHandle();
        removeSetbackHandle();
        removeScaleHandles();
        rebuildParcel3D(prevSelected);
    }

    placeholderEl.classList.remove('hidden');
    controlsEl.classList.add('hidden');
}

// Helper to update opacity/emission highlights on building selection
function setBuildingHighlight(meshOrGroup, isSelected) {
    if (!meshOrGroup) return;
    const tVal = (inTime && inTime.value) ? parseFloat(inTime.value) : 12.0;
    const isNight = tVal < 7.5 || tVal > 19.5;
    
    meshOrGroup.traverse(child => {
        if (child.isMesh && Array.isArray(child.material)) {
            const wallMat = child.material[1];
            if (wallMat) {
                wallMat.opacity = isSelected ? 1.0 : 0.85;
                if (isSelected) {
                    wallMat.emissive.setHex(0xaaaaaa); // selection highlight tint
                    wallMat.emissiveIntensity = 1.5;
                } else {
                    wallMat.emissive.setHex(0xffffff); // default emissiveMap color
                    wallMat.emissiveIntensity = isNight ? 1.0 : 0.0;
                }
            }
        }
    });
}

function calculateParcelMetrics(item) {
    item.params = sanitizeParcelParams(item.params || {}, item.area, item.outerRing);
    const params = item.params || {};
    const setback = parseFloat(params.setback) || 0;
    const floors = parseInt(params.floors) || 1;
    const floorHeight = parseFloat(params.floorHeight) || 3.0;
    const typology = params.typology || 'Tower';
    const usage = params.usage || 'Residential';
    const height = usage === 'Park' ? 0 : floors * floorHeight;
    const buildable = resolveBuildableRing(item, setback);
    const insetRing = scaleRingInLocalAxes(buildable.ring, params.scaleX, params.scaleY);
    let footprintArea = 0;
    let gfa = 0;

    if (usage !== 'Park' && insetRing && insetRing.length >= 3) {
        if (typology === 'Courtyard') {
            const innerSetback = 8;
            const innerRing = offsetPolygonRing(insetRing, innerSetback);
            const outerArea = calculatePolygonArea(insetRing);
            const innerArea = innerRing ? calculatePolygonArea(innerRing) : 0;
            footprintArea = Math.max(0, outerArea - innerArea);
            gfa = footprintArea * floors;
        } else if (typology === 'Slab') {
            const slabShape = buildSlabShape(insetRing, 12);
            footprintArea = calculateShapeArea(slabShape);
            gfa = footprintArea * floors;
        } else if (typology === 'LShape') {
            const lShape = buildLShape(insetRing, 12);
            footprintArea = calculateShapeArea(lShape);
            gfa = footprintArea * floors;
        } else if (typology === 'UShape') {
            const uShape = buildUShape(insetRing, 12);
            footprintArea = calculateShapeArea(uShape);
            gfa = footprintArea * floors;
        } else if (typology === 'PodiumTower') {
            const podiumArea = calculatePolygonArea(insetRing);
            const towerRing = offsetPolygonRing(insetRing, 3.5) || insetRing;
            const towerArea = calculatePolygonArea(towerRing);
            const podiumH = Math.min(height, 2 * floorHeight);
            const towerH = Math.max(0, height - podiumH);
            const podiumFloors = Math.round(podiumH / floorHeight);
            const towerFloors = Math.round(towerH / floorHeight);
            footprintArea = podiumArea;
            gfa = (podiumArea * podiumFloors) + (towerArea * towerFloors);
        } else if (typology === 'SteppedTower') {
            const stepInterval = params.stepbackInterval || 4;
            const stepDepth = params.stepbackDepth || 1.5;
            let remainingFloors = floors;
            let segmentIndex = 0;
            footprintArea = calculatePolygonArea(insetRing);
            while (remainingFloors > 0) {
                const currentSetback = setback + segmentIndex * stepDepth;
                const segmentRing = offsetPolygonRing(item.outerRing, currentSetback);
                if (!segmentRing || segmentRing.length < 3) break;
                const segFloors = Math.min(stepInterval, remainingFloors);
                const segArea = calculatePolygonArea(segmentRing);
                gfa += segArea * segFloors;
                remainingFloors -= segFloors;
                segmentIndex++;
            }
        } else if (typology === 'MultiBuildingBlock') {
            const ob = getOrientedBounds(insetRing);
            const W = ob.W;
            const localRing = insetRing.map(pt => {
                const rx = pt.x - ob.cx;
                const ry = pt.y - ob.cy;
                return {
                    x: rx * ob.ux + ry * ob.uy,
                    y: rx * ob.nx + ry * ob.ny
                };
            });
            const floorsA = Math.round(floors * 1.3);
            const floorsB = Math.round(floors * 0.7);
            if (W >= 40) {
                const localPoly1 = clipConvexPolygonVertical(localRing, ob.minX, ob.minX + W * 0.38);
                const localPoly3 = clipConvexPolygonVertical(localRing, ob.minX + W * 0.62, ob.maxX);
                let insetPoly1 = null;
                let insetPoly3 = null;
                if (localPoly1 && localPoly1.length >= 3) {
                    const globalPoly1 = localPoly1.map(pt => ({
                        x: ob.cx + pt.x * ob.ux + pt.y * ob.nx,
                        y: ob.cy + pt.x * ob.uy + pt.y * ob.ny
                    }));
                    insetPoly1 = offsetPolygonRing(globalPoly1, 1.2);
                }
                if (localPoly3 && localPoly3.length >= 3) {
                    const globalPoly3 = localPoly3.map(pt => ({
                        x: ob.cx + pt.x * ob.ux + pt.y * ob.nx,
                        y: ob.cy + pt.x * ob.uy + pt.y * ob.ny
                    }));
                    insetPoly3 = offsetPolygonRing(globalPoly3, 1.2);
                }
                if (insetPoly1 && insetPoly1.length >= 3) {
                    const a1 = calculatePolygonArea(insetPoly1);
                    footprintArea += a1;
                    gfa += a1 * floorsA;
                }
                if (insetPoly3 && insetPoly3.length >= 3) {
                    const a3 = calculatePolygonArea(insetPoly3);
                    footprintArea += a3;
                    gfa += a3 * floorsB;
                }
            } else {
                const localPoly1 = clipConvexPolygonVertical(localRing, ob.minX, ob.minX + W * 0.5);
                let insetPoly1 = null;
                if (localPoly1 && localPoly1.length >= 3) {
                    const globalPoly1 = localPoly1.map(pt => ({
                        x: ob.cx + pt.x * ob.ux + pt.y * ob.nx,
                        y: ob.cy + pt.x * ob.uy + pt.y * ob.ny
                    }));
                    insetPoly1 = offsetPolygonRing(globalPoly1, 1.2);
                }
                if (insetPoly1 && insetPoly1.length >= 3) {
                    const a1 = calculatePolygonArea(insetPoly1);
                    footprintArea += a1;
                    gfa += a1 * floors;
                }
            }
        } else {
            footprintArea = calculatePolygonArea(insetRing);
            gfa = footprintArea * floors;
        }
    }

    const bcr = item.area > 0 ? (footprintArea / item.area) : 0;
    const far = item.area > 0 ? (gfa / item.area) : 0;
    const heightViolation = usage !== 'Park' && height > params.maxHeight;
    const bcrViolation = bcr > params.maxBcr;
    const farViolation = far > params.maxFar;
    const footprintViolation = usage !== 'Park' && footprintArea === 0;
    const violated = heightViolation || bcrViolation || farViolation || footprintViolation;

    let dwellingUnits = 0;
    let population = 0;
    const AVG_UNIT_SIZE = 100;
    const AVG_PERSONS = 2.8;
    if (usage === 'Residential') {
        dwellingUnits = Math.floor(gfa / AVG_UNIT_SIZE);
        population = Math.round(dwellingUnits * AVG_PERSONS);
    } else if (usage === 'MixedUse') {
        const residentialGfa = Math.max(0, gfa - footprintArea);
        dwellingUnits = Math.floor(residentialGfa / AVG_UNIT_SIZE);
        population = Math.round(dwellingUnits * AVG_PERSONS);
    } else if (usage === 'Commercial' || usage === 'Civic') {
        population = Math.round(gfa / 15);
    }

    const densityPpHa = item.area > 0 ? Math.round(population / (item.area / 10000)) : 0;
    const openSpaceArea = Math.max(0, item.area - footprintArea);
    const osr = gfa > 0 ? (openSpaceArea / gfa) : 0;
    let carbonFactor = 0;
    if (usage === 'Residential') carbonFactor = 0.045;
    else if (usage === 'MixedUse') carbonFactor = 0.055;
    else if (usage === 'Commercial') carbonFactor = 0.075;
    else if (usage === 'Civic') carbonFactor = 0.050;
    const carbon = gfa * carbonFactor;
    const runoff = bcr * 0.90 + (1 - bcr) * 0.15;

    const result = {
        setback,
        floors,
        floorHeight,
        typology,
        usage,
        height,
        insetRing,
        footprintArea,
        gfa,
        bcr,
        far,
        violated,
        status: violated ? "VIOLATION" : "COMPLIANT",
        dwellingUnits,
        population,
        densityPpHa,
        openSpaceArea,
        osr,
        carbon,
        runoff,
        constraintLoad: 0,
        planScore: 0
    };
    result.constraintLoad = calculateConstraintLoad(result, item);
    result.planScore = calculatePlanScore(result, item);
    return result;
}

// Live calculation of regulatory compliance metrics (FAR, BCR, Height)
function updateDashboard(item) {
    const metrics = calculateParcelMetrics(item);
    const maxBcr = Math.max(0.01, item.params.maxBcr || 0.45);
    const maxFar = Math.max(0.01, item.params.maxFar || 2.5);

    if (metFootprint) metFootprint.textContent = Math.round(metrics.footprintArea).toLocaleString() + " sq m";
    if (metGfa) metGfa.textContent = Math.round(metrics.gfa).toLocaleString() + " sq m";
    if (metHeight) {
        metHeight.textContent = metrics.usage === 'Park' ? "0.0 m" : metrics.height.toFixed(1) + " m";
        metHeight.style.color = metrics.height > item.params.maxHeight && metrics.usage !== 'Park' ? "#ef4444" : "#10b981";
    }
    if (metZRange) metZRange.textContent = metrics.usage === 'Park' ? "0.0 - 0.0 m" : `0.0 - ${metrics.height.toFixed(1)} m`;

    if (metBcrLabel) {
        metBcrLabel.textContent = `${metrics.bcr.toFixed(2)} / ${maxBcr.toFixed(2)}`;
        metBcrLabel.style.color = metrics.bcr > maxBcr ? "#ef4444" : "#10b981";
    }
    if (metFarLabel) {
        metFarLabel.textContent = `${metrics.far.toFixed(2)} / ${maxFar.toFixed(2)}`;
        metFarLabel.style.color = metrics.far > maxFar ? "#ef4444" : "#10b981";
    }

    const bcrPercent = Math.min(100, (metrics.bcr / maxBcr) * 100);
    const farPercent = Math.min(100, (metrics.far / maxFar) * 100);
    if (bcrFillEl) {
        bcrFillEl.style.width = `${bcrPercent}%`;
        bcrFillEl.className = `gauge-bar-fill ${metrics.bcr > maxBcr ? "red-bar" : "green-bar"}`;
    }
    if (farFillEl) {
        farFillEl.style.width = `${farPercent}%`;
        farFillEl.className = `gauge-bar-fill ${metrics.far > maxFar ? "red-bar" : "green-bar"}`;
    }

    if (metStatus) {
        metStatus.textContent = metrics.status;
        metStatus.className = "stat-val status-badge " + (metrics.violated ? "violation" : "compliant");
    }

    if (metPlanScore) {
        metPlanScore.textContent = `${metrics.planScore}/100`;
        metPlanScore.className = `stat-val ${scoreClass(metrics.planScore)}`;
    }
    if (metConstraintLoad) {
        metConstraintLoad.textContent = `${metrics.constraintLoad.toFixed(2)}x`;
        metConstraintLoad.className = `stat-val ${metrics.constraintLoad > 1 ? "score-poor" : (metrics.constraintLoad > 0.88 ? "score-watch" : "score-good")}`;
    }

    if (metUnits) metUnits.textContent = metrics.usage === 'Park' ? '0' : metrics.dwellingUnits.toLocaleString();
    if (metPopulation) metPopulation.textContent = metrics.usage === 'Park' ? '0' : metrics.population.toLocaleString();
    if (metDensity) metDensity.textContent = metrics.usage === 'Park' ? '0 pp/ha' : `${metrics.densityPpHa.toLocaleString()} pp/ha`;

    if (metOsr) metOsr.textContent = metrics.gfa > 0 ? metrics.osr.toFixed(2) : 'N/A';
    if (metOpenSpace) metOpenSpace.textContent = `${Math.round(metrics.openSpaceArea).toLocaleString()} sq m`;
    if (metCarbon) metCarbon.textContent = metrics.carbon > 0 ? `${Math.round(metrics.carbon).toLocaleString()} t CO2e/yr` : '0 t CO2e/yr';
    if (metRunoff) metRunoff.textContent = metrics.runoff.toFixed(2);

    updateParcelGroundColor(item, metrics.violated);
}

// Capture current 3D WebGL viewport canvas as a PNG screenshot download
function captureViewport() {
    try {
        // Redraw scene through post-processing pipeline
        composer.render();
        const dataURL = renderer.domElement.toDataURL('image/png');
        
        const link = document.createElement('a');
        link.download = 'planx_urban_design_capture.png';
        link.href = dataURL;
        link.click();
    } catch (e) {
        console.error(e);
        showToast("Failed to capture viewport screenshot.", "error");
    }
}

// Export complete planning and sustainability parameters for all parcels as a CSV report
function exportPlanningReport() {
    try {
        if (!parcelFeatures || parcelFeatures.length === 0) {
            showToast("No parcel data available to export.", "warning");
            return;
        }

        const headers = [
            "Parcel ID",
            "Area (sq m)",
            "Primary Use",
            "Typology",
            "Roof Style",
            "Setback Distance (m)",
            "Mass X Scale",
            "Mass Y Scale",
            "Floor Count",
            "Floor Height (m)",
            "Max BCR (Allowed)",
            "Max FAR (Allowed)",
            "Max Height (Allowed)",
            "Actual Footprint Area (sq m)",
            "Actual GFA (sq m)",
            "Actual Height (m)",
            "Actual BCR",
            "Actual FAR",
            "Compliance Status",
            "PlanX Score",
            "Constraint Load",
            "Est. Dwelling Units",
            "Est. Population",
            "Pop. Density (pp/ha)",
            "Open Space Area (sq m)",
            "Open Space Ratio (OSR)",
            "Est. Carbon Footprint (t CO2e/yr)",
            "Stormwater Runoff Coefficient"
        ];

        const rows = [headers.join(",")];

        parcelFeatures.forEach(item => {
            const metrics = calculateParcelMetrics(item);
            const setback = metrics.setback;
            const floors = metrics.floors;
            const floorHeight = metrics.floorHeight;
            const height = metrics.height;
            const typology = metrics.typology;
            const usage = metrics.usage;
            const footprintArea = metrics.footprintArea;
            const gfa = metrics.gfa;
            const bcr = metrics.bcr;
            const far = metrics.far;
            const status = metrics.status;
            const dwellingUnits = metrics.dwellingUnits;
            const population = metrics.population;
            const densityPpHa = metrics.densityPpHa;
            const openSpaceArea = metrics.openSpaceArea;
            const osr = metrics.osr;
            const carbon = metrics.carbon;
            const runoff = metrics.runoff;

            const row = [
                item.fid !== undefined ? item.fid : "",
                item.area.toFixed(1),
                usage,
                typology,
                roofStyleForItem(item),
                setback.toFixed(1),
                (item.params.scaleX || 1).toFixed(2),
                (item.params.scaleY || 1).toFixed(2),
                floors,
                floorHeight.toFixed(1),
                item.params.maxBcr.toFixed(2),
                item.params.maxFar.toFixed(2),
                item.params.maxHeight.toFixed(1),
                footprintArea.toFixed(1),
                gfa.toFixed(1),
                (usage === 'Park' ? 0 : height).toFixed(1),
                bcr.toFixed(3),
                far.toFixed(3),
                status,
                metrics.planScore,
                metrics.constraintLoad.toFixed(3),
                dwellingUnits,
                population,
                densityPpHa,
                openSpaceArea.toFixed(1),
                gfa > 0 ? osr.toFixed(3) : "N/A",
                carbon.toFixed(1),
                runoff.toFixed(3)
            ];

            const csvRow = row.map(val => {
                const s = String(val);
                if (s.includes(",") || s.includes("\"") || s.includes("\n")) {
                    return `"${s.replace(/"/g, '""')}"`;
                }
                return s;
            }).join(",");

            rows.push(csvRow);
        });

        const csvContent = "\ufeff" + rows.join("\n"); // Add BOM for Excel compatibility
        const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
        const link = document.createElement("a");
        const url = URL.createObjectURL(blob);
        link.setAttribute("href", url);
        link.setAttribute("download", "planx_urban_planning_report.csv");
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        showToast("Planning report CSV exported.", "success");
    } catch (e) {
        console.error(e);
        showToast("Failed to export planning report CSV.", "error");
    }
}

// POST modifications back to the local Python QGIS server
async function syncToQGIS() {
    let modifiedParcels = parcelFeatures.filter(item => item.modified);
    
    // Fallback: If no parcels are flagged as modified, but one is selected, sync that selected one
    if (modifiedParcels.length === 0 && selectedParcel) {
        selectedParcel.modified = true;
        modifiedParcels = [selectedParcel];
    }
    
    if (modifiedParcels.length === 0) {
        showToast("No modifications to synchronize. Select a parcel and adjust sliders first.", "warning");
        return;
    }

    btnSync.disabled = true;
    btnSync.textContent = "Syncing...";

    const updates = modifiedParcels.map(item => {
        const metrics = calculateParcelMetrics(item);
        const insetRing = metrics.insetRing;
        
        let geoCoords = [];
        if (insetRing) {
            geoCoords = insetRing.map(pt => {
                return [pt.x + centerX, pt.y + centerY];
            });
        }

        return {
            id: item.fid,
            far: parseFloat(metrics.far.toFixed(2)),
            bcr: parseFloat(metrics.bcr.toFixed(2)),
            gfa: Math.round(metrics.gfa),
            setback: item.params.setback,
            scale_x: item.params.scaleX || 1,
            scale_y: item.params.scaleY || 1,
            floors: item.params.floors,
            floor_h: item.params.floorHeight,
            typology: item.params.typology,
            usage: item.params.usage,
            max_bcr: item.params.maxBcr,
            max_far: item.params.maxFar,
            max_height: item.params.maxHeight,
            roof_style: roofStyleForItem(item),
            stepback_i: item.params.stepbackInterval || 4,
            stepback_d: item.params.stepbackDepth || 1.5,
            plan_score: metrics.planScore,
            const_load: parseFloat(metrics.constraintLoad.toFixed(3)),
            height_m: parseFloat(metrics.height.toFixed(1)),
            z_base: 0,
            z_top: parseFloat(metrics.height.toFixed(1)),
            pop_est: metrics.population,
            carbon: parseFloat(metrics.carbon.toFixed(1)),
            runoff: parseFloat(metrics.runoff.toFixed(3)),
            open_space: parseFloat(metrics.openSpaceArea.toFixed(1)),
            coordinates: geoCoords
        };
    });

    const payload = { updates };

    try {
        const response = await fetch('/sync', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        const res = await response.json();
        if (res.status === 'ok') {
            modifiedParcels.forEach(item => { item.modified = false; });
            showToast(`Synced ${modifiedParcels.length} parcel modifications back to QGIS.`, "success");
        } else {
            showToast("Synchronization failed: " + res.message, "error");
        }
    } catch (e) {
        console.error(e);
        showToast("Connection error: could not reach the QGIS plugin server.", "error");
    } finally {
        btnSync.disabled = false;
        btnSync.textContent = "Sync Parameters to QGIS";
    }
}

// Mathematical geometry helpers

// Standard Polygon Area calculation (Shoelace formula)
function calculatePolygonArea(ring) {
    let area = 0;
    const N = ring.length;
    for (let i = 0; i < N; i++) {
        const p1 = ring[i];
        const p2 = ring[(i + 1) % N];
        area += p1.x * p2.y - p2.x * p1.y;
    }
    return Math.abs(area / 2);
}

// Calculate area of a THREE.Shape
function calculateShapeArea(shape) {
    const pts = shape.getPoints();
    return calculatePolygonArea(pts.map(pt => { return {x: pt.x, y: pt.y}; }));
}

// Perform polygon segment corner-bisector offsetting/insetting
function offsetPolygonRing(ring, distance) {
    if (Math.abs(distance) <= 0.05) return ring.map(pt => { return {x: pt.x, y: pt.y}; });

    // Detect winding order and flip distance if clockwise to ensure consistent inward/outward behavior
    let sum = 0;
    const N = ring.length;
    for (let i = 0; i < N; i++) {
        const p1 = ring[i];
        const p2 = ring[(i + 1) % N];
        sum += (p2.x - p1.x) * (p2.y + p1.y);
    }
    const activeDistance = (sum > 0) ? -distance : distance;

    const N_pts = ring.length;
    const offsetSegments = [];

    // Calculate inward shifted segments
    for (let i = 0; i < N_pts; i++) {
        const p1 = ring[i];
        const p2 = ring[(i + 1) % N_pts];

        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        const len = Math.sqrt(dx*dx + dy*dy);
        if (len < 0.001) continue;

        // Inward pointing normal
        const nx = -dy / len;
        const ny = dx / len;

        offsetSegments.push({
            p1: { x: p1.x + nx * activeDistance, y: p1.y + ny * activeDistance },
            p2: { x: p2.x + nx * activeDistance, y: p2.y + ny * activeDistance },
            dir: { x: dx / len, y: dy / len }
        });
    }

    if (offsetSegments.length < 3) return null;

    // Intersect adjacent shifted segments to find new vertices
    const insetRing = [];
    const M = offsetSegments.length;
    for (let i = 0; i < M; i++) {
        const s1 = offsetSegments[(i - 1 + M) % M];
        const s2 = offsetSegments[i];

        const pt = intersectLines(s1.p1, s1.dir, s2.p1, s2.dir);
        if (pt) {
            const d1 = distToSegment(pt, ring[(i - 1 + M) % M], ring[i]);
            const checkDist = Math.abs(activeDistance);
            if (d1 > checkDist * 4) return null; // self-intersection/degenerate
            insetRing.push(pt);
        } else {
            insetRing.push({ x: s2.p1.x, y: s2.p1.y });
        }
    }

    return insetRing;
}

// Find intersection point of two infinite 2D lines
function intersectLines(p1, d1, p2, d2) {
    const denom = d1.x * d2.y - d1.y * d2.x;
    if (Math.abs(denom) < 0.0001) return null;

    const t = ((p2.x - p1.x) * d2.y - (p2.y - p1.y) * d2.x) / denom;
    return {
        x: p1.x + d1.x * t,
        y: p1.y + d1.y * t
    };
}

// Distance from point to line segment
function distToSegment(p, a, b) {
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const l2 = dx*dx + dy*dy;
    if (l2 === 0) return Math.sqrt((p.x - a.x)**2 + (p.y - a.y)**2);
    
    let t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / l2;
    t = Math.max(0, Math.min(1, t));
    
    const projX = a.x + t * dx;
    const projY = a.y + t * dy;
    return Math.sqrt((p.x - projX)**2 + (p.y - projY)**2);
}

// Generate a rectangular Slab/Row building footprint along the longest side
function buildSlabShape(ring, width) {
    let maxLen = -1;
    let bestStart = null, bestEnd = null;
    const N = ring.length;
    
    for (let i = 0; i < N; i++) {
        const p1 = ring[i];
        const p2 = ring[(i + 1) % N];
        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        const len = Math.sqrt(dx*dx + dy*dy);
        if (len > maxLen) {
            maxLen = len;
            bestStart = p1;
            bestEnd = p2;
        }
    }

    let cx = 0, cy = 0;
    ring.forEach(pt => { cx += pt.x; cy += pt.y; });
    cx /= N;
    cy /= N;

    const dx = bestEnd.x - bestStart.x;
    const dy = bestEnd.y - bestStart.y;
    const len = Math.sqrt(dx*dx + dy*dy);
    const ux = dx / len;
    const uy = dy / len;

    const nx = -uy;
    const ny = ux;

    const slabLength = maxLen * 0.9;
    const shape = new THREE.Shape();
    
    const wHalf = width / 2;
    const lHalf = slabLength / 2;

    const c1x = cx - ux * lHalf - nx * wHalf;
    const c1y = cy - uy * lHalf - ny * wHalf;

    const c2x = cx + ux * lHalf - nx * wHalf;
    const c2y = cy + uy * lHalf - ny * wHalf;

    const c3x = cx + ux * lHalf + nx * wHalf;
    const c3y = cy + uy * lHalf + ny * wHalf;

    const c4x = cx - ux * lHalf + nx * wHalf;
    const c4y = cy - uy * lHalf + ny * wHalf;

    shape.moveTo(c1x, c1y);
    shape.lineTo(c2x, c2y);
    shape.lineTo(c3x, c3y);
    shape.lineTo(c4x, c4y);

    return shape;
}

// Start the application
init();

// Keyboard shortcuts
function handleKeyboardShortcuts(event) {
    if (event.key === 'Escape' && guidePanelEl && !guidePanelEl.classList.contains('hidden')) {
        closeGuidePanel();
        return;
    }

    // Ignore shortcuts when typing in inputs
    if (event.target.tagName === 'INPUT' || event.target.tagName === 'SELECT' || event.target.tagName === 'TEXTAREA') return;

    switch (event.key.toLowerCase()) {
        case 'h':
        case '?':
            openGuidePanel();
            break;

        case 'r': // Reset camera
            camera.position.set(0, 300, 450);
            controls.target.set(0, 0, 0);
            controls.update();
            break;

        case 'f': // Focus on selected parcel
            if (selectedParcel && selectedParcel.buildingMesh) {
                focusParcelCamera(selectedParcel, { toast: true });
            }
            break;

        case 'n': // Toggle night mode
            {
                const currentTime = (inTime && inTime.value) ? parseFloat(inTime.value) : 12.0;
                const isCurrentlyNight = currentTime < 7.5 || currentTime > 19.5;
                const newTime = isCurrentlyNight ? 12.0 : 21.0;
                if (inTime) inTime.value = newTime;
                const hours = Math.floor(newTime);
                const mins = (newTime % 1) === 0 ? "00" : "30";
                lblTime.textContent = `${hours}:${mins}`;
                updateSolarPhysics(newTime);
            }
            break;

        case 'g': // Toggle grid visibility
            if (gridHelper) {
                gridHelper.visible = !gridHelper.visible;
                if (toggleGridEl) {
                    toggleGridEl.checked = gridHelper.visible;
                }
            }
            break;
    }
}

// Apply to all parcels
function applyToAllParcels() {
    if (!selectedParcel) {
        showToast('Select a parcel first to use as the template.', 'warning');
        return;
    }

    const templateParams = { ...selectedParcel.params };

    const confirmed = confirm(
        `Apply the current design parameters to all ${parcelFeatures.length} parcels?\n\n` +
        `Typology: ${templateParams.typology}\n` +
        `Usage: ${templateParams.usage}\n` +
        `Roof Style: ${templateParams.roofStyle || defaultRoofStyleFor(templateParams.usage, templateParams.typology)}\n` +
        `Floors: ${templateParams.floors}\n` +
        `Floor Height: ${templateParams.floorHeight}m\n` +
        `Mass Scale: X ${(templateParams.scaleX || 1).toFixed(2)} / Y ${(templateParams.scaleY || 1).toFixed(2)}\n` +
        `Setback: ${templateParams.setback}m\n\n` +
        `This action cannot be undone.`
    );

    if (!confirmed) return;

    btnApplyAll.disabled = true;
    btnApplyAll.textContent = 'Applying...';

    parcelFeatures.forEach(item => {
        item.modified = true;
        item.params.setback = templateParams.setback;
        item.params.floors = templateParams.floors;
        item.params.floorHeight = templateParams.floorHeight;
        item.params.scaleX = templateParams.scaleX;
        item.params.scaleY = templateParams.scaleY;
        item.params.typology = templateParams.typology;
        item.params.usage = templateParams.usage;
        item.params.roofStyle = templateParams.roofStyle;
        item.params.stepbackInterval = templateParams.stepbackInterval;
        item.params.stepbackDepth = templateParams.stepbackDepth;
        item.params.maxBcr = templateParams.maxBcr;
        item.params.maxFar = templateParams.maxFar;
        item.params.maxHeight = templateParams.maxHeight;

        rebuildParcel3D(item);
    });

    // Refresh dashboard for selected
    updateDashboard(selectedParcel);
    updateCitySummary();

    btnApplyAll.disabled = false;
    btnApplyAll.textContent = 'Apply to All Parcels';
    showToast(`Applied the selected scenario to ${parcelFeatures.length} parcels.`, 'success');
}

// WebGL memory and resource cleanup

function clearScene() {
    // 1. Deselect any active parcel
    deselectParcel();

    // 2. Remove and dispose parcelFeatures elements
    parcelFeatures.forEach(item => {
        // Remove and dispose parcelMesh
        if (item.parcelMesh) {
            scene.remove(item.parcelMesh);
            if (item.parcelMesh.geometry) item.parcelMesh.geometry.dispose();
            disposeMaterialOrMaterials(item.parcelMesh.material);
        }

        // Remove and dispose buildingMesh
        if (item.buildingMesh) {
            scene.remove(item.buildingMesh);
            disposeObject3D(item.buildingMesh);
        }

        // Remove and dispose setbackMesh
        if (item.setbackMesh) {
            scene.remove(item.setbackMesh);
            if (item.setbackMesh.geometry) item.setbackMesh.geometry.dispose();
            disposeMaterialOrMaterials(item.setbackMesh.material);
        }

        // Remove and dispose sidewalkMesh
        if (item.sidewalkMesh) {
            scene.remove(item.sidewalkMesh);
            disposeObject3D(item.sidewalkMesh);
        }

        // Remove and dispose zoningMesh
        if (item.zoningMesh) {
            scene.remove(item.zoningMesh);
            disposeObject3D(item.zoningMesh);
        }

        removeHeightLabel(item);
    });
    parcelFeatures = [];

    // 3. Remove and dispose pedestrians
    pedestrians.forEach(ped => {
        if (ped.mesh) {
            scene.remove(ped.mesh);
            disposeObject3D(ped.mesh);
        }
    });
    pedestrians = [];

    // 4. Remove and dispose traffic cars
    trafficCars.forEach(car => {
        if (car.carMesh) {
            scene.remove(car.carMesh);
            disposeObject3D(car.carMesh);
        }
    });
    trafficCars = [];

    roadMeshes.forEach(mesh => {
        scene.remove(mesh);
        disposeObject3D(mesh);
    });
    roadMeshes = [];

    intersectionMeshes.forEach(mesh => {
        scene.remove(mesh);
        disposeObject3D(mesh);
    });
    intersectionMeshes = [];
}

// Deep dispose helper for geometry, material, textures
function disposeObject3D(obj) {
    obj.traverse(child => {
        if (child.geometry) child.geometry.dispose();
        disposeMaterialOrMaterials(child.material);
    });
}

function disposeMaterialOrMaterials(material) {
    if (!material) return;
    if (Array.isArray(material)) {
        material.forEach(m => disposeSingleMaterial(m));
    } else {
        disposeSingleMaterial(material);
    }
}

function disposeSingleMaterial(m) {
    if (!m) return;
    if (m.map) m.map.dispose();
    if (m.lightMap) m.lightMap.dispose();
    if (m.bumpMap) m.bumpMap.dispose();
    if (m.normalMap) m.normalMap.dispose();
    if (m.specularMap) m.specularMap.dispose();
    if (m.envMap) m.envMap.dispose();
    if (m.alphaMap) m.alphaMap.dispose();
    if (m.aoMap) m.aoMap.dispose();
    if (m.displacementMap) m.displacementMap.dispose();
    if (m.emissiveMap) m.emissiveMap.dispose();
    if (m.roughnessMap) m.roughnessMap.dispose();
    if (m.metalnessMap) m.metalnessMap.dispose();
    m.dispose();
}

// Dynamic layer visibility

function updateLayersVisibility() {
    const showBuildings = toggleBuildingsEl ? toggleBuildingsEl.checked : true;
    const showZoning = toggleZoningEl ? toggleZoningEl.checked : false;
    const showSetbacks = toggleSetbacksEl ? toggleSetbacksEl.checked : true;
    const showSidewalks = toggleSidewalksEl ? toggleSidewalksEl.checked : true;
    const showPedestrians = togglePedestriansEl ? togglePedestriansEl.checked : true;
    const showTraffic = toggleTrafficEl ? toggleTrafficEl.checked : true;
    const showGrid = toggleGridEl ? toggleGridEl.checked : false;

    // Toggle grid
    if (gridHelper) {
        gridHelper.visible = showGrid;
    }

    // Toggle features
    parcelFeatures.forEach(item => {
        if (item.buildingMesh) {
            item.buildingMesh.visible = showBuildings;
        }
        if (item.zoningMesh) {
            item.zoningMesh.visible = showZoning;
        }
        if (item.setbackMesh) {
            item.setbackMesh.visible = showSetbacks;
        }
        if (item.sidewalkMesh) {
            item.sidewalkMesh.visible = showSidewalks;
        }
    });

    // Toggle pedestrian meshes
    pedestrians.forEach(ped => {
        if (ped.mesh) ped.mesh.visible = showPedestrians;
    });

    // Toggle traffic car meshes
    trafficCars.forEach(car => {
        if (car.carMesh) car.carMesh.visible = showTraffic;
    });

    roadMeshes.forEach(mesh => {
        mesh.visible = showTraffic;
    });

    intersectionMeshes.forEach(mesh => {
        mesh.visible = showTraffic;
    });

    updateHeightLabels();
}

// Reload data from QGIS

async function reloadData() {
    if (btnReload) {
        btnReload.disabled = true;
        btnReload.textContent = "Reloading...";
    }
    
    // Re-show loading screen
    if (loadingEl) {
        loadingEl.style.opacity = 1;
        loadingEl.classList.remove('hidden');
        const textEl = document.getElementById('loading-text');
        if (textEl) textEl.innerText = "Reloading layer features from QGIS...";
    }

    try {
        const response = await fetch('/data.geojson');
        if (!response.ok) throw new Error("Could not load data");
        
        const data = await response.json();
        parseGeoJSON(data);
        
        // Hide loading screen
        if (loadingEl) {
            loadingEl.style.opacity = 0;
            setTimeout(() => loadingEl.classList.add('hidden'), 500);
        }
        
        // Keep checkboxes synchronized after reload
        updateLayersVisibility();
        showToast("Layer data reloaded from QGIS.", "success");
        
    } catch (e) {
        console.error(e);
        const textEl = document.getElementById('loading-text');
        if (textEl) textEl.innerText = "ERROR: Failed to reload. Verify QGIS server connection.";
        showToast("Reload failed. Verify the QGIS server connection.", "error");
    } finally {
        if (btnReload) {
            btnReload.disabled = false;
            btnReload.textContent = "Reload Data from QGIS";
        }
    }
}

// Pointer hover highlights

let hoveredParcel = null;

function onPointerMove(event) {
    if (isUiEventTarget(event.target)) {
        document.body.style.cursor = 'default';
        return;
    }

    mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);

    // Render temporary measurement line in Measurement Mode
    if (isMeasurementMode) {
        document.body.style.cursor = 'crosshair';
        
        if (measurementPoints.length === 1 && tempMeasureLine) {
            const allIntersects = raycaster.intersectObjects(scene.children, true);
            const filtered = allIntersects.filter(hit => {
                return hit.object.type === 'Mesh' && 
                       !hit.object.userData?.isHeightHandle && 
                       !hit.object.userData?.isSetbackHandle && 
                       !hit.object.userData?.isMeasurementElement;
            });

            if (filtered.length > 0) {
                const hitPoint = filtered[0].point;
                const start = measurementPoints[0];
                
                const positions = new Float32Array([
                    start.x, start.y, start.z,
                    hitPoint.x, hitPoint.y, hitPoint.z
                ]);
                tempMeasureLine.geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
                tempMeasureLine.geometry.attributes.position.needsUpdate = true;
                tempMeasureLine.geometry.computeBoundingSphere();
                tempMeasureLine.geometry.computeBoundingBox();
                tempMeasureLine.visible = true;
                
                // Show dynamic temporary label
                if (tempMeasureLabel) {
                    tempMeasureLabel.style.display = 'block';
                }
            }
        }
        return;
    }

    // 1. Resize selected mass in local X/Y from viewport handles
    if (isDraggingScaleAxis && selectedParcel && dragScaleCenter && dragScaleAxis) {
        const intersectPoint = new THREE.Vector3();
        raycaster.ray.intersectPlane(dragIntersectionPlane, intersectPoint);
        const planPt = { x: intersectPoint.x, y: -intersectPoint.z };
        const distance = Math.abs(
            (planPt.x - dragScaleCenter.x) * dragScaleAxis.x +
            (planPt.y - dragScaleCenter.y) * dragScaleAxis.y
        );
        const nextScale = clampNumber(
            Math.round((dragStartScale * distance / Math.max(0.1, dragStartScaleDistance)) * 20) / 20,
            0.35,
            1.60,
            dragStartScale
        );
        const key = isDraggingScaleAxis === 'x' ? 'scaleX' : 'scaleY';

        if (Math.abs((selectedParcel.params[key] || 1) - nextScale) > 0.001) {
            selectedParcel.params[key] = nextScale;
            selectedParcel.modified = true;
            if (isDraggingScaleAxis === 'x') {
                if (inScaleX) inScaleX.value = nextScale;
                if (lblScaleX) lblScaleX.textContent = nextScale.toFixed(2);
            } else {
                if (inScaleY) inScaleY.value = nextScale;
                if (lblScaleY) lblScaleY.textContent = nextScale.toFixed(2);
            }
            rebuildParcel3D(selectedParcel);
            updateDashboard(selectedParcel);
            updateCitySummary();
            updateHeightHandle();
            updateSetbackHandle();
            updateScaleHandles();
        }
        document.body.style.cursor = isDraggingScaleAxis === 'x' ? 'ew-resize' : 'ns-resize';
        return;
    }

    // 1. If actively dragging the setback handle
    if (isDraggingSetback && selectedParcel && setbackHandleMesh) {
        const intersectPoint = new THREE.Vector3();
        raycaster.ray.intersectPlane(dragIntersectionPlane, intersectPoint);
        
        const pt = { x: intersectPoint.x, y: -intersectPoint.z };
        const newSetback = getDistanceToPolygon(pt, selectedParcel.outerRing);
        const clampedSetback = Math.max(0, Math.min(15, Math.round(newSetback * 2) / 2)); // step = 0.5
        
        if (clampedSetback !== selectedParcel.params.setback) {
            selectedParcel.params.setback = clampedSetback;
            inSetback.value = clampedSetback;
            lblSetback.textContent = clampedSetback.toFixed(1);
            selectedParcel.modified = true;
            
            rebuildParcel3D(selectedParcel);
            updateDashboard(selectedParcel);
            updateHeightHandle();
            updateSetbackHandle();
            updateScaleHandles();
        }
        document.body.style.cursor = 'ew-resize';
        return;
    }

    // 2. If actively dragging the height handle
    if (isDraggingHeight && selectedParcel && heightHandleMesh) {
        const intersectPoint = new THREE.Vector3();
        raycaster.ray.intersectPlane(dragIntersectionPlane, intersectPoint);

        const deltaY = intersectPoint.y - dragStartHeight;
        const floorH = selectedParcel.params.floorHeight;
        const deltaFloors = Math.round(deltaY / floorH);
        
        const newFloors = Math.max(1, Math.min(30, dragStartFloors + deltaFloors));
        if (newFloors !== selectedParcel.params.floors) {
            inFloors.value = newFloors;
            lblFloors.textContent = newFloors;
            selectedParcel.params.floors = newFloors;
            selectedParcel.modified = true;
            
            rebuildParcel3D(selectedParcel);
            updateDashboard(selectedParcel);
            updateHeightHandle();
            updateScaleHandles();
        }
        document.body.style.cursor = 'ns-resize';
        return;
    }

    // 3. If hovering over X/Y mass scale handles
    const scaleHandles = [scaleXHandleMesh, scaleYHandleMesh].filter(Boolean);
    if (scaleHandles.length > 0) {
        const handleIntersects = raycaster.intersectObjects(scaleHandles, true);
        if (handleIntersects.length > 0) {
            const axis = handleIntersects[0].object.parent?.userData?.axis || handleIntersects[0].object.userData?.axis;
            document.body.style.cursor = axis === 'x' ? 'ew-resize' : 'ns-resize';
            if (hoveredParcel && hoveredParcel !== selectedParcel) {
                setBuildingHoverHighlight(hoveredParcel.buildingMesh, false);
                hoveredParcel = null;
            }
            return;
        }
    }

    // 4. If hovering over the setback handle
    if (setbackHandleMesh) {
        const handleIntersects = raycaster.intersectObject(setbackHandleMesh, true);
        if (handleIntersects.length > 0) {
            document.body.style.cursor = 'ew-resize';
            if (hoveredParcel && hoveredParcel !== selectedParcel) {
                setBuildingHoverHighlight(hoveredParcel.buildingMesh, false);
                hoveredParcel = null;
            }
            return;
        }
    }

    // 5. If hovering over the height handle
    if (heightHandleMesh) {
        const handleIntersects = raycaster.intersectObject(heightHandleMesh, true);
        if (handleIntersects.length > 0) {
            document.body.style.cursor = 'ns-resize';
            if (hoveredParcel && hoveredParcel !== selectedParcel) {
                setBuildingHoverHighlight(hoveredParcel.buildingMesh, false);
                hoveredParcel = null;
            }
            return;
        }
    }

    // 3. Fallback: Hovering over standard parcels / buildings
    const meshes = [];
    parcelFeatures.forEach(item => {
        if (item.parcelMesh) meshes.push(item.parcelMesh);
        if (item.buildingMesh) meshes.push(item.buildingMesh);
    });

    const intersects = raycaster.intersectObjects(meshes);

    if (intersects.length > 0) {
        const hitObject = intersects[0].object;
        const item = getParcelItemFromObject(hitObject);
        
        if (item) {
            document.body.style.cursor = 'pointer';
            if (hoveredParcel !== item) {
                // Un-highlight previous hover
                if (hoveredParcel && hoveredParcel !== selectedParcel) {
                    setBuildingHoverHighlight(hoveredParcel.buildingMesh, false);
                }
                // Apply hover highlight
                hoveredParcel = item;
                if (hoveredParcel !== selectedParcel) {
                    setBuildingHoverHighlight(hoveredParcel.buildingMesh, true);
                }
            }
        } else {
            document.body.style.cursor = 'default';
        }
    } else {
        document.body.style.cursor = 'default';
        if (hoveredParcel) {
            if (hoveredParcel !== selectedParcel) {
                setBuildingHoverHighlight(hoveredParcel.buildingMesh, false);
            }
            hoveredParcel = null;
        }
    }
}

function setBuildingHoverHighlight(meshOrGroup, isHovered) {
    if (!meshOrGroup) return;
    meshOrGroup.traverse(child => {
        if (child.isMesh && Array.isArray(child.material)) {
            const wallMat = child.material[1];
            if (wallMat) {
                if (isHovered) {
                    wallMat.emissive.setHex(0x555555); // subtle glow highlight on hover
                    wallMat.emissiveIntensity = 0.8;
                } else {
                    const tVal = (inTime && inTime.value) ? parseFloat(inTime.value) : 12.0;
                    const isNight = tVal < 7.5 || tVal > 19.5;
                    wallMat.emissive.setHex(0xffffff); // default emissive color
                    wallMat.emissiveIntensity = isNight ? 1.0 : 0.0;
                }
            }
        }
    });
}

function toggleTimeAnimation() {
    isTimeAnimating = !isTimeAnimating;
    if (isTimeAnimating) {
        btnPlayTime.textContent = "Pause";
        btnPlayTime.title = "Pause Shadow Animation";
        btnPlayTime.classList.add('playing');
        animateTime();
    } else {
        btnPlayTime.textContent = "Play";
        btnPlayTime.title = "Animate Solar Shadows";
        btnPlayTime.classList.remove('playing');
        if (timeAnimationId) {
            cancelAnimationFrame(timeAnimationId);
            timeAnimationId = null;
        }
    }
}

function animateTime() {
    if (!isTimeAnimating) return;

    let tVal = (inTime && inTime.value) ? parseFloat(inTime.value) : 12.0;
    tVal += 0.05; // speed of shadow animation
    if (tVal > 22.0) {
        tVal = 6.0; // loop back to morning
    }
    
    if (inTime) inTime.value = tVal.toFixed(2);
    
    const hours = Math.floor(tVal);
    const mins = Math.floor((tVal % 1) * 60).toString().padStart(2, '0');
    lblTime.textContent = `${hours}:${mins}`;
    updateSolarPhysics(tVal);

    timeAnimationId = requestAnimationFrame(animateTime);
}

// Spawn 3D vertical arrow drag handle on top of the selected building
function spawnHeightHandle(cx, cy, height) {
    removeHeightHandle();

    // Create an arrow shape pointing up (Teal cylinder + cone)
    const handleGroup = new THREE.Group();

    // Cylinder shaft
    const shaftGeom = new THREE.CylinderGeometry(0.18, 0.22, 2.2, 8);
    const mat = new THREE.MeshStandardMaterial({
        color: 0x0ea5e9, // bright light-blue/teal
        roughness: 0.3,
        metalness: 0.8,
        emissive: 0x0284c7,
        emissiveIntensity: 0.3
    });
    const shaft = new THREE.Mesh(shaftGeom, mat);
    shaft.position.y = 1.1;
    shaft.castShadow = true;
    handleGroup.add(shaft);

    // Cone tip
    const coneGeom = new THREE.ConeGeometry(0.45, 1.0, 8);
    const cone = new THREE.Mesh(coneGeom, mat);
    cone.position.y = 2.7;
    cone.castShadow = true;
    handleGroup.add(cone);

    handleGroup.position.set(cx, height + 0.5, -cy);
    handleGroup.userData = { isHeightHandle: true };

    scene.add(handleGroup);
    heightHandleMesh = handleGroup;
}

// Update height handle position matching building top
function updateHeightHandle() {
    if (!selectedParcel || !heightHandleMesh) return;
    
    // Calculate center of selected parcel
    let cx = 0, cy = 0;
    const ring = selectedParcel.outerRing;
    ring.forEach(pt => { cx += pt.x; cy += pt.y; });
    cx /= ring.length;
    cy /= ring.length;

    const floors = selectedParcel.params.floors;
    const floorH = selectedParcel.params.floorHeight;
    const height = floors * floorH;

    heightHandleMesh.position.set(cx, height + 0.5, -cy);
}

// Remove height handle and clean WebGL resources
function removeHeightHandle() {
    if (heightHandleMesh) {
        scene.remove(heightHandleMesh);
        heightHandleMesh.traverse(child => {
            if (child.isMesh) {
                child.geometry.dispose();
                child.material.dispose();
            }
        });
        heightHandleMesh = null;
    }
}

// Pointer down event handler to detect starting of height or setback dragging
function onPointerDown(event) {
    if (isUiEventTarget(event.target)) return;

    mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);

    const scaleHandles = [scaleXHandleMesh, scaleYHandleMesh].filter(Boolean);
    if (scaleHandles.length > 0 && selectedParcel) {
        const scaleIntersects = raycaster.intersectObjects(scaleHandles, true);
        if (scaleIntersects.length > 0) {
            const axis = scaleIntersects[0].object.parent?.userData?.axis || scaleIntersects[0].object.userData?.axis;
            if (axis) {
                isDraggingScaleAxis = axis;
                controls.enabled = false;
                dragIntersectionPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -0.1);
                const ring = getScaledBuildableRing(selectedParcel) || selectedParcel.outerRing;
                const ob = getOrientedBounds(ring);
                dragScaleCenter = { x: ob.cx, y: ob.cy };
                dragScaleAxis = axis === 'x'
                    ? { x: ob.ux, y: ob.uy }
                    : { x: ob.nx, y: ob.ny };
                dragStartScale = axis === 'x' ? selectedParcel.params.scaleX || 1 : selectedParcel.params.scaleY || 1;
                const hitPoint = new THREE.Vector3();
                raycaster.ray.intersectPlane(dragIntersectionPlane, hitPoint);
                const planPt = { x: hitPoint.x, y: -hitPoint.z };
                dragStartScaleDistance = Math.max(
                    0.1,
                    Math.abs((planPt.x - dragScaleCenter.x) * dragScaleAxis.x + (planPt.y - dragScaleCenter.y) * dragScaleAxis.y)
                );
                return;
            }
        }
    }

    if (setbackHandleMesh) {
        const handleIntersects = raycaster.intersectObject(setbackHandleMesh, true);
        if (handleIntersects.length > 0) {
            isDraggingSetback = true;
            controls.enabled = false; // Disable camera rotation
            
            // drag plane is the horizontal ground plane at y = 0.1
            dragIntersectionPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), -0.1);
            return;
        }
    }

    if (heightHandleMesh) {
        const handleIntersects = raycaster.intersectObject(heightHandleMesh, true);
        if (handleIntersects.length > 0) {
            isDraggingHeight = true;
            controls.enabled = false; // Disable camera rotation

            // Create a virtual vertical plane facing the camera, aligned with handle
            const normal = new THREE.Vector3();
            camera.getWorldDirection(normal);
            normal.y = 0;
            normal.normalize();
            
            dragIntersectionPlane = new THREE.Plane().setFromNormalAndCoplanarPoint(normal, heightHandleMesh.position);

            const intersectPoint = new THREE.Vector3();
            raycaster.ray.intersectPlane(dragIntersectionPlane, intersectPoint);
            
            dragStartHeight = intersectPoint.y;
            dragStartFloors = selectedParcel.params.floors;
        }
    }
}

// Pointer up event handler to release dragging
function onPointerUp(event) {
    if (isDraggingHeight) {
        isDraggingHeight = false;
        controls.enabled = true; // Re-enable camera rotation
    }
    if (isDraggingSetback) {
        isDraggingSetback = false;
        controls.enabled = true; // Re-enable camera rotation
    }
    if (isDraggingScaleAxis) {
        isDraggingScaleAxis = null;
        dragScaleCenter = null;
        dragScaleAxis = null;
        controls.enabled = true;
    }
}

// Spawn 3D horizontal dragging handle for setback adjustments
function spawnSetbackHandle(mx, my) {
    removeSetbackHandle();

    const handleGroup = new THREE.Group();

    // Torus ring flat on ground
    const torusGeom = new THREE.TorusGeometry(1.2, 0.22, 8, 24);
    torusGeom.rotateX(Math.PI / 2);
    const mat = new THREE.MeshStandardMaterial({
        color: 0x14b8a6,
        emissive: 0x14b8a6,
        emissiveIntensity: 0.6,
        roughness: 0.2,
        metalness: 0.8
    });
    const torus = new THREE.Mesh(torusGeom, mat);
    torus.castShadow = true;
    handleGroup.add(torus);

    // Cylinder pin
    const pinGeom = new THREE.CylinderGeometry(0.08, 0.08, 0.8, 8);
    const pin = new THREE.Mesh(pinGeom, mat);
    pin.position.y = 0.4;
    pin.castShadow = true;
    handleGroup.add(pin);

    // Sphere cap
    const capGeom = new THREE.SphereGeometry(0.22, 8, 8);
    const cap = new THREE.Mesh(capGeom, mat);
    cap.position.y = 0.8;
    cap.castShadow = true;
    handleGroup.add(cap);

    handleGroup.position.set(mx, 0.1, -my);
    handleGroup.userData = { isSetbackHandle: true };

    scene.add(handleGroup);
    setbackHandleMesh = handleGroup;
}

// Update setback handle position based on updated footprint coordinates
function updateSetbackHandle() {
    if (!selectedParcel || !setbackHandleMesh) return;

    const setback = selectedParcel.params.setback;
    const insetRing = offsetPolygonRing(selectedParcel.outerRing, setback);
    if (!insetRing || insetRing.length < 2) {
        removeSetbackHandle();
        return;
    }

    // Place handle on first segment midpoint
    const pt1 = insetRing[0];
    const pt2 = insetRing[1];
    const mx = (pt1.x + pt2.x) / 2;
    const my = (pt1.y + pt2.y) / 2;

    setbackHandleMesh.position.set(mx, 0.1, -my);
}

// Remove setback handle and clean WebGL resources
function removeSetbackHandle() {
    if (setbackHandleMesh) {
        scene.remove(setbackHandleMesh);
        setbackHandleMesh.traverse(child => {
            if (child.isMesh) {
                child.geometry.dispose();
                child.material.dispose();
            }
        });
        setbackHandleMesh = null;
    }
}

function buildScaleHandle(axis, colorHex) {
    const group = new THREE.Group();
    const mat = new THREE.MeshStandardMaterial({
        color: colorHex,
        emissive: colorHex,
        emissiveIntensity: 0.35,
        roughness: 0.24,
        metalness: 0.55
    });

    const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.16, 4.4, 12), mat);
    shaft.rotation.z = Math.PI / 2;
    shaft.position.y = 0.9;
    shaft.castShadow = true;
    group.add(shaft);

    [-1, 1].forEach(dir => {
        const cone = new THREE.Mesh(new THREE.ConeGeometry(0.42, 0.95, 16), mat);
        cone.rotation.z = dir > 0 ? -Math.PI / 2 : Math.PI / 2;
        cone.position.set(dir * 2.65, 0.9, 0);
        cone.castShadow = true;
        group.add(cone);
    });

    const box = new THREE.Mesh(new THREE.BoxGeometry(1.0, 1.0, 1.0), mat);
    box.position.y = 0.9;
    box.castShadow = true;
    group.add(box);

    const labelSprite = buildScaleHandleLabel(axis.toUpperCase(), colorHex);
    labelSprite.position.set(0, 1.95, 0);
    group.add(labelSprite);

    group.userData = { isScaleHandle: true, axis };
    return group;
}

function buildScaleHandleLabel(text, colorHex) {
    const canvas = document.createElement('canvas');
    canvas.width = 128;
    canvas.height = 72;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = 'rgba(255, 255, 255, 0.96)';
    ctx.strokeStyle = `#${colorHex.toString(16).padStart(6, '0')}`;
    ctx.lineWidth = 8;
    ctx.beginPath();
    drawRoundedRect(ctx, 8, 8, 112, 56, 18);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = `#${colorHex.toString(16).padStart(6, '0')}`;
    ctx.font = '800 34px Inter, Arial, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, 64, 39);

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    texture.magFilter = THREE.LinearFilter;
    const material = new THREE.SpriteMaterial({ map: texture, depthTest: false, depthWrite: false });
    const sprite = new THREE.Sprite(material);
    sprite.scale.set(3.2, 1.8, 1);
    return sprite;
}

function drawRoundedRect(ctx, x, y, width, height, radius) {
    const r = Math.min(radius, width / 2, height / 2);
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + width - r, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + r);
    ctx.lineTo(x + width, y + height - r);
    ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
    ctx.lineTo(x + r, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
    ctx.closePath();
}

function getScaledBuildableRing(item) {
    if (!item) return null;
    const buildable = resolveBuildableRing(item, item.params.setback || 0);
    return scaleRingInLocalAxes(buildable.ring, item.params.scaleX || 1, item.params.scaleY || 1);
}

function spawnScaleHandles(item) {
    removeScaleHandles();
    if (!item || item.params.usage === 'Park') return;

    const ring = getScaledBuildableRing(item);
    if (!ring || ring.length < 3) return;
    const ob = getOrientedBounds(ring);
    const massHeight = Math.max(1, (item.params.floors || 1) * (item.params.floorHeight || 3));
    const lift = massHeight + 1.2;

    scaleXHandleMesh = buildScaleHandle('x', 0xef4444);
    scaleXHandleMesh.position.set(
        ob.cx + ob.ux * (ob.W / 2 + 3.2),
        lift,
        -(ob.cy + ob.uy * (ob.W / 2 + 3.2))
    );
    scaleXHandleMesh.rotation.y = Math.atan2(ob.uy, ob.ux);
    scene.add(scaleXHandleMesh);

    scaleYHandleMesh = buildScaleHandle('y', 0x2563eb);
    scaleYHandleMesh.position.set(
        ob.cx + ob.nx * (ob.H / 2 + 3.2),
        lift,
        -(ob.cy + ob.ny * (ob.H / 2 + 3.2))
    );
    scaleYHandleMesh.rotation.y = Math.atan2(ob.ny, ob.nx);
    scene.add(scaleYHandleMesh);

    if (window.planxDebug) {
        window.planxDebug.scaleHandles = 2;
        window.planxDebug.scaleHandleAxes = ['x', 'y'];
    }
}

function updateScaleHandles() {
    if (!selectedParcel || selectedParcel.params.usage === 'Park') {
        removeScaleHandles();
        return;
    }
    spawnScaleHandles(selectedParcel);
}

function removeScaleHandles() {
    [scaleXHandleMesh, scaleYHandleMesh].forEach(handle => {
        if (!handle) return;
        scene.remove(handle);
        handle.traverse(child => {
            if (child.geometry) {
                child.geometry.dispose();
            }
            if (child.material) {
                if (child.material.map) child.material.map.dispose();
                child.material.dispose();
            }
        });
    });
    scaleXHandleMesh = null;
    scaleYHandleMesh = null;
    if (window.planxDebug) {
        window.planxDebug.scaleHandles = 0;
        window.planxDebug.scaleHandleAxes = [];
    }
}

// Helper to get minimum distance from point to polygon boundary
function getDistanceToPolygon(pt, ring) {
    let minDist = Infinity;
    const N = ring.length;
    for (let i = 0; i < N; i++) {
        const a = ring[i];
        const b = ring[(i + 1) % N];
        const dist = distToSegment(pt, a, b);
        if (dist < minDist) {
            minDist = dist;
        }
    }
    return minDist;
}

// 3D ruler and measurement tool

// Initialize the temporary measurement line and HTML label marker
function initTemporaryMeasurementAssets() {
    if (!tempMeasureLine) {
        const lineGeom = new THREE.BufferGeometry();
        const positions = new Float32Array(6); // 2 points * 3 coordinates
        lineGeom.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        const lineMat = new THREE.LineDashedMaterial({
            color: 0x38bdf8, // light blue/sky
            dashSize: 2,
            gapSize: 1,
            depthTest: false,
            transparent: true,
            opacity: 0.8
        });
        tempMeasureLine = new THREE.Line(lineGeom, lineMat);
        tempMeasureLine.visible = false;
        tempMeasureLine.userData = { isMeasurementElement: true };
        scene.add(tempMeasureLine);
    }

    if (!tempMeasureLabel) {
        const container = document.getElementById('measurement-overlay-container');
        if (container) {
            tempMeasureLabel = document.createElement('div');
            tempMeasureLabel.id = 'temp-measure-label';
            tempMeasureLabel.className = 'measurement-label temp';
            tempMeasureLabel.style.display = 'none';
            container.appendChild(tempMeasureLabel);
        }
    }
}

// Handle clicks in 3D scene when measurement tool is active
function handleMeasurementClick(pt) {
    initTemporaryMeasurementAssets();

    // Create marker at click position
    const markerGeom = new THREE.SphereGeometry(0.4, 16, 16);
    const markerMat = new THREE.MeshBasicMaterial({ color: 0x10b981, depthTest: false });
    const marker = new THREE.Mesh(markerGeom, markerMat);
    marker.position.copy(pt);
    marker.userData = { isMeasurementElement: true };
    scene.add(marker);

    if (measurementPoints.length === 0) {
        measurementPoints.push(pt);
        // Save the start marker
        savedMeasurements.push({ type: 'marker', mesh: marker });
    } else {
        const startPt = measurementPoints[0];
        const endPt = pt;
        
        // Permanent line
        const borderPoints = [startPt.clone(), endPt.clone()];
        const lineGeom = new THREE.BufferGeometry().setFromPoints(borderPoints);
        const lineMat = new THREE.LineBasicMaterial({
            color: 0x10b981, // neon emerald green
            linewidth: 2,
            depthTest: false
        });
        const line = new THREE.Line(lineGeom, lineMat);
        line.userData = { isMeasurementElement: true };
        scene.add(line);

        // Permanent Label
        const midpoint = new THREE.Vector3().addVectors(startPt, endPt).multiplyScalar(0.5);
        const container = document.getElementById('measurement-overlay-container');
        let labelEl = null;
        if (container) {
            labelEl = document.createElement('div');
            labelEl.className = 'measurement-label';
            const distance = startPt.distanceTo(endPt);
            labelEl.textContent = `${distance.toFixed(2)} m`;
            container.appendChild(labelEl);
        }

        // Save the permanent measurement assets
        savedMeasurements.push({
            type: 'measurement',
            line: line,
            markerStart: savedMeasurements.pop().mesh, // start marker mesh
            markerEnd: marker,
            labelEl: labelEl,
            midpoint: midpoint
        });

        // Show clear button
        if (btnClearMeasure) {
            btnClearMeasure.classList.remove('hidden');
        }

        // Reset for next measurement
        measurementPoints = [];
        if (tempMeasureLine) tempMeasureLine.visible = false;
        if (tempMeasureLabel) tempMeasureLabel.style.display = 'none';
    }
}

// Clear all measurements from scene and DOM
function clearAllMeasurements() {
    savedMeasurements.forEach(m => {
        if (m.type === 'marker' && m.mesh) {
            scene.remove(m.mesh);
            m.mesh.geometry.dispose();
            m.mesh.material.dispose();
        } else if (m.type === 'measurement') {
            if (m.line) {
                scene.remove(m.line);
                m.line.geometry.dispose();
                m.line.material.dispose();
            }
            if (m.markerStart) {
                scene.remove(m.markerStart);
                m.markerStart.geometry.dispose();
                m.markerStart.material.dispose();
            }
            if (m.markerEnd) {
                scene.remove(m.markerEnd);
                m.markerEnd.geometry.dispose();
                m.markerEnd.material.dispose();
            }
            if (m.labelEl) {
                m.labelEl.remove();
            }
        }
    });

    savedMeasurements = [];
    measurementPoints = [];
    if (tempMeasureLine) tempMeasureLine.visible = false;
    if (tempMeasureLabel) tempMeasureLabel.style.display = 'none';

    if (btnClearMeasure) {
        btnClearMeasure.classList.add('hidden');
    }
}

// Recalculate label coordinates on screen space
function updateMeasurementLabels() {
    const container = document.getElementById('measurement-overlay-container');
    if (!container) return;

    // 1. Update active temporary label
    if (tempMeasureLabel && tempMeasureLine && measurementPoints.length === 1) {
        // Find current intersection point under cursor
        const intersects = raycaster.intersectObjects(scene.children, true);
        const filtered = intersects.filter(hit => {
            return hit.object.type === 'Mesh' && 
                   !hit.object.userData?.isHeightHandle && 
                   !hit.object.userData?.isSetbackHandle && 
                   !hit.object.userData?.isMeasurementElement;
        });

        if (filtered.length > 0) {
            const hitPoint = filtered[0].point;
            const start = measurementPoints[0];
            const midpoint = new THREE.Vector3().addVectors(start, hitPoint).multiplyScalar(0.5);
            const screenPos = project3DToScreen(midpoint);
            tempMeasureLabel.style.left = `${screenPos.x}px`;
            tempMeasureLabel.style.top = `${screenPos.y}px`;
            
            const distance = start.distanceTo(hitPoint);
            tempMeasureLabel.textContent = `${distance.toFixed(2)} m`;
        }
    }

    // 2. Update all saved permanent labels
    savedMeasurements.forEach(m => {
        if (m.type === 'measurement' && m.labelEl) {
            const screenPos = project3DToScreen(m.midpoint);
            m.labelEl.style.left = `${screenPos.x}px`;
            m.labelEl.style.top = `${screenPos.y}px`;
        }
    });
}

function ensureHeightLabel(item, height) {
    const container = document.getElementById('measurement-overlay-container');
    if (!container || !item || item.params?.usage === 'Park' || height <= 0) {
        removeHeightLabel(item);
        return;
    }

    if (!item.heightLabelEl) {
        item.heightLabelEl = document.createElement('div');
        item.heightLabelEl.className = 'height-label';
        container.appendChild(item.heightLabelEl);
    }

    const bounds = getRingBounds(item.outerRing);
    item.heightLabelAnchor = new THREE.Vector3(bounds.cx, height + 2.5, -bounds.cy);
    item.heightLabelEl.textContent = `Z ${height.toFixed(1)} m`;
    item.heightLabelEl.classList.toggle('selected', selectedParcel === item);
}

function removeHeightLabel(item) {
    if (!item || !item.heightLabelEl) return;
    item.heightLabelEl.remove();
    item.heightLabelEl = null;
    item.heightLabelAnchor = null;
}

function updateHeightLabels() {
    const showLabels = toggleHeightLabelsEl ? toggleHeightLabelsEl.checked : true;
    parcelFeatures.forEach(item => {
        if (!item.heightLabelEl) return;
        const shouldShow = showLabels && item.heightLabelAnchor && toggleBuildingsEl && toggleBuildingsEl.checked;
        item.heightLabelEl.style.display = shouldShow ? 'block' : 'none';
        if (!shouldShow) return;

        item.heightLabelEl.classList.toggle('selected', selectedParcel === item);
        const screenPos = project3DToScreen(item.heightLabelAnchor);
        item.heightLabelEl.style.left = `${screenPos.x}px`;
        item.heightLabelEl.style.top = `${screenPos.y}px`;
    });
}

// Project 3D vector coordinates to screen pixel positions
function project3DToScreen(vec3) {
    const tempV = vec3.clone();
    tempV.project(camera);

    const x = (tempV.x * 0.5 + 0.5) * window.innerWidth;
    const y = (tempV.y * -0.5 + 0.5) * window.innerHeight;

    return { x, y };
}

// Procedural city solver and optimization

// Auto-solve zoning constraints for a specific parcel feature
function optimizeParcelZoning(item) {
    if (item.params.usage === 'Park') {
        item.params.floors = 0;
        item.params.setback = 3.0;
        item.params.typology = 'Tower';
        item.modified = true;
        return;
    }

    const maxBcr = item.params.maxBcr;
    const maxFar = item.params.maxFar;
    const maxHeight = item.params.maxHeight;
    const floorHeight = item.params.floorHeight || 3.0;

    // 1. Choose suitable building typology based on parcel area and aspect ratio
    const ob = getOrientedBounds(item.outerRing);
    const aspect = ob.W > 0 ? (ob.H / ob.W) : 1;
    let selectedTypology = 'Tower';

    if (item.area > 1500) {
        // Large parcels: MultiBuildingBlock, Courtyard, PodiumTower, or SteppedTower
        const r = Math.random();
        if (r < 0.40) selectedTypology = 'MultiBuildingBlock';
        else if (r < 0.60) selectedTypology = 'Courtyard';
        else if (r < 0.80) selectedTypology = 'PodiumTower';
        else selectedTypology = 'SteppedTower';
    } else if (item.area > 800) {
        // Medium parcels: Slab/Row, L-Shape, or U-Shape
        if (aspect > 1.7 || aspect < 0.6) {
            selectedTypology = 'Slab';
        } else {
            const r = Math.random();
            selectedTypology = r < 0.5 ? 'LShape' : 'UShape';
        }
    } else {
        // Small parcels: Tower
        selectedTypology = 'Tower';
    }

    item.params.typology = selectedTypology;

    // 2. Search for the optimal setback distance that satisfies the maximum BCR limit.
    let bestSetback = 3.0;
    let bestFootprint = 0;
    let bcrCompliantFound = false;

    // Search from 8.0 m down to 2.0 m for the smallest setback that keeps BCR compliant.
    for (let sb = 8.0; sb >= 2.0; sb -= 0.5) {
        const insetRing = offsetPolygonRing(item.outerRing, sb);
        if (!insetRing || insetRing.length < 3) continue;

        let footprintArea = 0;
        if (selectedTypology === 'Courtyard') {
            const innerSetback = 8;
            const innerRing = offsetPolygonRing(insetRing, innerSetback);
            const outerArea = calculatePolygonArea(insetRing);
            const innerArea = innerRing ? calculatePolygonArea(innerRing) : 0;
            footprintArea = Math.max(0, outerArea - innerArea);
        } else if (selectedTypology === 'Slab') {
            footprintArea = calculateShapeArea(buildSlabShape(insetRing, 12));
        } else if (selectedTypology === 'LShape') {
            footprintArea = calculateShapeArea(buildLShape(insetRing, 12));
        } else if (selectedTypology === 'UShape') {
            footprintArea = calculateShapeArea(buildUShape(insetRing, 12));
        } else if (selectedTypology === 'PodiumTower') {
            footprintArea = calculatePolygonArea(insetRing);
        } else if (selectedTypology === 'SteppedTower') {
            footprintArea = calculatePolygonArea(insetRing);
        } else if (selectedTypology === 'MultiBuildingBlock') {
            const obInset = getOrientedBounds(insetRing);
            const W = obInset.W;
            const localRing = insetRing.map(pt => {
                const rx = pt.x - obInset.cx;
                const ry = pt.y - obInset.cy;
                return {
                    x: rx * obInset.ux + ry * obInset.uy,
                    y: rx * obInset.nx + ry * obInset.ny
                };
            });
            let footArea = 0;
            if (W >= 40) {
                const localPoly1 = clipConvexPolygonVertical(localRing, obInset.minX, obInset.minX + W * 0.38);
                const localPoly3 = clipConvexPolygonVertical(localRing, obInset.minX + W * 0.62, obInset.maxX);
                let insetPoly1 = null;
                let insetPoly3 = null;
                if (localPoly1 && localPoly1.length >= 3) {
                    const globalPoly1 = localPoly1.map(pt => ({
                        x: obInset.cx + pt.x * obInset.ux + pt.y * obInset.nx,
                        y: obInset.cy + pt.x * obInset.uy + pt.y * obInset.ny
                    }));
                    insetPoly1 = offsetPolygonRing(globalPoly1, 1.2);
                }
                if (localPoly3 && localPoly3.length >= 3) {
                    const globalPoly3 = localPoly3.map(pt => ({
                        x: obInset.cx + pt.x * obInset.ux + pt.y * obInset.nx,
                        y: obInset.cy + pt.x * obInset.uy + pt.y * obInset.ny
                    }));
                    insetPoly3 = offsetPolygonRing(globalPoly3, 1.2);
                }
                if (insetPoly1 && insetPoly1.length >= 3) footArea += calculatePolygonArea(insetPoly1);
                if (insetPoly3 && insetPoly3.length >= 3) footArea += calculatePolygonArea(insetPoly3);
            } else {
                const localPoly1 = clipConvexPolygonVertical(localRing, obInset.minX, obInset.minX + W * 0.5);
                let insetPoly1 = null;
                if (localPoly1 && localPoly1.length >= 3) {
                    const globalPoly1 = localPoly1.map(pt => ({
                        x: obInset.cx + pt.x * obInset.ux + pt.y * obInset.nx,
                        y: obInset.cy + pt.x * obInset.uy + pt.y * obInset.ny
                    }));
                    insetPoly1 = offsetPolygonRing(globalPoly1, 1.2);
                }
                if (insetPoly1 && insetPoly1.length >= 3) footArea += calculatePolygonArea(insetPoly1);
            }
            footprintArea = footArea;
        } else { // Tower
            footprintArea = calculatePolygonArea(insetRing);
        }

        const bcr = item.area > 0 ? (footprintArea / item.area) : 0;
        if (bcr <= maxBcr) {
            bestSetback = sb;
            bestFootprint = footprintArea;
            bcrCompliantFound = true;
            break; // found the optimal setback maximizing footprint within constraints
        }
    }

    // Fallback if no compliant setback is found
    if (!bcrCompliantFound) {
        bestSetback = 4.0;
        const insetRing = offsetPolygonRing(item.outerRing, bestSetback);
        if (insetRing && insetRing.length >= 3) {
            bestFootprint = calculatePolygonArea(insetRing) * 0.5;
        }
    }

    item.params.setback = bestSetback;

    // 3. Optimize floor count by maximizing GFA up to FAR and height limits.
    let maxFloorsHeight = Math.floor(maxHeight / floorHeight);
    let maxFloorsFar = bestFootprint > 0 ? Math.floor((maxFar * item.area) / bestFootprint) : 1;

    // Refined solver for stacked typologies
    if (selectedTypology === 'PodiumTower') {
        const towerRing = offsetPolygonRing(offsetPolygonRing(item.outerRing, bestSetback), 3.5);
        const towerArea = towerRing ? calculatePolygonArea(towerRing) : bestFootprint * 0.6;
        const podiumArea = bestFootprint;
        const maxGfa = maxFar * item.area;
        const remainingGfa = maxGfa - podiumArea * 2;
        if (remainingGfa > 0 && towerArea > 0) {
            maxFloorsFar = 2 + Math.floor(remainingGfa / towerArea);
        } else {
            maxFloorsFar = Math.floor(maxGfa / podiumArea);
        }
    } else if (selectedTypology === 'SteppedTower') {
        const stepInterval = item.params.stepbackInterval || 4;
        const stepDepth = item.params.stepbackDepth || 1.5;
        let testFloors = 1;
        while (testFloors <= 30) {
            let remainingFloors = testFloors;
            let segmentIndex = 0;
            let testGfa = 0;
            while (remainingFloors > 0) {
                const currentSetback = bestSetback + segmentIndex * stepDepth;
                const segmentRing = offsetPolygonRing(item.outerRing, currentSetback);
                if (!segmentRing || segmentRing.length < 3) break;
                const segFloors = Math.min(stepInterval, remainingFloors);
                const segArea = calculatePolygonArea(segmentRing);
                testGfa += segArea * segFloors;
                remainingFloors -= segFloors;
                segmentIndex++;
            }
            if (testGfa / item.area > maxFar || testFloors * floorHeight > maxHeight) {
                testFloors--;
                break;
            }
            testFloors++;
        }
        maxFloorsFar = Math.max(1, testFloors);
    } else if (selectedTypology === 'MultiBuildingBlock') {
        const insetRing = offsetPolygonRing(item.outerRing, bestSetback);
        if (insetRing && insetRing.length >= 3) {
            const obInset = getOrientedBounds(insetRing);
            const W = obInset.W;
            const localRing = insetRing.map(pt => {
                const rx = pt.x - obInset.cx;
                const ry = pt.y - obInset.cy;
                return {
                    x: rx * obInset.ux + ry * obInset.uy,
                    y: rx * obInset.nx + ry * obInset.ny
                };
            });
            let footArea1 = 0;
            let footArea3 = 0;
            if (W >= 40) {
                const localPoly1 = clipConvexPolygonVertical(localRing, obInset.minX, obInset.minX + W * 0.38);
                const localPoly3 = clipConvexPolygonVertical(localRing, obInset.minX + W * 0.62, obInset.maxX);
                let insetPoly1 = null;
                let insetPoly3 = null;
                if (localPoly1 && localPoly1.length >= 3) {
                    const globalPoly1 = localPoly1.map(pt => ({
                        x: obInset.cx + pt.x * obInset.ux + pt.y * obInset.nx,
                        y: obInset.cy + pt.x * obInset.uy + pt.y * obInset.ny
                    }));
                    insetPoly1 = offsetPolygonRing(globalPoly1, 1.2);
                }
                if (localPoly3 && localPoly3.length >= 3) {
                    const globalPoly3 = localPoly3.map(pt => ({
                        x: obInset.cx + pt.x * obInset.ux + pt.y * obInset.nx,
                        y: obInset.cy + pt.x * obInset.uy + pt.y * obInset.ny
                    }));
                    insetPoly3 = offsetPolygonRing(globalPoly3, 1.2);
                }
                if (insetPoly1 && insetPoly1.length >= 3) footArea1 = calculatePolygonArea(insetPoly1);
                if (insetPoly3 && insetPoly3.length >= 3) footArea3 = calculatePolygonArea(insetPoly3);
            } else {
                const localPoly1 = clipConvexPolygonVertical(localRing, obInset.minX, obInset.minX + W * 0.5);
                let insetPoly1 = null;
                if (localPoly1 && localPoly1.length >= 3) {
                    const globalPoly1 = localPoly1.map(pt => ({
                        x: obInset.cx + pt.x * obInset.ux + pt.y * obInset.nx,
                        y: obInset.cy + pt.x * obInset.uy + pt.y * obInset.ny
                    }));
                    insetPoly1 = offsetPolygonRing(globalPoly1, 1.2);
                }
                if (insetPoly1 && insetPoly1.length >= 3) footArea1 = calculatePolygonArea(insetPoly1);
            }
            let testFloors = 1;
            while (testFloors <= 30) {
                const floorsA = Math.round(testFloors * 1.3);
                const floorsB = Math.round(testFloors * 0.7);
                const testGfa = footArea1 * floorsA + footArea3 * floorsB;
                const tallestHeight = Math.max(floorsA, floorsB) * floorHeight;
                if (testGfa / item.area > maxFar || tallestHeight > maxHeight) {
                    testFloors--;
                    break;
                }
                testFloors++;
            }
            maxFloorsFar = Math.max(1, testFloors);
        } else {
            maxFloorsFar = 1;
        }
    }

    let optimalFloors = Math.min(maxFloorsHeight, maxFloorsFar);
    optimalFloors = Math.max(1, Math.min(30, optimalFloors));

    item.params.floors = optimalFloors;
    item.modified = true;
}

// Automatically solve and optimize zoning constraints for all parcels in the city
function solveCityLayout() {
    if (!parcelFeatures || parcelFeatures.length === 0) {
        showToast("No parcels loaded to solve.", "warning");
        return;
    }

    parcelFeatures.forEach(item => {
        optimizeParcelZoning(item);
        rebuildParcel3D(item);
    });

    if (selectedParcel) {
        selectParcel(selectedParcel);
        updateDashboard(selectedParcel);
    }
    updateCitySummary();

    showToast(`Procedural solver optimized ${parcelFeatures.length} parcels.`, "success");
}

async function runPpudPipeline() {
    if (!parcelFeatures || parcelFeatures.length === 0) {
        showToast("No block features loaded for PPUD pipeline.", "warning");
        return;
    }
    showToast("Running PPUD Pipeline...", "info");
    try {
        const features = parcelFeatures.map(p => ({
            type: "Feature",
            geometry: {
                type: "Polygon",
                coordinates: [[...p.outerRing.map(pt => [pt.x, pt.y]), [p.outerRing[0].x, p.outerRing[0].y]]]
            },
            properties: { fid: p.fid }
        }));
        const resp = await fetch('/api/ppud/run', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                features,
                strategy: 'perimeter',
                block_typology: 'PerimeterBlock',
                max_bcr: 0.45,
                max_far: 2.0,
                max_height: 18.0,
                incremental_steps: 5,
                climate_feedback: true
            })
        });
        const data = await resp.json();
        if (data.status === 'ok' && data.results) {
            const summary = data.results[0]?.summary || {};
            showToast(
                `PPUD: ${summary.plot_count || '?'} plots, ` +
                `FAR ${summary.site_far || '?'}, ` +
                `Diversity ${summary.final_typology_diversity || '?'}`,
                "success"
            );
        } else {
            showToast("PPUD pipeline failed: " + (data.message || "unknown"), "error");
        }
    } catch (err) {
        console.error("PPUD error", err);
        showToast("PPUD pipeline error: " + err.message, "error");
    }
}

// Procedural landscaping and facade assets

// Generate a grass garden lawn in the setback zone
function buildSetbackLawn(item, insetRing) {
    if (item.params.usage === 'Park') return null;

    const lawnShape = new THREE.Shape();
    item.outerRing.forEach((pt, i) => {
        if (i === 0) lawnShape.moveTo(pt.x, pt.y);
        else lawnShape.lineTo(pt.x, pt.y);
    });

    if (insetRing && insetRing.length >= 3) {
        const hole = new THREE.Path();
        insetRing.forEach((pt, i) => {
            if (i === 0) hole.moveTo(pt.x, pt.y);
            else hole.lineTo(pt.x, pt.y);
        });
        lawnShape.holes.push(hole);
    }

    const lawnGeom = new THREE.ExtrudeGeometry(lawnShape, { depth: 0.08, bevelEnabled: false });
    lawnGeom.rotateX(-Math.PI / 2);
    lawnGeom.translate(0, 0.04, 0); // slightly elevated above street level

    const lawnMat = new THREE.MeshStandardMaterial({ color: 0x166534, roughness: 0.95 });
    const lawnMesh = new THREE.Mesh(lawnGeom, lawnMat);
    lawnMesh.receiveShadow = true;
    return lawnMesh;
}

// Construct a streetlight lamppost with a spotlight source
function buildStreetlight(x, y, z) {
    const group = new THREE.Group();
    group.position.set(x, y, z);

    // Pole
    const poleGeom = new THREE.CylinderGeometry(0.1, 0.15, 5, 8);
    const poleMat = new THREE.MeshStandardMaterial({ color: 0x475569, metalness: 0.8, roughness: 0.3 });
    const pole = new THREE.Mesh(poleGeom, poleMat);
    pole.position.y = 2.5;
    pole.castShadow = true;
    group.add(pole);

    // Arm
    const armGeom = new THREE.BoxGeometry(0.15, 0.15, 1.2);
    const arm = new THREE.Mesh(armGeom, poleMat);
    arm.position.set(0, 5.0, 0.5);
    arm.rotation.x = 0.1;
    arm.castShadow = true;
    group.add(arm);

    // Lamp bulb
    const bulbGeom = new THREE.SphereGeometry(0.2, 8, 8);
    const tVal = (inTime && inTime.value) ? parseFloat(inTime.value) : 12.0;
    const isNight = tVal < 7.5 || tVal > 19.5;
    const bulbMat = new THREE.MeshBasicMaterial({ 
        color: 0xfef08a,
        transparent: true,
        opacity: isNight ? 1.0 : 0.2
    });
    const bulb = new THREE.Mesh(bulbGeom, bulbMat);
    bulb.position.set(0, 4.9, 1.1);
    bulb.userData = { isStreetlightBulb: true };
    group.add(bulb);

    // Light source pointing downwards
    const spotlight = new THREE.SpotLight(0xfef08a, isNight ? 3.0 : 0.0, 15, Math.PI / 4, 0.5, 1);
    spotlight.position.set(0, 4.8, 1.1);
    spotlight.target.position.set(0, 0, 1.1);
    group.add(spotlight);
    group.add(spotlight.target);

    return group;
}

// Generate street trees and lamp posts along outer parcel boundary segments
function addSidewalkTreesAndAssets(group, item, insetRing) {
    if (item.params.usage === 'Park') return;

    // Calculate centroid of parcel to determine inward direction
    let cx = 0, cy = 0;
    item.outerRing.forEach(pt => { cx += pt.x; cy += pt.y; });
    cx /= item.outerRing.length;
    cy /= item.outerRing.length;

    const ring = item.outerRing;
    const len = ring.length;
    for (let i = 0; i < len; i++) {
        const p1 = ring[i];
        const p2 = ring[(i + 1) % len];

        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        // Place streetlights at corners
        if (i % 2 === 0) {
            const streetLamp = buildStreetlight(p1.x, 0.08, -p1.y);
            group.add(streetLamp);
        }

        // Place street trees on boundary segments longer than 12m
        if (dist > 12) {
            const numTrees = Math.floor(dist / 10);
            for (let j = 1; j <= numTrees; j++) {
                const t = j / (numTrees + 1);
                const bx = p1.x + dx * t;
                const by = p1.y + dy * t;

                // Inward normal pointing towards parcel center
                const nx = cx - bx;
                const ny = cy - by;
                const nLen = Math.sqrt(nx * nx + ny * ny);
                if (nLen > 0) {
                    // Offset inward by 1.8m so it sits inside the setback lawn
                    const offsetDistance = 1.8;
                    const tx = bx + (nx / nLen) * offsetDistance;
                    const ty = by + (ny / nLen) * offsetDistance;

                    const treeHeight = 3.5 + Math.random() * 2.5;
                    const styles = ['deciduous', 'spherical', 'conifer'];
                    const style = styles[Math.floor(Math.random() * styles.length)];
                    const tree = buildLowPolyTree(tx, 0.08, -ty, treeHeight, style);
                    group.add(tree);
                }
            }
        }
    }
}

// Procedurally extrude concrete balconies and railings on building facades
function addBuildingBalconies(group, insetRing, floors, floorHeight) {
    if (floors <= 1) return;

    const len = insetRing.length;
    for (let i = 0; i < len; i++) {
        // Place balconies on alternate facades for architectural rhythm
        if (i % 2 !== 0) continue;

        const p1 = insetRing[i];
        const p2 = insetRing[(i + 1) % len];

        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        const dist = Math.sqrt(dx * dx + dy * dy);

        // Build balconies on wide facades
        if (dist > 12) {
            const mx = (p1.x + p2.x) / 2;
            const my = (p1.y + p2.y) / 2;

            // Outward normal vector
            let nx = dy;
            let ny = -dx;
            const nLen = Math.sqrt(nx * nx + ny * ny);
            if (nLen > 0) {
                nx /= nLen;
                ny /= nLen;

                const angle = Math.atan2(dy, dx);

                // Add balconies for each upper floor
                for (let f = 1; f < floors; f++) {
                    const bh = f * floorHeight;

                    const balcony = new THREE.Group();
                    balcony.position.set(mx + nx * 0.5, bh, -(my + ny * 0.5));
                    balcony.rotation.y = angle;

                    // Slab
                    const slabWidth = dist * 0.4;
                    const slabGeom = new THREE.BoxGeometry(slabWidth, 0.12, 1.2);
                    const slabMat = new THREE.MeshStandardMaterial({ color: 0xe2e8f0, roughness: 0.5 });
                    const slab = new THREE.Mesh(slabGeom, slabMat);
                    slab.position.set(0, -0.06, 0.6);
                    slab.castShadow = true;
                    slab.receiveShadow = true;
                    balcony.add(slab);

                    // Glass railing
                    const railGeom = new THREE.BoxGeometry(slabWidth, 1.0, 0.05);
                    const railMat = new THREE.MeshStandardMaterial({ 
                        color: 0x38bdf8, 
                        transparent: true, 
                        opacity: 0.4,
                        roughness: 0.1,
                        metalness: 0.9
                    });
                    const rail = new THREE.Mesh(railGeom, railMat);
                    rail.position.set(0, 0.5, 1.2);
                    rail.castShadow = true;
                    balcony.add(rail);

                    // Glass railing sides
                    const sideRailGeom = new THREE.BoxGeometry(0.05, 1.0, 1.2);
                    for (let side = -1; side <= 1; side += 2) {
                        const sideRail = new THREE.Mesh(sideRailGeom, railMat);
                        sideRail.position.set(side * (slabWidth / 2), 0.5, 0.6);
                        sideRail.castShadow = true;
                        balcony.add(sideRail);
                    }

                    group.add(balcony);
                }
            }
        }
    }
}

// Clip convex polygon with vertical lines in 2D local space
function clipConvexPolygonVertical(localRing, X_start, X_end) {
    const N = localRing.length;
    const allPts = [];

    // 1. Get intersections at X_start
    const y_start_intersects = [];
    for (let i = 0; i < N; i++) {
        const p1 = localRing[i];
        const p2 = localRing[(i + 1) % N];
        if ((p1.x <= X_start && X_start <= p2.x) || (p2.x <= X_start && X_start <= p1.x)) {
            if (Math.abs(p2.x - p1.x) > 0.0001) {
                const t = (X_start - p1.x) / (p2.x - p1.x);
                const y = p1.y + t * (p2.y - p1.y);
                y_start_intersects.push(y);
            }
        }
    }
    y_start_intersects.sort((a, b) => a - b);
    if (y_start_intersects.length >= 2) {
        allPts.push({ x: X_start, y: y_start_intersects[0] });
        allPts.push({ x: X_start, y: y_start_intersects[y_start_intersects.length - 1] });
    }

    // 2. Get original vertices that lie between X_start and X_end
    for (let i = 0; i < N; i++) {
        const p = localRing[i];
        if (p.x > X_start && p.x < X_end) {
            allPts.push(p);
        }
    }

    // 3. Get intersections at X_end
    const y_end_intersects = [];
    for (let i = 0; i < N; i++) {
        const p1 = localRing[i];
        const p2 = localRing[(i + 1) % N];
        if ((p1.x <= X_end && X_end <= p2.x) || (p2.x <= X_end && X_end <= p1.x)) {
            if (Math.abs(p2.x - p1.x) > 0.0001) {
                const t = (X_end - p1.x) / (p2.x - p1.x);
                const y = p1.y + t * (p2.y - p1.y);
                y_end_intersects.push(y);
            }
        }
    }
    y_end_intersects.sort((a, b) => a - b);
    if (y_end_intersects.length >= 2) {
        allPts.push({ x: X_end, y: y_end_intersects[y_end_intersects.length - 1] });
        allPts.push({ x: X_end, y: y_end_intersects[0] });
    }

    // Filter duplicates
    const uniquePts = [];
    allPts.forEach(p => {
        if (!uniquePts.some(u => Math.abs(u.x - p.x) < 0.01 && Math.abs(u.y - p.y) < 0.01)) {
            uniquePts.push(p);
        }
    });

    if (uniquePts.length < 3) return null;

    // Sort counter-clockwise around centroid
    let cx = 0, cy = 0;
    uniquePts.forEach(p => { cx += p.x; cy += p.y; });
    cx /= uniquePts.length;
    cy /= uniquePts.length;

    uniquePts.sort((a, b) => {
        return Math.atan2(a.y - cy, a.x - cx) - Math.atan2(b.y - cy, b.x - cx);
    });

    return uniquePts;
}

// Generate a detailed low-poly car group (reused for parked cars and traffic)
function buildDetailedCar(colorHex, scale = 1.0) {
    const carGroup = new THREE.Group();

    // Body base
    const bodyGeom = new THREE.BoxGeometry(2.4 * scale, 0.6 * scale, 1.1 * scale);
    const bodyMat = new THREE.MeshStandardMaterial({ color: colorHex, roughness: 0.5 });
    const body = new THREE.Mesh(bodyGeom, bodyMat);
    body.castShadow = true;
    body.receiveShadow = true;
    body.position.y = 0.3 * scale;
    carGroup.add(body);

    // Cabin
    const cabinGeom = new THREE.BoxGeometry(1.3 * scale, 0.5 * scale, 0.95 * scale);
    const cabinMat = new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.2 });
    const cabin = new THREE.Mesh(cabinGeom, cabinMat);
    cabin.castShadow = true;
    cabin.position.set(-0.15 * scale, 0.8 * scale, 0);
    carGroup.add(cabin);

    // Wheels (4 cylinders)
    const wheelGeom = new THREE.CylinderGeometry(0.24 * scale, 0.24 * scale, 0.2 * scale, 8);
    wheelGeom.rotateX(Math.PI / 2);
    const wheelMat = new THREE.MeshStandardMaterial({ color: 0x18181b, roughness: 0.9 });
    
    const wheelOffsets = [
        { x: 0.7, z: 0.55 },
        { x: 0.7, z: -0.55 },
        { x: -0.7, z: 0.55 },
        { x: -0.7, z: -0.55 }
    ];
    
    wheelOffsets.forEach(offset => {
        const wheel = new THREE.Mesh(wheelGeom, wheelMat);
        wheel.position.set(offset.x * scale, 0.12 * scale, offset.z * scale);
        wheel.castShadow = true;
        carGroup.add(wheel);
    });

    // Lights
    const headlightGeom = new THREE.SphereGeometry(0.08 * scale, 8, 8);
    const headlightMat = new THREE.MeshBasicMaterial({ color: 0xfef08a });
    const taillightMat = new THREE.MeshBasicMaterial({ color: 0xef4444 });

    for (let side = -1; side <= 1; side += 2) {
        const hl = new THREE.Mesh(headlightGeom, headlightMat);
        hl.position.set(1.2 * scale, 0.3 * scale, side * 0.45 * scale);
        hl.userData = { isHeadlight: true };
        hl.visible = false;
        carGroup.add(hl);

        const tl = new THREE.Mesh(headlightGeom, taillightMat);
        tl.position.set(-1.2 * scale, 0.3 * scale, side * 0.45 * scale);
        tl.userData = { isTaillight: true };
        tl.visible = false;
        carGroup.add(tl);
    }

    return carGroup;
}

/* ==========================================================================
   Evolutionary Studio & Analytics Engine Logic (Parametric Process)
/* ==========================================================================
   Evolutionary Studio & Analytics Engine Logic (Parametric Process)
   ========================================================================== */

// State Variables
let wallaceiResult = null;
let activeParetoSolution = null;
let activeWallaceiSubtab = 'scatter';
let streamingRunId = null;
let streamingPollTimer = null;
let generationHistory = [];
let currentClusterResult = null;
let pcpBrushFilters = {};
let filteredSolutionIds = null;
let viewGeneration = -1;

const CLUSTER_COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#6366f1'];

// DOM Elements - Tabs and Views
const tabBtnParametric = document.getElementById('tab-btn-parametric');
const tabBtnWallacei = document.getElementById('tab-btn-wallacei');
const parametricView = document.getElementById('parametric-cockpit-view');
const wallaceiView = document.getElementById('wallacei-studio-view');
const editorControls = document.getElementById('editor-controls');

// DOM Elements - Wallacei Params
const inWallaceiPop = document.getElementById('input-wallacei-pop');
const valWallaceiPop = document.getElementById('val-wallacei-pop');
const inWallaceiGen = document.getElementById('input-wallacei-gen');
const valWallaceiGen = document.getElementById('val-wallacei-gen');
const inWallaceiCross = document.getElementById('input-wallacei-cross');
const valWallaceiCross = document.getElementById('val-wallacei-cross');
const inWallaceiMut = document.getElementById('input-wallacei-mut');
const valWallaceiMut = document.getElementById('val-wallacei-mut');

// Bounds
const inBoundMinFloors = document.getElementById('bound-min-floors');
const inBoundMaxFloors = document.getElementById('bound-max-floors');
const inBoundMinSetback = document.getElementById('bound-min-setback');
const inBoundMaxSetback = document.getElementById('bound-max-setback');

// DOM Elements - Run/Progress
const btnRunWallacei = document.getElementById('btn-run-wallacei');
const btnStopWallacei = document.getElementById('btn-stop-wallacei');
const wallaceiProgress = document.getElementById('wallacei-progress');
const wallaceiProgressFill = document.getElementById('wallacei-progress-fill');
const wallaceiProgressText = document.getElementById('wallacei-progress-text');
const progGenCounter = document.getElementById('prog-gen-counter');
const progElapsed = document.getElementById('prog-elapsed');
const progEta = document.getElementById('prog-eta');
const progParetoCount = document.getElementById('prog-pareto-count');
const progHv = document.getElementById('prog-hv');

// DOM Elements - Analytics & Subtabs
const wallaceiAnalyticsContainer = document.getElementById('wallacei-analytics-container');

const subtabsMap = [
    { btn: document.getElementById('subtab-scatter'), view: document.getElementById('view-scatter'), name: 'scatter' },
    { btn: document.getElementById('subtab-pcp'), view: document.getElementById('view-pcp'), name: 'pcp' },
    { btn: document.getElementById('subtab-fitness'), view: document.getElementById('view-fitness'), name: 'fitness' },
    { btn: document.getElementById('subtab-radar'), view: document.getElementById('view-radar'), name: 'radar' },
    { btn: document.getElementById('subtab-cluster'), view: document.getElementById('view-cluster'), name: 'cluster' },
    { btn: document.getElementById('subtab-population'), view: document.getElementById('view-population'), name: 'population' }
];

// DOM Elements - Scatter
const scatterAxisX = document.getElementById('scatter-axis-x');
const scatterAxisY = document.getElementById('scatter-axis-y');
const scatterColorMode = document.getElementById('scatter-color-mode');
const canvasScatter = document.getElementById('canvas-pareto-scatter');

// DOM Elements - PCP
const canvasPcp = document.getElementById('canvas-pcp');

// DOM Elements - Fitness
const fitnessMetricSelect = document.getElementById('fitness-metric-select');
const canvasFitness = document.getElementById('canvas-fitness');

// DOM Elements - Radar
const canvasRadar = document.getElementById('canvas-radar');

// DOM Elements - Cluster
const kmeansK = document.getElementById('kmeans-k');
const btnAutoK = document.getElementById('btn-auto-k');
const btnRunKmeans = document.getElementById('btn-run-kmeans');
const canvasCluster = document.getElementById('canvas-cluster');
const clusterSummary = document.getElementById('cluster-summary');

// DOM Elements - Population
const popFilter = document.getElementById('pop-filter');
const popSort = document.getElementById('pop-sort');
const popTableBody = document.getElementById('pop-table-body');
const popCountLabel = document.getElementById('pop-count-label');
const btnExportSolutions = document.getElementById('btn-export-solutions');
const btnExportJson = document.getElementById('btn-export-json');

// DOM Elements - Gen Slider
const genSlider = document.getElementById('gen-slider');
const genSliderVal = document.getElementById('gen-slider-val');
const genPopCount = document.getElementById('gen-pop-count');
const genParetoCount = document.getElementById('gen-pareto-count');
const genHypervolume = document.getElementById('gen-hypervolume');

// DOM Elements - Selection
const selectionMethod = document.getElementById('selection-method');

// DOM Elements - Solution Card & Sync
const solIdBadge = document.getElementById('sol-id-badge');
const solScoreBadge = document.getElementById('sol-score-badge');
const solMetricsGrid = document.getElementById('sol-metrics-grid');
const btnPreviewPhenotype = document.getElementById('btn-preview-phenotype');
const btnSyncWallaceiQgis = document.getElementById('btn-sync-wallacei-qgis');

// --- Tab Switching ---
const controlDockEl = document.getElementById('control-dock');
if (tabBtnParametric && tabBtnWallacei) {
    tabBtnParametric.addEventListener('click', () => {
        tabBtnParametric.classList.add('active');
        tabBtnWallacei.classList.remove('active');
        parametricView.classList.remove('hidden');
        wallaceiView.classList.add('hidden');
        if (editorControls) editorControls.classList.remove('hidden');
        if (controlDockEl) controlDockEl.classList.remove('wide-dock');
    });

    tabBtnWallacei.addEventListener('click', () => {
        tabBtnWallacei.classList.add('active');
        tabBtnParametric.classList.remove('active');
        wallaceiView.classList.remove('hidden');
        parametricView.classList.add('hidden');
        if (editorControls) editorControls.classList.add('hidden');
        if (controlDockEl) controlDockEl.classList.add('wide-dock');
    });
}

// --- Slider Input Handlers ---
if (inWallaceiPop) inWallaceiPop.addEventListener('input', e => { if (valWallaceiPop) valWallaceiPop.textContent = e.target.value; });
if (inWallaceiGen) inWallaceiGen.addEventListener('input', e => { if (valWallaceiGen) valWallaceiGen.textContent = e.target.value; });
if (inWallaceiCross) inWallaceiCross.addEventListener('input', e => { if (valWallaceiCross) valWallaceiCross.textContent = parseFloat(e.target.value).toFixed(2); });
if (inWallaceiMut) inWallaceiMut.addEventListener('input', e => { if (valWallaceiMut) valWallaceiMut.textContent = parseFloat(e.target.value).toFixed(2); });

// --- Subtab Switching ---
subtabsMap.forEach(item => {
    if (item.btn && item.view) {
        item.btn.addEventListener('click', () => {
            subtabsMap.forEach(s => {
                if (s.btn) s.btn.classList.remove('active');
                if (s.view) s.view.classList.add('hidden');
            });
            item.btn.classList.add('active');
            item.view.classList.remove('hidden');
            activeWallaceiSubtab = item.name;
            renderWallaceiCharts();
        });
    }
});

// --- Objective Specs Builder ---
function buildObjectiveSpecs() {
    const specs = [];
    const mapping = [
        { id: 'obj-gfa', dir: 'dir-gfa', name: 'gfa' },
        { id: 'obj-score', dir: 'dir-score', name: 'planx_score' },
        { id: 'obj-wind', dir: 'dir-wind', name: 'wind_ventilation' },
        { id: 'obj-solar', dir: 'dir-solar', name: 'solar_radiation_kwh' },
        { id: 'obj-pollution', dir: 'dir-pollution', name: 'pollution_dispersion' },
        { id: 'obj-svf', dir: 'dir-svf', name: 'sky_view_factor' },
        { id: 'obj-constraint', dir: 'dir-constraint', name: 'constraint_penalty' },
        { id: 'obj-carbon', dir: 'dir-carbon', name: 'carbon_kg' },
        { id: 'obj-daylight', dir: 'dir-daylight', name: 'daylight_index' },
        { id: 'obj-runoff', dir: 'dir-runoff', name: 'runoff_m3' },
        { id: 'obj-utci', dir: 'dir-utci', name: 'utci_score' },
        { id: 'obj-roi', dir: 'dir-roi', name: 'roi_percentage' },
        { id: 'obj-pv', dir: 'dir-pv', name: 'pv_yield_mwh' },
        { id: 'obj-openspace', dir: 'dir-openspace', name: 'open_space_ratio' },
        { id: 'obj-pedcomfort', dir: 'dir-pedcomfort', name: 'pedestrian_wind_comfort' }
    ];

    mapping.forEach(m => {
        const cb = document.getElementById(m.id);
        const d = document.getElementById(m.dir);
        if (cb && cb.checked) {
            specs.push({ name: m.name, direction: d ? d.value : 'max' });
        }
    });
    return specs;
}

// --- Streaming Optimization Client ---
if (btnRunWallacei) {
    btnRunWallacei.addEventListener('click', async () => {
        const objectiveSpecs = buildObjectiveSpecs();
        if (objectiveSpecs.length === 0) {
            showToast('Select at least one objective function.', 'warning');
            return;
        }

        const popSize = parseInt(inWallaceiPop?.value || '30', 10);
        const generations = parseInt(inWallaceiGen?.value || '15', 10);
        const crossoverRate = parseFloat(inWallaceiCross?.value || '0.8');
        const mutationRate = parseFloat(inWallaceiMut?.value || '0.15');

        let targetArea = 1200.0;
        if (selectedParcel && selectedParcel.area) targetArea = selectedParcel.area;
        else if (parcelFeatures.length > 0) targetArea = parcelFeatures.reduce((acc, p) => acc + (p.area || 1000), 0) / parcelFeatures.length;

        // Collect Bounds
        const bounds = {
            min_floors: parseInt(inBoundMinFloors?.value || '1', 10),
            max_floors: parseInt(inBoundMaxFloors?.value || '30', 10),
            min_setback: parseFloat(inBoundMinSetback?.value || '0'),
            max_setback: parseFloat(inBoundMaxSetback?.value || '10')
        };

        if (wallaceiProgress) wallaceiProgress.classList.remove('hidden');
        if (wallaceiProgressFill) wallaceiProgressFill.style.width = '5%';
        if (wallaceiProgressText) wallaceiProgressText.textContent = `Starting optimization...`;
        btnRunWallacei.disabled = true;
        if (btnStopWallacei) btnStopWallacei.disabled = false;

        generationHistory = [];
        wallaceiResult = null;
        viewGeneration = -1;
        if (genSlider) {
            genSlider.max = generations;
            genSlider.value = generations;
        }

        try {
            const resp = await fetch('/api/optimize/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    algorithm: document.getElementById('input-algorithm')?.value || 'nsga2',
                    parcel_area: targetArea,
                    parcels_data: parcelFeatures.map(p => ({ id: p.fid, area: p.area || 1000 })),
                    objective_specs: objectiveSpecs,
                    pop_size: popSize,
                    generations: generations,
                    crossover_rate: crossoverRate,
                    mutation_rate: mutationRate,
                    bounds: bounds
                })
            });

            if (!resp.ok) throw new Error(`Server returned HTTP ${resp.status}`);
            const data = await resp.json();
            if (data.status === 'error') throw new Error(data.message || 'Error starting optimization');

            streamingRunId = data.run_id;
            startPollingStatus(streamingRunId);
        } catch (err) {
            if (wallaceiProgress) wallaceiProgress.classList.add('hidden');
            showToast(`Failed to start optimization: ${err.message}`, 'error');
            btnRunWallacei.disabled = false;
            if (btnStopWallacei) btnStopWallacei.disabled = true;
        }
    });
}

if (btnStopWallacei) {
    btnStopWallacei.addEventListener('click', async () => {
        if (!streamingRunId) return;
        try {
            await fetch(`/api/optimize/stop/${streamingRunId}`, { method: 'POST' });
            showToast('Stop requested...', 'info');
        } catch (err) {
            console.error('Stop error', err);
        }
    });
}

function startPollingStatus(runId) {
    if (streamingPollTimer) clearInterval(streamingPollTimer);
    streamingPollTimer = setInterval(async () => {
        try {
            const resp = await fetch(`/api/optimize/status/${runId}`);
            if (!resp.ok) return;
            const data = await resp.json();

            if (data.status === 'error') {
                clearInterval(streamingPollTimer);
                showToast(`Optimization Error: ${data.message || 'Unknown error'}`, 'error');
                btnRunWallacei.disabled = false;
                if (btnStopWallacei) btnStopWallacei.disabled = true;
                if (wallaceiProgress) wallaceiProgress.classList.add('hidden');
                return;
            }

            const currentGen = data.current_generation || 0;
            const totalGen = data.total_generations || 1;
            const pct = (currentGen / totalGen) * 100;

            if (wallaceiProgressFill) wallaceiProgressFill.style.width = `${pct}%`;
            if (wallaceiProgressText) wallaceiProgressText.textContent = `Generation ${currentGen} / ${totalGen}`;
            if (progGenCounter) progGenCounter.textContent = `${currentGen}/${totalGen}`;

            if (data.elapsed_seconds !== undefined) {
                if (progElapsed) progElapsed.textContent = `${data.elapsed_seconds.toFixed(1)}s`;
                if (currentGen > 0 && progEta) {
                    const secPerGen = data.elapsed_seconds / currentGen;
                    const eta = secPerGen * (totalGen - currentGen);
                    progEta.textContent = `${eta.toFixed(1)}s`;
                }
            }

            if (data.generation_data) {
                const gdata = data.generation_data;
                generationHistory[gdata.generation] = gdata;
                
                if (progParetoCount) progParetoCount.textContent = (gdata.pareto_front || []).length;
                if (progHv && gdata.hypervolume !== undefined) progHv.textContent = gdata.hypervolume.toFixed(4);
                if (genParetoCount) genParetoCount.textContent = (gdata.pareto_front || []).length;
                if (genHypervolume && gdata.hypervolume !== undefined) genHypervolume.textContent = gdata.hypervolume.toFixed(4);

                if (wallaceiAnalyticsContainer && !wallaceiAnalyticsContainer.classList.contains('hidden')) {
                    renderWallaceiCharts();
                }
            }

            if (data.status === 'completed' || data.status === 'stopped') {
                clearInterval(streamingPollTimer);
                wallaceiResult = data;
                if (data.generation_data && data.generation_data.k_means_clusters) {
                    currentClusterResult = data.generation_data.k_means_clusters;
                }
                btnRunWallacei.disabled = false;
                if (btnStopWallacei) btnStopWallacei.disabled = true;
                
                setTimeout(() => { if (wallaceiProgress) wallaceiProgress.classList.add('hidden'); }, 1200);

                if (wallaceiAnalyticsContainer) wallaceiAnalyticsContainer.classList.remove('hidden');

                if (wallaceiResult.pareto_solutions && wallaceiResult.pareto_solutions.length > 0) {
                    activeParetoSolution = wallaceiResult.pareto_solutions[0];
                    displaySolutionCard(activeParetoSolution);
                    applyPhenotypeTo3D(activeParetoSolution);
                }
                
                if (genSlider) {
                    genSlider.max = totalGen;
                    genSlider.value = totalGen;
                }

                renderWallaceiCharts();
                showToast(`Optimization ${data.status}!`, data.status === 'completed' ? 'success' : 'warning');
            }
        } catch (err) {
            console.error('Poll error', err);
        }
    }, 500);
}

// --- Generation Slider ---
if (genSlider) {
    genSlider.addEventListener('input', e => {
        const val = parseInt(e.target.value, 10);
        const max = parseInt(genSlider.max, 10);
        if (val >= max) {
            viewGeneration = -1;
            if (genSliderVal) genSliderVal.textContent = 'All';
            const latest = generationHistory[generationHistory.length - 1];
            if (latest) {
                if (genPopCount) genPopCount.textContent = (latest.individuals || []).length;
                if (genParetoCount) genParetoCount.textContent = (latest.pareto_front || []).length;
                if (genHypervolume) genHypervolume.textContent = (latest.hypervolume || 0).toFixed(4);
            }
        } else {
            viewGeneration = val;
            if (genSliderVal) genSliderVal.textContent = `Gen ${val}`;
            const gdata = generationHistory[val];
            if (gdata) {
                if (genPopCount) genPopCount.textContent = (gdata.individuals || []).length;
                if (genParetoCount) genParetoCount.textContent = (gdata.pareto_front || []).length;
                if (genHypervolume) genHypervolume.textContent = (gdata.hypervolume || 0).toFixed(4);
            } else {
                if (genPopCount) genPopCount.textContent = '-';
                if (genParetoCount) genParetoCount.textContent = '-';
                if (genHypervolume) genHypervolume.textContent = '-';
            }
        }
        renderWallaceiCharts();
    });
}

function getCurrentSolutions() {
    if (viewGeneration === -1) {
        return wallaceiResult?.all_solutions || [];
    }
    const gdata = generationHistory[viewGeneration];
    return gdata?.individuals || [];
}

// --- Chart Renderers ---
function renderWallaceiCharts() {
    if (activeWallaceiSubtab === 'scatter') renderParetoScatter();
    else if (activeWallaceiSubtab === 'pcp') renderPCP();
    else if (activeWallaceiSubtab === 'radar') renderRadar();
    else if (activeWallaceiSubtab === 'fitness') renderFitnessChart();
    else if (activeWallaceiSubtab === 'cluster') renderClusterChart();
    else if (activeWallaceiSubtab === 'population') renderPopulationTable();
}

function renderParetoScatter() {
    if (!canvasScatter) return;
    const ctx = canvasScatter.getContext('2d');
    const w = canvasScatter.width;
    const h = canvasScatter.height;
    ctx.clearRect(0, 0, w, h);

    const xKey = scatterAxisX ? scatterAxisX.value : 'gfa';
    const yKey = scatterAxisY ? scatterAxisY.value : 'planx_score';
    const colorMode = scatterColorMode ? scatterColorMode.value : 'rank';

    const solutions = getCurrentSolutions();
    if (!solutions || solutions.length === 0) return;

    let xVals = solutions.map(s => s.metrics?.[xKey] ?? s.objectives?.[xKey] ?? 0);
    let yVals = solutions.map(s => s.metrics?.[yKey] ?? s.objectives?.[yKey] ?? 0);

    let minX = Math.min(...xVals), maxX = Math.max(...xVals);
    let minY = Math.min(...yVals), maxY = Math.max(...yVals);

    if (maxX === minX) { maxX += 1; minX -= 1; }
    if (maxY === minY) { maxY += 1; minY -= 1; }

    const pad = 35;
    const plotW = w - 2 * pad;
    const plotH = h - 2 * pad;

    ctx.strokeStyle = '#cbd5e1';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(pad, pad);
    ctx.lineTo(pad, h - pad);
    ctx.lineTo(w - pad, h - pad);
    ctx.stroke();

    ctx.fillStyle = '#64748b';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(xKey.toUpperCase(), w / 2, h - 8);
    ctx.save();
    ctx.translate(12, h / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.fillText(yKey.toUpperCase(), 0, 0);
    ctx.restore();

    solutions.forEach(sol => {
        if (filteredSolutionIds && !filteredSolutionIds.has(sol.id)) return;

        const xVal = sol.metrics?.[xKey] ?? sol.objectives?.[xKey] ?? 0;
        const yVal = sol.metrics?.[yKey] ?? sol.objectives?.[yKey] ?? 0;

        const px = pad + ((xVal - minX) / (maxX - minX)) * plotW;
        const py = (h - pad) - ((yVal - minY) / (maxY - minY)) * plotH;

        const isRank1 = sol.rank === 1;
        const isSelected = activeParetoSolution && activeParetoSolution.id === sol.id;

        ctx.beginPath();
        ctx.arc(px, py, isSelected ? 8 : (isRank1 ? 5 : 3), 0, Math.PI * 2);

        if (isSelected) {
            ctx.fillStyle = '#06b6d4';
            ctx.shadowColor = '#06b6d4';
            ctx.shadowBlur = 8;
        } else {
            if (colorMode === 'rank') {
                ctx.fillStyle = isRank1 ? '#10b981' : '#94a3b8';
            } else if (colorMode === 'cluster') {
                const clusterIdx = sol.cluster_id !== undefined ? sol.cluster_id : 0;
                ctx.fillStyle = CLUSTER_COLORS[clusterIdx % CLUSTER_COLORS.length];
            } else if (colorMode === 'generation') {
                const genNorm = sol.generation ? sol.generation / (wallaceiResult?.total_generations || 1) : 0;
                const r = Math.floor(255 * genNorm);
                const b = Math.floor(255 * (1 - genNorm));
                ctx.fillStyle = `rgb(${r}, 0, ${b})`;
            }
            ctx.shadowBlur = isRank1 ? 4 : 0;
            ctx.shadowColor = ctx.fillStyle;
        }
        ctx.fill();
        ctx.shadowBlur = 0;

        if (isRank1 || isSelected) {
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 1.5;
            ctx.stroke();
        }
    });
}

if (canvasScatter) {
    canvasScatter.addEventListener('click', e => {
        const solutions = getCurrentSolutions();
        if (!solutions || solutions.length === 0) return;
        const rect = canvasScatter.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        const w = canvasScatter.width;
        const h = canvasScatter.height;
        const pad = 35;
        const plotW = w - 2 * pad;
        const plotH = h - 2 * pad;

        const xKey = scatterAxisX ? scatterAxisX.value : 'gfa';
        const yKey = scatterAxisY ? scatterAxisY.value : 'planx_score';

        let xVals = solutions.map(s => s.metrics?.[xKey] ?? s.objectives?.[xKey] ?? 0);
        let yVals = solutions.map(s => s.metrics?.[yKey] ?? s.objectives?.[yKey] ?? 0);

        let minX = Math.min(...xVals), maxX = Math.max(...xVals);
        let minY = Math.min(...yVals), maxY = Math.max(...yVals);

        if (maxX === minX) { maxX += 1; minX -= 1; }
        if (maxY === minY) { maxY += 1; minY -= 1; }

        let closest = null;
        let minDist = Infinity;

        solutions.forEach(sol => {
            if (filteredSolutionIds && !filteredSolutionIds.has(sol.id)) return;
            const xVal = sol.metrics?.[xKey] ?? sol.objectives?.[xKey] ?? 0;
            const yVal = sol.metrics?.[yKey] ?? sol.objectives?.[yKey] ?? 0;

            const px = pad + ((xVal - minX) / (maxX - minX)) * plotW;
            const py = (h - pad) - ((yVal - minY) / (maxY - minY)) * plotH;

            const dist = Math.hypot(mouseX - px, mouseY - py);
            if (dist < minDist) {
                minDist = dist;
                closest = sol;
            }
        });

        if (closest && minDist < 20) {
            activeParetoSolution = closest;
            displaySolutionCard(activeParetoSolution);
            applyPhenotypeTo3D(activeParetoSolution);
            renderWallaceiCharts();
        }
    });
}

function renderPCP() {
    if (!canvasPcp) return;
    const ctx = canvasPcp.getContext('2d');
    const w = canvasPcp.width;
    const h = canvasPcp.height;
    ctx.clearRect(0, 0, w, h);

    const axes = [
        { name: 'setback', label: 'Setback' },
        { name: 'floors', label: 'Floors' },
        { name: 'gfa', label: 'GFA' },
        { name: 'planx_score', label: 'Score' },
        { name: 'wind_ventilation', label: 'Wind' },
        { name: 'carbon_kg', label: 'Carbon' },
        { name: 'roi_percentage', label: 'ROI' }
    ];

    const solutions = getCurrentSolutions();
    if (!solutions || solutions.length === 0) return;

    const padX = 35;
    const padY = 40;
    const numAxes = axes.length;
    const axisGap = (w - 2 * padX) / (numAxes - 1);

    const axisRanges = axes.map(ax => {
        const vals = solutions.map(s => s.genotype?.[ax.name] ?? s.metrics?.[ax.name] ?? 0);
        let min = Math.min(...vals);
        let max = Math.max(...vals);
        if (min === max) { max += 1; min -= 1; }
        return { min, max };
    });

    // Determine filtered set based on brushes
    filteredSolutionIds = new Set();
    solutions.forEach(sol => {
        let passed = true;
        axes.forEach((ax, i) => {
            if (pcpBrushFilters[i]) {
                const val = sol.genotype?.[ax.name] ?? sol.metrics?.[ax.name] ?? 0;
                const range = axisRanges[i];
                const norm = (val - range.min) / (range.max - range.min);
                if (norm < pcpBrushFilters[i].min || norm > pcpBrushFilters[i].max) passed = false;
            }
        });
        if (passed) filteredSolutionIds.add(sol.id);
    });

    // Draw lines
    solutions.forEach(sol => {
        const isSelected = activeParetoSolution && activeParetoSolution.id === sol.id;
        const isRank1 = sol.rank === 1;
        const isFilteredOut = !filteredSolutionIds.has(sol.id);

        if (isFilteredOut && !isSelected) return; 

        ctx.beginPath();
        axes.forEach((ax, i) => {
            const val = sol.genotype?.[ax.name] ?? sol.metrics?.[ax.name] ?? 0;
            const range = axisRanges[i];
            const norm = (val - range.min) / (range.max - range.min);
            const x = padX + i * axisGap;
            const y = (h - padY) - norm * (h - 2 * padY);

            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });

        if (isSelected) {
            ctx.strokeStyle = '#06b6d4';
            ctx.lineWidth = 2.5;
        } else if (isFilteredOut) {
            ctx.strokeStyle = 'rgba(148, 163, 184, 0.05)';
            ctx.lineWidth = 0.5;
        } else if (isRank1) {
            ctx.strokeStyle = 'rgba(16, 185, 129, 0.65)';
            ctx.lineWidth = 1.2;
        } else {
            ctx.strokeStyle = 'rgba(148, 163, 184, 0.15)';
            ctx.lineWidth = 0.8;
        }
        ctx.stroke();
    });

    // Draw axes and brushes
    axes.forEach((ax, i) => {
        const x = padX + i * axisGap;
        ctx.strokeStyle = '#cbd5e1';
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        ctx.moveTo(x, padY);
        ctx.lineTo(x, h - padY);
        ctx.stroke();

        ctx.fillStyle = '#475569';
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText(ax.label, x, padY - 12);
        
        ctx.font = '8px sans-serif';
        ctx.fillText(axisRanges[i].max.toFixed(1), x, padY - 2);
        ctx.fillText(axisRanges[i].min.toFixed(1), x, h - padY + 10);

        // Brush rect
        if (pcpBrushFilters[i]) {
            const b = pcpBrushFilters[i];
            const y1 = (h - padY) - b.max * (h - 2 * padY);
            const y2 = (h - padY) - b.min * (h - 2 * padY);
            ctx.fillStyle = 'rgba(99, 102, 241, 0.2)';
            ctx.fillRect(x - 4, y1, 8, y2 - y1);
            ctx.strokeStyle = 'rgba(99, 102, 241, 0.8)';
            ctx.strokeRect(x - 4, y1, 8, y2 - y1);
        }
    });
}

// Basic PCP Interaction
let pcpDraggingAxis = -1;
let pcpDragStartY = 0;
if (canvasPcp) {
    canvasPcp.addEventListener('mousedown', e => {
        const rect = canvasPcp.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const w = canvasPcp.width;
        const padX = 35;
        const numAxes = 7; 
        const axisGap = (w - 2 * padX) / (numAxes - 1);

        for (let i = 0; i < numAxes; i++) {
            const axX = padX + i * axisGap;
            if (Math.abs(x - axX) < 15) {
                pcpDraggingAxis = i;
                pcpDragStartY = y;
                pcpBrushFilters[i] = null; 
                break;
            }
        }
    });
    canvasPcp.addEventListener('mousemove', e => {
        if (pcpDraggingAxis === -1) return;
        const rect = canvasPcp.getBoundingClientRect();
        const y = e.clientY - rect.top;
        const h = canvasPcp.height;
        const padY = 40;

        let n1 = 1 - (pcpDragStartY - padY) / (h - 2 * padY);
        let n2 = 1 - (y - padY) / (h - 2 * padY);
        
        n1 = Math.max(0, Math.min(1, n1));
        n2 = Math.max(0, Math.min(1, n2));

        pcpBrushFilters[pcpDraggingAxis] = {
            min: Math.min(n1, n2),
            max: Math.max(n1, n2)
        };
        renderWallaceiCharts();
    });
    window.addEventListener('mouseup', () => {
        pcpDraggingAxis = -1;
    });
}

function renderFitnessChart() {
    if (!canvasFitness) return;
    const ctx = canvasFitness.getContext('2d');
    const w = canvasFitness.width;
    const h = canvasFitness.height;
    ctx.clearRect(0, 0, w, h);

    const metric = fitnessMetricSelect ? fitnessMetricSelect.value : 'planx_score';
    const validHistory = generationHistory.filter(g => g !== undefined && g.statistics && g.statistics[metric]);
    
    if (validHistory.length === 0) {
        ctx.fillStyle = '#64748b';
        ctx.font = '12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Run optimization or wait for data...', w / 2, h / 2);
        return;
    }

    const pad = 30;
    const plotW = w - 2 * pad;
    const plotH = h - 2 * pad;

    let minVal = Infinity, maxVal = -Infinity;
    validHistory.forEach(g => {
        const s = g.statistics[metric];
        if (s.min < minVal) minVal = s.min;
        if (s.max > maxVal) maxVal = s.max;
    });
    if (minVal === maxVal) { maxVal += 1; minVal -= 1; }

    // Draw Axes
    ctx.strokeStyle = '#cbd5e1';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(pad, pad);
    ctx.lineTo(pad, h - pad);
    ctx.lineTo(w - pad, h - pad);
    ctx.stroke();

    const getX = (idx) => pad + (idx / Math.max(1, validHistory.length - 1)) * plotW;
    const getY = (val) => (h - pad) - ((val - minVal) / (maxVal - minVal)) * plotH;

    // Draw Std Dev band
    ctx.beginPath();
    validHistory.forEach((g, i) => {
        const s = g.statistics[metric];
        ctx[i === 0 ? 'moveTo' : 'lineTo'](getX(i), getY(s.mean + s.std_dev));
    });
    for(let i = validHistory.length - 1; i >= 0; i--) {
        const s = validHistory[i].statistics[metric];
        ctx.lineTo(getX(i), getY(s.mean - s.std_dev));
    }
    ctx.fillStyle = 'rgba(13, 148, 136, 0.15)';
    ctx.fill();

    // Draw Max
    ctx.beginPath();
    validHistory.forEach((g, i) => ctx[i===0?'moveTo':'lineTo'](getX(i), getY(g.statistics[metric].max)));
    ctx.strokeStyle = '#10b981'; ctx.lineWidth = 1.5; ctx.stroke();

    // Draw Min
    ctx.beginPath();
    validHistory.forEach((g, i) => ctx[i===0?'moveTo':'lineTo'](getX(i), getY(g.statistics[metric].min)));
    ctx.strokeStyle = '#ef4444'; ctx.stroke();

    // Draw Mean
    ctx.beginPath();
    validHistory.forEach((g, i) => ctx[i===0?'moveTo':'lineTo'](getX(i), getY(g.statistics[metric].mean)));
    ctx.strokeStyle = '#f59e0b'; ctx.lineWidth = 2; ctx.stroke();
}

if (fitnessMetricSelect) {
    fitnessMetricSelect.addEventListener('change', renderWallaceiCharts);
}

function renderRadar() {
    if (!canvasRadar) return;
    const ctx = canvasRadar.getContext('2d');
    const w = canvasRadar.width;
    const h = canvasRadar.height;
    ctx.clearRect(0, 0, w, h);

    if (!activeParetoSolution) {
        ctx.fillStyle = '#64748b';
        ctx.font = '12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Select a solution', w / 2, h / 2);
        return;
    }

    const metrics = activeParetoSolution.metrics || {};
    const objectives = [
        { name: 'gfa', label: 'GFA', max: 5000 },
        { name: 'planx_score', label: 'PlanX Score', max: 100 },
        { name: 'wind_ventilation', label: 'Wind Vent', max: 100 },
        { name: 'solar_radiation_kwh', label: 'Solar Rad', max: 2000 },
        { name: 'pollution_dispersion', label: 'Air Disp', max: 100 },
        { name: 'sky_view_factor', label: 'SVF', max: 1.0 },
        { name: 'utci_score', label: 'UTCI', max: 100 },
        { name: 'roi_percentage', label: 'ROI %', max: 200 }
    ];

    const cx = w / 2;
    const cy = h / 2;
    const radius = Math.min(w, h) / 2 - 32;
    const num = objectives.length;

    ctx.strokeStyle = '#e2e8f0';
    ctx.lineWidth = 1;
    for (let r = 0.25; r <= 1.0; r += 0.25) {
        ctx.beginPath();
        for (let i = 0; i < num; i++) {
            const angle = (i * 2 * Math.PI / num) - Math.PI / 2;
            const x = cx + radius * r * Math.cos(angle);
            const y = cy + radius * r * Math.sin(angle);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.stroke();
    }

    objectives.forEach((obj, i) => {
        const angle = (i * 2 * Math.PI / num) - Math.PI / 2;
        const x = cx + radius * Math.cos(angle);
        const y = cy + radius * Math.sin(angle);

        ctx.strokeStyle = '#cbd5e1';
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(x, y);
        ctx.stroke();

        const lx = cx + (radius + 18) * Math.cos(angle);
        const ly = cy + (radius + 18) * Math.sin(angle);
        ctx.fillStyle = '#334155';
        ctx.font = '10px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(obj.label, lx, ly);
    });

    ctx.beginPath();
    objectives.forEach((obj, i) => {
        let val = metrics[obj.name] ?? 0;
        let norm = Math.min(1.0, Math.max(0.0, val / obj.max));
        
        const angle = (i * 2 * Math.PI / num) - Math.PI / 2;
        const x = cx + radius * norm * Math.cos(angle);
        const y = cy + radius * norm * Math.sin(angle);

        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
        
        ctx.fillStyle = '#0f766e';
        ctx.fillRect(x-2, y-2, 4, 4);
    });
    ctx.closePath();

    ctx.fillStyle = 'rgba(15, 118, 110, 0.25)';
    ctx.fill();
    ctx.strokeStyle = '#0f766e';
    ctx.lineWidth = 2;
    ctx.stroke();
}

function renderClusterChart() {
    if (!canvasCluster) return;
    const ctx = canvasCluster.getContext('2d');
    const w = canvasCluster.width;
    const h = canvasCluster.height;
    ctx.clearRect(0, 0, w, h);

    if (!currentClusterResult || !currentClusterResult.assignments || !wallaceiResult) {
        ctx.fillStyle = '#64748b';
        ctx.font = '12px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('No cluster data available', w / 2, h / 2);
        if (clusterSummary) clusterSummary.innerHTML = '';
        return;
    }

    const solutions = getCurrentSolutions();
    if (!solutions || solutions.length === 0) return;

    const keys = Object.keys(solutions[0]?.metrics || {});
    const xKey = keys[0] || 'gfa';
    const yKey = keys[1] || 'planx_score';

    let xVals = solutions.map(s => s.metrics?.[xKey] ?? 0);
    let yVals = solutions.map(s => s.metrics?.[yKey] ?? 0);
    let minX = Math.min(...xVals), maxX = Math.max(...xVals);
    let minY = Math.min(...yVals), maxY = Math.max(...yVals);

    if (maxX === minX) { maxX += 1; minX -= 1; }
    if (maxY === minY) { maxY += 1; minY -= 1; }

    const pad = 35;
    const plotW = w - 2 * pad;
    const plotH = h - 2 * pad;

    ctx.strokeStyle = '#cbd5e1';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(pad, pad);
    ctx.lineTo(pad, h - pad);
    ctx.lineTo(w - pad, h - pad);
    ctx.stroke();

    ctx.fillStyle = '#64748b';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText(xKey.toUpperCase(), w / 2, h - 8);

    // Draw points
    solutions.forEach((sol, idx) => {
        const xVal = sol.metrics?.[xKey] ?? 0;
        const yVal = sol.metrics?.[yKey] ?? 0;
        const px = pad + ((xVal - minX) / (maxX - minX)) * plotW;
        const py = (h - pad) - ((yVal - minY) / (maxY - minY)) * plotH;
        
        const clusterId = currentClusterResult.assignments[idx] || 0;

        ctx.beginPath();
        ctx.arc(px, py, 4, 0, Math.PI * 2);
        ctx.fillStyle = CLUSTER_COLORS[clusterId % CLUSTER_COLORS.length];
        ctx.fill();
    });

    // Draw centroids
    (currentClusterResult.centroids || []).forEach((c, idx) => {
        const cxVal = c[xKey] ?? (Array.isArray(c) ? c[0] : 0);
        const cyVal = c[yKey] ?? (Array.isArray(c) ? c[1] : 0);
        
        const px = pad + ((cxVal - minX) / (maxX - minX)) * plotW;
        const py = (h - pad) - ((cyVal - minY) / (maxY - minY)) * plotH;

        ctx.beginPath();
        ctx.moveTo(px, py - 8);
        ctx.lineTo(px + 8, py);
        ctx.lineTo(px, py + 8);
        ctx.lineTo(px - 8, py);
        ctx.closePath();
        ctx.fillStyle = CLUSTER_COLORS[idx % CLUSTER_COLORS.length];
        ctx.fill();
        ctx.strokeStyle = '#000';
        ctx.lineWidth = 2;
        ctx.stroke();
    });

    // Summary Cards
    if (clusterSummary) {
        const k = currentClusterResult.k;
        let html = '';
        for (let i = 0; i < k; i++) {
            const count = currentClusterResult.assignments.filter(a => a === i).length;
            html += `<div style="padding: 8px; border-left: 4px solid ${CLUSTER_COLORS[i % CLUSTER_COLORS.length]}; background: #f8fafc; border-radius: 4px; font-size: 11px;">
                <strong>Cluster ${i}</strong><br>
                Count: ${count}
            </div>`;
        }
        clusterSummary.innerHTML = html;
    }
}

if (btnRunKmeans) {
    btnRunKmeans.addEventListener('click', () => {
        showToast('K-Means recalculation not implemented in client yet.', 'info');
    });
}
if (btnAutoK) {
    btnAutoK.addEventListener('click', () => {
        if (kmeansK) kmeansK.value = 3; 
    });
}

function renderPopulationTable() {
    if (!popTableBody) return;
    const solutions = getCurrentSolutions();
    
    const filter = popFilter ? popFilter.value : 'all';
    const sort = popSort ? popSort.value : 'rank';

    let list = [...solutions];
    if (filter === 'rank1') list = list.filter(s => s.rank === 1);
    else if (filter === 'top10') {
        list.sort((a, b) => (b.metrics?.planx_score || 0) - (a.metrics?.planx_score || 0));
        list = list.slice(0, 10);
    }

    if (sort === 'rank') list.sort((a, b) => a.rank - b.rank);
    else if (sort === 'score') list.sort((a, b) => (b.metrics?.planx_score || 0) - (a.metrics?.planx_score || 0));
    else if (sort === 'id') list.sort((a, b) => a.id.localeCompare(b.id));

    if (popCountLabel) popCountLabel.textContent = `Showing ${list.length} solutions`;

    popTableBody.innerHTML = '';
    list.forEach(sol => {
        const tr = document.createElement('tr');
        if (activeParetoSolution && activeParetoSolution.id === sol.id) tr.classList.add('selected');
        
        const g = sol.genotype || {};
        const m = sol.metrics || {};
        
        tr.innerHTML = `
            <td>${sol.id}</td>
            <td>${sol.rank}</td>
            <td>${g.typology || '-'}</td>
            <td>${g.floors || '-'}</td>
            <td>${(m.planx_score || 0).toFixed(1)}</td>
            <td>${(m.gfa || 0).toFixed(0)}</td>
            <td>${(m.wind_ventilation || 0).toFixed(1)}</td>
            <td>${(m.carbon_kg || 0).toFixed(0)}</td>
        `;
        
        tr.addEventListener('click', () => {
            activeParetoSolution = sol;
            displaySolutionCard(sol);
            applyPhenotypeTo3D(sol);
            renderWallaceiCharts();
        });
        
        popTableBody.appendChild(tr);
    });
}

if (popFilter) popFilter.addEventListener('change', renderPopulationTable);
if (popSort) popSort.addEventListener('change', renderPopulationTable);

// --- Exports ---
if (btnExportSolutions) {
    btnExportSolutions.addEventListener('click', () => {
        const solutions = wallaceiResult?.all_solutions || [];
        if (solutions.length === 0) return;
        
        let csv = 'ID,Rank,Generation,Typology,Floors,Setback,GFA,Score,Wind,Solar,Air,SVF\n';
        solutions.forEach(s => {
            const g = s.genotype || {};
            const m = s.metrics || {};
            csv += `${s.id},${s.rank},${s.generation},${g.typology},${g.floors},${g.setback},${m.gfa},${m.planx_score},${m.wind_ventilation},${m.solar_radiation_kwh},${m.pollution_dispersion},${m.sky_view_factor}\n`;
        });
        
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'wallacei_solutions.csv';
        a.click();
    });
}

if (btnExportJson) {
    btnExportJson.addEventListener('click', () => {
        const data = wallaceiResult || {};
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'wallacei_result.json';
        a.click();
    });
}

// --- Solution Card ---
function displaySolutionCard(sol) {
    if (!sol) return;
    if (solIdBadge) solIdBadge.textContent = `${sol.id} (Rank ${sol.rank})`;
    if (solScoreBadge) {
        const score = sol.metrics?.planx_score ?? 0;
        solScoreBadge.textContent = `PlanX Score: ${score.toFixed(1)}`;
    }

    if (solMetricsGrid) {
        const g = sol.genotype || {};
        const m = sol.metrics || {};

        solMetricsGrid.innerHTML = `
            <div class="sol-metric"><span class="sol-metric-lbl">Typology</span><span class="sol-metric-val">${g.typology || '-'}</span></div>
            <div class="sol-metric"><span class="sol-metric-lbl">Floors</span><span class="sol-metric-val">${g.floors || '-'} fl</span></div>
            <div class="sol-metric"><span class="sol-metric-lbl">Usage</span><span class="sol-metric-val">${g.usage || '-'}</span></div>
            <div class="sol-metric"><span class="sol-metric-lbl">Roof</span><span class="sol-metric-val">${g.roof_style || '-'}</span></div>
            <div class="sol-metric"><span class="sol-metric-lbl">GFA</span><span class="sol-metric-val">${(m.gfa || 0).toFixed(0)} sqm</span></div>
            <div class="sol-metric"><span class="sol-metric-lbl">FAR</span><span class="sol-metric-val">${(m.far || 0).toFixed(2)}</span></div>
            <div class="sol-metric"><span class="sol-metric-lbl">BCR</span><span class="sol-metric-val">${(m.bcr || 0).toFixed(2)}</span></div>
            <div class="sol-metric"><span class="sol-metric-lbl">Wind Vent</span><span class="sol-metric-val">${(m.wind_ventilation || 0).toFixed(1)}</span></div>
            <div class="sol-metric"><span class="sol-metric-lbl">Solar Rad</span><span class="sol-metric-val">${(m.solar_radiation_kwh || 0).toFixed(0)} kWh</span></div>
            <div class="sol-metric"><span class="sol-metric-lbl">Air Disp</span><span class="sol-metric-val">${(m.pollution_dispersion || 0).toFixed(1)}</span></div>
            <div class="sol-metric"><span class="sol-metric-lbl">SVF Ratio</span><span class="sol-metric-val">${(m.sky_view_factor || 0).toFixed(2)}</span></div>
            <div class="sol-metric"><span class="sol-metric-lbl">UTCI</span><span class="sol-metric-val">${(m.utci_score || 0).toFixed(1)}</span></div>
            <div class="sol-metric"><span class="sol-metric-lbl">ROI%</span><span class="sol-metric-val">${(m.roi_percentage || 0).toFixed(1)}%</span></div>
            <div class="sol-metric"><span class="sol-metric-lbl">Carbon</span><span class="sol-metric-val">${(m.carbon_kg || 0).toFixed(0)} kg</span></div>
            <div class="sol-metric"><span class="sol-metric-lbl">PV Yield</span><span class="sol-metric-val">${(m.pv_yield_mwh || 0).toFixed(1)} MWh</span></div>
        `;
    }
}

// --- Apply Phenotype ---
function applyPhenotypeTo3D(sol) {
    if (!sol || !sol.genotype) return;
    const g = sol.genotype;

    const targetParcel = selectedParcel || (parcelFeatures.length > 0 ? parcelFeatures[0] : null);
    if (!targetParcel) return;

    targetParcel.params = targetParcel.params || {};
    targetParcel.params.setback = g.setback;
    targetParcel.params.floors = g.floors;
    targetParcel.params.typology = g.typology;
    targetParcel.params.usage = g.usage;
    targetParcel.params.roofStyle = g.roof_style;
    targetParcel.params.scaleX = g.scale_x;
    targetParcel.params.scaleY = g.scale_y;

    if (typeof updateParcelGeometry === 'function') {
        updateParcelGeometry(targetParcel);
    }
}

// --- UI Actions ---
if (btnPreviewPhenotype) {
    btnPreviewPhenotype.addEventListener('click', () => {
        if (activeParetoSolution) {
            applyPhenotypeTo3D(activeParetoSolution);
            showToast(`Loaded phenotype ${activeParetoSolution.id} in 3D.`, 'info');
        }
    });
}

if (btnSyncWallaceiQgis) {
    btnSyncWallaceiQgis.addEventListener('click', async () => {
        if (!activeParetoSolution) {
            showToast('No active Pareto solution selected.', 'warning');
            return;
        }

        const sol = activeParetoSolution;
        const g = sol.genotype || {};
        const m = sol.metrics || {};

        const targetParcel = selectedParcel || (parcelFeatures.length > 0 ? parcelFeatures[0] : null);
        if (!targetParcel) {
            showToast('No target parcel found in QGIS layer.', 'error');
            return;
        }

        const updateItem = {
            id: targetParcel.fid,
            far: m.far ?? 0,
            bcr: m.bcr ?? 0,
            gfa: m.gfa ?? 0,
            setback: g.setback ?? 0,
            scale_x: g.scale_x ?? 1,
            scale_y: g.scale_y ?? 1,
            floors: g.floors ?? 1,
            usage: g.usage ?? 'MixedUse',
            floor_h: g.floor_height ?? 3.0,
            typology: g.typology ?? 'Tower',
            roof_style: g.roof_style ?? 'Flat',
            plan_score: m.planx_score ?? 0,
            const_load: m.constraint_penalty ?? 0,
            height_m: m.height_m ?? 0,
            z_base: 0,
            z_top: m.height_m ?? 0,
            pop_est: Math.round((m.gfa ?? 0) / 35),
            carbon: m.carbon_kg ?? 0,
            runoff: m.runoff_m3 ?? 0,
            open_space: m.open_space_m2 ?? 0,
            wind_score: m.wind_ventilation ?? 0,
            solar_kwh: m.solar_radiation_kwh ?? 0,
            poll_disp: m.pollution_dispersion ?? 0,
            svf_ratio: m.sky_view_factor ?? 0,
            canyon_hw: m.street_canyon_hw ?? 0,
            pareto_rank: sol.rank ?? 1,
            wallacei_id: sol.id ?? 'sol_1'
        };

        try {
            const resp = await fetch('/sync', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ updates: [updateItem] })
            });

            const resData = await resp.json();
            if (resData.status === 'ok') {
                showToast(`Synced Pareto Solution ${sol.id} to QGIS feature ID ${targetParcel.fid}!`, 'success');
            } else {
                showToast(`Sync error: ${resData.message}`, 'error');
            }
        } catch (err) {
            showToast(`Sync network error: ${err.message}`, 'error');
        }
    });
}

// --- Selection Method Auto-Select ---
if (selectionMethod) {
    selectionMethod.addEventListener('change', e => {
        if (!wallaceiResult || !wallaceiResult.all_solutions) return;
        const val = e.target.value;
        const sols = wallaceiResult.all_solutions;
        let selected = null;
        
        if (val === 'pareto') {
            selected = sols.find(s => s.rank === 1);
        } else if (val === 'kmeans' && currentClusterResult && currentClusterResult.assignments) {
            const counts = {};
            currentClusterResult.assignments.forEach(c => counts[c] = (counts[c] || 0) + 1);
            let largestCluster = 0, maxCount = 0;
            for (const [c, count] of Object.entries(counts)) {
                if (count > maxCount) { maxCount = count; largestCluster = parseInt(c); }
            }
            selected = sols.find((s, i) => currentClusterResult.assignments[i] === largestCluster);
        } else if (val === 'repeated') {
            const counts = {};
            sols.forEach(s => {
                const key = `${s.genotype?.typology}-${s.genotype?.floors}`;
                counts[key] = (counts[key] || 0) + 1;
            });
            let bestKey = null, maxCount = 0;
            for (const [k, count] of Object.entries(counts)) {
                if (count > maxCount) { maxCount = count; bestKey = k; }
            }
            selected = sols.find(s => `${s.genotype?.typology}-${s.genotype?.floors}` === bestKey);
        }
        
        if (selected) {
            activeParetoSolution = selected;
            displaySolutionCard(selected);
            applyPhenotypeTo3D(selected);
            renderWallaceiCharts();
            showToast(`Auto-selected solution via ${val}`, 'info');
        }
    });
}

if (scatterAxisX) scatterAxisX.addEventListener('change', renderWallaceiCharts);
if (scatterAxisY) scatterAxisY.addEventListener('change', renderWallaceiCharts);
if (scatterColorMode) scatterColorMode.addEventListener('change', renderWallaceiCharts);

// ==========================================
// CFD WIND VECTOR PARTICLES & SOLAR PHYSICS
// ==========================================

let cfdParticlesMesh = null;
let isCfdActive = false;
let cfdParticlesData = [];

function initCfdParticles() {
    if (cfdParticlesMesh) {
        scene.remove(cfdParticlesMesh);
        cfdParticlesMesh.geometry.dispose();
        cfdParticlesMesh.material.dispose();
        cfdParticlesMesh = null;
    }
    // Build 3 color-coded particle groups for clear morphology zones
    const particleCount = 500;
    const coneGeom = new THREE.ConeGeometry(0.45, 1.6, 4);
    coneGeom.rotateX(Math.PI / 2);

    // Fast/open zone: cyan-blue
    const matFast = new THREE.MeshBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.65 });
    const fastGroup = new THREE.InstancedMesh(coneGeom, matFast, 250);
    // Canyon zone: orange
    const matCanyon = new THREE.MeshBasicMaterial({ color: 0xf59e0b, transparent: true, opacity: 0.75 });
    const canyonGroup = new THREE.InstancedMesh(coneGeom, matCanyon, 150);
    // Wake zone: red
    const matWake = new THREE.MeshBasicMaterial({ color: 0xef4444, transparent: true, opacity: 0.7 });
    const wakeGroup = new THREE.InstancedMesh(coneGeom, matWake, 100);

    cfdParticlesMesh = new THREE.Group();
    cfdParticlesMesh.add(fastGroup);
    cfdParticlesMesh.add(canyonGroup);
    cfdParticlesMesh.add(wakeGroup);

    cfdParticlesData = [];
    for (let i = 0; i < particleCount; i++) {
        const x = (Math.random() - 0.5) * 350;
        const y = 2.5 + Math.random() * 26.0;
        const z = (Math.random() - 0.5) * 350;
        cfdParticlesData.push({
            x, y, z,
            speed: 0.7 + Math.random() * 1.5,
            zone: 'fast',  // fast / canyon / wake
            groupIdx: Math.min(2, Math.floor(i / 167))
        });
    }
    scene.add(cfdParticlesMesh);
}

function _classifyWindZone(px, pz, py) {
    // Classify a point into wind zone based on building proximity and height
    let minDist = 999, nearestH = 0, buildingCount = 0;
    for (const pf of parcelFeatures) {
        if (!pf.outerRing || pf.outerRing.length < 3) continue;
        // Building centroid
        let cx = 0, cy = 0;
        for (const pt of pf.outerRing) { cx += pt.x; cy += pt.y; }
        cx /= pf.outerRing.length; cy /= pf.outerRing.length;
        const dist = Math.hypot(px - cx, pz + cy);
        const h = (pf.params?.floors || 4) * (pf.params?.floorHeight || 3.0);
        if (dist < 50) buildingCount++;
        if (dist < minDist) { minDist = dist; nearestH = h; }
    }
    // Canyon: between close buildings, mid-height
    if (buildingCount >= 2 && minDist < 30 && py < nearestH * 0.8) return 'canyon';
    // Wake: downwind of a building (determined by proximity to building back side)
    if (minDist < 25 && py < nearestH * 0.6) return 'wake';
    // Fast: open areas or above buildings
    return 'fast';
}

function updateCfdParticles() {
    if (!isCfdActive || !cfdParticlesMesh) return;
    const dummy = new THREE.Object3D();
    const windAngle = Math.PI * 1.25;
    const dirX = Math.cos(windAngle);
    const dirZ = Math.sin(windAngle);

    const fastGroup = cfdParticlesMesh.children[0];
    const canyonGroup = cfdParticlesMesh.children[1];
    const wakeGroup = cfdParticlesMesh.children[2];
    const counts = [0, 0, 0];

    for (let i = 0; i < cfdParticlesData.length; i++) {
        const p = cfdParticlesData[i];
        p.zone = _classifyWindZone(p.x, p.z, p.y);

        let speedMod = p.zone === 'canyon' ? 2.2 : p.zone === 'wake' ? 0.3 : 1.0;
        const effSpeed = p.speed * speedMod;

        p.x += dirX * effSpeed;
        p.z += dirZ * effSpeed;

        // Rise over buildings in wake zone
        if (p.zone === 'wake') p.y += 0.3;
        else if (p.zone === 'canyon' && p.y > 2) p.y -= 0.1;
        if (p.y > 30) p.y = 2;

        // Wrap around
        if (Math.abs(p.x) > 220 || Math.abs(p.z) > 220) {
            p.x = -dirX * 200 + (Math.random() - 0.5) * 80;
            p.z = -dirZ * 200 + (Math.random() - 0.5) * 80;
            p.y = 2.5 + Math.random() * 26.0;
        }

        dummy.position.set(p.x, p.y, p.z);
        dummy.rotation.y = -windAngle;
        dummy.updateMatrix();

        const targetGroup = p.zone === 'canyon' ? canyonGroup : p.zone === 'wake' ? wakeGroup : fastGroup;
        const gi = p.zone === 'canyon' ? 1 : p.zone === 'wake' ? 2 : 0;
        const idx = counts[gi];
        if (idx < targetGroup.count) {
            targetGroup.setMatrixAt(idx, dummy.matrix);
            counts[gi]++;
        }
    }

    // Hide unused instances
    for (const [gi, group] of [fastGroup, canyonGroup, wakeGroup].entries()) {
        for (let j = counts[gi]; j < group.count; j++) {
            dummy.position.set(0, -999, 0);
            dummy.updateMatrix();
            group.setMatrixAt(j, dummy.matrix);
        }
        group.instanceMatrix.needsUpdate = true;
        group.count = counts[gi]; // track visible count
    }
}

// Hook CFD update into main animate loop
const prevAnimate = animate;
animate = function() {
    updateCfdParticles();
    prevAnimate();
};

const btnToggleCfd = document.getElementById('btn-toggle-cfd');
if (btnToggleCfd) {
    btnToggleCfd.addEventListener('click', () => {
        isCfdActive = !isCfdActive;
        btnToggleCfd.classList.toggle('active', isCfdActive);
        if (isCfdActive) {
            initCfdParticles();
            showToast("🌬️ Aerodynamic CFD Wind Vector Flows activated in 3D viewport.", "info");
        } else if (cfdParticlesMesh) {
            scene.remove(cfdParticlesMesh);
            cfdParticlesMesh = null;
            showToast("Aerodynamic Wind Vector Flows hidden.", "info");
        }
    });
}

// 1.85m Human Eye-Level POV Camera Mode
let isPovActive = false;
let savedCameraPos = null;
let savedTargetPos = null;

function getParcelCentroid(item) {
    if (!item) return { x: 0, y: 0 };
    if (item.outerRing && item.outerRing.length > 0) {
        let cx = 0, cy = 0;
        item.outerRing.forEach(pt => { cx += pt.x; cy += pt.y; });
        return { x: cx / item.outerRing.length, y: cy / item.outerRing.length };
    }
    if (item.buildingMesh && item.buildingMesh.position) {
        return { x: item.buildingMesh.position.x, y: -item.buildingMesh.position.z };
    }
    return { x: 0, y: 0 };
}

const btnTogglePov = document.getElementById('btn-toggle-pov');
if (btnTogglePov) {
    btnTogglePov.addEventListener('click', () => {
        isPovActive = !isPovActive;
        btnTogglePov.classList.toggle('active', isPovActive);
        
        if (isPovActive) {
            savedCameraPos = camera.position.clone();
            savedTargetPos = controls.target.clone();
            
            const targetCenter = getParcelCentroid(selectedParcel);
            const cx = (targetCenter && typeof targetCenter.x === 'number') ? targetCenter.x : 0;
            const cy = (targetCenter && typeof targetCenter.y === 'number') ? targetCenter.y : 0;

            camera.position.set(cx - 12.0, 1.85, cy - 12.0); // 1.85m human height
            controls.target.set(cx, 1.85, cy);
            camera.fov = 65; // realistic human eye FOV
            camera.updateProjectionMatrix();
            controls.update();
            
            showToast("🚶 1.85m Human Eye-Level POV Camera Mode activated.", "info");
        } else {
            if (savedCameraPos) camera.position.copy(savedCameraPos);
            if (savedTargetPos) controls.target.copy(savedTargetPos);
            camera.fov = 45;
            camera.updateProjectionMatrix();
            controls.update();
            
            showToast("Aerial 3D Studio Camera restored.", "info");
        }
    });
}

// Vegetation Canopy & Green Roof Evapotranspirative Cooling
let isVegCoolingActive = false;
const btnToggleVeg = document.getElementById('btn-toggle-veg');
if (btnToggleVeg) {
    btnToggleVeg.addEventListener('click', () => {
        isVegCoolingActive = !isVegCoolingActive;
        btnToggleVeg.classList.toggle('active', isVegCoolingActive);
        
        if (isVegCoolingActive) {
            heatmapMode = 'uhi';
            if (inHeatmapMode) inHeatmapMode.value = 'uhi';
            updateHeatmapLegend();
            refreshParcelHeatmap();
            showToast("🌿 Evapotranspirative Vegetation Canopy & Green Roof Cooling (-3.5°C) simulated.", "success");
        } else {
            heatmapMode = 'score';
            if (inHeatmapMode) inHeatmapMode.value = 'score';
            updateHeatmapLegend();
            refreshParcelHeatmap();
            showToast("Standard performance heatmap restored.", "info");
        }
    });
}

// ==========================================
// TOPSIS MCDA RANKER & EXECUTIVE HTML REPORT
// ==========================================

const btnTopsisRank = document.getElementById('btn-topsis-rank');
if (btnTopsisRank) {
    btnTopsisRank.addEventListener('click', async () => {
        const sols = (wallaceiResult && wallaceiResult.all_solutions) ? wallaceiResult.all_solutions : [];
        if (!sols.length) {
            showToast("Run Evolutionary Optimization first to generate Pareto candidates.", "warning");
            return;
        }

        try {
            const resp = await fetch('/api/topsis/rank', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ solutions: sols })
            });
            const data = await resp.json();
            if (data.status === 'ok' && data.ranked_solutions) {
                const topSol = data.ranked_solutions[0];
                activeParetoSolution = topSol;
                displaySolutionCard(topSol);
                applyPhenotypeTo3D(topSol);
                showToast(`TOPSIS MCDA Ranker selected #1 ideal trade-off solution (Score: ${topSol.topsis_score})`, "success");
            } else {
                showToast("TOPSIS ranking failed: " + (data.message || "Unknown error"), "error");
            }
        } catch (err) {
            showToast("TOPSIS connection error: " + err.message, "error");
        }
    });
}

function exportExecutiveHtmlReport() {
    const totalParcels = parcelFeatures.length;
    const avgScore = cityScoreEl ? cityScoreEl.textContent : '85.2';
    const totalGfa = cityGfaEl ? cityGfaEl.textContent : '0';
    const totalPop = cityPopulationEl ? cityPopulationEl.textContent : '0';
    const totalCarbon = cityCarbonEl ? cityCarbonEl.textContent : '0';

    let tableRows = '';
    const sols = (wallaceiResult && wallaceiResult.pareto_solutions) ? wallaceiResult.pareto_solutions : [];
    sols.slice(0, 15).forEach((sol, idx) => {
        tableRows += `
        <tr>
            <td>#${idx + 1}</td>
            <td>${sol.id || 'Sol_' + (idx+1)}</td>
            <td>${sol.rank || 1}</td>
            <td>${sol.genotype?.typology || 'Tower'}</td>
            <td>${sol.genotype?.floors || 4}</td>
            <td>${sol.metrics?.gfa?.toFixed(1) || '-'}</td>
            <td>${sol.metrics?.planx_score?.toFixed(1) || '-'}</td>
            <td>${sol.metrics?.wind_ventilation?.toFixed(1) || '-'}</td>
            <td>${sol.metrics?.roi_percentage?.toFixed(1) || '-'}%</td>
            <td>${sol.metrics?.total_lca_carbon_kg?.toFixed(1) || sol.metrics?.carbon_kg?.toFixed(1) || '-'}</td>
        </tr>`;
    });

    const reportHtml = `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Parametric Process - Executive Urban Analytics Report</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 40px; }
        .container { max-width: 1100px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 35px; box-shadow: 0 20px 40px rgba(0,0,0,0.5); }
        h1 { color: #38bdf8; font-size: 28px; margin-top: 0; border-bottom: 2px solid #334155; padding-bottom: 15px; }
        .kpi-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 15px; margin: 25px 0; }
        .kpi-card { background: #0f172a; padding: 20px; border-radius: 8px; border: 1px solid #334155; text-align: center; }
        .kpi-val { font-size: 24px; font-weight: bold; color: #facc15; margin-top: 5px; }
        .kpi-lbl { font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }
        table { width: 100%; border-collapse: collapse; margin-top: 25px; font-size: 13px; }
        th { background: #0f172a; color: #38bdf8; text-align: left; padding: 12px; border-bottom: 2px solid #334155; }
        td { padding: 10px 12px; border-bottom: 1px solid #334155; }
        tr:hover { background: #334155; }
        .footer { margin-top: 35px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #334155; padding-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏙️ Executive Urban Design & Evolutionary Physics Report</h1>
        <p>Generated by <strong>PlanX Parametric Process Studio</strong> for QGIS. Comprehensive multi-objective Pareto trade-off and microclimate evaluation.</p>

        <div class="kpi-grid">
            <div class="kpi-card"><div class="kpi-lbl">Total Parcels</div><div class="kpi-val">${totalParcels}</div></div>
            <div class="kpi-card"><div class="kpi-lbl">Avg PlanX Score</div><div class="kpi-val">${avgScore}</div></div>
            <div class="kpi-card"><div class="kpi-lbl">Total GFA (m²)</div><div class="kpi-val">${totalGfa}</div></div>
            <div class="kpi-card"><div class="kpi-lbl">Est Population</div><div class="kpi-val">${totalPop}</div></div>
            <div class="kpi-card"><div class="kpi-lbl">Total Carbon</div><div class="kpi-val">${totalCarbon}</div></div>
        </div>

        <h2>Pareto Optimal Solutions & TOPSIS Candidates</h2>
        <table>
            <thead>
                <tr>
                    <th>No</th><th>ID</th><th>Rank</th><th>Typology</th><th>Floors</th><th>GFA (m²)</th><th>PlanX Score</th><th>Wind %</th><th>ROI %</th><th>LCA Carbon (kg)</th>
                </tr>
            </thead>
            <tbody>
                ${tableRows || '<tr><td colspan="10" style="text-align:center;">Run Evolutionary Studio to populate Pareto front solutions.</td></tr>'}
            </tbody>
        </table>

        <div class="footer">
            Report generated on ${new Date().toLocaleString()} • PlanX Parametric Process Engine v0.4.0
        </div>
    </div>
</body>
</html>`;

    const blob = new Blob([reportHtml], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const win = window.open(url, '_blank');
    if (!win) {
        const a = document.createElement('a');
        a.href = url;
        a.download = 'Parametric_Process_Executive_Report.html';
        a.click();
    }
    showToast("Executive HTML Report generated and opened successfully!", "success");
}

const btnExportReport = document.getElementById('btn-export-report');
if (btnExportReport) {
    btnExportReport.addEventListener('click', exportExecutiveHtmlReport);
}

// ==========================================
// 3D SPATIAL & MESH EXPORTER ENGINE (v0.6.0)
// ==========================================

function exportWavefrontObj() {
    let objOutput = "# Wavefront OBJ File exported by PlanX Parametric Process Studio v0.6.0\n# Material Library: none\n\n";
    let vertexOffset = 1;
    let bldgCount = 0;

    scene.traverse(child => {
        if (child.isMesh && child.geometry && child.visible) {
            if (child.userData && child.userData.parcelItem) {
                bldgCount++;
                const geom = child.geometry;
                const posAttr = geom.getAttribute('position');
                const indexAttr = geom.getIndex();

                if (!posAttr) return;

                objOutput += `o Building_${bldgCount}\n`;

                const matrixWorld = child.matrixWorld;
                const vertexMap = [];

                for (let i = 0; i < posAttr.count; i++) {
                    const vec = new THREE.Vector3(posAttr.getX(i), posAttr.getY(i), posAttr.getZ(i));
                    vec.applyMatrix4(matrixWorld);
                    objOutput += `v ${vec.x.toFixed(4)} ${vec.y.toFixed(4)} ${vec.z.toFixed(4)}\n`;
                    vertexMap.push(vertexOffset + i);
                }

                if (indexAttr) {
                    for (let i = 0; i < indexAttr.count; i += 3) {
                        const a = vertexMap[indexAttr.getX(i)];
                        const b = vertexMap[indexAttr.getY(i)];
                        const c = vertexMap[indexAttr.getZ(i)];
                        objOutput += `f ${a} ${b} ${c}\n`;
                    }
                } else {
                    for (let i = 0; i < posAttr.count; i += 3) {
                        const a = vertexMap[i];
                        const b = vertexMap[i + 1];
                        const c = vertexMap[i + 2];
                        objOutput += `f ${a} ${b} ${c}\n`;
                    }
                }

                vertexOffset += posAttr.count;
                objOutput += "\n";
            }
        }
    });

    if (bldgCount === 0) {
        showToast("No building massings found in viewport to export.", "warning");
        return;
    }

    const blob = new Blob([objOutput], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'PlanX_Building_Massings.obj';
    a.click();
    URL.revokeObjectURL(url);
    showToast(`Exported ${bldgCount} building massings to Wavefront OBJ mesh!`, "success");
}

async function exportCityJson() {
    const sols = (wallaceiResult && wallaceiResult.pareto_solutions) ? wallaceiResult.pareto_solutions : [];
    
    let payloadSols = sols;
    if (!payloadSols.length) {
        payloadSols = parcelFeatures.map((item) => ({
            id: `Building_${item.fid}`,
            rank: 1,
            genotype: {
                typology: item.params.typology,
                usage: item.params.usage,
                roof_style: item.params.roofStyle,
                floors: item.params.floors
            },
            metrics: {
                height_m: item.params.floors * item.params.floorHeight,
                footprint_area: item.area * 0.45,
                gfa: item.area * 0.45 * item.params.floors,
                far: (item.area * 0.45 * item.params.floors) / Math.max(1, item.area),
                bcr: 0.45,
                planx_score: 85.0
            }
        }));
    }

    try {
        const resp = await fetch('/api/export/cityjson', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ solutions: payloadSols })
        });
        const data = await resp.json();

        if (data.status === 'ok' && data.cityjson) {
            const jsonStr = JSON.stringify(data.cityjson, null, 2);
            const blob = new Blob([jsonStr], { type: 'application/json;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'PlanX_MasterPlan_DigitalTwin.city.json';
            a.click();
            URL.revokeObjectURL(url);
            showToast("Exported 3D CityJSON Urban Digital Twin model successfully!", "success");
        } else {
            showToast("CityJSON export error: " + (data.message || "Unknown error"), "error");
        }
    } catch (err) {
        showToast("CityJSON network error: " + err.message, "error");
    }
}

const btnExportObj = document.getElementById('btn-export-obj');
if (btnExportObj) {
    btnExportObj.addEventListener('click', exportWavefrontObj);
}

const btnExportCityJson = document.getElementById('btn-export-cityjson');
if (btnExportCityJson) {
    btnExportCityJson.addEventListener('click', exportCityJson);
}

// ==========================================
// WALLACEI-GRADE GENOME GALLERY VIEW
// ==========================================

function renderGenomeGallery() {
    const galleryGrid = document.getElementById('genome-gallery-grid');
    if (!galleryGrid) return;
    
    const sols = (wallaceiResult && wallaceiResult.all_solutions) ? wallaceiResult.all_solutions : [];
    if (!sols.length) {
        galleryGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #94a3b8; padding: 20px;">Run Evolutionary Optimization to populate Phenotype Genome Gallery.</div>';
        return;
    }

    let cardsHtml = '';
    sols.forEach((sol, idx) => {
        const isSelected = activeParetoSolution && activeParetoSolution.id === sol.id;
        const g = sol.genotype || {};
        const m = sol.metrics || {};

        cardsHtml += `
        <div class="genome-card ${isSelected ? 'selected' : ''}" data-sol-idx="${idx}">
            <div class="genome-card-header">
                <span>${sol.id || 'Sol_' + (idx+1)}</span>
                <span style="color: var(--accent); font-weight:700;">Rank ${sol.rank || 1}</span>
            </div>
            <div class="genome-card-metrics">
                <div>Typology: <b>${g.typology || 'Tower'}</b></div>
                <div>Floors: <b>${g.floors || 4}</b> (${m.height_m || 12}m)</div>
                <div>Score: <b>${m.planx_score || '-'}</b></div>
                <div>GFA: <b>${m.gfa || '-'} m²</b></div>
            </div>
        </div>`;
    });

    galleryGrid.innerHTML = cardsHtml;

    galleryGrid.querySelectorAll('.genome-card').forEach(card => {
        card.addEventListener('click', () => {
            const idx = parseInt(card.getAttribute('data-sol-idx'));
            const sol = sols[idx];
            if (sol) {
                activeParetoSolution = sol;
                displaySolutionCard(sol);
                applyPhenotypeTo3D(sol);
                renderGenomeGallery();
                showToast(`Loaded phenotype ${sol.id} into 3D view`, 'info');
            }
        });
    });
}

const subtabGallery = document.getElementById('subtab-gallery');
const viewGallery = document.getElementById('view-gallery');
if (subtabGallery && viewGallery) {
    subtabGallery.addEventListener('click', () => {
        document.querySelectorAll('.subtab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.subtab-view').forEach(view => view.classList.add('hidden'));
        subtabGallery.classList.add('active');
        viewGallery.classList.remove('hidden');
        renderGenomeGallery();
    });
}

// ==========================================
// 3D SECTION CUT & DISTRICT COUPLING ENGINE
// ==========================================

let isSectionCutActive = false;
let sectionCutPlane = new THREE.Plane(new THREE.Vector3(0, -1, 0), 15);

function toggleSectionCut() {
    isSectionCutActive = !isSectionCutActive;
    if (isSectionCutActive) {
        renderer.clippingPlanes = [sectionCutPlane];
        renderer.localClippingEnabled = true;
        showToast("3D Section Cut Plane Activated! (Cutting top plates at Y=15m)", "success");
    } else {
        renderer.clippingPlanes = [];
        renderer.localClippingEnabled = false;
        showToast("3D Section Cut Plane Deactivated.", "info");
    }
}

async function evaluateDistrictCoupling() {
    const payloadBldgs = parcelFeatures.map(item => ({
        id: `Building_${item.fid}`,
        metrics: {
            height_m: item.params.floors * item.params.floorHeight,
            footprint_area: item.area * 0.45,
            gfa: item.area * 0.45 * item.params.floors,
            planx_score: 82.0
        }
    }));

    try {
        const resp = await fetch('/api/district/evaluate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ buildings: payloadBldgs, site_area: 8000.0 })
        });
        const data = await resp.json();

        if (data.status === 'ok' && data.district_metrics) {
            const m = data.district_metrics;
            const msg = `🏢 District Coupling Evaluation:\n` +
                        `• Mutual Solar Shadow Loss: ${m.district_avg_solar_shadow_loss_pct}%\n` +
                        `• Canyon Wind Speed: ${m.district_canyon_wind_speed_ms} m/s\n` +
                        `• Pedestrian Comfort Score: ${m.district_pedestrian_comfort}/100\n` +
                        `• Stormwater Retention: ${m.district_runoff_retention_pct}%\n` +
                        `• District PlanX Score: ${m.district_planx_score}/100`;
            showToast(msg, 'success');
        } else {
            showToast("District evaluation error: " + (data.message || "Unknown error"), "error");
        }
    } catch (err) {
        showToast("District evaluation network error: " + err.message, "error");
    }
}

const btnSectionCut = document.getElementById('btn-section-cut');
if (btnSectionCut) {
    btnSectionCut.addEventListener('click', toggleSectionCut);
}

const btnDistrictEval = document.getElementById('btn-district-eval');
if (btnDistrictEval) {
    btnDistrictEval.addEventListener('click', evaluateDistrictCoupling);
}

/* ==========================================================================
   VISUAL CGA (VCGA) NODE GRAPH MODELER ENGINE
   ========================================================================== */

let vcgaNodes = [];
let vcgaConnections = [];
let selectedVcgaNodeId = null;
let vcgaConnectingPort = null;
let vcgaNextNodeId = 1;




