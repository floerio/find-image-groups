# Find Image Groups

A Python tool to find and organize similar images using DINOv2 deep learning embeddings and intelligent clustering.

## Features

- **Multi-format support**: RAW (RAF, NEF, ARW, CR2, CR3, etc.) and standard (JPG, PNG, TIFF, BMP)
- **DINOv2 AI-powered similarity detection**: Semantic understanding of image content
- **GPU acceleration**: CUDA and Apple Silicon MPS support
- **Automatically clusters similar images into groups**
- **Two clustering modes**: Transitive (loose) or Direct-only (tight)
- **Hybrid architecture: Python backend + Web frontend**
- **Interactive web-based viewer with smooth navigation**
- Adjustable similarity threshold
- Progress bars for large collections
- Clear output showing similarity percentages and groupings

## Installation

1. Clone or download this repository
2. Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Make sure your virtual environment is activated:
```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Basic usage (uses default directory `/Users/ofloericke/images`):
```bash
python find-image-groups.py --web-viewer
```

With custom directory:
```bash
python find-image-groups.py /path/to/photos --web-viewer
```

With custom threshold (higher = more strict, range 0.0-1.0):
```bash
python find-image-groups.py /path/to/photos --threshold 0.90 --web-viewer
```

With direct-only clustering (tighter groups):
```bash
python find-image-groups.py /path/to/photos --direct-only --web-viewer
```

Show individual pairs instead of clusters:
```bash
python find-image-groups.py /path/to/photos --no-cluster
```

**Launch web-based viewer:**
```bash
python find-image-groups.py /path/to/photos --web-viewer
```

This starts a local web server and opens a browser interface with smooth navigation, color tagging, and EXIF data display.

### Options

- `directory` - Directory containing image files (optional, default: `/Users/ofloericke/images`)
- `-t, --threshold` - Cosine similarity threshold (0.0-1.0, default: 0.85). Higher values require more similarity.
- `--max-size` - Maximum image size for DINOv2 (default: 512). Smaller = faster.
- `--model` - DINOv2 model variant (dinov2-small/base/large/giant, default: base).
- `--no-cluster` - Disable clustering and show individual pairs instead of grouped results.
- `-do, --direct-only` - Use direct similarity clustering (tighter groups, no transitive).
- `-w, --web-viewer` - Launch web-based viewer.
- `-p, --port` - Port for web viewer (default: 5020).
- `--no-cache` - Disable embedding caching (recompute all embeddings).
- `--no-parallel` - Disable parallel processing (already disabled by default for GPU).
- `-ug, --show-ungrouped` - Show images that are not part of any similar group.

## How It Works

1. **Image Loading**: Reads RAW files (RAF, NEF, ARW, CR2, etc.) using `rawpy` or standard images (JPG, PNG) using PIL
2. **DINOv2 Embeddings**: Computes deep learning embeddings that capture semantic image content
3. **GPU Acceleration**: Uses CUDA or Apple Silicon MPS if available for faster processing
4. **Comparison**: Compares all image pairs using cosine similarity between embeddings
5. **Clustering**: Groups similar images using union-find (transitive) or direct similarity algorithm
6. **Results**: Reports groups of similar images with detailed similarity information

## Use Cases

- Finding duplicate or near-duplicate shots from burst mode
- **Zoom in to inspect details and choose the sharpest image from a burst**
- **Compare camera settings (ISO, shutter, aperture) between similar shots**
- Identifying similar compositions from a photo session
- **Tagging keeper images vs. rejects while reviewing similar shots**
- Cleaning up large photo libraries
- Finding bracketed exposures with EXIF confirmation
- **Organizing images for import into Capture One with pre-applied color tags**
- **Compare exposure/focus differences by zooming into similar images**
- **Reviewing ungrouped images to find unique shots that don't have similar counterparts**

## Example Output

```
Found 25 RAF files. Processing...
Computing hashes: 100%|██████████| 25/25 [00:15<00:00,  1.62it/s]

Comparing 25 images...

================================================================================
Found 2 group(s) of similar images:
Total: 5 images in 4 similar pair(s)
================================================================================

Group 1: 3 similar image(s)
--------------------------------------------------------------------------------
  • DSCF1234.RAF
  • DSCF1235.RAF
  • DSCF1236.RAF

  Similarities within group:
    DSCF1234.RAF ↔ DSCF1235.RAF
      Similarity: 95.3% (distance: 3)
    DSCF1234.RAF ↔ DSCF1236.RAF
      Similarity: 92.8% (distance: 4)
    DSCF1235.RAF ↔ DSCF1236.RAF
      Similarity: 94.1% (distance: 3)

Group 2: 2 similar image(s)
--------------------------------------------------------------------------------
  • DSCF1250.RAF
  • DSCF1251.RAF

  Similarities within group:
    DSCF1250.RAF ↔ DSCF1251.RAF
      Similarity: 87.5% (distance: 8)
```

## Interactive Viewers

### Web Viewer (Recommended)

**Hybrid Architecture:**
- **Python backend**: Fast RAW processing with rawpy/libraw (C++)
- **JavaScript frontend**: Smooth, responsive web interface

**Features:**
- Modern, responsive web UI
- Smooth image loading with caching
- Grid layout with hover effects
- **Lightbox zoom viewer for detailed inspection**
- **Color tagging for Capture One integration**
- Detailed similarity information
- **Ungrouped images section** - View images that don't have similar counterparts
- Works in any modern browser

**Navigation:**
- `→` or `D` or `N` - Next group (cycles through all groups including ungrouped)
- `←` or `A` or `P` - Previous group (cycles through all groups including ungrouped)
- `Q` or `ESC` - Close window
- Click navigation buttons

**Image Zoom/Inspection:**
- **Click any image** to open fullscreen lightbox
- **Mouse wheel** - Zoom in/out
- **+/-** keys - Zoom in/out
- **Y/X** keys - Decrease/increase brightness (20%-200%) - **Works on all keyboards!**
- **, / .** keys - Alternative brightness control (US layout)
- **; / :** keys - Alternative brightness control (German layout)
- **Space** - Reset zoom and brightness to 100%
- **Click and drag** - Pan when zoomed
- **Arrow keys** - Navigate between images (or pan when zoomed with Shift/Ctrl)
- **ESC** - Close lightbox
- **1-8 keys** - Tag color while in lightbox view

**Online Threshold Adjustment:**
- **←/→ buttons** - Decrease/increase similarity threshold
- **Apply button** - Re-cluster images with new threshold
- **Real-time feedback** - See new grouping results instantly
- **Range: 1-64** - Lower = more similar required, Higher = less similar required
- **Status display** - Shows number of groups and ungrouped images after re-clustering
- **No restart needed** - Fine-tune grouping without restarting the application

**Color Filter (Main Grid):**
- **Color filter buttons** - Click to hide images with specific color tags
- **Multi-color filtering** - Filter by multiple colors simultaneously
- **Visual feedback** - Filtered images disappear from grid instantly
- **Clear filter button** - Reset to show all images
- **Live count** - Shows visible/total images (e.g., "5/8 visible")
- **Persistent filtering** - Filter stays active during navigation
- **Use case**: Hide rejected images (e.g., Red) to focus on keepers
- **Location**: Main interface, below threshold controls

**Workflow Example:**
1. Tag some images as Red (rejected) using keyboard shortcuts
2. Click the Red filter button in main interface
3. All Red-tagged images disappear from grid
4. Focus only on unfiltered images for final selection
5. Click "✕ Clear" when done to see all images again
- **EXIF data displayed**: ISO, shutter speed, aperture, focal length, exposure compensation
- **Brightness control**: Perfect for checking shadow detail and highlight clipping
- Inspect fine details to choose between similar shots

**Color Tagging (Fast Workflow!):**
- **Keyboard Shortcuts**: Press `1-8` to tag the focused image
  - `1` = None, `2` = Red, `3` = Orange, `4` = Yellow
  - `5` = Green, `6` = Blue, `7` = Purple, `8` = Pink
- **Focus Navigation**:
  - `TAB` - Focus next image
  - `SHIFT+TAB` - Focus previous image
  - Auto-advances to next image after tagging
- **Mouse**: Click color dots below any image
- Each image has 8 color tag options matching Capture One's color labels
- Tags are saved to XMP sidecar files (`.xmp`) next to RAF files
- Tags persist and can be imported into Capture One
- Existing XMP metadata is preserved when updating tags
- Visual feedback shows currently selected color
- Focused image has green border

**Usage:**
```bash
python fuji_similarity.py /path/to/photos --web-viewer
```

**With ungrouped images:**
```bash
python fuji_similarity.py /path/to/photos --web-viewer --show-ungrouped
```

Opens `http://localhost:5000` in your browser automatically.

## Requirements

- Python 3.8+
- rawpy (for reading RAW files - wraps libraw C++ library)
- Pillow (image processing)
- torch (PyTorch for DINOv2 and GPU acceleration)
- torchvision (required by transformers)
- transformers (Hugging Face library for DINOv2 model)
- scikit-learn (cosine similarity computation)
- numpy (array operations)
- tqdm (progress bars)
- flask (web server for web viewer)

## DINOv2 Models Explained

**Different model sizes for different use cases:**

- **`dinov2-small`**: Fastest, uses least memory. Good for quick processing of large collections.
- **`dinov2-base` (default)**: Balanced speed and accuracy. Best for most use cases.
- **`dinov2-large`**: Higher accuracy, slower processing. Better semantic understanding.
- **`dinov2-giant`**: Most accurate but slowest and requires more GPU memory.

**When to use which:**
- **Large collections (1000+ images)**: `dinov2-small` (fastest)
- **General use**: `dinov2-base` (default, balanced)
- **Best accuracy**: `dinov2-large` (more precise)
- **Research/maximum quality**: `dinov2-giant` (if you have powerful GPU)

**Example usage:**
```bash
# Use larger model for better accuracy
python find-image-groups.py /path/to/photos --model facebook/dinov2-large

# Use smaller model for speed
python find-image-groups.py /path/to/photos --model facebook/dinov2-small --max-size 384
```

## Ungrouped Images Feature

**What are ungrouped images?**
- Images that don't have any similar counterparts based on the current threshold
- Unique shots that don't match any other images in your collection
- Often the most distinctive or creative images from your session

**Why view ungrouped images?**
- **Find hidden gems**: Discover unique shots that might be your best work
- **Complete review**: Ensure no image is overlooked in your workflow
- **Quality control**: Check if these images are truly unique or just failed to match
- **Creative insights**: See which compositions stand out as completely different

**How to use:**
- Add `--show-ungrouped` flag to any viewer command
- Ungrouped images appear as an additional "group" at the end
- Navigation cycles through all groups including ungrouped
- Full functionality: zoom, color tagging, EXIF data, etc.
- Console output shows list of ungrouped filenames

**Example:**
```bash
# Console output with ungrouped images
python fuji_similarity.py /path/to/photos --show-ungrouped

# Web viewer with ungrouped images
python fuji_similarity.py /path/to/photos --web-viewer --show-ungrouped
```

## Performance Features

**Embedding Caching:**
- First run: Computes DINOv2 embeddings for all image files
- Subsequent runs: Loads embeddings from `.fuji_similarity_dinov2_cache.json`
- Only reprocesses files that have changed (checks file size + modification time)
- Instant re-runs with different thresholds or clustering modes
- Cache auto-updates when files are added/changed

**GPU Acceleration:**
- Automatically uses CUDA (NVIDIA) or MPS (Apple Silicon) if available
- Significantly faster than CPU-only processing
- Falls back to CPU if no GPU detected
- Sequential processing optimized for GPU workloads

**Auto-open Browser:**
- Web viewer automatically opens in your default browser
- No need to copy/paste URLs
- Just run the command and start tagging!

## Keyboard Layout Support

**International Keyboard Support:**
- **US Keyboard**: Use `,` (comma) and `.` (period) for brightness control
- **German Keyboard**: Use `;` (semicolon) and `:` (colon) for brightness control
- **Other Layouts**: Both key sets work simultaneously

**How it works:**
- **Primary keys**: `Y` (darker) and `X` (brighter) - **Works on ALL keyboard layouts!**
- **Alternative keys**: `,`/`.` (US) and `;`/`:` (German) for user preference
- The web viewer detects key presses and handles multiple key mappings
- No configuration needed - all keys work simultaneously

**Troubleshooting:**
If brightness control doesn't work, try:
1. **Use Y/X keys** - These work on all keyboards!
2. Use the on-screen buttons (☀− and ☀+)
3. Try alternative keys based on your layout
4. Check if your browser has keyboard shortcuts that might interfere
5. Use mouse wheel for zoom, spacebar to reset

## Architecture Notes

**Why Hybrid?**
- **Python backend**: Fastest RAW processing via libraw (C++)
- **JavaScript frontend**: Best user experience for interactive viewing
- Combines strengths of both ecosystems

**Performance:**
- RAW processing: ~1-2 seconds per image (Python/rawpy)
- Parallel processing: 4-8x faster with multiprocessing
- Hash caching: Near-instant for unchanged files
- Comparison: O(n²) but fast with numpy
- Web viewer: Images cached after first load
- JavaScript would be 5-10x slower for RAW processing

**Technical Details:**
- The tool uses half-size RAW processing and image resizing for speed while maintaining accuracy
- DINOv2 embeddings capture semantic similarity, not just pixel-level similarity
- Processing time depends on the number of files, image size, and GPU availability
- Web viewer converts images to JPEG for browser display (max 1920px wide)
- Cache file stores embeddings with file signatures for validation

**Example Workflow:**
```bash
# First run: Processes 100 image files (takes ~2-3 minutes with GPU)
python find-image-groups.py /path/to/photos --web-viewer --direct-only

# Browser opens automatically
# Review groups, tag images with keyboard shortcuts (1-8)
# Press TAB to focus next image, number key to tag, repeat!
# Click any image to zoom and inspect details
# Use mouse wheel to zoom in/out, click-drag to pan
# Tag colors even while in zoom view

# Second run with different threshold: Instant! (uses cache)
python find-image-groups.py /path/to/photos --web-viewer --threshold 0.92

# Third run with different clustering mode: Also instant!
python find-image-groups.py /path/to/photos --web-viewer

# Import into Capture One with color tags preserved
```
