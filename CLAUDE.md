# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hybrid Python/JavaScript tool that compares Fuji RAW files (.RAF) to identify similar images using perceptual hashing.

**Architecture:**
- **Python backend**: RAW processing, hashing, clustering, and comparison
- **JavaScript/Web frontend**: Interactive viewer with smooth UI
- Combines Python's speed for RAW processing with JavaScript's UI capabilities

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

Basic usage:
```bash
python fuji_similarity.py /path/to/photos
```

With custom parameters:
```bash
python fuji_similarity.py /path/to/photos --threshold 5 --hash-size 16
```

With web viewer (recommended):
```bash
python fuji_similarity.py /path/to/photos --web-viewer
```

With matplotlib viewer (offline):
```bash
python fuji_similarity.py /path/to/photos --viewer
```

## Architecture

**Core Components:**
- `fuji_similarity.py` - Main CLI and image processing logic
- `web_viewer.py` - Flask web server for hybrid viewer
- `templates/viewer.html` - Web UI template
- `static/js/viewer.js` - Client-side JavaScript for navigation
- `static/css/viewer.css` - Styling

**Python Backend (`fuji_similarity.py`):**
- `ImageSimilarityFinder` class handles all image processing and comparison logic
  - `load_raw_file()` - Uses rawpy to process RAF files with half-size rendering for performance
  - `compute_hash()` - Generates perceptual hash using average hash algorithm
  - `process_directory()` - Batch processes all RAF files in a directory
  - `find_similar_images()` - Compares all image pairs using Hamming distance
  - `cluster_similar_images()` - Groups similar images using union-find algorithm for transitive similarity
  - `print_clustered_results()` - Displays grouped results (default)
  - `print_results()` - Displays individual pairs (legacy mode with --no-cluster)
- `ClusterViewer` class provides interactive matplotlib-based viewer
  - `load_image_cached()` - Caches loaded images to avoid reprocessing
  - `show_cluster()` - Displays a cluster in a grid layout with similarity info
  - `on_key()` - Handles keyboard navigation (arrow keys, Q to quit)
  - `run()` - Main viewer loop with matplotlib event handling
- `main()` - CLI interface using argparse

**Web Viewer (`web_viewer.py`):**
- `WebViewer` class provides Flask-based web server
  - `_setup_routes()` - Configures Flask API endpoints
  - `/api/clusters` - Returns cluster metadata as JSON with current color tags
  - `/api/colors` - Returns available Capture One color labels
  - `/api/color/<cluster_id>/<image_id>` - POST endpoint to set color tag
  - `/api/image/<cluster_id>/<image_id>` - Serves processed images as JPEG
  - `read_color_tag()` - Reads xmp:Label from XMP sidecar files
  - `write_color_tag()` - Updates or creates XMP sidecar with color tag
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
- Color buttons show selected state with checkmark and green border
- Focused image highlighted with green border
- Keyboard shortcuts: 1-8 for colors, TAB for focus navigation

**Similarity detection approach**:
- Uses perceptual hashing (average hash) rather than pixel-by-pixel comparison
- Hamming distance between hashes determines similarity
- Lower distance = more similar (threshold default: 10, range: 0-64)
- Hash size default: 8x8 (can be increased for precision at cost of speed)

**Clustering algorithm**:
- Uses union-find (disjoint set) data structure for efficient grouping
- If A is similar to B, and B is similar to C, all three are grouped together
- Handles transitive similarity: images don't need to be directly similar to be in same cluster
- Clusters sorted by size (largest first) for better output readability

**Performance considerations**:
- RAW files processed at half-size for speed while maintaining similarity accuracy
- Parallel processing using multiprocessing.Pool for concurrent RAW loading
- Hash caching system stores computed hashes with file signatures
- Cache validation checks file size and modification time
- O(n²) comparison complexity - all pairs compared
- Progress bars via tqdm for user feedback on long operations

**XMP Sidecar Integration**:
- Color tags written to `<xmp:Label>` field in XMP sidecar files
- Compatible with Capture One color labels: None, Red, Orange, Yellow, Green, Blue, Purple, Pink
- Preserves all existing XMP metadata (creator, keywords, rating, etc.)
- Creates minimal XMP if none exists
- XMP files have same basename as RAF: `DSCF1234.RAF` → `DSCF1234.xmp`

## Key Parameters

- `--threshold`: Hamming distance threshold (0-64). Lower = stricter matching. Default: 10
- `--hash-size`: Perceptual hash dimensions (e.g., 8 = 8x8 = 64 bits). Higher = more precision. Default: 8
- `--no-cluster`: Disable clustering, show individual pairs instead (legacy mode)
- `--web-viewer`: Launch web-based viewer (recommended)
- `--viewer`: Launch matplotlib viewer (offline alternative)
- `--port`: Port for web server. Default: 5000
- `--no-cache`: Disable hash caching (forces recomputation)
- `--no-parallel`: Disable parallel processing

## Dependencies

- `rawpy`: RAF file reading and RAW processing (wraps libraw C++ library)
- `imagehash`: Perceptual hash computation
- `Pillow`: Image manipulation after RAW processing
- `numpy`: Array operations (dependency of rawpy)
- `tqdm`: Progress bar display
- `flask`: Web server for hybrid viewer
- `matplotlib`: Offline matplotlib viewer
