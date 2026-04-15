#!/usr/bin/env python3
import requests
import json

# Test the recluster API
url = 'http://localhost:5000/api/recluster'

# Test with threshold 0.95 (should give fewer groups)
data = {'threshold': 0.95}

print(f"Testing recluster with threshold: {data['threshold']}")
response = requests.post(url, json=data)

if response.ok:
    result = response.json()
    print(f"Success: {result['stats']['num_clusters']} clusters, {result['stats']['num_ungrouped']} ungrouped")
    print(f"Total images: {result['stats']['total_images']}")
else:
    print(f"Error: {response.status_code} - {response.text}")
