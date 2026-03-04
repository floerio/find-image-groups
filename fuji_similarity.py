#!/usr/bin/env python3
"""
Find Image Groups - Fuji RAW Similarity Finder

Compares Fuji RAW files (.RAF) to find similar images based on perceptual hashing.
Groups similar images and provides interactive viewer with color tagging.
"""

import argparse
import os
import sys
import json
import hashlib
from pathlib import Path
from typing import List, Tuple, Dict, Set
from multiprocessing import Pool, cpu_count
import rawpy
import imagehash
from PIL import Image
import numpy as np
from tqdm import tqdm
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from web_viewer import WebViewer


class ImageSimilarityFinder:
    """Find similar images in a collection of Fuji RAW files."""

    def __init__(self, hash_size: int = 8, threshold: int = 10, use_cache: bool = True, hash_method: str = "phash"):
        """
        Initialize the similarity finder.

        Args:
            hash_size: Size of the perceptual hash (larger = more precise)
            threshold: Hamming distance threshold (lower = more similar required)
            use_cache: Whether to use hash caching
            hash_method: Hash method to use (average, phash, dhash, whash)
        """
        self.hash_size = hash_size
        self.threshold = threshold
        self.use_cache = use_cache
        self.hash_method = hash_method
        self.image_hashes: Dict[str, imagehash.ImageHash] = {}
        self.cache_file = None

    def load_raw_file(self, filepath: Path) -> Image.Image:
        """
        Load a Fuji RAF file and convert to PIL Image.

        Args:
            filepath: Path to the RAF file

        Returns:
            PIL Image object
        """
        with rawpy.imread(str(filepath)) as raw:
            # Process RAW to RGB array
            rgb = raw.postprocess(
                use_camera_wb=True,
                half_size=True,  # Faster processing, still good for similarity
                no_auto_bright=True,
                output_bps=8
            )
        return Image.fromarray(rgb)

    def compute_hash(self, image: Image.Image) -> imagehash.ImageHash:
        """
        Compute perceptual hash for an image.

        Args:
            image: PIL Image object

        Returns:
            Perceptual hash
        """
        # Use the selected hash method
        if self.hash_method == "average":
            return imagehash.average_hash(image, hash_size=self.hash_size)
        elif self.hash_method == "phash":
            return imagehash.phash(image, hash_size=self.hash_size)
        elif self.hash_method == "dhash":
            return imagehash.dhash(image, hash_size=self.hash_size)
        elif self.hash_method == "whash":
            return imagehash.whash(image, hash_size=self.hash_size)
        else:
            # Default to phash if unknown method
            return imagehash.phash(image, hash_size=self.hash_size)

    def get_file_signature(self, filepath: Path) -> str:
        """
        Get a unique signature for a file (for cache validation).

        Args:
            filepath: Path to file

        Returns:
            Signature string combining size and mtime
        """
        stat = filepath.stat()
        return f"{stat.st_size}_{stat.st_mtime_ns}"

    def load_cache(self, directory: Path) -> Dict:
        """
        Load hash cache from directory.

        Args:
            directory: Directory containing the cache file

        Returns:
            Cache dictionary
        """
        if not self.use_cache:
            return {}

        self.cache_file = directory / '.fuji_similarity_cache.json'

        if not self.cache_file.exists():
            return {}

        try:
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)

            # Validate cache version and hash_size
            if cache_data.get('version') != '1.0' or cache_data.get('hash_size') != self.hash_size:
                print("Cache version mismatch or different hash_size, rebuilding cache...")
                return {}

            return cache_data.get('hashes', {})

        except Exception as e:
            print(f"Error loading cache: {e}")
            return {}

    def save_cache(self, directory: Path) -> None:
        """
        Save hash cache to directory.

        Args:
            directory: Directory to save cache file
        """
        if not self.use_cache or not self.cache_file:
            return

        try:
            # Convert imagehash objects to strings
            cache_data = {
                'version': '1.0',
                'hash_size': self.hash_size,
                'hashes': {}
            }

            for filepath, hash_obj in self.image_hashes.items():
                file_path_obj = Path(filepath)
                if file_path_obj.exists():
                    signature = self.get_file_signature(file_path_obj)
                    cache_data['hashes'][filepath] = {
                        'signature': signature,
                        'hash': str(hash_obj)
                    }

            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)

            print(f"\nCache saved to {self.cache_file}")

        except Exception as e:
            print(f"Error saving cache: {e}")

    def process_directory(self, directory: Path, parallel: bool = True) -> None:
        """
        Process all RAF files in a directory and compute their hashes.

        Args:
            directory: Path to directory containing RAF files
            parallel: Whether to use parallel processing
        """
        raf_files = list(directory.glob("*.RAF")) + list(directory.glob("*.raf"))

        if not raf_files:
            print(f"No RAF files found in {directory}")
            return

        print(f"Found {len(raf_files)} RAF files.")

        # Load cache
        cache = self.load_cache(directory)
        files_to_process = []
        cached_count = 0

        # Check which files need processing
        for filepath in raf_files:
            filepath_str = str(filepath)

            if filepath_str in cache:
                # Check if file signature matches (file hasn't changed)
                cached_entry = cache[filepath_str]
                current_signature = self.get_file_signature(filepath)

                if cached_entry.get('signature') == current_signature:
                    # Use cached hash
                    try:
                        hash_str = cached_entry['hash']
                        self.image_hashes[filepath_str] = imagehash.hex_to_hash(hash_str)
                        cached_count += 1
                        continue
                    except Exception:
                        pass  # Fall through to reprocess

            files_to_process.append(filepath)

        if cached_count > 0:
            print(f"Loaded {cached_count} hashes from cache.")

        if not files_to_process:
            print("All hashes loaded from cache!")
            return

        print(f"Processing {len(files_to_process)} files...")

        # Process files
        if parallel and len(files_to_process) > 1:
            # Use parallel processing
            num_workers = min(cpu_count(), len(files_to_process))
            print(f"Using {num_workers} parallel workers")

            with Pool(num_workers) as pool:
                results = list(tqdm(
                    pool.imap(self._process_single_file, files_to_process),
                    total=len(files_to_process),
                    desc="Computing hashes"
                ))

            # Collect results
            for filepath, hash_value in results:
                if hash_value is not None:
                    self.image_hashes[str(filepath)] = hash_value
        else:
            # Sequential processing
            for filepath in tqdm(files_to_process, desc="Computing hashes"):
                filepath_str, hash_value = self._process_single_file(filepath)
                if hash_value is not None:
                    self.image_hashes[filepath_str] = hash_value

        # Save cache
        if self.use_cache:
            self.save_cache(directory)

    def _process_single_file(self, filepath: Path) -> Tuple[str, imagehash.ImageHash]:
        """
        Process a single RAF file (for parallel processing).

        Args:
            filepath: Path to RAF file

        Returns:
            Tuple of (filepath_str, hash_value)
        """
        try:
            image = self.load_raw_file(filepath)
            hash_value = self.compute_hash(image)
            return (str(filepath), hash_value)
        except Exception as e:
            print(f"\nError processing {filepath.name}: {e}", file=sys.stderr)
            return (str(filepath), None)

    def find_similar_images(self) -> List[Tuple[str, str, int]]:
        """
        Find pairs of similar images based on hash comparison.

        Returns:
            List of tuples (image1_path, image2_path, distance)
        """
        similar_pairs = []
        image_paths = list(self.image_hashes.keys())

        print(f"\nComparing {len(image_paths)} images...")

        for i in range(len(image_paths)):
            for j in range(i + 1, len(image_paths)):
                path1, path2 = image_paths[i], image_paths[j]
                hash1, hash2 = self.image_hashes[path1], self.image_hashes[path2]

                # Calculate Hamming distance
                distance = hash1 - hash2

                print(f"P1: {path1} - {hash1}, P2: {path2} - {hash2}, Distance: {distance}")

                if distance <= self.threshold:
                    similar_pairs.append((path1, path2, distance))

        # Sort by similarity (lower distance = more similar)
        similar_pairs.sort(key=lambda x: x[2])

        return similar_pairs

    def cluster_similar_images(self, similar_pairs: List[Tuple[str, str, int]]) -> List[Dict]:
        """
        Cluster similar images into groups using union-find algorithm.

        Args:
            similar_pairs: List of similar image pairs

        Returns:
            List of cluster dictionaries with images and their relationships
        """
        if not similar_pairs:
            return []

        # Union-Find data structure
        parent = {}

        def find(x):
            if x not in parent:
                parent[x] = x
            if parent[x] != x:
                parent[x] = find(parent[x])  # Path compression
            return parent[x]

        def union(x, y):
            root_x = find(x)
            root_y = find(y)
            if root_x != root_y:
                parent[root_x] = root_y

        # Build clusters by unioning similar pairs
        for path1, path2, distance in similar_pairs:
            union(path1, path2)

        # Group ALL images by their root (not just those in similar_pairs)
        # First, ensure all images are in the parent dictionary
        all_images = set()
        for path1, path2, distance in similar_pairs:
            all_images.add(path1)
            all_images.add(path2)
        
        # Initialize parent for all images
        for img_path in all_images:
            find(img_path)  # This ensures the image is in the parent dict

        # Group images by their root
        clusters_dict = {}
        for img_path in all_images:
            root = find(img_path)
            if root not in clusters_dict:
                clusters_dict[root] = {
                    'images': set(),
                    'pairs': []
                }
            clusters_dict[root]['images'].add(img_path)

        # Add the similar pairs to each cluster
        for path1, path2, distance in similar_pairs:
            root = find(path1)
            if root in clusters_dict:
                clusters_dict[root]['pairs'].append((path1, path2, distance))

        # Convert to list and sort by cluster size
        clusters = []
        for root, data in clusters_dict.items():
            # Only include clusters with multiple images (actual groups)
            if len(data['images']) > 1:
                clusters.append({
                    'images': sorted(list(data['images'])),
                    'pairs': sorted(data['pairs'], key=lambda x: x[2])
                })

        # Sort clusters by size (largest first)
        clusters.sort(key=lambda x: len(x['images']), reverse=True)

        return clusters

    def find_ungrouped_images(self, clusters: List[Dict]) -> List[str]:
        """
        Find images that are not part of any cluster.

        Args:
            clusters: List of cluster dictionaries

        Returns:
            List of image paths that are not in any cluster
        """
        if not self.image_hashes:
            return []

        # Get all images that are in clusters
        clustered_images = set()
        for cluster in clusters:
            clustered_images.update(cluster['images'])

        # Find images that are not in any cluster
        ungrouped_images = []
        for image_path in self.image_hashes.keys():
            if image_path not in clustered_images:
                ungrouped_images.append(image_path)

        return sorted(ungrouped_images)

    def print_results(self, similar_pairs: List[Tuple[str, str, int]]) -> None:
        """
        Print the results of similarity comparison.

        Args:
            similar_pairs: List of similar image pairs
        """
        if not similar_pairs:
            print("\nNo similar images found.")
            return

        print(f"\n{'='*80}")
        print(f"Found {len(similar_pairs)} similar image pair(s):")
        print(f"{'='*80}\n")

        for i, (path1, path2, distance) in enumerate(similar_pairs, 1):
            similarity_pct = max(0, 100 - (distance / self.hash_size**2 * 100))
            print(f"{i}. Similarity: {similarity_pct:.1f}% (distance: {distance})")
            print(f"   - {Path(path1).name}")
            print(f"   - {Path(path2).name}")
            print()

    def print_clustered_results(self, clusters: List[Dict]) -> None:
        """
        Print clustered results showing groups of similar images.

        Args:
            clusters: List of cluster dictionaries
        """
        if not clusters:
            print("\nNo similar images found.")
            return

        total_images = sum(len(cluster['images']) for cluster in clusters)
        total_pairs = sum(len(cluster['pairs']) for cluster in clusters)

        print(f"\n{'='*80}")
        print(f"Found {len(clusters)} group(s) of similar images:")
        print(f"Total: {total_images} images in {total_pairs} similar pair(s)")
        print(f"{'='*80}\n")

        for i, cluster in enumerate(clusters, 1):
            num_images = len(cluster['images'])
            num_pairs = len(cluster['pairs'])

            print(f"Group {i}: {num_images} similar image(s)")
            print(f"{'-'*80}")

            # Print all images in the cluster
            for img_path in cluster['images']:
                print(f"  • {Path(img_path).name}")

            # Print similarity details for pairs
            print(f"\n  Similarities within group:")
            for path1, path2, distance in cluster['pairs']:
                similarity_pct = max(0, 100 - (distance / self.hash_size**2 * 100))
                print(f"    {Path(path1).name} ↔ {Path(path2).name}")
                print(f"      Similarity: {similarity_pct:.1f}% (distance: {distance})")

            print()


class ClusterViewer:
    """Interactive viewer for browsing clustered similar images."""

    def __init__(self, clusters: List[Dict], finder: ImageSimilarityFinder, show_ungrouped: bool = False):
        """
        Initialize the viewer.

        Args:
            clusters: List of cluster dictionaries
            finder: ImageSimilarityFinder instance (for loading images)
            show_ungrouped: Whether to show ungrouped images
        """
        self.clusters = clusters
        self.finder = finder
        self.show_ungrouped = show_ungrouped
        self.ungrouped_images = []
        if show_ungrouped:
            self.ungrouped_images = finder.find_ungrouped_images(clusters)
        self.current_cluster = 0
        self.fig = None
        self.loaded_images = {}  # Cache for loaded images

    def load_image_cached(self, filepath: str) -> Image.Image:
        """
        Load an image with caching.

        Args:
            filepath: Path to the image file

        Returns:
            PIL Image object
        """
        if filepath not in self.loaded_images:
            self.loaded_images[filepath] = self.finder.load_raw_file(Path(filepath))
        return self.loaded_images[filepath]

    def show_cluster(self, cluster_idx: int) -> None:
        """
        Display a cluster of similar images.

        Args:
            cluster_idx: Index of the cluster to display
        """
        if not self.clusters:
            print("No clusters to display")
            return

        # Handle ungrouped images as a special "cluster"
        if self.show_ungrouped and cluster_idx >= len(self.clusters):
            self.show_ungrouped_images()
            return

        # Wrap around
        cluster_idx = cluster_idx % len(self.clusters)
        self.current_cluster = cluster_idx

        cluster = self.clusters[cluster_idx]
        images = cluster['images']
        pairs = cluster['pairs']

        # Clear the figure
        if self.fig is not None:
            plt.clf()
        else:
            self.fig = plt.figure(figsize=(16, 10))

        # Calculate grid layout
        n_images = len(images)
        n_cols = min(3, n_images)
        n_rows = (n_images + n_cols - 1) // n_cols

        # Set up the figure title
        self.fig.suptitle(
            f'Group {cluster_idx + 1} of {len(self.clusters)} - {n_images} similar images\n'
            f'Use ← → to navigate groups, Q to quit',
            fontsize=14,
            fontweight='bold'
        )

        # Create subplots for images
        for idx, img_path in enumerate(images):
            ax = self.fig.add_subplot(n_rows, n_cols, idx + 1)

            try:
                # Load image
                img = self.load_image_cached(img_path)

                # Display image
                ax.imshow(np.array(img))
                ax.axis('off')

                # Add filename as title
                filename = Path(img_path).name
                ax.set_title(filename, fontsize=10, pad=5)

            except Exception as e:
                ax.text(0.5, 0.5, f'Error loading\n{Path(img_path).name}',
                       ha='center', va='center', transform=ax.transAxes)
                ax.axis('off')

        # Add similarity information at the bottom
        similarity_text = "Similarities:\n"
        for path1, path2, distance in pairs:
            similarity_pct = max(0, 100 - (distance / self.finder.hash_size**2 * 100))
            name1 = Path(path1).name
            name2 = Path(path2).name
            similarity_text += f"  {name1} ↔ {name2}: {similarity_pct:.1f}%\n"

        # Add text box with similarity info
        self.fig.text(0.02, 0.02, similarity_text, fontsize=9,
                     verticalalignment='bottom', fontfamily='monospace',
                     bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.tight_layout(rect=[0, 0.1, 1, 0.95])
        plt.draw()

    def show_ungrouped_images(self) -> None:
        """Display ungrouped images."""
        if not self.ungrouped_images:
            print("No ungrouped images to display")
            return

        # Clear the figure
        if self.fig is not None:
            plt.clf()
        else:
            self.fig = plt.figure(figsize=(16, 10))

        images = self.ungrouped_images
        n_images = len(images)
        n_cols = min(3, n_images)
        n_rows = (n_images + n_cols - 1) // n_cols

        # Set up the figure title
        self.fig.suptitle(
            f'Ungrouped Images - {n_images} images not in any similar group\n'
            f'Use ← → to navigate, Q to quit',
            fontsize=14,
            fontweight='bold'
        )

        # Create subplots for images
        for idx, img_path in enumerate(images):
            ax = self.fig.add_subplot(n_rows, n_cols, idx + 1)

            try:
                # Load image
                img = self.load_image_cached(img_path)

                # Display image
                ax.imshow(np.array(img))
                ax.axis('off')

                # Add filename as title
                filename = Path(img_path).name
                ax.set_title(filename, fontsize=10, pad=5)

            except Exception as e:
                ax.text(0.5, 0.5, f'Error loading\n{Path(img_path).name}',
                       ha='center', va='center', transform=ax.transAxes)
                ax.axis('off')

        # Add info text at the bottom
        info_text = "These images have no similar counterparts based on the current threshold."
        self.fig.text(0.02, 0.02, info_text, fontsize=9,
                     verticalalignment='bottom', fontfamily='monospace',
                     bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.tight_layout(rect=[0, 0.1, 1, 0.95])
        plt.draw()

    def on_key(self, event) -> None:
        """
        Handle keyboard events for navigation.

        Args:
            event: Matplotlib key event
        """
        if event.key == 'right' or event.key == 'n':
            # Next cluster
            total_groups = self.get_total_groups()
            next_cluster = self.current_cluster + 1
            if next_cluster >= total_groups:
                next_cluster = 0
            self.show_cluster(next_cluster)
        elif event.key == 'left' or event.key == 'p':
            # Previous cluster
            total_groups = self.get_total_groups()
            prev_cluster = self.current_cluster - 1
            if prev_cluster < 0:
                prev_cluster = total_groups - 1
            self.show_cluster(prev_cluster)
        elif event.key == 'q' or event.key == 'escape':
            # Quit
            plt.close(self.fig)

    def run(self) -> None:
        """Start the interactive viewer."""
        if not self.clusters:
            print("\nNo similar images to display.")
            return

        print("\n" + "="*80)
        print("INTERACTIVE VIEWER")
        print("="*80)
        print("Controls:")
        print("  → or N : Next group")
        print("  ← or P : Previous group")
        print("  Q or ESC : Quit viewer")
        print("="*80 + "\n")

        # Show first cluster
        self.show_cluster(0)

        # Connect keyboard handler
        self.fig.canvas.mpl_connect('key_press_event', self.on_key)

        # Show the plot
        plt.show()

        # Clear cache after viewer closes
        self.loaded_images.clear()

    def get_total_groups(self) -> int:
        """Get total number of groups including ungrouped images."""
        total = len(self.clusters)
        if self.show_ungrouped and self.ungrouped_images:
            total += 1
        return total


def main():
    parser = argparse.ArgumentParser(
        description="Find similar images in a collection of Fuji RAW files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /path/to/photos
  %(prog)s /path/to/photos --threshold 5
  %(prog)s /path/to/photos --hash-size 16 --threshold 8
        """
    )

    parser.add_argument(
        "directory",
        type=Path,
        help="Directory containing Fuji RAF files"
    )

    parser.add_argument(
        "-t", "--threshold",
        type=int,
        default=10,
        help="Similarity threshold (0-64, lower = more similar required). Default: 10"
    )

    parser.add_argument(
        "-s", "--hash-size",
        type=int,
        default=8,
        help="Hash size for comparison (larger = more precise). Default: 8"
    )

    parser.add_argument(
        "--no-cluster",
        action="store_true",
        help="Disable clustering and show individual pairs instead"
    )

    parser.add_argument(
        "-v", "--viewer",
        action="store_true",
        help="Launch interactive matplotlib viewer to browse similar image groups"
    )

    parser.add_argument(
        "-w", "--web-viewer",
        action="store_true",
        help="Launch web-based viewer (better performance and UI)"
    )

    parser.add_argument(
        "-p", "--port",
        type=int,
        default=5000,
        help="Port for web viewer (default: 5000)"
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable hash caching (recompute all hashes)"
    )

    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel processing (slower but uses less memory)"
    )

    parser.add_argument(
        "--show-ungrouped",
        action="store_true",
        help="Show images that are not part of any similar group"
    )

    parser.add_argument(
        "--hash-method",
        choices=["average", "phash", "dhash", "whash"],
        default="phash",
        help="Hash method to use (average, phash, dhash, whash). Default: phash"
    )

    args = parser.parse_args()

    # Validate directory
    if not args.directory.exists():
        print(f"Error: Directory '{args.directory}' does not exist", file=sys.stderr)
        sys.exit(1)

    if not args.directory.is_dir():
        print(f"Error: '{args.directory}' is not a directory", file=sys.stderr)
        sys.exit(1)

    # Create finder and process images
    finder = ImageSimilarityFinder(
        hash_size=args.hash_size,
        threshold=args.threshold,
        use_cache=not args.no_cache,
        hash_method=args.hash_method
    )

    finder.process_directory(args.directory, parallel=not args.no_parallel)

    if not finder.image_hashes:
        print("No images were successfully processed.")
        sys.exit(1)

    similar_pairs = finder.find_similar_images()

    if args.no_cluster:
        finder.print_results(similar_pairs)
    else:
        clusters = finder.cluster_similar_images(similar_pairs)
        finder.print_clustered_results(clusters)

        # Show ungrouped images if requested
        if args.show_ungrouped:
            ungrouped_images = finder.find_ungrouped_images(clusters)
            if ungrouped_images:
                print(f"\n{'='*80}")
                print(f"Ungrouped Images ({len(ungrouped_images)} images not in any similar group):")
                print(f"{'='*80}")
                for i, img_path in enumerate(ungrouped_images, 1):
                    print(f"{i}. {Path(img_path).name}")
            else:
                print(f"\n{'='*80}")
                print("No ungrouped images found (all images are in similar groups)")
                print(f"{'='*80}")

        # Launch viewer if requested
        if args.web_viewer and clusters:
            web_viewer = WebViewer(clusters, finder, port=args.port, show_ungrouped=args.show_ungrouped)
            web_viewer.run()
        elif args.viewer and clusters:
            viewer = ClusterViewer(clusters, finder, show_ungrouped=args.show_ungrouped)
            viewer.run()


if __name__ == "__main__":
    main()
