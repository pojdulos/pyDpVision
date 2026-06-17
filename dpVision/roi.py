# ROI definitions
import numpy as np
from scipy.ndimage import binary_erosion


class MarginROI:
    """Remove margin around surface edges.
    
    Parameters
    ----------
    margin_x, margin_y : float, optional
        Symmetric margins in physical units (left=right=margin_x, top=bottom=margin_y)
    left, right, top, bottom : float, optional
        Individual margins in physical units (overrides margin_x/margin_y if specified)
    """
    def __init__(self, margin_x=None, margin_y=None, left=None, right=None, top=None, bottom=None):
        # Support both symmetric (margin_x/margin_y) and asymmetric (left/right/top/bottom) modes
        if left is not None or right is not None or top is not None or bottom is not None:
            # Asymmetric mode
            self.left = left or 0
            self.right = right or 0
            self.top = top or 0
            self.bottom = bottom or 0
        elif margin_x is not None or margin_y is not None:
            # Symmetric mode (backward compatibility)
            self.left = self.right = margin_x or 0
            self.top = self.bottom = margin_y or 0
        else:
            # Default: no margins
            self.left = self.right = self.top = self.bottom = 0

    def apply(self, surface):
        nx, ny = surface.shape[1], surface.shape[0]
        
        # Convert physical margins to pixels
        left_px = int(self.left / surface.dx)
        right_px = int(self.right / surface.dx)
        top_px = int(self.top / surface.dy)
        bottom_px = int(self.bottom / surface.dy)

        mask = surface.mask.copy()
        if top_px > 0:
            mask[:top_px, :] = False
        if bottom_px > 0:
            mask[-bottom_px:, :] = False
        if left_px > 0:
            mask[:, :left_px] = False
        if right_px > 0:
            mask[:, -right_px:] = False

        out = surface.copy()
        out.mask = mask
        # Set values outside mask to NaN
        out.height[~mask] = np.nan
        return out


class ErosionROI:
    """Erode mask to remove edge artifacts.
    
    Useful for removing unstable edges after auto-ROI or interpolation.
    Uses morphological erosion to shrink the valid region.
    """
    def __init__(self, radius=1):
        """
        Parameters
        ----------
        radius : int
            Erosion radius in pixels. Default is 1 (removes 1-pixel border).
        """
        self.radius = radius
    
    def apply(self, surface):
        """Apply erosion to surface mask."""
        # Create circular structuring element
        size = 2 * self.radius + 1
        y, x = np.ogrid[-self.radius:self.radius+1, -self.radius:self.radius+1]
        structure = (x**2 + y**2 <= self.radius**2)
        
        # Erode mask
        eroded_mask = binary_erosion(surface.mask, structure=structure)
        
        out = surface.copy()
        out.mask = eroded_mask
        # Set values outside mask to NaN
        out.height[~eroded_mask] = np.nan
        return out


class RectangleROI:
    """Select rectangular region of interest in physical coordinates.
    
    Useful when you want to analyze a specific area of the surface,
    defined by physical coordinates (e.g., center section, avoiding edges).
    
    Parameters
    ----------
    x_start, x_end : float
        Start and end X coordinates in physical units (mm, µm, etc.)
    y_start, y_end : float
        Start and end Y coordinates in physical units
        
    Examples
    --------
    >>> # Select central 0.5×0.5 mm region from 1×1 mm surface
    >>> roi = RectangleROI(x_start=0.25, x_end=0.75, y_start=0.25, y_end=0.75)
    >>> surface_roi = roi.apply(surface)
    """
    def __init__(self, x_start, x_end, y_start, y_end):
        """
        Initialize rectangular ROI.
        
        Coordinates are in physical units and will be converted to pixels
        based on surface dx/dy.
        """
        if x_end <= x_start:
            raise ValueError("RectangleROI: x_end must be > x_start")
        if y_end <= y_start:
            raise ValueError("RectangleROI: y_end must be > y_start")
            
        self.x_start = x_start
        self.x_end = x_end
        self.y_start = y_start
        self.y_end = y_end
    
    def apply(self, surface):
        """Apply rectangular ROI to surface."""
        ny, nx = surface.height.shape
        
        # Convert physical coordinates to pixel indices (accounting for surface origin)
        x_start_px = max(0, int((self.x_start - surface.x0) / surface.dx))
        x_end_px = min(nx, int((self.x_end - surface.x0) / surface.dx))
        y_start_px = max(0, int((self.y_start - surface.y0) / surface.dy))
        y_end_px = min(ny, int((self.y_end - surface.y0) / surface.dy))
        
        # Validate that ROI is within bounds
        if x_start_px >= x_end_px or y_start_px >= y_end_px:
            raise ValueError(
                f"RectangleROI: Invalid ROI bounds. "
                f"Physical: x=[{self.x_start}, {self.x_end}], y=[{self.y_start}, {self.y_end}]. "
                f"Pixels: x=[{x_start_px}, {x_end_px}], y=[{y_start_px}, {y_end_px}]. "
                f"Surface size: {nx}×{ny} pixels"
            )
        
        # Create mask
        mask = np.zeros_like(surface.mask, dtype=bool)
        mask[y_start_px:y_end_px, x_start_px:x_end_px] = True
        
        # Combine with existing mask
        mask = mask & surface.mask
        
        out = surface.copy()
        out.mask = mask
        # Set values outside mask to NaN
        out.height[~mask] = np.nan
        return out


class CenterROI:
    """Select centered rectangular region of specified size.
    
    Automatically centers the ROI on the surface, useful for analyzing
    the central region while avoiding edge effects.
    
    Parameters
    ----------
    width : float
        Width of ROI in physical units
    height : float, optional
        Height of ROI in physical units. If None, uses width (square ROI)
        
    Examples
    --------
    >>> # Select centered 0.5×0.5 mm square
    >>> roi = CenterROI(width=0.5)
    >>> surface_roi = roi.apply(surface)
    
    >>> # Select centered 0.6×0.4 mm rectangle
    >>> roi = CenterROI(width=0.6, height=0.4)
    >>> surface_roi = roi.apply(surface)
    """
    def __init__(self, width, height=None):
        """
        Initialize centered ROI.
        
        If height is None, creates a square ROI with size width×width.
        """
        if width <= 0:
            raise ValueError("CenterROI: width must be > 0")
        
        self.width = width
        self.height = height if height is not None else width
        
        if self.height <= 0:
            raise ValueError("CenterROI: height must be > 0")
    
    def apply(self, surface):
        """Apply centered ROI to surface."""
        ny, nx = surface.height.shape
        
        # Calculate surface dimensions
        surface_width = nx * surface.dx
        surface_height = ny * surface.dy
        
        # Check if ROI fits
        if self.width > surface_width:
            raise ValueError(
                f"CenterROI: width {self.width} exceeds surface width {surface_width}"
            )
        if self.height > surface_height:
            raise ValueError(
                f"CenterROI: height {self.height} exceeds surface height {surface_height}"
            )
        
        # Calculate centered coordinates (accounting for surface origin)
        x_center = surface.x0 + surface_width / 2
        y_center = surface.y0 + surface_height / 2
        
        x_start = x_center - self.width / 2
        x_end = x_center + self.width / 2
        y_start = y_center - self.height / 2
        y_end = y_center + self.height / 2
        
        # Use RectangleROI for actual implementation
        rect_roi = RectangleROI(x_start, x_end, y_start, y_end)
        return rect_roi.apply(surface)


class CircleROI:
    """Select circular region of interest.
    
    Useful for analyzing circular specimens or focusing on a radially
    symmetric region.
    
    Parameters
    ----------
    center_x, center_y : float
        Center coordinates in physical units
    radius : float
        Radius in physical units
        
    Examples
    --------
    >>> # Select 0.3 mm radius circle at center
    >>> roi = CircleROI(center_x=0.5, center_y=0.5, radius=0.3)
    >>> surface_roi = roi.apply(surface)
    """
    def __init__(self, center_x, center_y, radius):
        """Initialize circular ROI."""
        if radius <= 0:
            raise ValueError("CircleROI: radius must be > 0")
        
        self.center_x = center_x
        self.center_y = center_y
        self.radius = radius
    
    def apply(self, surface, combine='and'):
        """Apply circular ROI to surface.
        combine can be 'and' (default) to intersect with existing mask,
        or 'or' to union,
        or 'replace' to ignore existing mask.
        """
        ny, nx = surface.height.shape
        
        # Create coordinate grids in physical units, including surface origin
        x = surface.x0 + np.arange(nx) * surface.dx
        y = surface.y0 + np.arange(ny) * surface.dy
        X, Y = np.meshgrid(x, y)
        
        # Calculate distance from center
        dist = np.sqrt((X - self.center_x)**2 + (Y - self.center_y)**2)
        
        # Create circular mask
        mask = dist <= self.radius
        
        # Combine with existing mask
        if combine == 'and':
            mask = mask & surface.mask
        elif combine == 'or':
            mask = mask | surface.mask
        elif combine == 'replace':
            pass  # use mask as is
        
        out = surface.copy()
        out.mask = mask
        # Set values outside mask to NaN
        out.height[~mask] = np.nan
        return out


class AnnulusROI:
    """Select annular (ring-shaped) region of interest.
    
    Useful for analyzing tubular specimens like broken pipes, where you want
    to focus on the material between inner and outer radii.
    
    Parameters
    ----------
    center_x, center_y : float
        Center coordinates in physical units
    inner_radius : float
        Inner radius in physical units
    outer_radius : float
        Outer radius in physical units
        
    Examples
    --------
    >>> # Select ring with inner radius 0.2 mm and outer radius 0.4 mm
    >>> roi = AnnulusROI(center_x=0.5, center_y=0.5, inner_radius=0.2, outer_radius=0.4)
    >>> surface_roi = roi.apply(surface)
    """
    def __init__(self, center_x, center_y, inner_radius, outer_radius):
        """Initialize annular ROI."""
        if inner_radius < 0:
            raise ValueError("AnnulusROI: inner_radius must be >= 0")
        if outer_radius <= 0:
            raise ValueError("AnnulusROI: outer_radius must be > 0")
        if inner_radius >= outer_radius:
            raise ValueError("AnnulusROI: inner_radius must be < outer_radius")
        
        self.center_x = center_x
        self.center_y = center_y
        self.inner_radius = inner_radius
        self.outer_radius = outer_radius
    
    def apply(self, surface):
        """Apply annular ROI to surface."""
        ny, nx = surface.height.shape
        
        # Create coordinate grids in physical units, including surface origin
        x = surface.x0 + np.arange(nx) * surface.dx
        y = surface.y0 + np.arange(ny) * surface.dy
        X, Y = np.meshgrid(x, y)
        
        # Calculate distance from center
        dist = np.sqrt((X - self.center_x)**2 + (Y - self.center_y)**2)
        
        # Create annular mask (ring between inner and outer radius)
        mask = (dist >= self.inner_radius) & (dist <= self.outer_radius)
        
        # Combine with existing mask
        mask = mask & surface.mask
        
        out = surface.copy()
        out.mask = mask
        # Set values outside mask to NaN
        out.height[~mask] = np.nan
        return out


class PolygonROI:
    """Select polygonal region of interest.
    
    Define an arbitrary polygon by specifying vertices in physical coordinates.
    Uses point-in-polygon test to create mask.
    
    Parameters
    ----------
    vertices : array-like of shape (N, 2)
        Polygon vertices as [(x1, y1), (x2, y2), ...] in physical units.
        Vertices should be ordered (clockwise or counter-clockwise).
        
    Examples
    --------
    >>> # Select triangular region
    >>> roi = PolygonROI(vertices=[(0.2, 0.2), (0.8, 0.2), (0.5, 0.8)])
    >>> surface_roi = roi.apply(surface)
    """
    def __init__(self, vertices):
        """Initialize polygonal ROI."""
        vertices = np.asarray(vertices)
        if vertices.shape[1] != 2:
            raise ValueError("PolygonROI: vertices must have shape (N, 2)")
        if len(vertices) < 3:
            raise ValueError("PolygonROI: need at least 3 vertices")
        
        self.vertices = vertices
    
    def apply(self, surface):
        """Apply polygonal ROI to surface."""
        from matplotlib.path import Path
        
        ny, nx = surface.height.shape
        
        # Create coordinate grids in physical units, including surface origin
        x = surface.x0 + np.arange(nx) * surface.dx
        y = surface.y0 + np.arange(ny) * surface.dy
        X, Y = np.meshgrid(x, y)
        
        # Flatten coordinates for point-in-polygon test
        points = np.column_stack([X.ravel(), Y.ravel()])
        
        # Create path and test
        path = Path(self.vertices)
        mask = path.contains_points(points).reshape(ny, nx)
        
        # Combine with existing mask
        mask = mask & surface.mask
        
        out = surface.copy()
        out.mask = mask
        # Set values outside mask to NaN
        out.height[~mask] = np.nan
        return out
