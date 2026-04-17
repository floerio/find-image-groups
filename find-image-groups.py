#!/usr/bin/env python3
"""
Find Image Groups - Multi-Format Image Similarity Finder

Compares RAW and standard image files to find similar images using DINOv2 embeddings.
Supports RAW formats (RAF, NEF, ARW, CR2, CR3, etc.) and standard formats (JPG, PNG, TIFF, BMP).
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
from PIL import Image, ImageOps
from io import BytesIO
import numpy as np
from tqdm import tqdm
from web_viewer import WebViewer
import torch
from transformers import AutoImageProcessor, AutoModel
from sklearn.metrics.pairwise import cosine_similarity


class ImageSimilarityFinder:
    """Find similar images in a collection of RAW and standard image files using DINOv2."""

    def __init__(self, threshold: float = 0.85, use_cache: bool = True, max_size: int = 512, model_name: str = "facebook/dinov2-base", use_transitive: bool = False, use_raw_preview: bool = True):
        """
        Initialize the similarity finder.

        Args:
            threshold: Cosine similarity threshold (0-1, higher = more similar required)
            use_cache: Whether to use embedding caching
            max_size: Maximum image size for DINOv2 processing (smaller = faster)
            model_name: DINOv2 model to use (dinov2-small, dinov2-base, dinov2-large, dinov2-giant)
            use_transitive: If True, use transitive clustering. If False, use direct similarity only.
            use_raw_preview: If True, extract embedded previews from RAW files (10-20x faster)
        """
        self.threshold = threshold
        self.use_cache = use_cache
        self.max_size = max_size
        self.model_name = model_name
        self.use_transitive = use_transitive
        self.use_raw_preview = use_raw_preview
        self.image_embeddings: Dict[str, np.ndarray] = {}
        self.cache_file = None

        # Setup device (GPU if available)
        if torch.cuda.is_available():
            self.device = torch.device("cuda")
            print("✓ Using GPU (CUDA)")
        elif torch.backends.mps.is_available():
            self.device = torch.device("mps")
            print("✓ Using GPU (Apple Silicon MPS)")
        else:
            self.device = torch.device("cpu")
            print("⚠ Using CPU (slower)")

        # Load DINOv2 model
        print(f"Loading DINOv2 model: {model_name}")
        print("(First time: downloading model, this may take a few minutes...)")
        self.processor = AutoImageProcessor.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()
        print("✓ Model loaded and ready")

    def load_image_file(self, filepath: Path) -> Image.Image:
        """
        Load a RAW or standard image file and convert to PIL Image.

        Args:
            filepath: Path to the image file (RAW, JPG, PNG, etc.)

        Returns:
            PIL Image object (resized for DINOv2 processing)
        """
        # Define RAW file extensions
        raw_extensions = {'.raf', '.nef', '.nrw', '.arw', '.srf', '.sr2',
                         '.cr2', '.cr3', '.crw', '.orf', '.pef', '.rw2',
                         '.dng', '.raw', '.rwl', '.mrw', '.erf', '.3fr',
                         '.dcr', '.kdc', '.mef', '.mos', '.ptx', '.r3d'}

        if filepath.suffix.lower() in raw_extensions:
            # Process RAW file
            if self.use_raw_preview:
                # Try fast preview extraction first
                try:
                    with rawpy.imread(str(filepath)) as raw:
                        thumb = raw.extract_thumb()

                        if thumb.format == rawpy.ThumbFormat.JPEG:
                            # JPEG thumbnail: decode from bytes
                            img = Image.open(BytesIO(thumb.data))
                        else:  # rawpy.ThumbFormat.BITMAP
                            # Bitmap thumbnail: convert from numpy array
                            img = Image.fromarray(thumb.data)

                        # Apply EXIF orientation to handle portrait/landscape correctly
                        img = ImageOps.exif_transpose(img) or img

                except rawpy.LibRawNoThumbnailError:
                    # No embedded preview available, fallback to full RAW processing
                    img = self._process_full_raw(filepath)
                except rawpy.LibRawUnsupportedThumbnailError:
                    # Unsupported preview format, fallback to full RAW processing
                    img = self._process_full_raw(filepath)
            else:
                # Preview extraction disabled by user
                img = self._process_full_raw(filepath)
        else:
            # Process standard image file (JPG, PNG, etc.)
            img = Image.open(filepath)
            # Apply EXIF orientation to handle portrait/landscape correctly
            img = ImageOps.exif_transpose(img) or img
            # Convert to RGB if needed (e.g., PNG with alpha, grayscale)
            if img.mode != 'RGB':
                img = img.convert('RGB')

        # Resize to max_size for faster DINOv2 processing
        img.thumbnail((self.max_size, self.max_size), Image.Resampling.LANCZOS)
        return img

    def _process_full_raw(self, filepath: Path) -> Image.Image:
        """
        Process RAW file using full RAW postprocessing.

        Args:
            filepath: Path to RAW file

        Returns:
            PIL Image object (RGB, not yet resized)
        """
        with rawpy.imread(str(filepath)) as raw:
            rgb = raw.postprocess(
                use_camera_wb=True,
                half_size=True,  # Faster processing, still good for similarity
                no_auto_bright=True,
                output_bps=8
            )
        return Image.fromarray(rgb)

    def compute_embedding(self, image: Image.Image) -> np.ndarray:
        """
        Compute DINOv2 embedding for an image.

        Args:
            image: PIL Image object

        Returns:
            Embedding vector as numpy array
        """
        # Preprocess image
        inputs = self.processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        # Generate embedding
        with torch.no_grad():
            outputs = self.model(**inputs)
            # DINOv2 uses [CLS] token as image representation
            embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy()[0]

        return embedding

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
        Load embedding cache from directory.

        Args:
            directory: Directory containing the cache file

        Returns:
            Cache dictionary
        """
        if not self.use_cache:
            return {}

        self.cache_file = directory / '.fuji_similarity_dinov2_cache.json'

        if not self.cache_file.exists():
            return {}

        try:
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)

            # Validate cache version and model
            if cache_data.get('version') != '2.0' or cache_data.get('model_name') != self.model_name:
                print("Cache version mismatch or different model, rebuilding cache...")
                return {}

            return cache_data.get('embeddings', {})

        except Exception as e:
            print(f"Error loading cache: {e}")
            return {}

    def save_cache(self, directory: Path) -> None:
        """
        Save embedding cache to directory.

        Args:
            directory: Directory to save cache file
        """
        if not self.use_cache or not self.cache_file:
            return

        try:
            # Convert numpy embeddings to lists for JSON serialization
            cache_data = {
                'version': '2.0',
                'model_name': self.model_name,
                'embeddings': {}
            }

            for filepath, embedding in self.image_embeddings.items():
                file_path_obj = Path(filepath)
                if file_path_obj.exists():
                    signature = self.get_file_signature(file_path_obj)
                    cache_data['embeddings'][filepath] = {
                        'signature': signature,
                        'embedding': embedding.tolist()
                    }

            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)

            print(f"\nCache saved to {self.cache_file}")

        except Exception as e:
            print(f"Error saving cache: {e}")

    def process_directory(self, directory: Path, parallel: bool = False) -> None:
        """
        Process all image files in a directory and compute their embeddings.

        Args:
            directory: Path to directory containing image files
            parallel: Whether to use parallel processing (disabled for DINOv2 - GPU doesn't benefit)
        """
        # Define supported file formats
        raw_patterns = ['*.raf', '*.RAF', '*.nef', '*.NEF', '*.nrw', '*.NRW',
                       '*.arw', '*.ARW', '*.srf', '*.SRF', '*.sr2', '*.SR2',
                       '*.cr2', '*.CR2', '*.cr3', '*.CR3', '*.crw', '*.CRW',
                       '*.orf', '*.ORF', '*.pef', '*.PEF', '*.rw2', '*.RW2',
                       '*.dng', '*.DNG', '*.raw', '*.RAW']
        jpg_patterns = ['*.jpg', '*.JPG', '*.jpeg', '*.JPEG',
                       '*.png', '*.PNG', '*.tif', '*.TIF',
                       '*.tiff', '*.TIFF', '*.bmp', '*.BMP']

        # Collect all matching files
        image_files = []
        for pattern in raw_patterns + jpg_patterns:
            image_files.extend(directory.glob(pattern))

        if not image_files:
            print(f"No supported image files found in {directory}")
            return

        print(f"Found {len(image_files)} image files.")

        # Load cache
        cache = self.load_cache(directory)
        files_to_process = []
        cached_count = 0

        # Check which files need processing
        for filepath in image_files:
            filepath_str = str(filepath)

            if filepath_str in cache:
                # Check if file signature matches (file hasn't changed)
                cached_entry = cache[filepath_str]
                current_signature = self.get_file_signature(filepath)

                if cached_entry.get('signature') == current_signature:
                    # Use cached embedding
                    try:
                        embedding_list = cached_entry['embedding']
                        self.image_embeddings[filepath_str] = np.array(embedding_list)
                        cached_count += 1
                        continue
                    except Exception:
                        pass  # Fall through to reprocess

            files_to_process.append(filepath)

        if cached_count > 0:
            print(f"Loaded {cached_count} embeddings from cache.")

        if not files_to_process:
            print("All embeddings loaded from cache!")
            return

        print(f"Processing {len(files_to_process)} files...")

        # Process files sequentially (GPU processing doesn't benefit from multiprocessing)
        for filepath in tqdm(files_to_process, desc="Computing embeddings"):
            filepath_str, embedding = self._process_single_file(filepath)
            if embedding is not None:
                self.image_embeddings[filepath_str] = embedding

        # Save cache
        if self.use_cache:
            self.save_cache(directory)

    def _process_single_file(self, filepath: Path) -> Tuple[str, np.ndarray]:
        """
        Process a single image file.

        Args:
            filepath: Path to image file

        Returns:
            Tuple of (filepath_str, embedding)
        """
        try:
            image = self.load_image_file(filepath)
            embedding = self.compute_embedding(image)
            return (str(filepath), embedding)
        except Exception as e:
            print(f"\nError processing {filepath.name}: {e}", file=sys.stderr)
            return (str(filepath), None)

    def find_similar_images(self) -> List[Tuple[str, str, float]]:
        """
        Find pairs of similar images based on cosine similarity.

        Returns:
            List of tuples (image1_path, image2_path, similarity_score)
        """
        similar_pairs = []
        image_paths = list(self.image_embeddings.keys())

        print(f"\nComparing {len(image_paths)} images...")

        # Convert embeddings to matrix for efficient computation
        embeddings_matrix = np.array([self.image_embeddings[path] for path in image_paths])

        # Compute cosine similarity matrix
        similarity_matrix = cosine_similarity(embeddings_matrix)

        # Find similar pairs
        for i in range(len(image_paths)):
            for j in range(i + 1, len(image_paths)):
                similarity = similarity_matrix[i][j]

                if similarity >= self.threshold:
                    similar_pairs.append((image_paths[i], image_paths[j], similarity))

        # Sort by similarity (higher similarity = more similar)
        similar_pairs.sort(key=lambda x: x[2], reverse=True)

        return similar_pairs

    def cluster_similar_images_direct(self, similar_pairs: List[Tuple[str, str, float]]) -> List[Dict]:
        """
        Cluster similar images using direct similarity only (no transitive grouping).
        Images are only grouped together if ALL images in the group are directly similar
        to each other above the threshold.

        Args:
            similar_pairs: List of similar image pairs

        Returns:
            List of cluster dictionaries with images and their relationships
        """
        if not similar_pairs:
            return []

        # Build adjacency list from similar pairs
        from collections import defaultdict
        adjacency = defaultdict(set)
        similarity_map = {}

        for path1, path2, similarity in similar_pairs:
            adjacency[path1].add(path2)
            adjacency[path2].add(path1)
            similarity_map[(path1, path2)] = similarity
            similarity_map[(path2, path1)] = similarity

        # Get all unique images
        all_images = set()
        for path1, path2, _ in similar_pairs:
            all_images.add(path1)
            all_images.add(path2)

        # Find maximal cliques (groups where all images are directly similar)
        def is_clique(images_set):
            """Check if all images in the set are directly similar to each other."""
            images_list = list(images_set)
            for i in range(len(images_list)):
                for j in range(i + 1, len(images_list)):
                    if images_list[j] not in adjacency[images_list[i]]:
                        return False
            return True

        # Greedy clique finding: start with each pair and try to grow
        clusters = []
        used_images = set()

        # Sort pairs by similarity (highest first)
        sorted_pairs = sorted(similar_pairs, key=lambda x: x[2], reverse=True)

        for path1, path2, similarity in sorted_pairs:
            # Skip if either image is already in a cluster
            if path1 in used_images or path2 in used_images:
                continue

            # Start a new cluster with this pair
            cluster_images = {path1, path2}

            # Try to add more images to this cluster
            # An image can be added if it's directly similar to ALL current members
            for candidate in all_images:
                if candidate in cluster_images or candidate in used_images:
                    continue

                # Check if candidate is similar to all images in current cluster
                if all(candidate in adjacency[img] for img in cluster_images):
                    cluster_images.add(candidate)

            # Record this cluster
            if len(cluster_images) > 1:
                # Mark images as used
                used_images.update(cluster_images)

                # Get all pairs within this cluster
                cluster_pairs = []
                cluster_images_list = sorted(list(cluster_images))
                for i in range(len(cluster_images_list)):
                    for j in range(i + 1, len(cluster_images_list)):
                        img1, img2 = cluster_images_list[i], cluster_images_list[j]
                        if (img1, img2) in similarity_map:
                            sim = similarity_map[(img1, img2)]
                            cluster_pairs.append((img1, img2, sim))

                # Sort pairs by similarity
                cluster_pairs.sort(key=lambda x: x[2], reverse=True)

                clusters.append({
                    'images': cluster_images_list,
                    'pairs': cluster_pairs
                })

        # Sort clusters by size (largest first)
        clusters.sort(key=lambda x: len(x['images']), reverse=True)

        return clusters

    def cluster_similar_images(self, similar_pairs: List[Tuple[str, str, float]], use_transitive: bool = True) -> List[Dict]:
        """
        Cluster similar images into groups.

        Args:
            similar_pairs: List of similar image pairs
            use_transitive: If True, use transitive clustering (union-find).
                          If False, use direct similarity only.

        Returns:
            List of cluster dictionaries with images and their relationships
        """
        if not use_transitive:
            return self.cluster_similar_images_direct(similar_pairs)

        if not similar_pairs:
            return []

        # Union-Find data structure for transitive clustering
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
        for path1, path2, similarity in similar_pairs:
            union(path1, path2)

        # Group ALL images by their root (not just those in similar_pairs)
        # First, ensure all images are in the parent dictionary
        all_images = set()
        for path1, path2, similarity in similar_pairs:
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
        for path1, path2, similarity in similar_pairs:
            root = find(path1)
            if root in clusters_dict:
                clusters_dict[root]['pairs'].append((path1, path2, similarity))

        # Convert to list and sort by cluster size
        clusters = []
        for root, data in clusters_dict.items():
            # Only include clusters with multiple images (actual groups)
            if len(data['images']) > 1:
                clusters.append({
                    'images': sorted(list(data['images'])),
                    'pairs': sorted(data['pairs'], key=lambda x: x[2], reverse=True)
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
        if not self.image_embeddings:
            return []

        # Get all images that are in clusters
        clustered_images = set()
        for cluster in clusters:
            clustered_images.update(cluster['images'])

        # Find images that are not in any cluster
        ungrouped_images = []
        for image_path in self.image_embeddings.keys():
            if image_path not in clustered_images:
                ungrouped_images.append(image_path)

        return sorted(ungrouped_images)

    def print_results(self, similar_pairs: List[Tuple[str, str, float]]) -> None:
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

        for i, (path1, path2, similarity) in enumerate(similar_pairs, 1):
            similarity_pct = similarity * 100
            print(f"{i}. Similarity: {similarity_pct:.1f}% (score: {similarity:.4f})")
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
            for path1, path2, similarity in cluster['pairs']:
                similarity_pct = similarity * 100
                print(f"    {Path(path1).name} ↔ {Path(path2).name}")
                print(f"      Similarity: {similarity_pct:.1f}% (score: {similarity:.4f})")

            print()


def main():
    parser = argparse.ArgumentParser(
        description="Find similar images in a collection of RAW and standard image files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Uses default directory: /Users/ofloericke/images
  %(prog)s /path/to/photos                    # Use custom directory
  %(prog)s --threshold 0.90 --web-viewer      # Higher threshold with web viewer
  %(prog)s /path/to/photos --model facebook/dinov2-large
  %(prog)s --direct-only                      # Use direct similarity clustering

Supported formats:
  RAW: RAF, NEF, ARW, CR2, CR3, ORF, PEF, RW2, DNG, and more
  Standard: JPG, JPEG, PNG, TIFF, BMP
        """
    )

    parser.add_argument(
        "directory",
        type=Path,
        nargs='?',
        default=Path("/Users/ofloericke/images"),
        help="Directory containing image files (default: /Users/ofloericke/images)"
    )

    parser.add_argument(
        "-t", "--threshold",
        type=float,
        default=0.85,
        help="Similarity threshold (0.0-1.0, higher = more similar required). Default: 0.85"
    )

    parser.add_argument(
        "--max-size",
        type=int,
        default=512,
        help="Maximum image size for DINOv2 processing (smaller = faster). Default: 512"
    )

    parser.add_argument(
        "--model",
        choices=["facebook/dinov2-small", "facebook/dinov2-base", "facebook/dinov2-large", "facebook/dinov2-giant"],
        default="facebook/dinov2-base",
        help="DINOv2 model to use. Default: facebook/dinov2-base"
    )

    parser.add_argument(
        "--no-cluster",
        action="store_true",
        help="Disable clustering and show individual pairs instead"
    )

    parser.add_argument(
        "-w", "--web-viewer",
        action="store_true",
        help="Launch web-based viewer (better performance and UI)"
    )

    parser.add_argument(
        "-p", "--port",
        type=int,
        default=5020,
        help="Port for web viewer (default: 5020)"
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
        "-ug", "--show-ungrouped",
        action="store_true",
        help="Show images that are not part of any similar group"
    )

    parser.add_argument(
        "-do", "--direct-only",
        action="store_true",
        help="Use direct similarity clustering only (no transitive grouping). Groups will only contain images that are ALL directly similar to each other."
    )

    parser.add_argument(
        "--no-raw-preview",
        action="store_true",
        help="Disable RAW preview extraction optimization (use full RAW processing instead). By default, embedded previews are extracted for 10-20x faster performance."
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
        threshold=args.threshold,
        use_cache=not args.no_cache,
        max_size=args.max_size,
        model_name=args.model,
        use_transitive=not args.direct_only,
        use_raw_preview=not args.no_raw_preview
    )

    finder.process_directory(args.directory, parallel=not args.no_parallel)

    if not finder.image_embeddings:
        print("No images were successfully processed.")
        sys.exit(1)

    similar_pairs = finder.find_similar_images()

    if args.no_cluster:
        finder.print_results(similar_pairs)
    else:
        clustering_mode = "transitive" if finder.use_transitive else "direct similarity only"
        print(f"Clustering mode: {clustering_mode}")
        clusters = finder.cluster_similar_images(similar_pairs, use_transitive=finder.use_transitive)
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

        # Launch web viewer if requested
        if args.web_viewer and clusters:
            web_viewer = WebViewer(clusters, finder, port=args.port, show_ungrouped=args.show_ungrouped)
            web_viewer.run()


if __name__ == "__main__":
    main()
