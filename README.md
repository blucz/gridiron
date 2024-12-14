<div align="center">
  <h1>
    <img src="gridiron.jpg" alt="Gridiron Logo" height="96px" width="96px">
    Gridiron
  </h1>
</div>

# Gridiron

A powerful tool for generating and analyzing image grids to evaluate diffusion model training, prompting, and parameters.

## Features

- Generate comparison grids using one or more ComfyUI instances as the backend
- Cache previous results for faster grid generation during model development.
- Python-based DSL for defining grids

## Installation

```bash
pip install gridiron
```

## Usage

Create a Python file with the following content:

```python
from gridiron import Grid
```

Basic usage example:

```bash
gridiron run test_grid.py
```

This will generate a grid according to the definitions in `my_grid_definitions.py`.

```bash
gridiron serve test_grid.py
```

This will generate a grid according to the definitions in `my_grid_definitions.py`, starting in HTTP server so you can watch the grid as it generates.

## Requirements

- Python 3.11+

## License

See [LICENSE](LICENSE) file for details.
