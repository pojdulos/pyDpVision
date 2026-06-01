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
from enum import IntEnum
from OpenGL.GL import *

from .object import Object
from .shaders import create_program
from .colormaps import make_colormap

# Maksymalna liczba pikseli wgrywanej do GPU tekstury RGBA32F.
_GPU_MAX_PIXELS = 16 * 1024 * 1024


class DisplayMode(IntEnum):
    RGB          = 0   # kolor z pliku JPG / E57 (wymaga _rgb)
    INTENSITY    = 1   # intensywnosc (wymaga _intensity)
    GREYSCALE    = 2   # jasnosc z RGB lub intensity jako skala szarosci
    RANGE_COLOR  = 3   # colormap wg odleglosci od skanera
    UNIFORM      = 4   # staly kolor
    SPLAT        = 5   # Gaussian splat (rozmiar splatu wg zasiegu i kroku katowego)
    UNCERTAINTY  = 6   # miara niepewnosci: sigma = range * d_theta [m]


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
                 unit="m",
                 az_per_col=None,
                 el_per_row=None):

        Object.__init__(self, parent)

        self._range = np.asarray(range_map, dtype=np.float32)
        if self._range.ndim != 2:
            raise ValueError("range_map musi być macierzą 2D (H × W)")

        self._mask = np.isfinite(self._range) & (self._range > 0.0)

        self.azimuth_range   = tuple(float(v) for v in azimuth_range)    # (min, max) [°]
        self.elevation_range = tuple(float(v) for v in elevation_range)  # (min, max) [°]
        self.origin          = np.asarray(origin, dtype=np.float32)
        self.unit            = unit

        # Mapy kątowe (1D) — eliminują zniekształcenia przy rekonstrukcji sferycznej
        self._az_per_col = np.asarray(az_per_col, dtype=np.float32) if az_per_col is not None else None
        self._el_per_row = np.asarray(el_per_row, dtype=np.float32) if el_per_row is not None else None

        # Opcjonalne kanały dodatkowe
        if intensity is not None:
            self._intensity = np.asarray(intensity, dtype=np.float32)
            if self._intensity.shape != self._range.shape:
                raise ValueError("intensity musi mieć ten sam kształt co range_map")
        else:
            self._intensity = None

        if rgb is not None:
            self._rgb = np.asarray(rgb, dtype=np.uint8)
            H, W = self._range.shape
            rh, rw = self._rgb.shape[:2]
            if self._rgb.ndim != 3 or self._rgb.shape[2] != 3:
                raise ValueError("rgb musi mieć kształt (H, W, 3)")
            if not ((rh == H and rw == W) or (rh == H - 1 and rw == W - 1)):
                raise ValueError(f"rgb musi mieć kształt ({H}\u00d7{W}) lub ({H-1}\u00d7{W-1})")
        else:
            self._rgb = None

        # Ustawienia wizualizacji
        # Tryb domyslny: RGB jesli dostepny, inaczej RANGE_COLOR
        if self._rgb is not None:
            self.display_mode    = DisplayMode.RGB
        elif self._intensity is not None:
            self.display_mode    = DisplayMode.INTENSITY
        else:
            self.display_mode    = DisplayMode.RANGE_COLOR
        self.uniform_color       = [0.6, 0.6, 0.6]
        self._colormap_name      = 'skala'
        self.vmin                = None    # None = auto
        self.vmax                = None
        self.splat_scale         = 1.0    # mnożnik rozmiaru splatów

        # Zasoby OpenGL
        self.shader_program = None
        self.tex            = None         # tekstura RGBA32F (range, intensity, 0, mask)
        self.palette_tex    = None
        self._render_h      = None         # wymiary tekstury GPU (po próbkowaniu)
        self._render_w      = None
        self.fast_shader    = None         # shader dla pre-baked VBO
        self._fast_vbo      = None         # VBO z pre-baked XYZ (tylko ważne punkty)
        self._fast_vbo_count = 0
        self.splat_shader   = None         # shader Gaussian splat
        self.wboit_splat_shader = None

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
        """Zwraca (vmin, vmax) dla aktualnego kanalu koloru."""
        # Dla SPLAT uzyj trybu koloru splatu, nie samego SPLAT
        effective = self.display_mode
        if effective == DisplayMode.SPLAT:
            effective = self._splat_color_mode

        if effective == DisplayMode.UNCERTAINTY:
            # sigma_lateral = range * d_theta_rad — obliczane zawsze swiezo
            ang = float(np.deg2rad(max(abs(self.d_azimuth), abs(self.d_elevation))))
            valid_r = self._range[self._mask]
            if len(valid_r):
                return float(np.min(valid_r) * ang), float(np.max(valid_r) * ang)
            return 0.0, 1.0

        if effective == DisplayMode.INTENSITY and self._intensity is not None:
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
        print(f"  [SphereGrid.upload_to_gpu] tekstura OK", flush=True)

        # --- Pre-baked VBO (tylko ważne punkty, szybkie renderowanie) ---
        vbo_data = self._bake_vbo()
        n_pts = len(vbo_data)
        print(f"  [SphereGrid.upload_to_gpu] VBO: {n_pts:,} punktów", flush=True)
        if self._fast_vbo is None:
            self._fast_vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self._fast_vbo)
        glBufferData(GL_ARRAY_BUFFER, vbo_data.nbytes, vbo_data, GL_STATIC_DRAW)
        glBindBuffer(GL_ARRAY_BUFFER, 0)
        self._fast_vbo_count = n_pts
        print(f"  [SphereGrid.upload_to_gpu] VBO OK", flush=True)

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

    def _bake_vbo(self):
        """Pre-compute XYZ+value buffer dla ważnych komórek siatki.
        Korzysta z map kątowych (az_per_col, el_per_row) jeśli dostępne,
        co eliminuje zniekształcenia wynikające z liniowej interpolacji kątów.
        Zwraca tablicę float32 (N, 5): x, y, z, range, intensity."""
        import math
        H, W = self._range.shape
        step = 1
        if H * W > _GPU_MAX_PIXELS:
            step = max(2, math.ceil(math.sqrt(H * W / _GPU_MAX_PIXELS)))

        rng = self._range[::step, ::step]
        msk = self._mask [::step, ::step]
        rH, rW = rng.shape

        # Azymut na kolumnę [rad]
        if self._az_per_col is not None:
            az_arr = self._az_per_col[::step]
            # Zastąp NaN interpolacją liniową
            if not np.isfinite(az_arr).all():
                az_lin = self.azimuth_range[0] + (np.arange(rW, dtype=np.float32) + 0.5) * \
                         (self.azimuth_range[1] - self.azimuth_range[0]) / rW
                az_arr = np.where(np.isfinite(az_arr), az_arr, az_lin)
            az_col = np.deg2rad(az_arr.astype(np.float32))
        else:
            az_col = np.deg2rad(
                self.azimuth_range[0] +
                (np.arange(rW, dtype=np.float32) + 0.5) *
                (self.azimuth_range[1] - self.azimuth_range[0]) / rW
            )

        # Elewacja na wiersz [rad]
        if self._el_per_row is not None:
            el_arr = self._el_per_row[::step]
            if not np.isfinite(el_arr).all():
                el_lin = self.elevation_range[0] + (np.arange(rH, dtype=np.float32) + 0.5) * \
                         (self.elevation_range[1] - self.elevation_range[0]) / rH
                el_arr = np.where(np.isfinite(el_arr), el_arr, el_lin)
            el_row = np.deg2rad(el_arr.astype(np.float32))
        else:
            el_row = np.deg2rad(
                self.elevation_range[0] +
                (np.arange(rH, dtype=np.float32) + 0.5) *
                (self.elevation_range[1] - self.elevation_range[0]) / rH
            )

        # Broadcast do 2D i odfiltruj ważne
        az_2d = np.broadcast_to(az_col[np.newaxis, :], (rH, rW))
        el_2d = np.broadcast_to(el_row[:, np.newaxis], (rH, rW))
        msk_f = msk.ravel()
        r     = rng.ravel()[msk_f].astype(np.float32)
        az    = az_2d.ravel()[msk_f].astype(np.float32)
        el    = el_2d.ravel()[msk_f].astype(np.float32)

        cos_el = np.cos(el)
        x = r * cos_el * np.cos(az) + self.origin[0]
        y = r * cos_el * np.sin(az) + self.origin[1]
        z = r * np.sin(el)          + self.origin[2]

        if self._intensity is not None:
            intens = self._intensity[::step, ::step].ravel()[msk_f].astype(np.float32)
        else:
            intens = np.zeros(len(r), dtype=np.float32)

        # RGB (0.0-1.0) — trafia do VBO jako atrybuty wierzchołka
        if self._rgb is not None:
            H_full, W_full = self._range.shape
            rh_t, rw_t = self._rgb.shape[:2]
            between_pts = (rh_t == H_full - 1 and rw_t == W_full - 1)

            if between_pts:
                # Tekstura leży między punktami pomiaru: piksel [i,j] → środek między
                # skanem (i,j) a (i+1,j+1). Biliniarne dostępowanie z offset 0.5:
                # dla punktu skanu [si*step, sj*step] interpolujemy między
                # wierszami/kolumnami [si*step-1] i [si*step] z wagami 0.5/0.5.
                i_orig = np.arange(rH) * step          # oryginalne wiersze skanu
                j_orig = np.arange(rW) * step

                # Elewacja nigdy się nie zapętla — clip
                i0 = np.clip(i_orig - 1, 0, rh_t - 1)  # (rH,)
                i1 = np.clip(i_orig,     0, rh_t - 1)

                # Azymut: przy skanach 360° kolumna 0 sąsiaduje z ostatnią → wrap
                az_span = self.azimuth_range[1] - self.azimuth_range[0]
                if az_span >= 359.9:
                    j0 = (j_orig - 1) % rw_t   # wrap: col 0 → rw_t-1 (piksel po drugiej stronie szwu)
                    j1 =  j_orig      % rw_t
                else:
                    j0 = np.clip(j_orig - 1, 0, rw_t - 1)
                    j1 = np.clip(j_orig,     0, rw_t - 1)
                # Średnio z 4 narożników (waga zawsze 0.25 bo offset = 0.5)
                rgb_2d = (
                    self._rgb[i0[:, None], j0[None, :], :].astype(np.float32) +
                    self._rgb[i0[:, None], j1[None, :], :].astype(np.float32) +
                    self._rgb[i1[:, None], j0[None, :], :].astype(np.float32) +
                    self._rgb[i1[:, None], j1[None, :], :].astype(np.float32)
                ) * 0.25  # (rH, rW, 3) float32
                rf = rgb_2d[:, :, 0].ravel()[msk_f] / 255.0
                gf = rgb_2d[:, :, 1].ravel()[msk_f] / 255.0
                bf = rgb_2d[:, :, 2].ravel()[msk_f] / 255.0
            else:
                rgb_sub = self._rgb[::step, ::step]  # (rH, rW, 3) uint8
                rf = rgb_sub[:, :, 0].ravel()[msk_f].astype(np.float32) / 255.0
                gf = rgb_sub[:, :, 1].ravel()[msk_f].astype(np.float32) / 255.0
                bf = rgb_sub[:, :, 2].ravel()[msk_f].astype(np.float32) / 255.0
        else:
            rf = gf = bf = np.zeros(len(r), dtype=np.float32)

        # Format VBO: x(0) y(4) z(8) range(12) intensity(16) r(20) g(24) b(28) → stride 32
        buf = np.empty((len(r), 8), dtype=np.float32)
        buf[:, 0] = x
        buf[:, 1] = y
        buf[:, 2] = z
        buf[:, 3] = r
        buf[:, 4] = intens
        buf[:, 5] = rf
        buf[:, 6] = gf
        buf[:, 7] = bf
        return buf

    def _render_vbo(self):
        """Szybkie renderowanie z pre-baked VBO przy użyciu fast_shader."""
        if self.display_mode == DisplayMode.SPLAT:
            self._render_vbo_splat()
            return
        import ctypes
        glUseProgram(self.fast_shader)

        modelview  = np.array(glGetFloatv(GL_MODELVIEW_MATRIX),  dtype=np.float32).T
        projection = np.array(glGetFloatv(GL_PROJECTION_MATRIX), dtype=np.float32).T
        mvp = projection @ modelview
        glUniformMatrix4fv(glGetUniformLocation(self.fast_shader, "u_mvp"), 1, GL_FALSE, mvp.T)

        minVal, maxVal = self.get_colormap_range()
        glUniform1f(glGetUniformLocation(self.fast_shader, "u_minVal"), minVal)
        glUniform1f(glGetUniformLocation(self.fast_shader, "u_maxVal"), maxVal)
        glUniform1i(glGetUniformLocation(self.fast_shader, "u_mode"),   int(self.display_mode))
        glUniform3fv(glGetUniformLocation(self.fast_shader, "u_uniformColor"), 1, self.uniform_color)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.palette_tex)
        glUniform1i(glGetUniformLocation(self.fast_shader, "u_palette"), 0)

        glUniform1i(glGetUniformLocation(self.fast_shader, "u_hasRgb"),  int(self._rgb is not None))
        glUniform1i(glGetUniformLocation(self.fast_shader, "u_hasInten"), int(self._intensity is not None))

        # u_ang_step_rad — potrzebny dla trybu UNCERTAINTY (sigma = range * d_theta)
        ang_step_rad = float(np.deg2rad(max(abs(self.d_azimuth), abs(self.d_elevation))))
        glUniform1f(glGetUniformLocation(self.fast_shader, "u_ang_step_rad"), ang_step_rad)

        stride = 8 * 4  # 8 floatow x 4 bajty = 32
        glBindBuffer(GL_ARRAY_BUFFER, self._fast_vbo)
        # attr 0: xyz (offset 0)
        glVertexAttribPointer(0, 3, GL_FLOAT, False, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        # attr 1: range+intensity (offset 12)
        glVertexAttribPointer(1, 2, GL_FLOAT, False, stride, ctypes.c_void_p(12))
        glEnableVertexAttribArray(1)
        # attr 2: rgb 0.0-1.0 (offset 20)
        glVertexAttribPointer(2, 3, GL_FLOAT, False, stride, ctypes.c_void_p(20))
        glEnableVertexAttribArray(2)

        glEnable(GL_PROGRAM_POINT_SIZE)
        glPointSize(1)
        glDrawArrays(GL_POINTS, 0, self._fast_vbo_count)

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisableVertexAttribArray(0)
        glDisableVertexAttribArray(1)
        glDisableVertexAttribArray(2)
        glUseProgram(0)

    def _render_vbo_splat(self):
        """Renderowanie Gaussian splat."""
        import ctypes, traceback
        if self.splat_shader is None:
            # Proba ponownej kompilacji (np. po bledzie przy pierwszym initializeGL)
            self._compile_splat_shader()
        if self.splat_shader is None:
            print('[SphereGrid] SPLAT: brak splat_shader, pomijam render', flush=True)
            return
        try:
            self._render_vbo_splat_impl(ctypes)
        except Exception as e:
            print(f'[SphereGrid] SPLAT render ERROR: {e}', flush=True)
            traceback.print_exc()

    def _render_vbo_splat_impl(self, ctypes):
        glUseProgram(self.splat_shader)

        modelview  = np.array(glGetFloatv(GL_MODELVIEW_MATRIX),  dtype=np.float32).T
        projection = np.array(glGetFloatv(GL_PROJECTION_MATRIX), dtype=np.float32).T
        mvp = projection @ modelview

        glUniformMatrix4fv(glGetUniformLocation(self.splat_shader, "u_mvp"),
                           1, GL_FALSE, mvp.T)
        glUniformMatrix4fv(glGetUniformLocation(self.splat_shader, "u_mv"),
                           1, GL_FALSE, modelview.T)

        ang_step     = max(abs(self.d_azimuth), abs(self.d_elevation))
        ang_step_rad = float(np.deg2rad(ang_step))
        glUniform1f(glGetUniformLocation(self.splat_shader, "u_ang_step_rad"), ang_step_rad)
        glUniform1f(glGetUniformLocation(self.splat_shader, "u_splat_scale"),
                    float(self.splat_scale))

        viewport = glGetIntegerv(GL_VIEWPORT)   # [x, y, w, h]
        glUniform1f(glGetUniformLocation(self.splat_shader, "u_viewport_h"),
                    float(viewport[3]))
        focal_y = float(projection[1, 1])
        glUniform1f(glGetUniformLocation(self.splat_shader, "u_focal_y"), focal_y)

        # --- diagnostyka przy pierwszym wywolaniu ---
        if not getattr(self, '_splat_diag_done', False):
            self._splat_diag_done = True
            valid_r = self._range[self._mask]
            r_med   = float(np.median(valid_r)) if len(valid_r) else 1.0
            world_r   = r_med * ang_step_rad * self.splat_scale
            size_apx  = focal_y * float(viewport[3]) * 0.5 * (2.0 * world_r) / max(r_med, 0.001)
            print(f'[SPLAT DIAG] ang_step={ang_step:.3f}deg  ang_step_rad={ang_step_rad:.5f}')
            print(f'[SPLAT DIAG] focal_y={focal_y:.3f}  viewport_h={viewport[3]}')
            print(f'[SPLAT DIAG] r_median={r_med:.3f}m  world_radius={world_r:.5f}m')
            print(f'[SPLAT DIAG] expected_size_px~={size_apx:.2f}  n_pts={self._fast_vbo_count}',
                  flush=True)

        # Colormap
        minVal, maxVal = self.get_colormap_range()
        glUniform1f(glGetUniformLocation(self.splat_shader, "u_minVal"), minVal)
        glUniform1f(glGetUniformLocation(self.splat_shader, "u_maxVal"), maxVal)
        color_mode = self._splat_color_mode
        glUniform1i(glGetUniformLocation(self.splat_shader, "u_color_mode"), int(color_mode))
        glUniform3fv(glGetUniformLocation(self.splat_shader, "u_uniformColor"), 1,
                     np.array(self.uniform_color, dtype=np.float32))
        glUniform1i(glGetUniformLocation(self.splat_shader, "u_hasRgb"),  int(self._rgb is not None))
        glUniform1i(glGetUniformLocation(self.splat_shader, "u_hasInten"), int(self._intensity is not None))

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.palette_tex)
        glUniform1i(glGetUniformLocation(self.splat_shader, "u_palette"), 0)

        stride = 8 * 4
        glBindBuffer(GL_ARRAY_BUFFER, self._fast_vbo)
        glVertexAttribPointer(0, 3, GL_FLOAT, False, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(1, 2, GL_FLOAT, False, stride, ctypes.c_void_p(12))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(2, 3, GL_FLOAT, False, stride, ctypes.c_void_p(20))
        glEnableVertexAttribArray(2)

        # GL_POINT_SPRITE jest wymagane w trybie kompatybilnosci OpenGL
        # (bez niego gl_PointCoord = (0,0) dla kazdego fragmentu -> wszystko discard)
        try:
            glEnable(GL_POINT_SPRITE)
        except Exception:
            pass   # core profile: GL_POINT_SPRITE nie istnieje — ignoruj

        glEnable(GL_PROGRAM_POINT_SIZE)
        glDepthMask(GL_FALSE)
        glDrawArrays(GL_POINTS, 0, self._fast_vbo_count)
        glDepthMask(GL_TRUE)

        try:
            glDisable(GL_POINT_SPRITE)
        except Exception:
            pass

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisableVertexAttribArray(0)
        glDisableVertexAttribArray(1)
        glDisableVertexAttribArray(2)
        glUseProgram(0)

    @property
    def _splat_color_mode(self):
        """Tryb koloru używany wewnątrz SPLAT (oddzielna kontrolka w UI)."""
        return getattr(self, '_splat_color_mode_val', DisplayMode.RANGE_COLOR)

    @_splat_color_mode.setter
    def _splat_color_mode(self, value):
        self._splat_color_mode_val = DisplayMode(value)

    def initializeGL(self):
        self.upload_to_gpu()
        self.shader_program = create_program(
            vertex_shader_name='sphereGrid.vert',
            fragment_shader_name='sphereGrid.frag'
        )
        self.fast_shader = create_program(
            vertex_shader_name='sphereGridFast.vert',
            fragment_shader_name='sphereGridFast.frag'
        )
        self._compile_splat_shader()
        self.upload_palette_to_gpu()

    def _compile_splat_shader(self):
        """Kompiluje splat_shader. Oddzielna metoda, by blad nie crashowal reszty."""
        self._splat_diag_done = False   # reset diagnostyki przy recompile
        try:
            self.splat_shader = create_program(
                vertex_shader_name='sphereGridSplat.vert',
                fragment_shader_name='sphereGridSplat.frag'
            )
            print('[SphereGrid] splat_shader OK', flush=True)
        except Exception as e:
            print(f'[SphereGrid] BLAD kompilacji splat_shader: {e}', flush=True)
            self.splat_shader = None

    def _compile_wboit_splat_shader(self):
        try:
            self.wboit_splat_shader = create_program(
                vertex_shader_name='sphereGridSplat.vert',
                fragment_shader_name='wboit_sphereGridSplat.frag'
            )
            print('[SphereGrid] wboit_splat_shader OK', flush=True)
        except Exception as e:
            print(f'[SphereGrid] BLAD kompilacji wboit_splat_shader: {e}', flush=True)
            self.wboit_splat_shader = None

    def render_wboit(self, pass_idx):
        import ctypes

        if self.display_mode != DisplayMode.SPLAT:
            return
        if self._fast_vbo is None or self._fast_vbo_count <= 0:
            return
        if self.wboit_splat_shader is None:
            self._compile_wboit_splat_shader()
        if self.wboit_splat_shader is None:
            return

        glUseProgram(self.wboit_splat_shader)

        modelview = np.array(glGetFloatv(GL_MODELVIEW_MATRIX), dtype=np.float32).T
        projection = np.array(glGetFloatv(GL_PROJECTION_MATRIX), dtype=np.float32).T
        mvp = projection @ modelview

        glUniformMatrix4fv(glGetUniformLocation(self.wboit_splat_shader, "u_mvp"),
                           1, GL_FALSE, mvp.T)
        glUniformMatrix4fv(glGetUniformLocation(self.wboit_splat_shader, "u_mv"),
                           1, GL_FALSE, modelview.T)

        ang_step_rad = float(np.deg2rad(max(abs(self.d_azimuth), abs(self.d_elevation))))
        glUniform1f(glGetUniformLocation(self.wboit_splat_shader, "u_ang_step_rad"), ang_step_rad)
        glUniform1f(glGetUniformLocation(self.wboit_splat_shader, "u_splat_scale"),
                    float(self.splat_scale))

        viewport = glGetIntegerv(GL_VIEWPORT)
        glUniform1f(glGetUniformLocation(self.wboit_splat_shader, "u_viewport_h"),
                    float(viewport[3]))
        glUniform1f(glGetUniformLocation(self.wboit_splat_shader, "u_focal_y"),
                    float(projection[1, 1]))

        minVal, maxVal = self.get_colormap_range()
        glUniform1f(glGetUniformLocation(self.wboit_splat_shader, "u_minVal"), minVal)
        glUniform1f(glGetUniformLocation(self.wboit_splat_shader, "u_maxVal"), maxVal)
        glUniform1i(glGetUniformLocation(self.wboit_splat_shader, "u_color_mode"),
                    int(self._splat_color_mode))
        glUniform3fv(glGetUniformLocation(self.wboit_splat_shader, "u_uniformColor"), 1,
                     np.array(self.uniform_color, dtype=np.float32))
        glUniform1i(glGetUniformLocation(self.wboit_splat_shader, "u_hasRgb"), int(self._rgb is not None))
        glUniform1i(glGetUniformLocation(self.wboit_splat_shader, "u_hasInten"), int(self._intensity is not None))
        glUniform1i(glGetUniformLocation(self.wboit_splat_shader, "u_wboit_pass"), pass_idx)

        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.palette_tex)
        glUniform1i(glGetUniformLocation(self.wboit_splat_shader, "u_palette"), 0)

        stride = 8 * 4
        glBindBuffer(GL_ARRAY_BUFFER, self._fast_vbo)
        glVertexAttribPointer(0, 3, GL_FLOAT, False, stride, ctypes.c_void_p(0))
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(1, 2, GL_FLOAT, False, stride, ctypes.c_void_p(12))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(2, 3, GL_FLOAT, False, stride, ctypes.c_void_p(20))
        glEnableVertexAttribArray(2)

        try:
            glEnable(GL_POINT_SPRITE)
        except Exception:
            pass

        glEnable(GL_PROGRAM_POINT_SIZE)
        glDrawArrays(GL_POINTS, 0, self._fast_vbo_count)

        try:
            glDisable(GL_POINT_SPRITE)
        except Exception:
            pass

        glBindBuffer(GL_ARRAY_BUFFER, 0)
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, 0)
        glDisableVertexAttribArray(0)
        glDisableVertexAttribArray(1)
        glDisableVertexAttribArray(2)
        glUseProgram(0)

    @property
    def is_transparent(self):
        return self.display_mode == DisplayMode.SPLAT

    def renderSelf(self):
        from .globals import AP
        if self.shader_program is None:
            self.initializeGL()

        if AP.wboit_pass is not None:
            if AP.wboit_pass >= 0:
                if self.is_transparent:
                    self.render_wboit(AP.wboit_pass)
                return
            if self.is_transparent:
                return

        # Preferuj szybki VBO (pre-baked XYZ, tylko ważne punkty)
        if self._fast_vbo is not None and self._fast_vbo_count > 0:
            self._render_vbo()
            return

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
        glUniform1i(glGetUniformLocation(self.shader_program, "u_mode"),   int(self.display_mode))
        glUniform3fv(glGetUniformLocation(self.shader_program, "u_uniformColor"), 1, self.uniform_color)
        glUniform1i(glGetUniformLocation(self.shader_program, "u_hasInten"),
                    1 if self._intensity is not None else 0)

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

    def getLocalBB(self):
        valid_r = self._range[self._mask]
        if len(valid_r) == 0:
            return False, None, None

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

        return True, pt_min, pt_max

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self):
        return (f"SphereGrid(shape={self.shape}, "
                f"az={self.azimuth_range}, el={self.elevation_range}, "
                f"unit='{self.unit}', valid={int(self._mask.sum())}pts)")
