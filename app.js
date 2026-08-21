// --- USTAWIENIA DŹWIĘKU (HOWLER.JS) ---
const soundSFX = new Howl({
    src: ['https://assets.mixkit.co/active_storage/sfx/2568/2568-preview.mp3'], // Syntetyczny impuls sci-fi
    volume: 0.3
});

// --- THREE.JS PRZESTRZEŃ 3D ---
const canvas = document.getElementById('webgl-canvas');
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true });

renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

// WERSJA SYMMETRYCZNA / ŚWIATŁO
const ambientLight = new THREE.AmbientLight(0xffffff, 0.2);
scene.add(ambientLight);

const pointLight = new THREE.PointLight(0xa855f7, 2, 50);
pointLight.position.set(0, 0, 0);
scene.add(pointLight);

// --- 1. SFERA PROJEKTÓW 360° (PANORAMICZNA KULA) ---
const sphereGroup = new THREE.Group();
scene.add(sphereGroup);

// PUNKTY CZĄSTECZEK SFERY
const particlesGeo = new THREE.BufferGeometry();
const count = 2000;
const positions = new Float32Array(count * 3);

for(let i = 0; i < count * 3; i += 3) {
    const u = Math.random();
    const v = Math.random();
    const theta = u * 2.0 * Math.PI;
    const phi = Math.acos(2.0 * v - 1.0);
    const r = 25; // Promień kuli
    positions[i] = r * Math.sin(phi) * Math.cos(theta);
    positions[i+1] = r * Math.sin(phi) * Math.sin(theta);
    positions[i+2] = r * Math.cos(phi);
}

particlesGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
const particlesMat = new THREE.PointsMaterial({ size: 0.15, color: 0xa855f7, transparent: true, opacity: 0.7 });
const particleSphere = new THREE.Points(particlesGeo, particlesMat);
sphereGroup.add(particleSphere);

// DANIA PROJEKTÓW NA ŚCIANACH SFERY
const projectsData = [
    {
        title: "HandTrack OS",
        desc: "Bezdotykowe sterowanie komputerem za pomocą gestów dłoni. Zawiera liczne tryby pracy (np. Tryb prezentacji).",
        progress: "80%",
        tech: ["Python", "MediaPipe", "OpenCV"],
        pos: new THREE.Vector3(15, 0, -15)
    },
    {
        title: "Nixi AI Assistant",
        desc: "Zaawansowana wirtualna asystentka głosowa z architekturą agentową sterująca urządzeniami.",
        progress: "50%",
        tech: ["Ollama", "Local LLMs", "Python", "Agent Architecture"],
        pos: new THREE.Vector3(-15, 0, -15)
    }
];

const projectMeshes = [];

projectsData.forEach((proj) => {
    const geo = new THREE.BoxGeometry(4, 3, 0.2);
    const mat = new THREE.MeshBasicMaterial({ color: 0xa855f7, wireframe: true });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.position.copy(proj.pos);
    mesh.lookAt(0, 0, 0);
    mesh.userData = proj;
    sphereGroup.add(mesh);
    projectMeshes.push(mesh);
});

// --- 2. TESSERACT (HIPERKOSTKA DLA KONTAKTU) ---
const tesseractGroup = new THREE.Group();
const cubeGeo = new THREE.BoxGeometry(5, 5, 5);
const cubeMat = new THREE.MeshBasicMaterial({ color: 0xd8b4fe, wireframe: true });
const tesseractCube = new THREE.Mesh(cubeGeo, cubeMat);
tesseractGroup.add(tesseractCube);
tesseractGroup.position.set(0, -100, 0); // Ukryty domyślnie
scene.add(tesseractGroup);

// --- 3. RZEŹBIARZ 3D (LABORATORIUM) ---
const sculptureGeo = new THREE.IcosahedronGeometry(4, 3);
const sculptureMat = new THREE.MeshStandardMaterial({ color: 0xa855f7, wireframe: true, roughness: 0.1 });
const sculptureMesh = new THREE.Mesh(sculptureGeo, sculptureMat);
sculptureMesh.position.set(0, 100, 0); // Ukryty domyślnie
scene.add(sculptureMesh);

camera.position.z = 0.1; // Kamera wewnątrz sfery

// --- OBSŁUGA OBRACANIA KULEM 360 DEG ---
let isDragging = false;
let previousMousePosition = { x: 0, y: 0 };

window.addEventListener('mousedown', () => isDragging = true);
window.addEventListener('mouseup', () => isDragging = false);
window.addEventListener('mousemove', (e) => {
    if (isDragging) {
        const deltaMove = { x: e.clientX - previousMousePosition.x, y: e.clientY - previousMousePosition.y };
        sphereGroup.rotation.y += deltaMove.x * 0.005;
        sphereGroup.rotation.x += deltaMove.y * 0.005;
    }
    previousMousePosition = { x: e.clientX, y: e.clientY };

    // Interakcja w Rzeźbiarzu 3D
    if (sculptureMesh.position.y === 0) {
        sculptureMesh.rotation.x += 0.01;
        sculptureMesh.rotation.y += 0.01;
    }
});

// --- INTERAKCJA KLIKNIĘCIA W HOLOGRAM PROJEKTU ---
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

window.addEventListener('click', (e) => {
    mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObjects(projectMeshes);

    if (intersects.length > 0) {
        soundSFX.play();
        const data = intersects[0].object.userData;
        openHologramModal(data);
    }
});

function openHologramModal(data) {
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

document.getElementById('close-modal').addEventListener('click', () => {
    document.getElementById('project-modal').classList.add('hidden');
});

// --- PRELOADER ANIMACJA ---
let progressVal = 0;
const progressInterval = setInterval(() => {
    progressVal += 2;
    document.getElementById('progress').innerText = `${progressVal}%`;
    if (progressVal >= 100) {
        clearInterval(progressInterval);
        document.getElementById('start-btn').classList.remove('hidden');
    }
}, 30);

document.getElementById('start-btn').addEventListener('click', () => {
    soundSFX.play();
    gsap.to('#preloader', { opacity: 0, duration: 1, onComplete: () => {
        document.getElementById('preloader').classList.add('hidden');
    }});
});

// --- NAWIGACJA MIĘDZY PODSTRONAMI ---
const navBtns = document.querySelectorAll('.nav-btn');
const sections = document.querySelectorAll('.hud-section');

navBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        soundSFX.play();
        navBtns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        const target = btn.getAttribute('data-section');
        sections.forEach(s => s.classList.add('hidden'));

        // RESET POZYCJI OBIEKTÓW 3D
        gsap.to(sphereGroup.position, { y: target === 'home' ? 0 : 500, duration: 1.5 });
        gsap.to(tesseractGroup.position, { y: target === 'contact' ? 0 : -100, duration: 1.5 });
        gsap.to(sculptureMesh.position, { y: target === 'lab' ? 0 : 100, duration: 1.5 });

        if (target !== 'home') {
            document.getElementById(`${target}-section`).classList.remove('hidden');
        }
    });
});

// DRZEWO SKILLI
document.querySelectorAll('.tree-node').forEach(node => {
    node.addEventListener('click', () => {
        soundSFX.play();
        const info = node.getAttribute('data-info');
        if(info) document.getElementById('skill-description').innerText = info;
    });
});

// DISCORD COPY
document.getElementById('discord-btn').addEventListener('click', (e) => {
    e.preventDefault();
    soundSFX.play();
    navigator.clipboard.writeText("Rejson#0000");
    alert("Skopiowano Twój nick Discord do schowka!");
});

// PETLA ANIMACJI THREE.JS
function animate() {
    requestAnimationFrame(animate);
    particleSphere.rotation.y += 0.001;
    tesseractGroup.rotation.x += 0.01;
    tesseractGroup.rotation.y += 0.01;
    renderer.render(scene, camera);
}
animate();

window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
});
