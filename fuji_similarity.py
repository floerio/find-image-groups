#!/usr/bin/env python3
"""
Fuji RAW Image Similarity Finder

Compares Fuji RAW files (.RAF) to find similar images based on perceptual hashing.
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Set
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

    def __init__(self, hash_size: int = 8, threshold: int = 10):
        """
        Initialize the similarity finder.

        Args:
            hash_size: Size of the perceptual hash (larger = more precise)
            threshold: Hamming distance threshold (lower = more similar required)
        """
        self.hash_size = hash_size
        self.threshold = threshold
        self.image_hashes: Dict[str, imagehash.ImageHash] = {}

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
        # Using average hash - fast and effective for similarity detection
        return imagehash.average_hash(image, hash_size=self.hash_size)

    def process_directory(self, directory: Path) -> None:
        """
        Process all RAF files in a directory and compute their hashes.

        Args:
            directory: Path to directory containing RAF files
        """
        raf_files = list(directory.glob("*.RAF")) + list(directory.glob("*.raf"))

        if not raf_files:
            print(f"No RAF files found in {directory}")
            return

        print(f"Found {len(raf_files)} RAF files. Processing...")

        for filepath in tqdm(raf_files, desc="Computing hashes"):
            try:
                image = self.load_raw_file(filepath)
                hash_value = self.compute_hash(image)
                self.image_hashes[str(filepath)] = hash_value
            except Exception as e:
                print(f"\nError processing {filepath.name}: {e}", file=sys.stderr)

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

        # Group images by their root
        clusters_dict = {}
        for path1, path2, distance in similar_pairs:
            root = find(path1)
            if root not in clusters_dict:
                clusters_dict[root] = {
                    'images': set(),
                    'pairs': []
                }
            clusters_dict[root]['images'].add(path1)
            clusters_dict[root]['images'].add(path2)
            clusters_dict[root]['pairs'].append((path1, path2, distance))

        # Convert to list and sort by cluster size
        clusters = []
        for root, data in clusters_dict.items():
            clusters.append({
                'images': sorted(list(data['images'])),
                'pairs': sorted(data['pairs'], key=lambda x: x[2])
            })

        # Sort clusters by size (largest first)
        clusters.sort(key=lambda x: len(x['images']), reverse=True)

        return clusters

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

    def __init__(self, clusters: List[Dict], finder: ImageSimilarityFinder):
        """
        Initialize the viewer.

        Args:
            clusters: List of cluster dictionaries
            finder: ImageSimilarityFinder instance (for loading images)
        """
        self.clusters = clusters
        self.finder = finder
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

    def on_key(self, event) -> None:
        """
        Handle keyboard events for navigation.

        Args:
            event: Matplotlib key event
        """
        if event.key == 'right' or event.key == 'n':
            # Next cluster
            self.show_cluster(self.current_cluster + 1)
        elif event.key == 'left' or event.key == 'p':
            # Previous cluster
            self.show_cluster(self.current_cluster - 1)
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
        threshold=args.threshold
    )

    finder.process_directory(args.directory)

    if not finder.image_hashes:
        print("No images were successfully processed.")
        sys.exit(1)

    similar_pairs = finder.find_similar_images()

    if args.no_cluster:
        finder.print_results(similar_pairs)
    else:
        clusters = finder.cluster_similar_images(similar_pairs)
        finder.print_clustered_results(clusters)

        # Launch viewer if requested
        if args.web_viewer and clusters:
            web_viewer = WebViewer(clusters, finder, port=args.port)
            web_viewer.run()
        elif args.viewer and clusters:
            viewer = ClusterViewer(clusters, finder)
            viewer.run()


if __name__ == "__main__":
    main()
