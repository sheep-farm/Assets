# Assets

<p align="center">
  <img src="data/icons/hicolor/scalable/apps/com.github.sheep.farm.assets.svg" width="128" height="128" alt="Assets Logo"/>
</p>

<p align="center">
  <strong>Visual Python Programming with Code Export</strong>
</p>

<p align="center">
  A modern GNOME application for visual Python development. Design workflows visually, execute them interactively, and export to standalone Python scripts.
</p>

---

## Overview

**Assets** is a visual Python programming environment that bridges the gap between visual programming and traditional code. Create Python workflows by connecting nodes on a canvas, execute them interactively, and export to standalone Python scripts for production use.

Unlike traditional node-based tools that lock you into their environment, Assets generates clean, readable Python code that runs independently. This makes it ideal for rapid prototyping, education, and building production-ready data pipelines.

**Key Concept:** Design visually → Execute interactively → Export to Python → Deploy anywhere

### Who Is This For?

- **Data Scientists**: Build ETL pipelines visually, export for production deployment
- **Data Analysts**: Create analysis workflows without deep programming knowledge
- **Financial Analysts**: Analyze market data and economic indicators
- **Students**: Learn Python programming through visual experimentation
- **Engineers**: Prototype data workflows quickly, then refine the exported code
- **Researchers**: Build reproducible workflows that can be shared as Python scripts

## Features

### Visual Node Editor
- **Drag-and-drop canvas**: Create workflows visually with an intuitive interface
- **Node-based programming**: Connect nodes to build data pipelines
- **Type-safe connections**: Ports are color-coded by data type (DataFrame, Array, Figure, etc.)
- **Real-time execution**: See results immediately in the output panel
- **Parallel execution**: Nodes at the same level execute concurrently
- **Zoom and pan**: Navigate large workflows easily
- **Multi-selection**: Select and move multiple nodes at once

### 🎯 Export to Python (Standalone Scripts)
**The killer feature that sets Assets apart from other visual tools:**

- **Export to executable Python**: Press `Ctrl+Shift+E` to export your visual workflow as a standalone `.py` script
- **No dependencies on Assets**: Exported scripts run with just Python and pip-installable packages
- **Production-ready code**: Clean, readable Python with proper imports and structure
- **Preserves parallelization**: ThreadPoolExecutor maintains concurrent execution of independent nodes
- **Command-line interface**: Run exported scripts with optional verbose mode (`-v` flag)
- **Perfect for deployment**: Use in cron jobs, CI/CD pipelines, Docker containers, or anywhere Python runs

```bash
# In Assets: Design visually, press Ctrl+Shift+E to export
# In terminal: Run the exported script
python3 my_pipeline.py              # Run quietly
python3 my_pipeline.py -v           # Run with verbose output
```

### Python Development Environment
- **Full Python support**: Write custom Python code within each node
- **Rich data types**: Built-in support for DataFrames, arrays, plots, and more
- **Standard libraries**: Use pandas, numpy, matplotlib, scipy, and any pip package
- **Data helpers**: Built-in `load_data()` and `save_data()` functions for common formats
- **Financial data integration**: Yahoo Finance, FRED API for economic data (but not limited to finance!)
- **Visualization**: Create matplotlib/seaborn plots that render in the output panel or export
- **Group nodes**: Organize complex workflows into reusable components

### Professional Workflow
- **Save/Load projects**: Persist your workflows as `.assets` files
- **Node library**: Save and reuse custom nodes across projects
- **Undo/Redo**: Full undo history for all operations
- **Keyboard shortcuts**: Efficient navigation and editing
- **Output panel**: View results, console output, and errors
- **Modern GNOME design**: Clean, native interface following GNOME HIG

## Why Assets?

### The Best of Both Worlds

**Traditional Visual Tools** (Node-RED, Orange, KNIME):
- ❌ Lock you into their environment
- ❌ Can't deploy without the tool installed
- ❌ Hard to version control
- ❌ Limited to tool-specific workflows

**Traditional Python Scripting**:
- ❌ Steep learning curve
- ❌ Hard to visualize complex workflows
- ❌ Time-consuming to prototype

**Assets Combines Both**:
- ✅ Visual design for rapid prototyping
- ✅ Interactive execution with immediate feedback
- ✅ Export to clean, standalone Python scripts
- ✅ Git-friendly (both `.assets` projects and exported `.py` code)
- ✅ No lock-in: exported code runs anywhere Python runs
- ✅ Production-ready: deploy to cron, CI/CD, containers

### Comparison Table

| Feature | Assets | Node-RED | Orange | KNIME | Python Scripts |
|---------|--------|----------|--------|-------|----------------|
| Visual Editor | ✅ | ✅ | ✅ | ✅ | ❌ |
| Python Code | ✅ | ❌ | ⚠️ | ⚠️ | ✅ |
| Export Standalone Scripts | ✅ | ❌ | ❌ | ❌ | N/A |
| No Runtime Dependencies | ✅* | ❌ | ❌ | ❌ | ✅ |
| Parallel Execution | ✅ | ⚠️ | ⚠️ | ✅ | Manual |
| Open Source | ✅ | ✅ | ✅ | ⚠️ | ✅ |
| Native Linux App | ✅ | ❌ | ⚠️ | ❌ | ✅ |

\* Exported scripts only need Python + pip packages

## Installation

### Dependencies

- GTK 4.0
- Libadwaita 1.0
- Python 3.12+
- Cairo
- Meson build system

### Build from Source

```bash
# Navigate to the project directory
cd /path/to/Assets

# Build with Meson
meson setup builddir
meson compile -C builddir

# Install (optional)
meson install -C builddir

# Or run directly
./builddir/src/assets
```

### Flatpak (Recommended)

```bash
# Build and install as Flatpak
flatpak-builder --user --install --force-clean flatpak_app com.github.sheep.farm.assets.json

# Run the application
flatpak run com.github.sheep.farm.assets
```

## Quick Start

### Creating Your First Workflow

1. **Add nodes**: Right-click on the canvas → "Add Node from Library"
2. **Connect nodes**: Click and drag from output ports (right) to input ports (left)
3. **Configure nodes**: Double-click nodes to edit their Python code
4. **Execute**: Click "Run" or press F5 to execute the workflow
5. **View results**: Check the Output panel for results and visualizations
6. **Export**: Press `Ctrl+Shift+E` to export as standalone Python script

### Example 1: Data Analysis Pipeline

```
[Load CSV] → [Filter Data] → [Aggregate] → [Plot Chart]
                                        ↘ [Export to File]
```

1. Add a "Code" node to load CSV data using pandas
2. Connect it to transformation nodes (filter, aggregate)
3. Split output to visualization and export nodes
4. Execute to see results, then export the entire workflow to Python

### Example 2: Financial Data Analysis

```
[Yahoo Finance] → [Calculate Returns] → [Statistical Analysis] → [Report]
```

1. Fetch stock data from Yahoo Finance
2. Calculate daily returns and moving averages
3. Run statistical tests (correlations, volatility)
4. Generate comprehensive report with plots and tables

## Use Cases

Assets is versatile and can be used for various Python workflows:

### Data Science & Analytics
- ETL pipelines for data cleaning and transformation
- Statistical analysis and hypothesis testing
- Machine learning preprocessing workflows
- Exploratory data analysis (EDA)

### Financial Analysis
- Market data analysis (stocks, forex, crypto)
- Economic indicator tracking (FRED API)
- Portfolio analysis and risk assessment
- Trading strategy backtesting

### Research & Education
- Reproducible research workflows
- Teaching Python programming visually
- Prototyping algorithms before implementation
- Collaborative data analysis projects

### DevOps & Automation
- Data processing pipelines for CI/CD
- Log analysis and monitoring workflows
- Automated report generation
- Batch processing tasks

## Node Types

All nodes can contain custom Python code. Common patterns include:

### Data Sources
- **Code nodes**: Load data from CSV, Excel, JSON, Parquet, APIs
- **Yahoo Finance**: Fetch stock/market data (built-in)
- **FRED API**: Economic indicators (built-in)
- **Web scraping**: Use requests/BeautifulSoup for web data

### Transformations
- **Data manipulation**: pandas operations (filter, merge, groupby)
- **Calculations**: numpy array operations, custom formulas
- **Text processing**: String operations, regex, NLP
- **Feature engineering**: Create derived features for ML

### Outputs & Visualization
- **Matplotlib/Seaborn**: Create publication-quality plots
- **Tables**: Display DataFrames in the output panel
- **Console output**: Print progress, statistics, logs
- **File export**: Save to CSV, Excel, JSON, or images

### Utilities
- **Code**: General-purpose Python execution node
- **Group**: Organize complex workflows into reusable components
- **Comment**: Add documentation to your workflow

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+N` | New project |
| `Ctrl+O` | Open project |
| `Ctrl+S` | Save project |
| `Ctrl+Shift+S` | Save as... |
| `Ctrl+Shift+E` | **Export to Python** |
| `Ctrl+Z` | Undo |
| `Ctrl+Shift+Z` | Redo |
| `Ctrl+C` | Copy selected nodes |
| `Ctrl+V` | Paste nodes |
| `Ctrl+D` | Duplicate selected nodes |
| `Delete` | Delete selected nodes |
| `F5` | Run workflow |
| `Tab` | Navigate between nodes |
| `Arrow Keys` | Move selected node |
| `+/-` | Zoom in/out |
| `Ctrl+0` | Reset zoom |

## Development

### Project Structure

```
Assets/
├── src/
│   ├── main.py              # Application entry point
│   ├── window.py            # Main window
│   ├── canvas.py            # Node canvas implementation
│   ├── node.py              # Node class
│   ├── graph_executor.py    # Graph execution engine
│   ├── export_to_code.py    # Export to Python functionality
│   ├── node_library.py      # Node library system
│   ├── node_dialogs.py      # Node configuration dialogs
│   ├── output_panel.py      # Results output panel
│   ├── graph_io.py          # Save/load functionality
│   ├── undo_redo.py         # Undo/Redo manager
│   └── blp/                 # Blueprint UI files
├── data/
│   ├── icons/               # Application icons
│   ├── *.desktop.in         # Desktop entry
│   └── *.metainfo.xml.in    # AppStream metadata
├── po/                      # Translations
├── wheels/                  # Python dependencies
└── meson.build             # Build configuration
```

### Adding Custom Nodes

Nodes are defined in JSON files in `~/.nodes/`:

```json
{
  "Data Sources": {
    "icon": "📊",
    "nodes": [
      {
        "name": "My Data Source",
        "description": "Custom data loader",
        "num_inputs": 0,
        "num_outputs": 1,
        "default_code": "# Your Python code here\n_data = load_data()",
        "tags": ["data", "custom"],
        "category": "Data Sources"
      }
    ]
  }
}
```

## Status

This project is currently in **active development** (v0.1.0). Core features are functional, but APIs may change.

### Current Features
- ✅ Visual node-based editor
- ✅ Real-time Python execution
- ✅ **Export to standalone Python scripts** (`Ctrl+Shift+E`)
- ✅ Parallel execution (ThreadPoolExecutor)
- ✅ Project-based dependency management
- ✅ Rich output panel (tables, plots, console)
- ✅ Undo/Redo system
- ✅ Custom node library

### Planned Features
- [ ] Enhanced code editor with syntax highlighting and autocompletion
- [ ] Debugger integration (breakpoints, step execution)
- [ ] Additional data sources (Alpha Vantage, Quandl, databases)
- [ ] More visualization types (interactive plots, dashboards)
- [ ] Version control integration (Git diff for workflows)
- [ ] Collaborative features (shared node libraries)
- [ ] Plugin/extension system
- [ ] Cloud storage integration

## License

This project is licensed under the MIT License.

See [LICENSE](LICENSE) for details.

## Author

**Flavio de Vasconcellos Corrêa** ([@sheep-farm](https://github.com/sheep-farm))

## Technologies

- **GTK 4** & **Libadwaita** - Modern GNOME user interface
- **Python 3.12+** - Core logic and node execution
- **Cairo** - High-performance canvas rendering
- **Meson** - Build system
- **ThreadPoolExecutor** - Parallel node execution
- **pandas, numpy, matplotlib** - Data science libraries (bundled)
- **Yahoo Finance & FRED** - Financial data APIs (optional)

---

<p align="center">
  <em>Design visually. Execute interactively. Export to Python. Deploy anywhere.</em>
</p>
