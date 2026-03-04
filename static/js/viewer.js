// Fuji RAW Similarity Viewer - Client-side JavaScript

let clusters = [];
let currentCluster = 0;
let availableColors = [];
let focusedImageIndex = 0;

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
        // Load colors and clusters in parallel
        const [colorsResponse, clustersResponse] = await Promise.all([
            fetch('/api/colors'),
            fetch('/api/clusters')
        ]);

        if (!colorsResponse.ok || !clustersResponse.ok) {
            throw new Error('Failed to load data');
        }

        availableColors = await colorsResponse.json();
        clusters = await clustersResponse.json();

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

    // Reset focused image
    focusedImageIndex = 0;

    // Create image cards
    cluster.images.forEach((image, idx) => {
        const card = document.createElement('div');
        card.className = 'image-card';
        card.dataset.imageIndex = idx;

        // Set initial focus
        if (idx === 0) {
            card.classList.add('focused');
        }

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

        // Create color picker
        const colorPicker = createColorPicker(image, idx);

        card.appendChild(wrapper);
        card.appendChild(filename);
        card.appendChild(colorPicker);
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

// Create color picker for an image
function createColorPicker(image, imageIdx) {
    const picker = document.createElement('div');
    picker.className = 'color-picker';

    const label = document.createElement('span');
    label.className = 'color-picker-label';
    label.textContent = 'Tag:';
    picker.appendChild(label);

    availableColors.forEach(color => {
        const btn = document.createElement('button');
        btn.className = 'color-btn';
        btn.setAttribute('data-color', color);
        btn.title = color;

        // Set selected state
        if (image.color === color || (color === 'None' && !image.color)) {
            btn.classList.add('selected');
        }

        // Click handler
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            await setImageColor(imageIdx, color, picker);
        });

        picker.appendChild(btn);
    });

    return picker;
}

// Set color for an image
async function setImageColor(imageIdx, color, pickerElement) {
    try {
        const response = await fetch(`/api/color/${currentCluster}/${imageIdx}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ color })
        });

        if (!response.ok) {
            throw new Error('Failed to set color');
        }

        const result = await response.json();

        // Update UI
        const buttons = pickerElement.querySelectorAll('.color-btn');
        buttons.forEach(btn => {
            if (btn.getAttribute('data-color') === color) {
                btn.classList.add('selected');
            } else {
                btn.classList.remove('selected');
            }
        });

        // Update cluster data
        clusters[currentCluster].images[imageIdx].color = color === 'None' ? null : color;

    } catch (error) {
        console.error('Error setting color:', error);
        alert('Failed to set color tag. Check console for details.');
    }
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

// Set focus to an image
function focusImage(index) {
    const cluster = clusters[currentCluster];
    if (!cluster) return;

    // Wrap around
    focusedImageIndex = ((index % cluster.images.length) + cluster.images.length) % cluster.images.length;

    // Update UI
    const cards = document.querySelectorAll('.image-card');
    cards.forEach((card, idx) => {
        if (idx === focusedImageIndex) {
            card.classList.add('focused');
            card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } else {
            card.classList.remove('focused');
        }
    });
}

// Tag focused image with color
async function tagFocusedImage(colorIndex) {
    if (colorIndex < 0 || colorIndex >= availableColors.length) return;

    const color = availableColors[colorIndex];
    const cluster = clusters[currentCluster];
    if (!cluster) return;

    const card = document.querySelector(`.image-card[data-image-index="${focusedImageIndex}"]`);
    if (!card) return;

    const picker = card.querySelector('.color-picker');
    await setImageColor(focusedImageIndex, color, picker);

    // Auto-advance to next image
    focusImage(focusedImageIndex + 1);
}

// Set up event listeners
function setupEventListeners() {
    prevBtn.addEventListener('click', prevCluster);
    nextBtn.addEventListener('click', nextCluster);

    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
        // Don't interfere with text input
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }

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
            case 'Tab':
                e.preventDefault();
                if (e.shiftKey) {
                    focusImage(focusedImageIndex - 1);
                } else {
                    focusImage(focusedImageIndex + 1);
                }
                break;
            case '1':
            case '2':
            case '3':
            case '4':
            case '5':
            case '6':
            case '7':
            case '8':
                e.preventDefault();
                const colorIndex = parseInt(e.key) - 1;
                tagFocusedImage(colorIndex);
                break;
        }
    });
}

// Start the application
init();
