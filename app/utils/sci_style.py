"""
SCI-standard plotting utilities for academic publications.

This module provides a simplified plotting style manager that follows
scientific journal standards for figures and charts.
"""

import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from typing import Optional, List, Union, Tuple


class SCIPlotStyle:
    """
    Scientific plotting style manager for academic publications.
    
    This class provides standardized plotting styles and utilities for creating
    publication-ready figures that meet SCI journal requirements.
    """
    
    # Predefined color palettes
    COLOR_PALETTES = {
        'default': ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"],
        'colorblind': ["#0173b2", "#de8f05", "#029e73", "#cc78bc", "#ca9161", "#fbafe4"],
        'nature': ["#E64B35", "#4DBBD5", "#00A087", "#3C5488", "#F39B7F", "#8491B4"],
        'science': ["#3B4992", "#EE0000", "#008B45", "#631879", "#008280", "#BB0021"],
        'grayscale': ["#000000", "#404040", "#808080", "#BFBFBF", "#E0E0E0", "#F5F5F5"],
        'vibrant': ["#E41A1C", "#377EB8", "#4DAF4A", "#984EA3", "#FF7F00", "#FFFF33"]
    }
    
    # Standard figure sizes (width, height) in inches
    FIGURE_SIZES = {
        'single_column': (3.5, 2.625),      # Single column figure
        'double_column': (7.0, 5.25),       # Double column figure
        'full_page': (7.0, 9.0),           # Full page figure
        'square': (4.0, 4.0),              # Square figure
        'wide': (8.0, 4.0),                # Wide figure for landscape
        'tall': (4.0, 8.0)                 # Tall figure for portrait
    }
    
    def __init__(self, 
                 color_palette: Union[str, List[str]] = 'colorblind',
                 figure_size: Union[str, Tuple[float, float]] = 'double_column',
                 dpi: int = 300):
        """
        Initialize the SCI plotting style manager.
        
        Args:
            color_palette: Color palette name or list of colors
            figure_size: Figure size name or tuple (width, height)
            dpi: Resolution for figure saving
        """
        self.dpi = dpi
        
        # Set color palette
        if isinstance(color_palette, str):
            self.color_palette = self.COLOR_PALETTES.get(color_palette, self.COLOR_PALETTES['colorblind'])
        else:
            self.color_palette = color_palette
            
        # Set figure size
        if isinstance(figure_size, str):
            self.figure_size = self.FIGURE_SIZES.get(figure_size, self.FIGURE_SIZES['double_column'])
        else:
            self.figure_size = figure_size
        
        # Apply the style
        self.apply_style()
    
    def apply_style(self) -> None:
        """Apply SCI-standard plotting style to matplotlib."""
        # Update rcParams for SCI standards
        sci_params = {
            # Font settings
            'font.family': 'serif',
            'font.serif': ['Times New Roman', 'DejaVu Serif'],
            'font.size': 10,
            'axes.titlesize': 12,
            'axes.labelsize': 10,
            'xtick.labelsize': 9,
            'ytick.labelsize': 9,
            'legend.fontsize': 9,
            'figure.titlesize': 14,
            
            # Figure settings
            'figure.dpi': self.dpi,
            'savefig.dpi': self.dpi,
            'savefig.bbox': 'tight',
            'figure.figsize': self.figure_size,
            
            # Line and marker settings
            'axes.linewidth': 0.8,
            'grid.linewidth': 0.5,
            'lines.linewidth': 1.2,
            'lines.markersize': 4,
            
            # Grid and spines
            'axes.grid': True,
            'grid.alpha': 0.3,
            'axes.spines.top': False,
            'axes.spines.right': False,
            
            # Text and math
            'text.usetex': False,  # Set to True if LaTeX is available
            'mathtext.fontset': 'stix'
        }
        
        plt.rcParams.update(sci_params)
        
        # Set seaborn theme and palette
        sns.set_theme(style="whitegrid")
        sns.set_palette(self.color_palette)
    
    def save_figure(self, 
                   filename: Union[str, Path], 
                   format: str = "pdf", 
                   dpi: Optional[int] = None,
                   bbox_inches: str = "tight") -> Path:
        """
        Save figure in high-resolution format suitable for publications.
        
        Args:
            filename: Output filename (without extension)
            format: Output format ("pdf", "svg", "eps", "png", "jpg")
            dpi: Resolution (if None, uses class default)
            bbox_inches: Bounding box setting
            
        Returns:
            Path to saved file
        """
        if dpi is None:
            dpi = self.dpi
            
        # Ensure filename has correct extension
        filepath = Path(filename)
        if filepath.suffix.lower() != f'.{format.lower()}':
            filepath = filepath.with_suffix(f'.{format.lower()}')
        
        # Create directory if it doesn't exist
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Get current figure and save
        fig = plt.gcf()
        fig.savefig(
            filepath, 
            format=format, 
            dpi=dpi, 
            bbox_inches=bbox_inches,
            facecolor='white'
        )
        
        return filepath

# Convenience function for quick setup (simplified version)
def setup_sci_style(color_palette: Union[str, List[str]] = 'colorblind',
                   figure_size: Union[str, Tuple[float, float]] = 'double_column',
                   dpi: int = 300) -> SCIPlotStyle:
    """
    Quick setup function for SCI plotting style.
    
    Args:
        color_palette: Color palette name or list of colors  
        figure_size: Figure size name or tuple
        dpi: Resolution for saving
        
    Returns:
        SCIPlotStyle instance
    """
    return SCIPlotStyle(color_palette=color_palette, figure_size=figure_size, dpi=dpi)