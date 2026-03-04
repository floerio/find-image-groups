#!/usr/bin/env python3
"""
Web-based viewer for Fuji RAW similarity results.
Provides a fast, interactive browser-based interface.
"""

import json
import base64
from io import BytesIO
from pathlib import Path
from typing import List, Dict
from flask import Flask, render_template, send_file, jsonify
from PIL import Image
import rawpy


class WebViewer:
    """Web-based viewer using Flask."""

    def __init__(self, clusters: List[Dict], finder, port: int = 5000):
        """
        Initialize the web viewer.

        Args:
            clusters: List of cluster dictionaries
            finder: ImageSimilarityFinder instance
            port: Port to run the web server on
        """
        self.clusters = clusters
        self.finder = finder
        self.port = port
        self.app = Flask(__name__)
        self.image_cache = {}
        self._setup_routes()

    def _setup_routes(self):
        """Set up Flask routes."""

        @self.app.route('/')
        def index():
            """Serve the main viewer page."""
            return render_template('viewer.html')

        @self.app.route('/api/clusters')
        def get_clusters():
            """Return cluster metadata."""
            clusters_data = []
            for i, cluster in enumerate(self.clusters):
                cluster_info = {
                    'id': i,
                    'num_images': len(cluster['images']),
                    'images': [
                        {
                            'path': img,
                            'filename': Path(img).name
                        }
                        for img in cluster['images']
                    ],
                    'similarities': [
                        {
                            'img1': Path(pair[0]).name,
                            'img2': Path(pair[1]).name,
                            'distance': int(pair[2]),
                            'percentage': float(max(0, 100 - (pair[2] / self.finder.hash_size**2 * 100)))
                        }
                        for pair in cluster['pairs']
                    ]
                }
                clusters_data.append(cluster_info)
            return jsonify(clusters_data)

        @self.app.route('/api/image/<int:cluster_id>/<int:image_id>')
        def get_image(cluster_id, image_id):
            """Serve a processed image as JPEG."""
            if cluster_id >= len(self.clusters):
                return "Cluster not found", 404

            cluster = self.clusters[cluster_id]
            if image_id >= len(cluster['images']):
                return "Image not found", 404

            image_path = cluster['images'][image_id]

            # Check cache
            cache_key = f"{cluster_id}_{image_id}"
            if cache_key in self.image_cache:
                return send_file(
                    BytesIO(self.image_cache[cache_key]),
                    mimetype='image/jpeg'
                )

            try:
                # Load and process RAW file
                img = self.finder.load_raw_file(Path(image_path))

                # Resize for web display (max 1920px wide)
                max_width = 1920
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_size = (max_width, int(img.height * ratio))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)

                # Convert to JPEG
                buffer = BytesIO()
                img.save(buffer, format='JPEG', quality=85, optimize=True)
                jpeg_data = buffer.getvalue()

                # Cache it
                self.image_cache[cache_key] = jpeg_data

                return send_file(
                    BytesIO(jpeg_data),
                    mimetype='image/jpeg'
                )

            except Exception as e:
                print(f"Error loading image: {e}")
                return f"Error loading image: {e}", 500

    def run(self):
        """Start the web server."""
        print("\n" + "="*80)
        print("WEB VIEWER")
        print("="*80)
        print(f"Starting web server at http://localhost:{self.port}")
        print("\nOpen your browser and navigate to the URL above.")
        print("Press Ctrl+C to stop the server.")
        print("="*80 + "\n")

        self.app.run(host='0.0.0.0', port=self.port, debug=False)
