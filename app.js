// DŹWIĘK
const soundSFX = new Howl({
    src: ['https://assets.mixkit.co/active_storage/sfx/2568/2568-preview.mp3'],
    volume: 0.2
});

// SCENA THREE.JS
const canvas = document.getElementById('webgl-canvas');
const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x030008, 0.025);

const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });

renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

// TEKSTURA CZĄSTECZEK
function createParticleTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 64; canvas.height = 64;
    const ctx = canvas.getContext('2d');
    const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    gradient.addColorStop(0, 'rgba(216, 180, 254, 1)');
    gradient.addColorStop(0.3, 'rgba(168, 85, 247, 0.6)');
    gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 64, 64);
    return new THREE.CanvasTexture(canvas);
}

// GENERATOR TEKSTURY HOLOGRAMU Z TEKSTEM
function createHologramTexture(title, tag) {
    const canvas = document.createElement('canvas');
    canvas.width = 512; canvas.height = 340;
    const ctx = canvas.getContext('2d');

    // Tło szkła
    ctx.fillStyle = 'rgba(20, 8, 38, 0.85)';
    ctx.fillRect(0, 0, 512, 340);

    // Obramowanie
    ctx.strokeStyle = '#a855f7';
    ctx.lineWidth = 8;
    ctx.strokeRect(10, 10, 492, 320);

    // Teksty
    ctx.fillStyle = '#a855f7';
    ctx.font = 'bold 24px sans-serif';
    ctx.fillText(`// ${tag}`, 30, 60);

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 42px sans-serif';
    ctx.fillText(title, 30, 140);

    ctx.fillStyle = '#d8b4fe';
    ctx.font = '22px sans-serif';
    ctx.fillText('KLIKNIJ / DOTKNIJ Szczegóły', 30, 260);

    return new THREE.CanvasTexture(canvas);
}

// 1. SFERA CZĄSTECZEK
const sphereGroup = new THREE.Group();
scene.add(sphereGroup);

const count = 1500;
const positions = new Float32Array(count * 3);

for(let i = 0; i < count * 3; i += 3) {
    const u = Math.random();
    const v = Math.random();
    const theta = u * 2.0 * Math.PI;
    const phi = Math.acos(2.0 * v - 1.0);
    const r = 18 + (Math.random() - 0.5) * 3;
    positions[i] = r * Math.sin(phi) * Math.cos(theta);
    positions[i+1] = r * Math.sin(phi) * Math.sin(theta);
    positions[i+2] = r * Math.cos(phi);
}

const particlesGeo = new THREE.BufferGeometry();
particlesGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
const particlesMat = new THREE.PointsMaterial({
    size: 0.8,
    map: createParticleTexture(),
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false
});

sphereGroup.add(new THREE.Points(particlesGeo, particlesMat));

// PROJEKTY
const projectsData = [
    {
        title: "HandTrack OS",
        tag: "COMPUTER VISION",
        desc: "Bezdotykowe sterowanie komputerem za pomocą gestów dłoni i kamerki.",
        progress: "80%",
        tech: ["Python", "MediaPipe", "OpenCV"],
        pos: new THREE.Vector3(0, 0, -12)
    },
    {
        title: "Nixi AI",
        tag: "AUTONOMOUS AGENT",
        desc: "Autonomiczna asystentka głosowa z zespołem lokalnych agentów AI.",
        progress: "50%",
        tech: ["Ollama", "Local LLMs", "Python"],
        pos: new THREE.Vector3(0, 0, 12)
    }
];

const projectMeshes = [];
projectsData.forEach((proj) => {
    const geo = new THREE.PlaneGeometry(7, 4.5);
    const texture = createHologramTexture(proj.title, proj.tag);
    const mat = new THREE.MeshBasicMaterial({
        map: texture,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.9
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.copy(proj.pos);
    mesh.lookAt(0, 0, 0);
    mesh.userData = proj;
    sphereGroup.add(mesh);
    projectMeshes.push(mesh);
});

// 2. TESSERACT & 3. RZEŹBIARZ
const tesseractGroup = new THREE.Group();
tesseractGroup.add(new THREE.Mesh(new THREE.BoxGeometry(4, 4, 4), new THREE.MeshBasicMaterial({ color: 0xd8b4fe, wireframe: true })));
tesseractGroup.position.set(0, -100, 0);
scene.add(tesseractGroup);

const sculptureMesh = new THREE.Mesh(new THREE.IcosahedronGeometry(3, 2), new THREE.MeshBasicMaterial({ color: 0xa855f7, wireframe: true }));
sculptureMesh.position.set(0, 100, 0);
scene.add(sculptureMesh);

camera.position.z = 0.1;

// STEROWANIE DOTYKIEM / MYSZKĄ
let isDragging = false;
let previousTouch = { x: 0, y: 0 };

const handleStart = (x, y) => { isDragging = true; previousTouch = { x, y }; };
const handleEnd = () => { isDragging = false; };
const handleMove = (x, y) => {
    if (isDragging) {
        sphereGroup.rotation.y += (x - previousTouch.x) * 0.005;
        sphereGroup.rotation.x += (y - previousTouch.y) * 0.005;
        previousTouch = { x, y };
    }
};

window.addEventListener('mousedown', (e) => handleStart(e.clientX, e.clientY));
window.addEventListener('mouseup', handleEnd);
window.addEventListener('mousemove', (e) => handleMove(e.clientX, e.clientY));

window.addEventListener('touchstart', (e) => handleStart(e.touches[0].clientX, e.touches[0].clientY));
window.addEventListener('touchend', handleEnd);
window.addEventListener('touchmove', (e) => handleMove(e.touches[0].clientX, e.touches[0].clientY));

// KLIKNIĘCIE W PROJEKT
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

function checkIntersects(x, y) {
    mouse.x = (x / window.innerWidth) * 2 - 1;
    mouse.y = -(y / window.innerHeight) * 2 + 1;
    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(projectMeshes);

    if (intersects.length > 0) {
        soundSFX.play();
        const data = intersects[0].object.userData;
        document.getElementById('modal-title').innerText = data.title;
        document.getElementById('modal-description').innerText = data.desc;
        document.getElementById('modal-progress').style.width = data.progress;
        
        const techBox = document.getElementById('modal-tech');
        techBox.innerHTML = '';
        data.tech.forEach(t => {
            const span = document.createElement('span');
            span.className = 'tree-node';
            span.innerText = t;
            techBox.appendChild(span);
        });

        document.getElementById('project-modal').classList.remove('hidden');
    }
}

window.addEventListener('click', (e) => checkIntersects(e.clientX, e.clientY));

document.getElementById('close-modal').addEventListener('click', () => {
    document.getElementById('project-modal').classList.add('hidden');
});

// PRELOADER & NAV
let progressVal = 0;
const progressInterval = setInterval(() => {
    progressVal += 5;
    document.getElementById('progress').innerText = `${progressVal}%`;
    if (progressVal >= 100) {
        clearInterval(progressInterval);
        document.getElementById('start-btn').classList.remove('hidden');
    }
}, 30);

document.getElementById('start-btn').addEventListener('click', () => {
    soundSFX.play();
    gsap.to('#preloader', { opacity: 0, duration: 0.8, onComplete: () => {
        document.getElementById('preloader').classList.add('hidden');
    }});
});

const navBtns = document.querySelectorAll('.nav-btn');
const sections = document.querySelectorAll('.hud-section');

navBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        soundSFX.play();
        navBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const target = btn.getAttribute('data-section');
        sections.forEach(s => s.classList.add('hidden'));

        gsap.to(sphereGroup.position, { y: target === 'home' ? 0 : 500, duration: 1 });
        gsap.to(tesseractGroup.position, { y: target === 'contact' ? 0 : -100, duration: 1 });
        gsap.to(sculptureMesh.position, { y: target === 'lab' ? 0 : 100, duration: 1 });

        if (target !== 'home') {
            document.getElementById(`${target}-section`).classList.remove('hidden');
        }
    });
});

function animate() {
    requestAnimationFrame(animate);
    sphereGroup.rotation.y += 0.001;
    tesseractGroup.rotation.x += 0.01;
    tesseractGroup.rotation.y += 0.01;
    sculptureMesh.rotation.y += 0.01;
    renderer.render(scene, camera);
}
animate();

window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});
