# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Find Image Groups** - A hybrid Python/JavaScript tool that compares Fuji RAW files (.RAF) to identify similar images using DINOv2 deep learning embeddings.

**Architecture:**
- **Python backend**: RAW processing, DINOv2 embedding generation, clustering, and comparison
- **JavaScript/Web frontend**: Interactive viewer with smooth UI
- Combines Python's AI-powered similarity detection with JavaScript's UI capabilities
- GPU-accelerated when available (CUDA or Apple Silicon MPS)

## Development Setup

Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Tool

Ensure virtual environment is activated first:
```bash
source venv/bin/activate
```

Basic usage (uses default directory: /Users/ofloericke/images):
```bash
python find-image-groups.py
```

With custom directory:
```bash
python find-image-groups.py /path/to/photos
```

With custom parameters:
```bash
python find-image-groups.py /path/to/photos --threshold 0.90 --max-size 768
```

With web viewer:
```bash
python find-image-groups.py --web-viewer
```

## Architecture

**Core Components:**
- `find-image-groups.py` - Main CLI and image processing logic
- `web_viewer.py` - Flask web server for hybrid viewer
- `templates/viewer.html` - Web UI template
- `static/js/viewer.js` - Client-side JavaScript for navigation
- `static/css/viewer.css` - Styling

**Python Backend (`find-image-groups.py`):**
- `ImageSimilarityFinder` class handles all image processing and comparison logic
  - `load_image_file()` - Uses rawpy for RAW files or PIL for standard images, with resizing for performance
  - `compute_embedding()` - Generates DINOv2 embeddings using transformer model
  - `process_directory()` - Batch processes all image files in a directory (sequential for GPU optimization)
  - `find_similar_images()` - Compares all image pairs using cosine similarity
  - `cluster_similar_images()` - Groups similar images using union-find (transitive) or direct similarity algorithm
  - `cluster_similar_images_direct()` - Direct similarity clustering (no transitive grouping)
  - `print_clustered_results()` - Displays grouped results (default)
  - `print_results()` - Displays individual pairs (legacy mode with --no-cluster)
- `main()` - CLI interface using argparse

**Web Viewer (`web_viewer.py`):**
- `WebViewer` class provides Flask-based web server
  - `_setup_routes()` - Configures Flask API endpoints
  - `/api/clusters` - Returns cluster metadata as JSON with current color tags
  - `/api/colors` - Returns available Capture One color labels
  - `/api/color/<cluster_id>/<image_id>` - POST endpoint to set color tag
  - `/api/image/<cluster_id>/<image_id>` - Serves processed images as JPEG
  - `/api/exif/<cluster_id>/<image_id>` - Returns EXIF data for image
  - `read_color_tag()` - Reads xmp:Label from XMP sidecar files
  - `write_color_tag()` - Updates or creates XMP sidecar with color tag
  - `get_exif_data()` - Extracts EXIF data from RAF files (ISO, shutter, aperture, focal length, etc.)
  - `get_xmp_path()` - Resolves XMP path from RAF path
  - Image caching to avoid reprocessing on navigation
  - Automatic image resizing for web display (max 1920px)
  - XMP metadata preservation when updating color tags

**Frontend (`static/js/viewer.js`):**
- Fetches cluster data and color options from API
- Renders image grid dynamically with color pickers
- Handles keyboard navigation and shortcuts
- Displays similarity percentages
- `createColorPicker()` - Renders color tag buttons for each image
- `setImageColor()` - Updates color via API and reflects in UI
- `focusImage()` - Manages focused image state for keyboard tagging
- `tagFocusedImage()` - Tags focused image and auto-advances
- **Lightbox zoom viewer**:
  - `openLightbox()` - Opens fullscreen image viewer
  - `showLightboxImage()` - Updates lightbox display with current image and EXIF data
  - `displayExifData()` - Renders EXIF information (ISO, shutter, aperture, focal length, exposure comp)
  - `setZoom()` - Handles zoom level (0.5x to 5x)
  - `fitToScreen()` - Resets zoom to 100%
  - Mouse wheel zoom, click-drag panning
  - Keyboard navigation in lightbox mode
  - Color tagging available in lightbox
  - EXIF data fetched and displayed for each image
- Color buttons show selected state with checkmark and green border
- Focused image highlighted with green border
- Keyboard shortcuts: 1-8 for colors, TAB for focus navigation, click for zoom

**Similarity detection approach**:
- Uses DINOv2 deep learning embeddings for semantic similarity
- Cosine similarity between embeddings determines similarity
- Higher similarity = more similar (threshold default: 0.85, range: 0.0-1.0)
- Model options: dinov2-small, dinov2-base (default), dinov2-large, dinov2-giant
- GPU-accelerated when CUDA or Apple Silicon MPS is available

**Clustering algorithms**:
- **Transitive clustering** (default): Uses union-find algorithm. If A~B and B~C, all three are grouped together even if A and C aren't directly similar. Good for finding "families" of related images.
- **Direct similarity clustering** (--direct-only): Groups only contain images that are ALL directly similar to each other. Results in tighter, more coherent groups. Better for finding exact duplicates or near-duplicates.
- Clusters sorted by size (largest first) for better output readability

**Performance considerations**:
- RAW files processed at half-size and resized (default 512px) for speed while maintaining similarity accuracy
- Sequential processing for GPU optimization (parallel processing doesn't benefit GPU workloads)
- Embedding caching system stores computed embeddings with file signatures
- Cache validation checks file size and modification time
- GPU acceleration significantly speeds up embedding generation
- O(n²) comparison complexity - all pairs compared using vectorized cosine similarity
- Progress bars via tqdm for user feedback on long operations

**XMP Sidecar Integration**:
- Color tags written to `<xmp:Label>` field in XMP sidecar files
- Compatible with Capture One color labels: None, Red, Orange, Yellow, Green, Blue, Purple, Pink
- Preserves all existing XMP metadata (creator, keywords, rating, etc.)
- Creates minimal XMP if none exists
- XMP files have same basename as RAF: `DSCF1234.RAF` → `DSCF1234.xmp`

## Key Parameters

- `--threshold`: Cosine similarity threshold (0.0-1.0). Higher = stricter matching. Default: 0.85
- `--max-size`: Maximum image size for DINOv2 processing. Smaller = faster. Default: 512
- `--model`: DINOv2 model variant (facebook/dinov2-small, facebook/dinov2-base, facebook/dinov2-large, facebook/dinov2-giant). Default: facebook/dinov2-base
- `--no-cluster`: Disable clustering, show individual pairs instead (legacy mode)
- `--web-viewer`: Launch web-based viewer
- `--port`: Port for web server. Default: 5000
- `--no-cache`: Disable embedding caching (forces recomputation)
- `--no-parallel`: Disable parallel processing (already disabled by default for GPU optimization)
- `--direct-only`: Use direct similarity clustering (no transitive grouping). Groups only contain images ALL directly similar to each other.

## Dependencies

- `rawpy`: RAF file reading and RAW processing (wraps libraw C++ library)
- `torch`: PyTorch for deep learning and GPU acceleration
- `transformers`: Hugging Face transformers library for DINOv2 model
- `scikit-learn`: Cosine similarity computation
- `Pillow`: Image manipulation after RAW processing
- `numpy`: Array operations
- `tqdm`: Progress bar display
- `flask`: Web server for web viewer
