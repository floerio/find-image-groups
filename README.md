# Find Image Groups

A Python tool to find and organize similar Fuji RAW images using perceptual hashing and intelligent clustering. 

## Features

- Processes Fuji RAW (.RAF) files directly using optimized Python libraries
- Uses perceptual hashing for fast, effective similarity detection
- **Automatically clusters similar images into groups**
- **Hybrid architecture: Python backend + Web frontend**
- **Interactive web-based viewer with smooth navigation**
- Alternative matplotlib viewer for offline use
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

Basic usage:
```bash
python fuji_similarity.py /path/to/photos
```

With custom threshold (lower = more strict):
```bash
python fuji_similarity.py /path/to/photos --threshold 5
```

With higher precision:
```bash
python fuji_similarity.py /path/to/photos --hash-size 16 --threshold 8
```

Show individual pairs instead of clusters:
```bash
python fuji_similarity.py /path/to/photos --no-cluster
```

**Launch web-based viewer (recommended):**
```bash
python fuji_similarity.py /path/to/photos --web-viewer
```

This starts a local web server and opens a browser interface. Better performance and smoother UI than the matplotlib viewer.

**Launch matplotlib viewer (offline):**
```bash
python fuji_similarity.py /path/to/photos --viewer
```

Both viewers display images in each group side-by-side and support keyboard navigation.

### Options

- `directory` - Directory containing Fuji RAF files (required)
- `-t, --threshold` - Similarity threshold (0-64, default: 10). Lower values require more similarity.
- `-s, --hash-size` - Hash size for comparison (default: 8). Larger values give more precision but take longer.
- `--no-cluster` - Disable clustering and show individual pairs instead of grouped results.
- `-w, --web-viewer` - Launch web-based viewer (recommended - better UI and performance).
- `-v, --viewer` - Launch matplotlib viewer (alternative, works offline).
- `-p, --port` - Port for web viewer (default: 5000).
- `--no-cache` - Disable hash caching (recompute all hashes).
- `--no-parallel` - Disable parallel processing (slower but uses less memory).
- `--show-ungrouped` - Show images that are not part of any similar group.

## How It Works

1. **RAW Processing**: Reads RAF files using `rawpy` and converts them to RGB images
2. **Perceptual Hashing**: Computes an average hash for each image that captures its visual structure
3. **Comparison**: Compares all image pairs using Hamming distance between their hashes
4. **Clustering**: Groups similar images together using union-find algorithm (transitive similarity)
5. **Results**: Reports groups of similar images with detailed similarity information

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
- **, / .** keys - Decrease/increase brightness (20%-200%)
- **Space** - Reset zoom and brightness to 100%
- **Click and drag** - Pan when zoomed
- **Arrow keys** - Navigate between images (or pan when zoomed with Shift/Ctrl)
- **ESC** - Close lightbox
- **1-8 keys** - Tag color while in lightbox view
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

### Matplotlib Viewer (Offline Alternative)

A desktop viewer using matplotlib. Works without internet/browser but with simpler UI.

**Controls:**
- `→` or `N` - Next group (cycles through all groups including ungrouped)
- `←` or `P` - Previous group (cycles through all groups including ungrouped)
- `Q` or `ESC` - Quit

**Usage:**
```bash
python fuji_similarity.py /path/to/photos --viewer
```

**With ungrouped images:**
```bash
python fuji_similarity.py /path/to/photos --viewer --show-ungrouped
```

## Requirements

- Python 3.8+
- rawpy (for reading RAF files - wraps libraw C++ library)
- Pillow (image processing)
- imagehash (perceptual hashing)
- numpy (array operations)
- tqdm (progress bars)
- flask (web server for hybrid viewer)
- matplotlib (offline matplotlib viewer)

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

# Matplotlib viewer with ungrouped images  
python fuji_similarity.py /path/to/photos --viewer --show-ungrouped
```

## Performance Features

**Hash Caching:**
- First run: Computes hashes for all RAF files
- Subsequent runs: Loads hashes from `.fuji_similarity_cache.json`
- Only reprocesses files that have changed (checks file size + modification time)
- Instant re-runs with different thresholds
- Cache auto-updates when files are added/changed

**Parallel Processing:**
- Uses all CPU cores to process multiple RAF files simultaneously
- 4-8x faster on multi-core systems
- Automatically scales to available cores
- Can be disabled with `--no-parallel` if needed

**Auto-open Browser:**
- Web viewer automatically opens in your default browser
- No need to copy/paste URLs
- Just run the command and start tagging!

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
- The tool uses half-size RAW processing for speed while maintaining accuracy for similarity detection
- Perceptual hashing is resistant to minor edits like resizing, slight color adjustments, and compression
- Processing time depends on the number of files and hash size setting
- Web viewer converts RAW to JPEG for browser display (max 1920px wide)
- Cache file stores hash strings with file signatures for validation

**Example Workflow:**
```bash
# First run: Processes 100 RAF files (takes ~3 minutes on 8-core CPU)
python fuji_similarity.py /path/to/photos --web-viewer

# Browser opens automatically
# Review groups, tag images with keyboard shortcuts (1-8)
# Press TAB to focus next image, number key to tag, repeat!
# Click any image to zoom and inspect details
# Use mouse wheel to zoom in/out, click-drag to pan
# Tag colors even while in zoom view

# Second run with different threshold: Instant! (uses cache)
python fuji_similarity.py /path/to/photos --web-viewer --threshold 5

# Import into Capture One with color tags preserved
```
