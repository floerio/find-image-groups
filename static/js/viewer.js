// Find Image Groups - Client-side JavaScript

let clusters = [];
let ungroupedImages = [];
let currentCluster = 0;
let availableColors = [];
let focusedImageIndex = 0;
let showUngrouped = false;
let gridBrightness = 100; // Global brightness for grid view

// Lightbox state
let lightboxOpen = false;
let lightboxImageIndex = 0;
let zoomLevel = 1;
let brightnessLevel = 100;
let isPanning = false;
let panStartX = 0;
let panStartY = 0;
let panOffsetX = 0;
let panOffsetY = 0;

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
        // Load colors, clusters, and ungrouped images in parallel
        const [colorsResponse, clustersResponse, ungroupedResponse] = await Promise.all([
            fetch('/api/colors'),
            fetch('/api/clusters'),
            fetch('/api/ungrouped')
        ]);

        if (!colorsResponse.ok || !clustersResponse.ok || !ungroupedResponse.ok) {
            throw new Error('Failed to load data');
        }

        availableColors = await colorsResponse.json();
        clusters = await clustersResponse.json();
        ungroupedImages = await ungroupedResponse.json();

        showUngrouped = ungroupedImages.length > 0;

        if (clusters.length === 0 && !showUngrouped) {
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
    // Handle ungrouped images as a special "cluster"
    if (showUngrouped && index >= clusters.length) {
        showUngroupedImages();
        return;
    }

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
        wrapper.style.cursor = 'pointer';
        wrapper.title = 'Click to zoom';

        // Click to open lightbox
        wrapper.addEventListener('click', () => {
            openLightbox(idx);
        });

        const img = document.createElement('img');
        img.className = 'loading';
        img.alt = image.filename;
        img.src = `/api/image/${currentCluster}/${idx}`;
        img.style.filter = `brightness(${gridBrightness}%)`;

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

// Display ungrouped images
function showUngroupedImages() {
    currentCluster = clusters.length; // Special index for ungrouped
    
    // Update header info
    groupInfo.textContent = `Ungrouped Images (${ungroupedImages.length} images)`;

    // Clear previous content
    imageGrid.innerHTML = '';
    similarityList.innerHTML = '';

    // Add info message
    const infoDiv = document.createElement('div');
    infoDiv.className = 'ungrouped-info';
    infoDiv.innerHTML = '<p>These images have no similar counterparts based on the current threshold.</p>';
    similarityList.appendChild(infoDiv);

    // Reset focused image
    focusedImageIndex = 0;

    // Create image cards
    ungroupedImages.forEach((image, idx) => {
        const card = document.createElement('div');
        card.className = 'image-card';
        card.dataset.imageIndex = idx;

        // Set initial focus
        if (idx === 0) {
            card.classList.add('focused');
        }

        const wrapper = document.createElement('div');
        wrapper.className = 'image-wrapper';
        wrapper.style.cursor = 'pointer';
        wrapper.title = 'Click to zoom';

        // Click to open lightbox
        wrapper.addEventListener('click', () => {
            openLightbox(idx);
        });

        const img = document.createElement('img');
        img.className = 'loading';
        img.alt = image.filename;
        img.src = `/api/ungrouped/${idx}`;
        img.style.filter = `brightness(${gridBrightness}%)`;

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
        let response;
        const isUngrouped = currentCluster >= clusters.length;
        
        if (isUngrouped) {
            response = await fetch(`/api/ungrouped/color/${imageIdx}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ color })
            });
        } else {
            response = await fetch(`/api/color/${currentCluster}/${imageIdx}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ color })
            });
        }

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

        // Update data
        if (isUngrouped) {
            ungroupedImages[imageIdx].color = color === 'None' ? null : color;
        } else {
            clusters[currentCluster].images[imageIdx].color = color === 'None' ? null : color;
        }

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
    const totalGroups = getTotalGroups();
    const nextIndex = currentCluster + 1;
    if (nextIndex >= totalGroups) {
        showCluster(0); // Wrap around to first group
    } else {
        showCluster(nextIndex);
    }
}

// Navigate to previous cluster
function prevCluster() {
    const totalGroups = getTotalGroups();
    const prevIndex = currentCluster - 1;
    if (prevIndex < 0) {
        showCluster(totalGroups - 1); // Wrap around to last group
    } else {
        showCluster(prevIndex);
    }
}

// Get total number of groups including ungrouped
function getTotalGroups() {
    let total = clusters.length;
    if (showUngrouped && ungroupedImages.length > 0) {
        total += 1;
    }
    return total;
}

// Set focus to an image
function focusImage(index) {
    const isUngrouped = currentCluster >= clusters.length;
    const totalImages = isUngrouped ? ungroupedImages.length : clusters[currentCluster].images.length;

    // Wrap around
    focusedImageIndex = ((index % totalImages) + totalImages) % totalImages;

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

// Set grid brightness
function setGridBrightness(newBrightness) {
    gridBrightness = Math.max(20, Math.min(200, newBrightness));
    
    // Update all images in the current view
    const images = document.querySelectorAll('.image-wrapper img');
    images.forEach(img => {
        img.style.filter = `brightness(${gridBrightness}%)`;
    });
    
    // Update brightness display if in grid view
    if (!lightboxOpen) {
        const brightnessDisplay = document.getElementById('gridBrightnessDisplay');
        if (brightnessDisplay) {
            brightnessDisplay.textContent = `${gridBrightness}%`;
        }
    }
}

// Reset grid brightness
function resetGridBrightness() {
    setGridBrightness(100);
}

// Tag focused image with color
async function tagFocusedImage(colorIndex) {
    if (colorIndex < 0 || colorIndex >= availableColors.length) return;

    const color = availableColors[colorIndex];
    const isUngrouped = currentCluster >= clusters.length;
    
    if (!isUngrouped) {
        const cluster = clusters[currentCluster];
        if (!cluster) return;
    }

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
    
    // Set up grid brightness button event listeners
    const brightnessDownBtn = document.getElementById('gridBrightnessDown');
    const brightnessUpBtn = document.getElementById('gridBrightnessUp');
    const brightnessResetBtn = document.getElementById('gridBrightnessReset');
    
    if (brightnessDownBtn) {
        brightnessDownBtn.onclick = () => setGridBrightness(gridBrightness - 10);
    }
    if (brightnessUpBtn) {
        brightnessUpBtn.onclick = () => setGridBrightness(gridBrightness + 10);
    }
    if (brightnessResetBtn) {
        brightnessResetBtn.onclick = resetGridBrightness;
    }

    // Keyboard navigation
    document.addEventListener('keydown', (e) => {
        // Don't interfere with text input
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }

        // Lightbox controls
        if (lightboxOpen) {
            switch(e.key) {
                case 'Escape':
                    e.preventDefault();
                    closeLightbox();
                    break;
                case 'ArrowLeft':
                    e.preventDefault();
                    if (e.shiftKey || e.ctrlKey) {
                        // Pan left when zoomed
                        if (zoomLevel > 1) {
                            panOffsetX += 50;
                            showLightboxImage();
                        }
                    } else {
                        lightboxPrevImage();
                    }
                    break;
                case 'ArrowRight':
                    e.preventDefault();
                    if (e.shiftKey || e.ctrlKey) {
                        // Pan right when zoomed
                        if (zoomLevel > 1) {
                            panOffsetX -= 50;
                            showLightboxImage();
                        }
                    } else {
                        lightboxNextImage();
                    }
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    if (zoomLevel > 1) {
                        panOffsetY += 50;
                        showLightboxImage();
                    }
                    break;
                case 'ArrowDown':
                    e.preventDefault();
                    if (zoomLevel > 1) {
                        panOffsetY -= 50;
                        showLightboxImage();
                    }
                    break;
                case '+':
                case '=':
                    e.preventDefault();
                    setZoom(zoomLevel * 1.2);
                    break;
                case '-':
                case '_':
                    e.preventDefault();
                    setZoom(zoomLevel / 1.2);
                    break;
                case ' ':
                    e.preventDefault();
                    fitToScreen();
                    break;
                case 'y':
                case 'Y':
                    e.preventDefault();
                    setBrightness(brightnessLevel - 10);
                    break;
                case 'x':
                case 'X':
                    e.preventDefault();
                    setBrightness(brightnessLevel + 10);
                    break;
                case ',':
                case '<':
                case ';':  // German keyboard: Shift + ,
                case ':':  // German keyboard: Shift + .
                    e.preventDefault();
                    setBrightness(brightnessLevel - 10);
                    break;
                case '.':
                case '>':
                case ':':  // German keyboard: Shift + .
                case ';':  // German keyboard: Shift + ,
                    e.preventDefault();
                    setBrightness(brightnessLevel + 10);
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
                    if (colorIndex >= 0 && colorIndex < availableColors.length) {
                        const color = availableColors[colorIndex];
                        const picker = document.querySelector('#lightboxColorPicker .color-picker');
                        setImageColor(lightboxImageIndex, color, picker);
                    }
                    break;
            }
            return;
        }

        // Normal grid view controls
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
            case 'y':
            case 'Y':
                e.preventDefault();
                setGridBrightness(gridBrightness - 10);
                break;
            case 'x':
            case 'X':
                e.preventDefault();
                setGridBrightness(gridBrightness + 10);
                break;
            case ' ':
                e.preventDefault();
                resetGridBrightness();
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

// Lightbox functions
function openLightbox(imageIndex) {
    lightboxOpen = true;
    lightboxImageIndex = imageIndex;
    zoomLevel = 1;
    brightnessLevel = 100;
    panOffsetX = 0;
    panOffsetY = 0;

    const lightbox = document.getElementById('lightbox');
    lightbox.classList.remove('hidden');

    showLightboxImage();
    setupLightboxEventListeners();
}

function closeLightbox() {
    lightboxOpen = false;
    const lightbox = document.getElementById('lightbox');
    lightbox.classList.add('hidden');
}

async function showLightboxImage() {
    let image, cluster;
    const isUngrouped = currentCluster >= clusters.length;
    
    if (isUngrouped) {
        image = ungroupedImages[lightboxImageIndex];
    } else {
        cluster = clusters[currentCluster];
        if (!cluster) return;
        image = cluster.images[lightboxImageIndex];
    }

    const lightboxImg = document.getElementById('lightboxImage');
    const filenameElem = document.querySelector('.lightbox-filename');
    const imageNumElem = document.getElementById('lightboxImageNum');
    const colorPickerElem = document.getElementById('lightboxColorPicker');
    const exifElemHeader = document.getElementById('lightboxExifHeader');
    const exifElemFooter = document.getElementById('lightboxExif');

    // Update image
    if (isUngrouped) {
        lightboxImg.src = `/api/ungrouped/${lightboxImageIndex}`;
    } else {
        lightboxImg.src = `/api/image/${currentCluster}/${lightboxImageIndex}`;
    }
    lightboxImg.style.transform = `scale(${zoomLevel}) translate(${panOffsetX}px, ${panOffsetY}px)`;
    lightboxImg.style.filter = `brightness(${brightnessLevel}%)`;

    // Update filename
    filenameElem.textContent = image.filename;

    // Update image number
    const totalImages = isUngrouped ? ungroupedImages.length : cluster.images.length;
    imageNumElem.textContent = `${lightboxImageIndex + 1} of ${totalImages}`;

    // Update zoom level display
    document.querySelector('.lightbox-zoom-level').textContent = `${Math.round(zoomLevel * 100)}%`;

    // Update brightness level display
    document.querySelector('.lightbox-brightness-level').textContent = `${brightnessLevel}%`;

    // Update color picker
    colorPickerElem.innerHTML = '';
    const picker = createColorPicker(image, lightboxImageIndex);
    picker.classList.remove('color-picker');
    picker.className = 'color-picker';
    colorPickerElem.appendChild(picker);

    // Load and display EXIF data
    try {
        let exifResponse;
        if (isUngrouped) {
            exifResponse = await fetch(`/api/ungrouped/exif/${lightboxImageIndex}`);
        } else {
            exifResponse = await fetch(`/api/exif/${currentCluster}/${lightboxImageIndex}`);
        }
        
        if (exifResponse.ok) {
            const exif = await exifResponse.json();
            console.log('EXIF data received:', exif); // Debug logging
            displayExifData(exif, exifElemHeader, exifElemFooter);
        } else {
            console.error('EXIF request failed:', exifResponse.status);
            exifElemHeader.innerHTML = '<span style="color: #888;">No EXIF data available</span>';
        }
    } catch (error) {
        console.error('Error loading EXIF data:', error);
        exifElemHeader.innerHTML = '<span style="color: #888;">Error loading EXIF</span>';
    }
}

function displayExifData(exif, containerHeader, containerFooter) {
    containerHeader.innerHTML = '';
    if (containerFooter) containerFooter.innerHTML = '';

    const fields = [
        { key: 'iso', label: 'ISO' },
        { key: 'shutter_speed', label: 'Shutter' },
        { key: 'aperture', label: 'Aperture' },
        { key: 'focal_length', label: 'Focal' },
        { key: 'exposure_bias', label: 'Exp Comp' }
    ];

    let hasData = false;

    fields.forEach(field => {
        if (exif[field.key]) {
            hasData = true;
            const item = document.createElement('div');
            item.className = 'exif-item';

            const label = document.createElement('div');
            label.className = 'exif-label';
            label.textContent = field.label;

            const value = document.createElement('div');
            value.className = 'exif-value';
            value.textContent = exif[field.key];

            item.appendChild(label);
            item.appendChild(value);
            containerHeader.appendChild(item);
        }
    });

    if (!hasData) {
        console.log('No EXIF fields found in data:', exif);
        containerHeader.innerHTML = '<span style="color: #ff9800; font-size: 0.9rem;">⚠ No EXIF data found in file</span>';
    }
}

function setZoom(newZoom) {
    zoomLevel = Math.max(0.5, Math.min(5, newZoom));

    // Reset pan if zoomed out
    if (zoomLevel <= 1) {
        panOffsetX = 0;
        panOffsetY = 0;
    }

    showLightboxImage();
}

function fitToScreen() {
    zoomLevel = 1;
    brightnessLevel = 100;
    panOffsetX = 0;
    panOffsetY = 0;
    showLightboxImage();
}

function setBrightness(newBrightness) {
    brightnessLevel = Math.max(20, Math.min(200, newBrightness));
    const lightboxImg = document.getElementById('lightboxImage');
    lightboxImg.style.filter = `brightness(${brightnessLevel}%)`;
    document.querySelector('.lightbox-brightness-level').textContent = `${brightnessLevel}%`;
}

function lightboxPrevImage() {
    const isUngrouped = currentCluster >= clusters.length;
    const totalImages = isUngrouped ? ungroupedImages.length : clusters[currentCluster].images.length;

    lightboxImageIndex = (lightboxImageIndex - 1 + totalImages) % totalImages;
    zoomLevel = 1;
    brightnessLevel = 100;
    panOffsetX = 0;
    panOffsetY = 0;
    showLightboxImage();
}

function lightboxNextImage() {
    const isUngrouped = currentCluster >= clusters.length;
    const totalImages = isUngrouped ? ungroupedImages.length : clusters[currentCluster].images.length;

    lightboxImageIndex = (lightboxImageIndex + 1) % totalImages;
    zoomLevel = 1;
    brightnessLevel = 100;
    panOffsetX = 0;
    panOffsetY = 0;
    showLightboxImage();
}

function setupLightboxEventListeners() {
    const lightboxImg = document.getElementById('lightboxImage');
    const container = document.querySelector('.lightbox-image-container');

    // Brightness buttons
    document.getElementById('brightnessUp').onclick = () => setBrightness(brightnessLevel + 10);
    document.getElementById('brightnessDown').onclick = () => setBrightness(brightnessLevel - 10);

    // Zoom buttons
    document.getElementById('zoomIn').onclick = () => setZoom(zoomLevel * 1.2);
    document.getElementById('zoomOut').onclick = () => setZoom(zoomLevel / 1.2);
    document.getElementById('fitScreen').onclick = fitToScreen;
    document.getElementById('closeLightbox').onclick = closeLightbox;

    // Navigation buttons
    document.getElementById('lightboxPrev').onclick = lightboxPrevImage;
    document.getElementById('lightboxNext').onclick = lightboxNextImage;

    // Mouse wheel zoom
    container.onwheel = (e) => {
        e.preventDefault();
        const delta = e.deltaY > 0 ? 0.9 : 1.1;
        setZoom(zoomLevel * delta);
    };

    // Pan functionality
    container.onmousedown = (e) => {
        if (zoomLevel > 1) {
            isPanning = true;
            panStartX = e.clientX - panOffsetX;
            panStartY = e.clientY - panOffsetY;
            container.classList.add('grabbing');
        }
    };

    container.onmousemove = (e) => {
        if (isPanning) {
            panOffsetX = e.clientX - panStartX;
            panOffsetY = e.clientY - panStartY;
            lightboxImg.style.transform = `scale(${zoomLevel}) translate(${panOffsetX}px, ${panOffsetY}px)`;
        }
    };

    container.onmouseup = () => {
        isPanning = false;
        container.classList.remove('grabbing');
    };

    container.onmouseleave = () => {
        isPanning = false;
        container.classList.remove('grabbing');
    };
}

// Start the application
init();
