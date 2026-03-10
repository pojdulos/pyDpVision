# Surface data model
from functools import cached_property

import numpy as np

# ---------------------------------------------------------------------------
# Unit normalisation
# ---------------------------------------------------------------------------

# Conversion factors: how many µm is 1 <unit>
_TO_UM: dict[str, float] = {
    'nm':  0.001,
    'um':  1.0,
    'µm':  1.0,
    'mm':  1_000.0,
    'cm':  10_000.0,
    'm':   1_000_000.0,
}

# All Surface objects store data in this unit internally.
CANONICAL_UNIT = 'um'


class Surface:
    """
    Unified 2D surface data model.

    Represents gridded surface data together with physical spacing,
    optional mask, visualization limits, and metadata.

    All spatial data (``height``, ``dx``, ``dy``, ``x0``, ``y0``) are stored
    internally in **micrometres** (µm) regardless of the ``unit`` argument
    passed to the constructor.  The conversion happens once at construction
    time so every downstream algorithm operates on a single, consistent scale.

    To obtain a copy in a different unit (e.g. for export to dpVision) use
    :meth:`to_unit`.
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
        scale = _TO_UM.get(unit)
        if scale is None:
            raise ValueError(
                f"Unknown unit '{unit}'. Supported units: {list(_TO_UM)}"
            )

        self.height = np.asarray(height, dtype=float) * scale
        self.dx = float(dx) * scale
        self.dy = float(dy) * scale
        self.x0 = float(x0) * scale
        self.y0 = float(y0) * scale

        self.mask = mask if mask is not None else ~np.isnan(self.height)

        # Always canonical — callers must not rely on this being their input unit.
        self.unit = CANONICAL_UNIT
        self.metadata = metadata or {}

        # visualization-related (previously GridData)
        self.vmin = vmin
        self.vmax = vmax

    @classmethod
    def _create_normalized(
        cls,
        height,
        dx,
        dy,
        x0=0.0,
        y0=0.0,
        mask=None,
        unit=CANONICAL_UNIT,
        metadata=None,
        vmin=None,
        vmax=None,
    ):
        """Create a Surface whose data is *already* in ``unit`` — skip scaling.

        For internal use only (copy/crop/to_unit) where data has already been
        converted.  External code should always go through :meth:`__init__`.
        """
        obj = object.__new__(cls)
        obj.height = np.asarray(height, dtype=float)
        obj.dx = float(dx)
        obj.dy = float(dy)
        obj.x0 = float(x0)
        obj.y0 = float(y0)
        obj.mask = mask if mask is not None else ~np.isnan(obj.height)
        obj.unit = unit
        obj.metadata = metadata or {}
        obj.vmin = vmin
        obj.vmax = vmax
        return obj

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
        """Return a deep copy (data already in canonical µm unit)."""
        return Surface._create_normalized(
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

    def to_unit(self, target_unit: str) -> 'Surface':
        """Return a copy of this surface with all spatial data in *target_unit*.

        The original surface is not modified.  Useful for export — e.g. to
        dpVision which uses a millimetre coordinate space::

            surface_mm = surface.to_unit('mm')

        Parameters
        ----------
        target_unit : str
            Any unit recognised by the library: ``'nm'``, ``'um'`` / ``'µm'``,
            ``'mm'``, ``'cm'``, ``'m'``.

        Returns
        -------
        Surface
            New Surface whose data are in *target_unit*.  ``surface.unit``
            will reflect the requested unit (not the canonical ``'um'``).
        """
        if target_unit == self.unit:
            return self.copy()
        scale_to_target = _TO_UM.get(target_unit)
        if scale_to_target is None:
            raise ValueError(
                f"Unknown target unit '{target_unit}'. Supported: {list(_TO_UM)}"
            )
        # self is already in µm; 1 µm = (1 / scale_to_target) target_units
        inv = 1.0 / scale_to_target
        return Surface._create_normalized(
            self.height * inv,
            self.dx * inv,
            self.dy * inv,
            self.x0 * inv,
            self.y0 * inv,
            self.mask.copy(),
            target_unit,
            self.metadata.copy(),
            self.vmin,
            self.vmax,
        )

    def crop(self, ny, nx):
        """Crop surface to ny rows and nx columns, keeping the same origin."""
        return Surface._create_normalized(
            self.height[:ny, :nx],
            self.dx,
            self.dy,
            self.x0,
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
        
        return Surface._create_normalized(
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

