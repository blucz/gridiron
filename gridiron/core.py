import os
import hashlib
import json
import asyncio
from pathlib import Path
from typing import Callable, List, Any
import aiohttp
from jinja2 import Environment, FileSystemLoader
import shutil
from tqdm import tqdm
import json

class Image:
    def __init__(self, workflow):
        self.workflow = workflow
        self.image = None
        self._hash = hashlib.sha256(
            json.dumps(workflow.to_dict(), sort_keys=True).encode()
        ).hexdigest()

    async def generate(self, gridiron) -> str:
        cached_path = gridiron.try_get_cached(self._hash)
        if cached_path:
            return cached_path
        
        # Generate the image using the workflow
        images = []
        #print("Generating image from workflow", json.dumps(self.workflow.to_dict(), indent=2))
        async for image in gridiron.comfy.generate(self.workflow):
            images.append(image)
        image_bytes = images[0]
        
        # Cache and return the path
        return gridiron.put_cache(self._hash, image_bytes)

class Gridiron:
    def __init__(self, comfy, output_dir: str):
        self.comfy = comfy
        self.output_dir = Path(output_dir)
        self.cache_dir = Path.home() / '.cache' / 'gridiron'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / 'images').mkdir(exist_ok=True)

    def try_get_cached(self, hash_id: str) -> Path:
        """Try to get an image from the cache"""
        cache_path = self.cache_dir / f"{hash_id}.png"
        if cache_path.exists():
            return cache_path
        return None

    def put_cache(self, hash_id: str, image_bytes: bytes) -> Path:
        """Put an image into the cache"""
        cache_path = self.cache_dir / f"{hash_id}.png"
        with open(cache_path, 'wb') as f:
            f.write(image_bytes)
        
        # Copy to output directory
        output_path = self.output_dir / 'images' / f"{hash_id}.png"
        shutil.copy(cache_path, output_path)
        return output_path

    async def generate(self, workflow_fn: Callable, *args: List[Any]):
        """Generate grid from all combinations of arguments"""
        # Generate all combinations
        combinations = [(x, y) for x in args[0] for y in args[1]]
        
        # Create grid data structure
        grid = []
        for prompt in args[0]:
            row = []
            for lora in args[1]:
                seed = 42  # You might want to make this configurable
                workflow = workflow_fn(prompt, lora, seed)
                image = Image(workflow)
                row.append(image)
            grid.append(row)

        # Generate all images in parallel with progress bar
        total_images = len(grid) * len(grid[0])
        tasks = []
        with tqdm(total=total_images, desc="Generating images") as pbar:
            for row in grid:
                for image in row:
                    async def generate_and_update(img):
                        result = await img.generate(self)
                        pbar.update(1)
                        return result
                    tasks.append(generate_and_update(image))
            await asyncio.gather(*tasks)

        # Generate HTML
        self._generate_html(grid, args[0], args[1])

    def _generate_html(self, grid, row_labels, col_labels):
        """Generate HTML grid view"""
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                table { border-collapse: collapse; }
                td, th { padding: 10px; border: 1px solid #ddd; }
                img { max-width: 256px; }
            </style>
        </head>
        <body>
            <table>
                <tr>
                    <th></th>
                    {% for col in col_labels %}
                    <th>{{ col }}</th>
                    {% endfor %}
                </tr>
                {% for row in grid %}
                <tr>
                    <th>{{ row_labels[loop.index0] }}</th>
                    {% for img in row %}
                    <td><img src="images/{{ img._hash }}.png"></td>
                    {% endfor %}
                </tr>
                {% endfor %}
            </table>
        </body>
        </html>
        """
        
        env = Environment(loader=FileSystemLoader('.'))
        template = env.from_string(template)
        html = template.render(grid=grid, row_labels=row_labels, col_labels=col_labels)
        
        with open(self.output_dir / 'index.html', 'w') as f:
            f.write(html)
