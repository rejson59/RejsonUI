// DŹWIĘK
const soundSFX = new Howl({
    src: ['https://assets.mixkit.co/active_storage/sfx/2568/2568-preview.mp3'],
    volume: 0.2
});

// SCENA THREE.JS Z MGŁĄ DLA GŁĘBI
const canvas = document.getElementById('webgl-canvas');
const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x030008, 0.025);

const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });

renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

// EFEKT GLOW DLA CZĄSTECZEK (TEKSTURA SFERY)
function createParticleTexture() {
    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');
    const gradient = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
    gradient.addColorStop(0, 'rgba(216, 180, 254, 1)');
    gradient.addColorStop(0.3, 'rgba(168, 85, 247, 0.6)');
    gradient.addColorStop(1, 'rgba(0, 0, 0, 0)');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, 64, 64);
    return new THREE.CanvasTexture(canvas);
}

// 1. GŁÓWNA KULA CZĄSTECZEK 3D
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

const particleSphere = new THREE.Points(particlesGeo, particlesMat);
sphereGroup.add(particleSphere);

// KARTY PROJEKTÓW
const projectsData = [
    {
        title: "HandTrack OS",
        desc: "Bezdotykowe sterowanie komputerem za pomocą gestów dłoni i kamerki.",
        progress: "80%",
        tech: ["Python", "MediaPipe", "OpenCV"],
        pos: new THREE.Vector3(0, 0, -12)
    },
    {
        title: "Nixi AI Assistant",
        desc: "Autonomiczna asystentka głosowa z zespołem lokalnych agentów AI.",
        progress: "50%",
        tech: ["Ollama", "Local LLMs", "Python"],
        pos: new THREE.Vector3(0, 0, 12)
    }
];

const projectMeshes = [];
projectsData.forEach((proj) => {
    const geo = new THREE.PlaneGeometry(6, 4);
    const mat = new THREE.MeshBasicMaterial({
        color: 0xa855f7,
        side: THREE.DoubleSide,
        wireframe: true,
        transparent: true,
        opacity: 0.8
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.copy(proj.pos);
    mesh.lookAt(0, 0, 0);
    mesh.userData = proj;
    sphereGroup.add(mesh);
    projectMeshes.push(mesh);
});

// 2. TESSERACT
const tesseractGroup = new THREE.Group();
const cubeGeo = new THREE.BoxGeometry(4, 4, 4);
const cubeMat = new THREE.MeshBasicMaterial({ color: 0xd8b4fe, wireframe: true });
tesseractGroup.add(new THREE.Mesh(cubeGeo, cubeMat));
tesseractGroup.position.set(0, -100, 0);
scene.add(tesseractGroup);

// 3. RZEŹBIARZ 3D
const sculptureGeo = new THREE.IcosahedronGeometry(3, 2);
const sculptureMat = new THREE.MeshBasicMaterial({ color: 0xa855f7, wireframe: true });
const sculptureMesh = new THREE.Mesh(sculptureGeo, sculptureMat);
sculptureMesh.position.set(0, 100, 0);
scene.add(sculptureMesh);

camera.position.z = 0.1;

// OBSŁUGA DOTYKU I MYSZKI
let isDragging = false;
let previousTouch = { x: 0, y: 0 };

const handleStart = (x, y) => { isDragging = true; previousTouch = { x, y }; };
const handleEnd = () => { isDragging = false; };
const handleMove = (x, y) => {
    if (isDragging) {
        const deltaX = x - previousTouch.x;
        const deltaY = y - previousTouch.y;
        sphereGroup.rotation.y += deltaX * 0.005;
        sphereGroup.rotation.x += deltaY * 0.005;
        previousTouch = { x, y };
    }
};

window.addEventListener('mousedown', (e) => handleStart(e.clientX, e.clientY));
window.addEventListener('mouseup', handleEnd);
window.addEventListener('mousemove', (e) => handleMove(e.clientX, e.clientY));

window.addEventListener('touchstart', (e) => handleStart(e.touches[0].clientX, e.touches[0].clientY));
window.addEventListener('touchend', handleEnd);
window.addEventListener('touchmove', (e) => handleMove(e.touches[0].clientX, e.touches[0].clientY));

// PRELOADER
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

// NAWIGACJA
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

// ANIMACJA GŁÓWNA
function animate() {
    requestAnimationFrame(animate);
    particleSphere.rotation.y += 0.002;
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
