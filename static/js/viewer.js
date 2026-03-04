// Fuji RAW Similarity Viewer - Client-side JavaScript

let clusters = [];
let currentCluster = 0;

// DOM elements
const loading = document.getElementById('loading');
const viewer = document.getElementById('viewer');
const errorDiv = document.getElementById('error');
const imageGrid = document.getElementById('imageGrid');
const similarityList = document.getElementById('similarityList');
const groupInfo = document.getElementById('groupInfo');
const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');

// Initialize
async function init() {
    try {
        const response = await fetch('/api/clusters');
        if (!response.ok) {
            throw new Error('Failed to load clusters');
        }

        clusters = await response.json();

        if (clusters.length === 0) {
            showError();
            return;
        }

        loading.classList.add('hidden');
        viewer.classList.remove('hidden');

        showCluster(0);
        setupEventListeners();
    } catch (error) {
        console.error('Error loading clusters:', error);
        loading.classList.add('hidden');
        errorDiv.classList.remove('hidden');
        errorDiv.querySelector('p').textContent = `Error: ${error.message}`;
    }
}

// Show error state
function showError() {
    loading.classList.add('hidden');
    errorDiv.classList.remove('hidden');
}

// Display a cluster
function showCluster(index) {
    // Wrap around
    currentCluster = ((index % clusters.length) + clusters.length) % clusters.length;

    const cluster = clusters[currentCluster];

    // Update header info
    groupInfo.textContent = `Group ${currentCluster + 1} of ${clusters.length} (${cluster.num_images} images)`;

    // Clear previous content
    imageGrid.innerHTML = '';
    similarityList.innerHTML = '';

    // Create image cards
    cluster.images.forEach((image, idx) => {
        const card = document.createElement('div');
        card.className = 'image-card';

        const wrapper = document.createElement('div');
        wrapper.className = 'image-wrapper';

        const img = document.createElement('img');
        img.className = 'loading';
        img.alt = image.filename;
        img.src = `/api/image/${currentCluster}/${idx}`;

        img.onload = () => {
            img.classList.remove('loading');
        };

        img.onerror = () => {
            img.alt = 'Failed to load';
            img.classList.remove('loading');
        };

        wrapper.appendChild(img);

        const filename = document.createElement('div');
        filename.className = 'image-filename';
        filename.textContent = image.filename;

        card.appendChild(wrapper);
        card.appendChild(filename);
        imageGrid.appendChild(card);
    });

    // Create similarity items
    cluster.similarities.forEach(sim => {
        const item = document.createElement('div');
        item.className = 'similarity-item';

        const files = document.createElement('div');
        files.className = 'similarity-files';
        files.innerHTML = `
            <span>${sim.img1}</span>
            <span class="similarity-arrow">↔</span>
            <span>${sim.img2}</span>
        `;

        const stats = document.createElement('div');
        stats.innerHTML = `
            <span class="similarity-percentage">Similarity: ${sim.percentage.toFixed(1)}%</span>
            <span class="similarity-distance">(distance: ${sim.distance})</span>
        `;

        item.appendChild(files);
        item.appendChild(stats);
        similarityList.appendChild(item);
    });

    // Update button states
    updateButtons();
}

// Update navigation buttons
function updateButtons() {
    prevBtn.disabled = false;
    nextBtn.disabled = false;
}

// Navigate to next cluster
function nextCluster() {
    showCluster(currentCluster + 1);
}

// Navigate to previous cluster
function prevCluster() {
    showCluster(currentCluster - 1);
}

// Set up event listeners
function setupEventListeners() {
    prevBtn.addEventListener('click', prevCluster);
    nextBtn.addEventListener('click', nextCluster);

    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
        switch(e.key) {
            case 'ArrowLeft':
            case 'a':
            case 'A':
            case 'p':
            case 'P':
                e.preventDefault();
                prevCluster();
                break;
            case 'ArrowRight':
            case 'd':
            case 'D':
            case 'n':
            case 'N':
                e.preventDefault();
                nextCluster();
                break;
            case 'q':
            case 'Q':
            case 'Escape':
                e.preventDefault();
                if (confirm('Close the viewer?')) {
                    window.close();
                }
                break;
        }
    });
}

// Start the application
init();
