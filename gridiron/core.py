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
    def __init__(self, workflow, row_label=None, col_label=None):
        self.workflow = workflow
        self.image = None
        self.row_label = row_label
        self.col_label = col_label
        self._hash = hashlib.sha256(
            json.dumps(workflow.to_dict(), sort_keys=True).encode()
        ).hexdigest()

    async def generate(self, gridiron) -> str:
        cached_path = gridiron.try_get_cached(self._hash)
        if cached_path:
            return cached_path
        
        try:
            # Generate the image using the workflow
            images = []
            async for image in gridiron.comfy.generate(self.workflow):
                images.append(image)
            image_bytes = images[0]
            
            # Cache and return the path
            return gridiron.put_cache(self._hash, image_bytes)
        except RuntimeError as e:
            # Parse the error JSON if present
            try:
                error_data = json.loads(str(e).split(": ", 1)[1])
                if "node_errors" in error_data:
                    for node_id, node_error in error_data["node_errors"].items():
                        if "errors" in node_error:
                            for error in node_error["errors"]:
                                print(f"\nComfyUI Error at position [Row: {self.row_label}, Col: {self.col_label}]")
                                print(f"Node {node_id}:")
                                print(f"Type: {error.get('type', 'unknown')}")
                                print(f"Message: {error.get('message', 'unknown')}")
                                print(f"Details: {error.get('details', 'none')}\n")
            except:
                print(f"\nComfyUI Error: {str(e)}\n")
            
            return "ERROR"

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
            # Copy to output directory
            output_path = self.output_dir / 'images' / f"{hash_id}.png"
            shutil.copy(cache_path, output_path)
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
                image = Image(workflow, row_label=prompt, col_label=lora)
                row.append(image)
            grid.append(row)

        # Generate all images in parallel with progress bar (column-major order)
        total_images = len(grid) * len(grid[0])
        tasks = []
        
        with tqdm(total=total_images, desc="Generating images") as pbar:
            for col_idx in range(len(grid[0])):
                for row in grid:
                    image = row[col_idx]
                    task = asyncio.create_task(image.generate(self))
                    task.add_done_callback(lambda _: pbar.update(1))
                    tasks.append(task)
            
            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle any exceptions
            for result in results:
                if isinstance(result, Exception):
                    print(f"Error during generation: {result}")

        # Generate HTML
        self._generate_html(grid, args[0], args[1])

    def _generate_html(self, grid, row_labels, col_labels):
        """Generate HTML grid view"""
        template = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { margin: 0; padding: 20px; font-family: system-ui, -apple-system, sans-serif; }
                .grid-container { 
                    overflow: auto;
                    max-height: 98vh;
                    position: relative;
                }
                table { 
                    border-collapse: separate;
                    border-spacing: 0;
                    background: white;
                }
                td, th { 
                    padding: 10px; 
                    border: 1px solid #ddd;
                    background: white;
                }
                th {
                    background: #f5f5f5;
                    font-weight: 600;
                }
                .grid-image { 
                    max-width: 256px;
                    display: block;
                    cursor: pointer;
                    transition: opacity 0.2s;
                }
                .grid-image:hover {
                    opacity: 0.9;
                }
                /* Sticky headers */
                thead th {
                    position: sticky;
                    top: 0;
                    z-index: 2;
                }
                tbody th {
                    position: sticky;
                    left: 0;
                    z-index: 1;
                }
                thead th:first-child {
                    z-index: 3;
                }
                /* Border fixes for sticky elements */
                th:after {
                    content: '';
                    position: absolute;
                    left: 0;
                    right: 0;
                    top: 0;
                    bottom: 0;
                    border: 1px solid #ddd;
                    pointer-events: none;
                }
                /* Modal styles */
                .modal {
                    display: none;
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.8);
                    z-index: 1000;
                    cursor: pointer;
                }
                .modal.active {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                }
                .modal-content {
                    max-width: 90vw;
                    max-height: 90vh;
                    margin: auto;
                    position: relative;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    background: rgba(0, 0, 0, 0.5);
                    padding: 10px;
                    border-radius: 8px;
                }
                .modal-image {
                    max-width: 100%;
                    max-height: calc(90vh - 80px);
                    object-fit: contain;
                }
                .modal-header {
                    color: white;
                    font-size: 1.2em;
                    text-align: center;
                    padding: 5px;
                }
                .modal-row-label {
                    color: white;
                    font-size: 1.2em;
                    text-align: center;
                    padding: 5px;
                    margin-bottom: 10px;
                }
            </style>
        </head>
        <body>
            <div class="grid-container">
                <table>
                    <thead>
                        <tr>
                            <th></th>
                            {% for col in col_labels %}
                            <th>{{ col }}</th>
                            {% endfor %}
                        </tr>
                    </thead>
                    <tbody>
                        {% for row in grid %}
                        <tr>
                            <th>{{ row_labels[loop.index0] }}</th>
                            {% set row_index = loop.index0 %}
                            {% for img in row %}
                            <td>
                                {% if img._hash == "ERROR" %}
                                    <div style="text-align: center; padding: 20px; background: #fee; color: #c00; border: 1px solid #fcc;">Error</div>
                                {% else %}
                                    <img class="grid-image" src="images/{{ img._hash }}.png" loading="lazy" data-row="{{ row_index }}" data-col="{{ loop.index0 }}">
                                {% endif %}
                            </td>
                            {% endfor %}
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            <div class="modal" id="imageModal">
                <div class="modal-content">
                    <div class="modal-header" id="modalHeader"></div>
                    <div class="modal-row-label" id="modalRowLabel"></div>
                    <img class="modal-image" id="modalImage" src="" alt="Large preview">
                </div>
            </div>
            <script>
                const modal = document.getElementById('imageModal');
                const modalImg = document.getElementById('modalImage');
                let currentRow = 0;
                let currentCol = 0;
                const gridImages = document.querySelectorAll('.grid-image');
                const maxRow = Math.max(...Array.from(gridImages).map(img => parseInt(img.dataset.row)));
                const maxCol = Math.max(...Array.from(gridImages).map(img => parseInt(img.dataset.col)));

                const modalHeader = document.getElementById('modalHeader');
                const modalRowLabel = document.getElementById('modalRowLabel');
                
                function showModal(img) {
                    currentRow = parseInt(img.dataset.row);
                    currentCol = parseInt(img.dataset.col);
                    modalImg.src = img.src;
                    
                    // Update headers
                    const colHeader = document.querySelector(`thead th:nth-child(${currentCol + 2})`).textContent;
                    const rowHeader = document.querySelector(`tbody tr:nth-child(${currentRow + 1}) th`).textContent;
                    
                    modalHeader.textContent = colHeader;
                    modalRowLabel.textContent = rowHeader;
                    
                    modal.classList.add('active');
                }

                function hideModal() {
                    modal.classList.remove('active');
                }

                function navigateImage(rowDelta, colDelta) {
                    const newRow = Math.max(0, Math.min(currentRow + rowDelta, maxRow));
                    const newCol = Math.max(0, Math.min(currentCol + colDelta, maxCol));
                    const newImage = document.querySelector(`.grid-image[data-row="${newRow}"][data-col="${newCol}"]`);
                    if (newImage) {
                        currentRow = newRow;
                        currentCol = newCol;
                        modalImg.src = newImage.src;
                        
                        // Update headers
                        const colHeader = document.querySelector(`thead th:nth-child(${currentCol + 2})`).textContent;
                        const rowHeader = document.querySelector(`tbody tr:nth-child(${currentRow + 1}) th`).textContent;
                        
                        modalHeader.textContent = colHeader;
                        modalRowLabel.textContent = rowHeader;
                    }
                }

                document.querySelectorAll('.grid-image').forEach(img => {
                    img.addEventListener('click', () => showModal(img));
                });

                modal.addEventListener('click', (e) => {
                    if (e.target === modal) {
                        hideModal();
                    }
                });

                document.addEventListener('keydown', (e) => {
                    if (!modal.classList.contains('active')) return;
                    
                    switch(e.key.toLowerCase()) {
                        case 'escape':
                            hideModal();
                            e.preventDefault();
                            break;
                        case 'arrowleft':
                        case 'a':
                            navigateImage(0, -1);
                            e.preventDefault();
                            break;
                        case 'arrowright':
                        case 'd':
                            navigateImage(0, 1);
                            e.preventDefault();
                            break;
                        case 'arrowup':
                        case 'w':
                            navigateImage(-1, 0);
                            e.preventDefault();
                            break;
                        case 'arrowdown':
                        case 's':
                            navigateImage(1, 0);
                            e.preventDefault();
                            break;
                    }
                });
            </script>
        </body>
        </html>
        """
        
        env = Environment(loader=FileSystemLoader('.'))
        template = env.from_string(template)
        html = template.render(grid=grid, row_labels=row_labels, col_labels=col_labels)
        
        with open(self.output_dir / 'index.html', 'w') as f:
            f.write(html)
