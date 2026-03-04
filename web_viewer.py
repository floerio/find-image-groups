#!/usr/bin/env python3
"""
Web-based viewer for Fuji RAW similarity results.
Provides a fast, interactive browser-based interface.
"""

import json
import base64
import webbrowser
import threading
import time
import subprocess
from io import BytesIO
from pathlib import Path
from typing import List, Dict, Optional
from flask import Flask, render_template, send_file, jsonify, request
from PIL import Image
import rawpy
import xml.etree.ElementTree as ET
from xml.dom import minidom


class WebViewer:
    """Web-based viewer using Flask."""

    # Capture One color labels
    COLORS = ["None", "Red", "Orange", "Yellow", "Green", "Blue", "Purple", "Pink"]

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

    def get_exif_data(self, raf_path: str) -> Dict:
        """
        Extract EXIF data from RAF file using exiftool.

        Args:
            raf_path: Path to RAF file

        Returns:
            Dictionary with EXIF data
        """
        exif_data = {
            'iso': None,
            'shutter_speed': None,
            'aperture': None,
            'focal_length': None,
            'datetime': None,
            'lens': None,
            'exposure_bias': None,
        }

        try:
            # Use exiftool to extract EXIF data
            result = subprocess.run(
                ['exiftool', '-j', '-ISO', '-ShutterSpeed', '-Aperture', '-FocalLength',
                 '-DateTimeOriginal', '-LensModel', '-ExposureCompensation', str(raf_path)],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                if data and len(data) > 0:
                    exif = data[0]

                    # ISO
                    if 'ISO' in exif:
                        exif_data['iso'] = str(exif['ISO'])

                    # Shutter speed
                    if 'ShutterSpeed' in exif:
                        exif_data['shutter_speed'] = exif['ShutterSpeed']

                    # Aperture
                    if 'Aperture' in exif:
                        exif_data['aperture'] = f"f/{exif['Aperture']}"

                    # Focal length
                    if 'FocalLength' in exif:
                        focal_str = exif['FocalLength']
                        # Remove 'mm' if present
                        focal_str = focal_str.replace(' mm', '').replace('mm', '')
                        try:
                            focal = float(focal_str)
                            exif_data['focal_length'] = f"{int(focal)}mm"
                        except:
                            exif_data['focal_length'] = focal_str

                    # DateTime
                    if 'DateTimeOriginal' in exif:
                        exif_data['datetime'] = exif['DateTimeOriginal']

                    # Lens
                    if 'LensModel' in exif:
                        exif_data['lens'] = exif['LensModel']

                    # Exposure compensation
                    if 'ExposureCompensation' in exif:
                        comp_str = exif['ExposureCompensation']
                        try:
                            comp = float(comp_str)
                            if comp != 0:
                                exif_data['exposure_bias'] = f"{comp:+.1f} EV"
                        except:
                            if comp_str and comp_str != '0':
                                exif_data['exposure_bias'] = comp_str

        except subprocess.TimeoutExpired:
            print(f"Timeout reading EXIF from {raf_path}")
        except Exception as e:
            print(f"Error reading EXIF from {raf_path}: {e}")

        return exif_data

    def get_xmp_path(self, raf_path: str) -> Path:
        """Get the XMP sidecar path for a RAF file."""
        raf_path_obj = Path(raf_path)
        return raf_path_obj.with_suffix('.xmp')

    def read_color_tag(self, raf_path: str) -> Optional[str]:
        """
        Read color tag from XMP sidecar file.

        Args:
            raf_path: Path to RAF file

        Returns:
            Color label or None
        """
        xmp_path = self.get_xmp_path(raf_path)

        if not xmp_path.exists():
            return None

        try:
            tree = ET.parse(xmp_path)
            root = tree.getroot()

            # Find xmp:Label element
            namespaces = {
                'x': 'adobe:ns:meta/',
                'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                'xmp': 'http://ns.adobe.com/xap/1.0/'
            }

            label_elem = root.find('.//xmp:Label', namespaces)
            if label_elem is not None and label_elem.text:
                return label_elem.text

            return None
        except Exception as e:
            print(f"Error reading XMP for {raf_path}: {e}")
            return None

    def write_color_tag(self, raf_path: str, color: str) -> bool:
        """
        Write color tag to XMP sidecar file.

        Args:
            raf_path: Path to RAF file
            color: Color label to set

        Returns:
            True if successful
        """
        xmp_path = self.get_xmp_path(raf_path)

        try:
            if xmp_path.exists():
                # Update existing XMP
                tree = ET.parse(xmp_path)
                root = tree.getroot()

                namespaces = {
                    'x': 'adobe:ns:meta/',
                    'rdf': 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
                    'xmp': 'http://ns.adobe.com/xap/1.0/'
                }

                # Register namespaces to preserve them
                for prefix, uri in namespaces.items():
                    ET.register_namespace(prefix, uri)
                ET.register_namespace('dc', 'http://purl.org/dc/elements/1.1/')
                ET.register_namespace('photoshop', 'http://ns.adobe.com/photoshop/1.0/')
                ET.register_namespace('lightroom', 'http://ns.adobe.com/lightroom/1.0/')
                ET.register_namespace('exif', 'http://ns.adobe.com/exif/1.0/')

                # Find or create xmp:Label element
                label_elem = root.find('.//xmp:Label', namespaces)

                if label_elem is not None:
                    if color == "None":
                        # Remove the label element
                        desc = root.find('.//rdf:Description', namespaces)
                        if desc is not None:
                            desc.remove(label_elem)
                    else:
                        label_elem.text = color
                else:
                    # Add new label element
                    if color != "None":
                        desc = root.find('.//rdf:Description', namespaces)
                        if desc is not None:
                            label_elem = ET.SubElement(desc, '{http://ns.adobe.com/xap/1.0/}Label')
                            label_elem.text = color

                # Write back
                tree.write(xmp_path, encoding='utf-8', xml_declaration=True)

            else:
                # Create new minimal XMP
                if color == "None":
                    return True  # No need to create file for no color

                xmp_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="XMP Core 5.5.0">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
    xmlns:xmp="http://ns.adobe.com/xap/1.0/">
   <xmp:Label>{color}</xmp:Label>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>'''

                xmp_path.write_text(xmp_content, encoding='utf-8')

            return True

        except Exception as e:
            print(f"Error writing XMP for {raf_path}: {e}")
            return False

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
                            'filename': Path(img).name,
                            'color': self.read_color_tag(img)
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

        @self.app.route('/api/colors')
        def get_color_list():
            """Return available colors."""
            return jsonify(self.COLORS)

        @self.app.route('/api/color/<int:cluster_id>/<int:image_id>', methods=['POST'])
        def set_color(cluster_id, image_id):
            """Set color tag for an image."""
            if cluster_id >= len(self.clusters):
                return jsonify({'error': 'Cluster not found'}), 404

            cluster = self.clusters[cluster_id]
            if image_id >= len(cluster['images']):
                return jsonify({'error': 'Image not found'}), 404

            data = request.get_json()
            color = data.get('color')

            if color not in self.COLORS:
                return jsonify({'error': 'Invalid color'}), 400

            image_path = cluster['images'][image_id]
            success = self.write_color_tag(image_path, color)

            if success:
                return jsonify({'success': True, 'color': color})
            else:
                return jsonify({'error': 'Failed to write XMP'}), 500

        @self.app.route('/api/exif/<int:cluster_id>/<int:image_id>')
        def get_exif(cluster_id, image_id):
            """Get EXIF data for an image."""
            if cluster_id >= len(self.clusters):
                return jsonify({'error': 'Cluster not found'}), 404

            cluster = self.clusters[cluster_id]
            if image_id >= len(cluster['images']):
                return jsonify({'error': 'Image not found'}), 404

            image_path = cluster['images'][image_id]
            exif_data = self.get_exif_data(image_path)

            return jsonify(exif_data)

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

    def open_browser(self):
        """Open browser after a short delay."""
        time.sleep(1.5)  # Wait for server to start
        webbrowser.open(f'http://localhost:{self.port}')

    def run(self):
        """Start the web server."""
        print("\n" + "="*80)
        print("WEB VIEWER")
        print("="*80)
        print(f"Starting web server at http://localhost:{self.port}")
        print("\nOpening browser automatically...")
        print("Press Ctrl+C to stop the server.")
        print("="*80 + "\n")

        # Open browser in background thread
        threading.Thread(target=self.open_browser, daemon=True).start()

        self.app.run(host='0.0.0.0', port=self.port, debug=False)
