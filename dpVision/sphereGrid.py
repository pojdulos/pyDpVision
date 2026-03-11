# -*- coding: utf-8 -*-
"""
SphereGrid — sferyczna siatka danych (Range Image).

Układ osi:
  - kolumna j  : kąt azymutu  φ [°], zakres azimuth_range
  - wiersz  i  : kąt elewacji θ [°], zakres elevation_range
  - wartość    : zasięg r (odległość od origin) [jedn.]

Konwencja kartezjańska:
  x = r · cos(θ) · cos(φ)   (Az 0° = +X)
  y = r · cos(θ) · sin(φ)   (Az 90° = +Y)
  z = r · sin(θ)             (El +90° = +Z / zenit)

Typowe zastosowania: skanery LiDAR (Velodyne, Ouster, Hesai),
sferyczne skanery naziemne, panoramiczne kamery głębi.
"""

import numpy as np
from OpenGL.GL import *

from .object import Object
from .shaders import create_program
from .colormaps import make_colormap

# Maksymalna liczba pikseli wgrywanej do GPU tekstury RGBA32F.
# Przy 16 MB px × 16 B/px = 256 MB VRAM — bezpieczny limit dla większości kart.
# Większe siatki są automatycznie próbkowane przed wgraniem.
_GPU_MAX_PIXELS = 16 * 1024 * 1024


class SphereGrid(Object):
    """
    Sferyczna siatka danych (range image).

    Parametry
    ----------
    range_map : array_like, shape (H, W)
        Macierz zasięgów [jedn.]. NaN / <=0 oznacza punkt nieważny.
    azimuth_range : (float, float)
        Zakres azymutu [°]: (min, max). Domyślnie (0, 360).
    elevation_range : (float, float)
        Zakres elewacji [°]: (min, max). Domyślnie (-90, 90).
    intensity : array_like shape (H, W) or None
        Intensywność odbicia [0..1] — typowy kanał LiDAR. Opcjonalne.
    rgb : array_like shape (H, W, 3) uint8 or None
        Kolor z kamery RGB (po kalibracji z sensorem). Opcjonalne.
    origin : (float, float, float)
        Pozycja czujnika w przestrzeni świata. Domyślnie (0, 0, 0).
    parent : Object or None
    unit : str
        Jednostka zasięgu ('m', 'mm', ...).
    """

    def __init__(self,
                 range_map,
                 azimuth_range=(0.0, 360.0),
                 elevation_range=(-90.0, 90.0),
                 intensity=None,
                 rgb=None,
                 origin=(0.0, 0.0, 0.0),
                 parent=None,
                 unit="m"):

        Object.__init__(self, parent)

        self._range = np.asarray(range_map, dtype=np.float32)
        if self._range.ndim != 2:
            raise ValueError("range_map musi być macierzą 2D (H × W)")

        self._mask = np.isfinite(self._range) & (self._range > 0.0)

        self.azimuth_range   = tuple(float(v) for v in azimuth_range)    # (min, max) [°]
        self.elevation_range = tuple(float(v) for v in elevation_range)  # (min, max) [°]
        self.origin          = np.asarray(origin, dtype=np.float32)
        self.unit            = unit

        # Opcjonalne kanały dodatkowe
        if intensity is not None:
            self._intensity = np.asarray(intensity, dtype=np.float32)
            if self._intensity.shape != self._range.shape:
                raise ValueError("intensity musi mieć ten sam kształt co range_map")
        else:
            self._intensity = None

        if rgb is not None:
            self._rgb = np.asarray(rgb, dtype=np.uint8)
            if self._rgb.shape[:2] != self._range.shape or self._rgb.shape[2] != 3:
                raise ValueError("rgb musi mieć kształt (H, W, 3)")
        else:
            self._rgb = None

        # Ustawienia wizualizacji
        self.use_uniform_color   = True
        self.uniform_color       = [0.6, 0.6, 0.6]
        self.color_by_intensity  = False   # True → paleta wg intensywności, False → wg zasięgu
        self._colormap_name      = 'skala'
        self.vmin                = None    # None = auto
        self.vmax                = None

        # Zasoby OpenGL
        self.shader_program = None
        self.tex            = None         # tekstura RGBA32F (range, intensity, 0, mask)
        self.palette_tex    = None
        self._render_h      = None         # wymiary tekstury GPU (po próbkowaniu)
        self._render_w      = None

    # ------------------------------------------------------------------
    # Właściwości geometryczne
    # ------------------------------------------------------------------

    @property
    def shape(self):
        """(H, W) — liczba wierszy (elewacja) × kolumn (azymut)."""
        return self._range.shape

    @property
    def h(self):
        return self._range.shape[0]

    @property
    def w(self):
        return self._range.shape[1]

    @property
    def range_map(self):
        return self._range

    @range_map.setter
    def range_map(self, value):
        self._range = np.asarray(value, dtype=np.float32)
        self._mask  = np.isfinite(self._range) & (self._range > 0.0)
        self.vmin = self.vmax = None
        self.invalidate_bb()

    @property
    def mask(self):
        return self._mask

    @property
    def intensity(self):
        return self._intensity

    @intensity.setter
    def intensity(self, value):
        self._intensity = np.asarray(value, dtype=np.float32) if value is not None else None

    @property
    def rgb(self):
        return self._rgb

    @rgb.setter
    def rgb(self, value):
        self._rgb = np.asarray(value, dtype=np.uint8) if value is not None else None

    # ------------------------------------------------------------------
    # Kroki kątowe (computed)
    # ------------------------------------------------------------------

    @property
    def d_azimuth(self):
        """Krok kątowy jednej kolumny [°]."""
        return (self.azimuth_range[1] - self.azimuth_range[0]) / self.w

    @property
    def d_elevation(self):
        """Krok kątowy jednego wiersza [°]."""
        return (self.elevation_range[1] - self.elevation_range[0]) / self.h

    # ------------------------------------------------------------------
    # Fabryki
    # ------------------------------------------------------------------

    @classmethod
    def from_point_cloud(cls, pc, azimuth_range=(0.0, 360.0), elevation_range=(-90.0, 90.0),
                         width=360, height=180, origin=(0, 0, 0), parent=None, unit="m"):
        """
        Utwórz SphereGrid przez rzutowanie chmury punktów na siatkę sferyczną.

        pc : PointCloud
        width, height : rozdzielczość siatki (kolumny × wiersze)
        """
        pts = pc.m_vertices - np.asarray(origin, dtype=np.float32)

        r   = np.linalg.norm(pts, axis=1)
        az  = np.degrees(np.arctan2(pts[:, 1], pts[:, 0]))   # −180..+180
        el  = np.degrees(np.arcsin(np.clip(pts[:, 2] / np.where(r > 0, r, 1), -1, 1)))

        # Normalizuj azymut do zakresu azimuth_range
        az = az % 360.0
        az_min, az_max = azimuth_range
        el_min, el_max = elevation_range

        range_map = np.full((height, width), np.nan, dtype=np.float32)

        j_idx = ((az - az_min) / (az_max - az_min) * width).astype(int)
        i_idx = ((el - el_min) / (el_max - el_min) * height).astype(int)

        valid = (j_idx >= 0) & (j_idx < width) & (i_idx >= 0) & (i_idx < height) & (r > 0)

        # Dla punktów trafniętych do tego samego piksela zostawiamy bliższy
        for k in np.where(valid)[0]:
            ii, jj = i_idx[k], j_idx[k]
            if np.isnan(range_map[ii, jj]) or r[k] < range_map[ii, jj]:
                range_map[ii, jj] = r[k]

        intens = None
        if pc.m_vcolors.shape[0] == pc.m_vertices.shape[0]:
            intens_full = pc.m_vcolors[:, :3].mean(axis=1).astype(np.float32) / 255.0
            intens_map  = np.full((height, width), 0.0, dtype=np.float32)
            for k in np.where(valid)[0]:
                intens_map[i_idx[k], j_idx[k]] = intens_full[k]
            intens = intens_map

        return cls(range_map, azimuth_range=azimuth_range, elevation_range=elevation_range,
                   intensity=intens, origin=origin, parent=parent, unit=unit)

    # ------------------------------------------------------------------
    # Konwersja do PointCloud
    # ------------------------------------------------------------------

    def to_point_cloud(self):
        """Konwertuje zasięgi do kartezjańskiej PointCloud."""
        from .pointCloud import PointCloud

        rows, cols = self._range.shape

        j_arr = np.arange(cols, dtype=np.float32)
        i_arr = np.arange(rows, dtype=np.float32)
        jj, ii = np.meshgrid(j_arr, i_arr)

        az_deg = self.azimuth_range[0]   + (jj + 0.5) * self.d_azimuth
        el_deg = self.elevation_range[0] + (ii + 0.5) * self.d_elevation
        az = np.deg2rad(az_deg)
        el = np.deg2rad(el_deg)

        r = self._range
        cos_el = np.cos(el)
        x = (r * cos_el * np.cos(az) + self.origin[0]).astype(np.float32)
        y = (r * cos_el * np.sin(az) + self.origin[1]).astype(np.float32)
        z = (r * np.sin(el)          + self.origin[2]).astype(np.float32)

        valid = self._mask
        pts = np.stack([x[valid], y[valid], z[valid]], axis=1)

        pc = PointCloud()
        pc.m_vertices = pts

        # Kolory: preferuj RGB → intensywność → brak
        if self._rgb is not None:
            rgb_valid = self._rgb[valid]
            pc.m_vcolors = np.column_stack([
                rgb_valid,
                np.full(len(rgb_valid), 255, dtype=np.uint8)
            ])
        elif self._intensity is not None:
            c = (np.clip(self._intensity[valid], 0.0, 1.0) * 255).astype(np.uint8)
            pc.m_vcolors = np.column_stack([c, c, c, np.full_like(c, 255)])

        return pc

    # ------------------------------------------------------------------
    # Colormap
    # ------------------------------------------------------------------

    def get_colormap_range(self):
        """Zwraca (vmin, vmax) dla aktualnego kanału koloru."""
        if self.color_by_intensity and self._intensity is not None:
            data = self._intensity[self._mask]
        else:
            data = self._range[self._mask]

        if self.vmin is None or self.vmax is None:
            if len(data):
                self.vmin = float(np.min(data))
                self.vmax = float(np.max(data))
            else:
                self.vmin, self.vmax = 0.0, 1.0
        return self.vmin, self.vmax

    def set_colormap(self, name):
        """Ustaw colormapę (np. 'jet', 'skala', 'gray', ...)."""
        self._colormap_name = name
        if self.palette_tex is not None:
            self.upload_palette_to_gpu()

    # ------------------------------------------------------------------
    # OpenGL - inicjalizacja i rendering
    # ------------------------------------------------------------------

    def _build_texture_data(self):
        """Pakuje (range, intensity, 0, mask) → RGBA32F (rH × rW × 4).

        Jeśli siatka ma ponad _GPU_MAX_PIXELS pikseli, jest próbkowana co
        `step` wierszy/kolumn tak, by zmieścić się w limicie VRAM.
        Ustala self._render_h / self._render_w używane przez renderSelf().
        """
        H, W = self._range.shape
        step = 1
        if H * W > _GPU_MAX_PIXELS:
            import math
            step = max(2, math.ceil(math.sqrt(H * W / _GPU_MAX_PIXELS)))
            print(f"SphereGrid: siatka {W}×{H} ({H*W//1_000_000}M px) "
                  f"→ próbkowanie co {step} (GPU limit {_GPU_MAX_PIXELS//1_000_000}M px)")

        rng = self._range[::step, ::step]
        msk = self._mask [::step, ::step]
        rH, rW = rng.shape
        self._render_h = rH
        self._render_w = rW

        data = np.zeros((rH, rW, 4), dtype=np.float32)
        data[:, :, 0] = rng
        if self._intensity is not None:
            data[:, :, 1] = self._intensity[::step, ::step]
        data[:, :, 3] = msk.astype(np.float32)
        return data

    def upload_to_gpu(self):
        """Tworzy / aktualizuje teksturę RGBA32F w GPU."""
        print(f"  [SphereGrid.upload_to_gpu] {self.w}\u00d7{self.h}...", flush=True)
        data = self._build_texture_data()
        H, W = data.shape[:2]
        print(f"  [SphereGrid.upload_to_gpu] tekstura GPU: {W}\u00d7{H} ({W*H*16//1024//1024} MB)", flush=True)

        if self.tex is None:
            self.tex = glGenTextures(1)

        glBindTexture(GL_TEXTURE_2D, self.tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA32F,
                     W, H, 0,
                     GL_RGBA, GL_FLOAT, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glBindTexture(GL_TEXTURE_2D, 0)
        print(f"  [SphereGrid.upload_to_gpu] upload OK", flush=True)

    def upload_palette_to_gpu(self):
        """Tworzy / aktualizuje 256×1 teksturę RGB z aktualną paletą."""
        colors = make_colormap(self._colormap_name)   # (256, 3) float32
        rgba = np.concatenate(
            [colors, np.ones((len(colors), 1), dtype=np.float32)], axis=1
        )
        if self.palette_tex is None:
            self.palette_tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.palette_tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA32F,
                     len(colors), 1, 0,
                     GL_RGBA, GL_FLOAT, rgba)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE)
        glBindTexture(GL_TEXTURE_2D, 0)

    def initializeGL(self):
        self.upload_to_gpu()
        self.shader_program = create_program(
            vertex_shader_name='sphereGrid.vert',
            fragment_shader_name='sphereGrid.frag'
        )
        self.upload_palette_to_gpu()

    def renderSelf(self):
        if self.shader_program is None:
            self.initializeGL()

        glUseProgram(self.shader_program)

        # --- MVP ---
        modelview  = np.array(glGetFloatv(GL_MODELVIEW_MATRIX),  dtype=np.float32).T
        projection = np.array(glGetFloatv(GL_PROJECTION_MATRIX), dtype=np.float32).T
        mvp = projection @ modelview

        glUniformMatrix4fv(
            glGetUniformLocation(self.shader_program, "u_mvp"),
            1, GL_FALSE, mvp.T
        )

        # --- Rozmiar siatki (renderowa, po ewentualnym próbkowaniu) ---
        rw = getattr(self, '_render_w', self.w)
        rh = getattr(self, '_render_h', self.h)
        glUniform1i(glGetUniformLocation(self.shader_program, "u_width"),  rw)
        glUniform1i(glGetUniformLocation(self.shader_program, "u_height"), rh)

        # --- Kąty (kroki kątowe dostosowane do rozdzielczości renderowej) ---
        d_az_render = (self.azimuth_range[1]   - self.azimuth_range[0])   / rw
        d_el_render = (self.elevation_range[1] - self.elevation_range[0]) / rh
        glUniform1f(glGetUniformLocation(self.shader_program, "u_az_min"), self.azimuth_range[0])
        glUniform1f(glGetUniformLocation(self.shader_program, "u_d_az"),   d_az_render)
        glUniform1f(glGetUniformLocation(self.shader_program, "u_el_min"), self.elevation_range[0])
        glUniform1f(glGetUniformLocation(self.shader_program, "u_d_el"),   d_el_render)

        # --- Origin ---
        glUniform3fv(glGetUniformLocation(self.shader_program, "u_origin"), 1,
                     self.origin.astype(np.float32))

        # --- Tekstura danych (unit 0) ---
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.tex)
        glUniform1i(glGetUniformLocation(self.shader_program, "u_gridTex"), 0)

        # --- Paleta kolorów (unit 1) ---
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, self.palette_tex)
        glUniform1i(glGetUniformLocation(self.shader_program, "u_palette"), 1)
        glActiveTexture(GL_TEXTURE0)

        # --- Tryb koloru ---
        minVal, maxVal = self.get_colormap_range()
        glUniform1f(glGetUniformLocation(self.shader_program, "u_minVal"), minVal)
        glUniform1f(glGetUniformLocation(self.shader_program, "u_maxVal"), maxVal)
        glUniform1i(glGetUniformLocation(self.shader_program, "u_useUniformColor"),  int(self.use_uniform_color))
        glUniform3fv(glGetUniformLocation(self.shader_program, "u_uniformColor"),    1, self.uniform_color)
        glUniform1i(glGetUniformLocation(self.shader_program, "u_colorByIntensity"), int(self.color_by_intensity))

        # --- Rysowanie (jeden punkt na każdą komórkę renderowej siatki) ---
        glEnable(GL_PROGRAM_POINT_SIZE)
        glPointSize(1)
        glDrawArrays(GL_POINTS, 0, rh * rw)

        # --- Sprzątanie ---
        glActiveTexture(GL_TEXTURE1)
        glBindTexture(GL_TEXTURE_2D, 0)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, 0)
        glUseProgram(0)

    def update_data(self, range_map, intensity=None, rgb=None):
        """Aktualizuje dane i odświeża GPU (bez zmiany rozdzielczości / zakresów)."""
        self._range = np.asarray(range_map, dtype=np.float32)
        self._mask  = np.isfinite(self._range) & (self._range > 0.0)
        self._intensity = (np.asarray(intensity, dtype=np.float32)
                           if intensity is not None else None)
        self._rgb       = (np.asarray(rgb, dtype=np.uint8)
                           if rgb is not None else None)
        self.vmin = self.vmax = None
        if self.tex is not None:
            self.upload_to_gpu()
        self.invalidate_bb()

    # ------------------------------------------------------------------
    # Bounding box
    # ------------------------------------------------------------------

    def getBB(self):
        _b, _min1, _max1 = Object.getBB(self)

        valid_r = self._range[self._mask]
        if len(valid_r) == 0:
            return _b, _min1, _max1

        # Analityczne AABB — O(1) pamięci.
        # Konwertujemy 8 narożников (r_min/max × az_min/max × el_min/max)
        # do kartezjańskich i bierzemy min/max.
        # Wynik jest konserwatywny (nieco za duży) ale natychmiastowy
        # — żadnych meshgridów ani pętli po milionach punktów.
        r_min = float(valid_r.min())
        r_max = float(valid_r.max())
        az_lo, az_hi = np.deg2rad(self.azimuth_range[0]),   np.deg2rad(self.azimuth_range[1])
        el_lo, el_hi = np.deg2rad(self.elevation_range[0]), np.deg2rad(self.elevation_range[1])

        corners = []
        for r in (r_min, r_max):
            for az in (az_lo, az_hi):
                for el in (el_lo, el_hi):
                    cos_el = np.cos(el)
                    corners.append([
                        r * cos_el * np.cos(az) + self.origin[0],
                        r * cos_el * np.sin(az) + self.origin[1],
                        r * np.sin(el)          + self.origin[2],
                    ])
        corners = np.array(corners, dtype=np.float32)
        pt_min = corners.min(axis=0).tolist()
        pt_max = corners.max(axis=0).tolist()

        if not _b:
            self._cached_bb = (True, pt_min, pt_max)
        else:
            merged_min = [min(a, b) for a, b in zip(_min1, pt_min)]
            merged_max = [max(a, b) for a, b in zip(_max1, pt_max)]
            self._cached_bb = (True, merged_min, merged_max)

        return self._cached_bb

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self):
        return (f"SphereGrid(shape={self.shape}, "
                f"az={self.azimuth_range}, el={self.elevation_range}, "
                f"unit='{self.unit}', valid={int(self._mask.sum())}pts)")
