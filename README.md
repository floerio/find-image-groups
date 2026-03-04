# Fuji RAW Similarity Finder

A simple Python tool to compare Fuji RAW files (.RAF) and find similar images using perceptual hashing.

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

## How It Works

1. **RAW Processing**: Reads RAF files using `rawpy` and converts them to RGB images
2. **Perceptual Hashing**: Computes an average hash for each image that captures its visual structure
3. **Comparison**: Compares all image pairs using Hamming distance between their hashes
4. **Clustering**: Groups similar images together using union-find algorithm (transitive similarity)
5. **Results**: Reports groups of similar images with detailed similarity information

## Use Cases

- Finding duplicate or near-duplicate shots from burst mode
- Identifying similar compositions from a photo session
- **Tagging keeper images vs. rejects while reviewing similar shots**
- Cleaning up large photo libraries
- Finding bracketed exposures
- **Organizing images for import into Capture One with pre-applied color tags**

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
- **Color tagging for Capture One integration**
- Detailed similarity information
- Works in any modern browser

**Controls:**
- `→` or `D` or `N` - Next group
- `←` or `A` or `P` - Previous group
- `Q` or `ESC` - Close window
- Click navigation buttons
- **Click color dots to tag images** (None, Red, Orange, Yellow, Green, Blue, Purple, Pink)

**Color Tagging:**
- Each image has 8 color tag options matching Capture One's color labels
- Tags are saved to XMP sidecar files (`.xmp`) next to RAF files
- Tags persist and can be imported into Capture One
- Existing XMP metadata is preserved when updating tags
- Visual feedback shows currently selected color

**Usage:**
```bash
python fuji_similarity.py /path/to/photos --web-viewer
```

Opens `http://localhost:5000` in your browser automatically.

### Matplotlib Viewer (Offline Alternative)

A desktop viewer using matplotlib. Works without internet/browser but with simpler UI.

**Controls:**
- `→` or `N` - Next group
- `←` or `P` - Previous group
- `Q` or `ESC` - Quit

**Usage:**
```bash
python fuji_similarity.py /path/to/photos --viewer
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

## Architecture Notes

**Why Hybrid?**
- **Python backend**: Fastest RAW processing via libraw (C++)
- **JavaScript frontend**: Best user experience for interactive viewing
- Combines strengths of both ecosystems

**Performance:**
- RAW processing: ~1-2 seconds per image (Python/rawpy)
- Comparison: O(n²) but fast with numpy
- Web viewer: Images cached after first load
- JavaScript would be 5-10x slower for RAW processing

**Technical Details:**
- The tool uses half-size RAW processing for speed while maintaining accuracy for similarity detection
- Perceptual hashing is resistant to minor edits like resizing, slight color adjustments, and compression
- Processing time depends on the number of files and hash size setting
- Web viewer converts RAW to JPEG for browser display (max 1920px wide)
