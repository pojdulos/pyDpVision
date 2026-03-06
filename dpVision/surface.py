# Surface data model
from functools import cached_property

import numpy as np


class Surface:
    """
    Unified 2D surface data model.
    
    Represents gridded surface data together with physical spacing,
    optional mask, visualization limits, and metadata.
    """

    def __init__(
        self,
        height,
        dx,
        dy,
        x0=0.0,
        y0=0.0,
        mask=None,
        unit="um",
        metadata=None,
        vmin=None,
        vmax=None,
    ):
        self.height = np.asarray(height, dtype=float)
        self.dx = dx
        self.dy = dy
        self.x0 = x0  # Origin/offset for X coordinates
        self.y0 = y0  # Origin/offset for Y coordinates

        self.mask = mask if mask is not None else ~np.isnan(self.height)

        self.unit = unit
        self.metadata = metadata or {}

        # visualization-related (previously GridData)
        self.vmin = vmin
        self.vmax = vmax

    # ---------------------------
    # Basic properties
    # ---------------------------

    @property
    def shape(self):
        return self.height.shape

    @property
    def ny(self):
        """Number of data points in Y (rows)."""
        return self.height.shape[0]

    @property
    def nx(self):
        """Number of data points in X (columns)."""
        return self.height.shape[1]

    @property
    def length(self):
        """Physical length in Y direction."""
        return (self.ny - 1) * self.dy

    @property
    def width(self):
        """Physical width in X direction."""
        return (self.nx - 1) * self.dx

    # ---------------------------
    # Coordinate arrays (xi, yi)
    # replaces GridData.xi, yi
    # ---------------------------

    @cached_property
    def xi(self):
        """X coordinates array (cached)."""
        return self.x0 + np.arange(self.nx) * self.dx

    @cached_property
    def yi(self):
        """Y coordinates array (cached)."""
        return self.y0 + np.arange(self.ny) * self.dy

    # ---------------------------
    # Utilities
    # ---------------------------

    def copy(self):
        return Surface(
            self.height.copy(),
            self.dx,
            self.dy,
            self.x0,
            self.y0,
            self.mask.copy(),
            self.unit,
            self.metadata.copy(),
            self.vmin,
            self.vmax,
        )

    def crop(self, ny, nx):
        """Crop surface to ny rows and nx columns, keeping the same origin."""
        return Surface(
            self.height[:ny, :nx],
            self.dx,
            self.dy,
            self.x0,  # Keep the same origin
            self.y0,
            self.mask[:ny, :nx],
            self.unit,
            self.metadata.copy(),
            self.vmin,
            self.vmax,
        )
    
    def crop_to_mask(self):
        """Crop surface to minimal bounding box containing all valid (masked) pixels.
        
        Returns
        -------
        Surface
            New surface cropped to the bounding box of the mask
            
        Examples
        --------
        >>> # Apply ROI and then crop to minimal size
        >>> roi = CircleROI(center_x=3.0, center_y=3.0, radius=1.0)
        >>> surface_roi = roi.apply(surface)
        >>> surface_cropped = surface_roi.crop_to_mask()
        """
        if not self.mask.any():
            raise ValueError("Cannot crop to mask: mask is empty (no valid pixels)")
        
        # Find bounding box of mask
        rows = np.any(self.mask, axis=1)
        cols = np.any(self.mask, axis=0)
        y_min, y_max = np.where(rows)[0][[0, -1]]
        x_min, x_max = np.where(cols)[0][[0, -1]]
        
        # Crop to bounding box (inclusive, so +1 for slicing)
        cropped_height = self.height[y_min:y_max+1, x_min:x_max+1]
        cropped_mask = self.mask[y_min:y_max+1, x_min:x_max+1]
        
        # Update origin to reflect the crop offset
        new_x0 = self.x0 + x_min * self.dx
        new_y0 = self.y0 + y_min * self.dy
        
        return Surface(
            cropped_height,
            self.dx,
            self.dy,
            new_x0,
            new_y0,
            cropped_mask,
            self.unit,
            self.metadata.copy(),
            self.vmin,
            self.vmax,
        )

