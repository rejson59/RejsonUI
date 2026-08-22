/**
 * Rejson UI - app.js
 * Vibe Coder Portfolio
 */

// --- Configuration ---
const CONFIG = {
    particleCount: 1500,
    accentColor: 0xa855f7,
    bgColor: 0x030008,
    projects: [
        {
            id: 'handtrack',
            title: 'HandTrack OS',
            tag: 'COMPUTER VISION',
            progress: 80,
            tech: ['Python', 'MediaPipe', 'OpenCV'],
            desc: 'Zaawansowany system bezdotykowego sterowania gestami w czasie rzeczywistym. Wykorzystuje głębokie uczenie do mapowania punktów dłoni na komendy systemowe.'
        },
        {
            id: 'nixi',
            title: 'Nixi',
            tag: 'AUTONOMOUS AGENT',
            progress: 50,
            tech: ['Ollama', 'Local LLMs', 'Python'],
            desc: 'Autonomiczna asystentka typu Jarvis działająca lokalnie. Zarządzanie plikami, automatyzacja workflow i inteligentna analiza kontekstu.'
        }
    ]
};

// --- State ---
let state = {
    currentView: 'home',
    isLoaded: false,
    rotationAuto: true,
    mouse: { x: 0, y: 0 },
    touch: { x: 0, y: 0, isDown: false }
};

// --- Audio ---
const sounds = {
    boot: new Howl({ src: ['https://assets.mixkit.co/active_storage/sfx/2571/2571-preview.mp3'], volume: 0.5 }),
    click: new Howl({ src: ['https://assets.mixkit.co/active_storage/sfx/2568/2568-preview.mp3'], volume: 0.3 }),
    transition: new Howl({ src: ['https://assets.mixkit.co/active_storage/sfx/2576/2576-preview.mp3'], volume: 0.3 }),
};

// --- Three.js Setup ---
let scene, camera, renderer, raycaster, mouseVector;
let particles, projectPanels = [], tesseract, labGeo;
let clock = new THREE.Clock();

function initThree() {
    scene = new THREE.Scene();
    scene.background = new THREE.Color(CONFIG.bgColor);
    scene.fog = new THREE.FogExp2(CONFIG.bgColor, 0.015);

    camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 5;

    renderer = new THREE.WebGLRenderer({
        canvas: document.getElementById('bg-canvas'),
        antialias: true,
        alpha: true
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    raycaster = new THREE.Raycaster();
    mouseVector = new THREE.Vector2();

    // Lighting
    const ambientLight = new THREE.AmbientLight(0x404040, 2);
    scene.add(ambientLight);
    const pointLight = new THREE.PointLight(CONFIG.accentColor, 10, 50);
    pointLight.position.set(0, 0, 0);
    scene.add(pointLight);

    createParticles();
    createProjectPanels();
    createTesseract();
    createLab();

    window.addEventListener('resize', onWindowResize);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mousedown', onMouseDown);
    window.addEventListener('touchstart', onTouchStart, { passive: false });
    window.addEventListener('touchmove', onTouchMove, { passive: false });
}

// Create a glowing soft circle texture
function createCircleTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');
    const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    gradient.addColorStop(0, 'rgba(216, 180, 254, 1)');
    gradient.addColorStop(0.2, 'rgba(168, 85, 247, 0.8)');
    gradient.addColorStop(0.5, 'rgba(168, 85, 247, 0.2)');
    gradient.addColorStop(1, 'rgba(168, 85, 247, 0)');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 64, 64);
    return new THREE.CanvasTexture(canvas);
}

function createParticles() {
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(CONFIG.particleCount * 3);
    const colors = new Float32Array(CONFIG.particleCount * 3);
    const sizes = new Float32Array(CONFIG.particleCount);

    const radius = 50;
    for (let i = 0; i < CONFIG.particleCount; i++) {
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos(2 * Math.random() - 1);
        
        positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta);
        positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
        positions[i * 3 + 2] = radius * Math.cos(phi);

        const color = new THREE.Color();
        color.setHSL(0.75, 0.6, 0.5 + Math.random() * 0.2);
        colors[i * 3] = color.r;
        colors[i * 3 + 1] = color.g;
        colors[i * 3 + 2] = color.b;

        sizes[i] = Math.random() * 2 + 0.5;
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const material = new THREE.PointsMaterial({
        size: 0.4,
        map: createCircleTexture(),
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        vertexColors: true
    });

    particles = new THREE.Points(geometry, material);
    scene.add(particles);
}

function createProjectPanelTexture(project) {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 256;
    const ctx = canvas.getContext('2d');

    // Background
    ctx.fillStyle = 'rgba(20, 0, 40, 0.7)';
    ctx.fillRect(0, 0, 512, 256);
    
    // Border
    ctx.strokeStyle = '#a855f7';
    ctx.lineWidth = 10;
    ctx.strokeRect(5, 5, 502, 246);

    // Text
    ctx.fillStyle = '#fff';
    ctx.font = 'bold 40px Arial';
    ctx.fillText(project.title, 40, 60);

    ctx.fillStyle = '#d8b4fe';
    ctx.font = 'bold 20px Arial';
    ctx.fillText(project.tag, 40, 100);

    ctx.fillStyle = '#aaa';
    ctx.font = '16px Arial';
    ctx.fillText('CLICK TO ACCESS SYSTEM', 40, 200);
    
    // Decoration
    ctx.strokeStyle = 'rgba(168, 85, 247, 0.3)';
    ctx.beginPath();
    ctx.moveTo(40, 120);
    ctx.lineTo(472, 120);
    ctx.stroke();

    return new THREE.CanvasTexture(canvas);
}

function createProjectPanels() {
    CONFIG.projects.forEach((proj, i) => {
        const geometry = new THREE.PlaneGeometry(4, 2);
        const material = new THREE.MeshBasicMaterial({
            map: createProjectPanelTexture(proj),
            transparent: true,
            side: THREE.DoubleSide
        });
        const panel = new THREE.Mesh(geometry, material);
        
        const angle = (i / CONFIG.projects.length) * Math.PI * 2;
        panel.position.set(Math.cos(angle) * 8, Math.sin(angle) * 2, Math.sin(angle) * 8);
        panel.lookAt(0, 0, 0);
        panel.userData = proj;
        
        scene.add(panel);
        projectPanels.push(panel);
    });
}

function createTesseract() {
    tesseract = new THREE.Group();
    const geo = new THREE.BoxGeometry(1, 1, 1);
    const mat = new THREE.MeshBasicMaterial({ color: CONFIG.accentColor, wireframe: true });
    
    for(let i = 0; i < 3; i++) {
        const cube = new THREE.Mesh(geo, mat);
        cube.scale.setScalar(1 + i * 0.5);
        cube.rotation.set(Math.random(), Math.random(), Math.random());
        tesseract.add(cube);
    }
    
    tesseract.position.set(0, 0, -20);
    tesseract.visible = false;
    scene.add(tesseract);
}

function createLab() {
    const geo = new THREE.IcosahedronGeometry(2, 1);
    const mat = new THREE.MeshBasicMaterial({ 
        color: CONFIG.accentColor, 
        wireframe: true,
        transparent: true,
        opacity: 0.8
    });
    labGeo = new THREE.Mesh(geo, mat);
    labGeo.position.set(0, 0, -20);
    labGeo.visible = false;
    scene.add(labGeo);
}

// --- Interaction & Animation ---

function onWindowResize() {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}

function onMouseMove(e) {
    state.mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
    state.mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
    mouseVector.set(state.mouse.x, state.mouse.y);
}

function onMouseDown() {
    raycaster.setFromCamera(mouseVector, camera);
    const intersects = raycaster.intersectObjects(projectPanels);
    if (intersects.length > 0) {
        const project = intersects[0].object.userData;
        openProjectModal(project);
    }
}

function onTouchStart(e) {
    state.touch.isDown = true;
    state.touch.x = e.touches[0].clientX;
    state.touch.y = e.touches[0].clientY;
}

function onTouchMove(e) {
    if (!state.touch.isDown) return;
    const dx = e.touches[0].clientX - state.touch.x;
    const dy = e.touches[0].clientY - state.touch.y;
    
    particles.rotation.y += dx * 0.005;
    particles.rotation.x += dy * 0.005;
    
    state.touch.x = e.touches[0].clientX;
    state.touch.y = e.touches[0].clientY;
    e.preventDefault();
}

function animate() {
    requestAnimationFrame(animate);
    const delta = clock.getDelta();
    const time = clock.getElapsedTime();

    if (state.rotationAuto && state.currentView === 'home') {
        particles.rotation.y += 0.001;
        particles.rotation.x += 0.0005;
    }

    if (tesseract.visible) {
        tesseract.rotation.x += 0.01;
        tesseract.rotation.y += 0.01;
    }

    if (labGeo.visible) {
        labGeo.rotation.y += 0.005;
        labGeo.rotation.x += 0.005;
        // React to mouse slightly
        labGeo.rotation.y += state.mouse.x * 0.05;
        labGeo.rotation.x += state.mouse.y * 0.05;
    }

    renderer.render(scene, camera);
}

// --- UI Logic ---

function openProjectModal(proj) {
    sounds.click.play();
    document.getElementById('project-title').innerText = proj.title;
    document.getElementById('project-tag').innerText = proj.tag;
    document.getElementById('project-progress').innerText = proj.progress + '%';
    document.getElementById('project-progress-fill').style.width = proj.progress + '%';
    document.getElementById('project-desc').innerText = proj.desc;
    
    const techContainer = document.getElementById('project-tech');
    techContainer.innerHTML = '';
    proj.tech.forEach(t => {
        const pill = document.createElement('div');
        pill.className = 'tech-pill';
        pill.innerText = t;
        techContainer.appendChild(pill);
    });
    
    document.getElementById('modal-projects').style.display = 'flex';
}

function switchView(viewId) {
    sounds.transition.play();
    state.currentView = viewId;
    
    // Reset visibility
    tesseract.visible = false;
    labGeo.visible = false;
    projectPanels.forEach(p => p.visible = true);

    // GSAP Transitions
    if (viewId === 'home') {
        gsap.to(camera.position, { z: 5, x: 0, y: 0, duration: 1.5, ease: 'power2.inOut' });
        state.rotationAuto = true;
    } else if (viewId === 'projects') {
        gsap.to(camera.position, { z: 12, x: 0, y: 0, duration: 1.5, ease: 'power2.inOut' });
        state.rotationAuto = false;
    } else if (viewId === 'synapse') {
        gsap.to(camera.position, { z: 15, x: 0, y: 0, duration: 1.5, ease: 'power2.inOut' });
        document.getElementById('view-synapse').style.display = 'flex';
    } else if (viewId === 'tesseract') {
        tesseract.visible = true;
        gsap.to(camera.position, { z: 0, x: 0, y: 0, duration: 1.5, ease: 'power2.inOut' });
        document.getElementById('view-tesseract').style.display = 'flex';
    } else if (viewId === 'lab') {
        labGeo.visible = true;
        gsap.to(camera.position, { z: 0, x: 0, y: 0, duration: 1.5, ease: 'power2.inOut' });
        document.getElementById('view-lab').style.display = 'flex';
    }
}

// --- Initialization ---

document.addEventListener('DOMContentLoaded', () => {
    initThree();
    animate();

    const preloader = document.getElementById('preloader');
    const progressFill = document.querySelector('.progress-fill');
    const startBtn = document.getElementById('start-btn');

    // Simulate loading
    let loadProgress = 0;
    const loadInt = setInterval(() => {
        loadProgress += Math.random() * 15;
        if (loadProgress > 100) loadProgress = 100;
        progressFill.style.width = loadProgress + '%';
        if (loadProgress === 100) clearInterval(loadInt);
    }, 150);

    startBtn.addEventListener('click', () => {
        sounds.boot.play();
        preloader.style.opacity = '0';
        setTimeout(() => {
            preloader.style.visibility = 'hidden';
            state.isLoaded = true;
        }, 1000);
    });

    // HUD Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');
            switchView(item.dataset.target);
        });
    });

    // Close buttons
    document.querySelectorAll('.close-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const parent = e.target.closest('.modal, .full-view');
            parent.style.display = 'none';
            if (parent.id !== 'modal-projects') {
                switchView('home');
                document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            }
        });
    });

    // Discord Copy
    document.getElementById('discord-btn').addEventListener('click', () => {
        navigator.clipboard.writeText('Rejson#0000');
        alert('Copied: Rejson#0000');
    });
});
