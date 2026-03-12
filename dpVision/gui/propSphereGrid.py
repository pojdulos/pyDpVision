# -*- coding: utf-8 -*-
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtWidgets import (QFormLayout, QComboBox, QDoubleSpinBox,
                              QLabel, QGroupBox, QVBoxLayout)

from .propBaseObject import PropBaseObject
from .propWidget import PropWidget
from .multiSpinBox import MultiSpinBox
from .. import AP, COLORMAPS
from ..sphereGrid import DisplayMode
import weakref


# Tryby widoczne w UI: (etykieta, DisplayMode, wymaga_rgb, wymaga_intensity)
_MODES = [
    ("RGB",              DisplayMode.RGB,          True,  False),
    ("Intensity",        DisplayMode.INTENSITY,    False, True),
    ("Greyscale",        DisplayMode.GREYSCALE,    False, False),
    ("Range color",      DisplayMode.RANGE_COLOR,  False, False),
    ("Uniform color",    DisplayMode.UNIFORM,      False, False),
    ("Gaussian splat",   DisplayMode.SPLAT,        False, False),
    ("Uncertainty (σ)",  DisplayMode.UNCERTAINTY,  False, False),
]

# Tryby koloru dostępne wewnątrz Gaussian splat
# (label, DisplayMode, wymaga_rgb, wymaga_intensity)
_SPLAT_COLOR_MODES = [
    ("Range color",   DisplayMode.RANGE_COLOR,  False, False),
    ("RGB",           DisplayMode.RGB,         True,  False),
    ("Intensity",     DisplayMode.INTENSITY,    False, True),
    ("Greyscale",     DisplayMode.GREYSCALE,    False, False),
    ("Uniform color", DisplayMode.UNIFORM,      False, False),
]


class PropSphereGrid(PropWidget):
    def __init__(self, _obj, parent=None):
        super().__init__(parent)
        self.obj_ref = weakref.ref(_obj)
        self.buildUI()

    def buildUI(self):
        layout = QFormLayout(self)

        # --- Tryb wyświetlania ---
        self.mode_combo = QComboBox()
        for label, *_ in _MODES:
            self.mode_combo.addItem(label)
        layout.addRow("display mode", self.mode_combo)

        # --- Colormap (dla Range color / Intensity) ---
        self.colormap_combo = QComboBox()
        for name in COLORMAPS.keys():
            self.colormap_combo.addItem(name)
        self.colormap_range = MultiSpinBox(count=2, labels=("min: ", "max: "))
        layout.addRow("colormap",       self.colormap_combo)
        layout.addRow("range",          self.colormap_range)

        # --- Stały kolor ---
        self.uniform_color = MultiSpinBox(count=3, labels=("R=", "G=", "B="))
        self.uniform_color.setStyleSheet("border:none")
        layout.addRow("uniform color",  self.uniform_color)

        # --- Gaussian splat ---
        self.splat_scale = QDoubleSpinBox()
        self.splat_scale.setRange(0.1, 20.0)
        self.splat_scale.setSingleStep(0.1)
        self.splat_scale.setDecimals(2)
        self.splat_scale.setValue(1.0)
        layout.addRow("splat scale",     self.splat_scale)

        self.splat_color_combo = QComboBox()
        for label, *_ in _SPLAT_COLOR_MODES:
            self.splat_color_combo.addItem(label)
        layout.addRow("splat color",     self.splat_color_combo)

        # --- Info ---
        self.lbl_shape  = QLabel()
        self.lbl_origin = QLabel()
        self.lbl_az     = QLabel()
        self.lbl_el     = QLabel()
        self.lbl_pts    = QLabel()
        layout.addRow("shape (rows×cols):", self.lbl_shape)
        layout.addRow("origin [m]:",        self.lbl_origin)
        layout.addRow("azimuth [°]:",       self.lbl_az)
        layout.addRow("elevation [°]:",     self.lbl_el)
        layout.addRow("valid points:",      self.lbl_pts)

        self.setLayout(layout)

        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        self.colormap_combo.currentTextChanged.connect(self.on_colormap_changed)
        self.colormap_range.valueChanged.connect(self.on_colormap_range_changed)
        self.uniform_color.valueChanged.connect(self.on_uniform_color_changed)
        self.splat_scale.valueChanged.connect(self.on_splat_scale_changed)
        self.splat_color_combo.currentIndexChanged.connect(self.on_splat_color_changed)

    @staticmethod
    def create(m, parent=0):
        return PropWidget.build([
            PropSphereGrid(m),
            PropBaseObject(m),
        ], parent)

    def _current_mode(self):
        idx = self.mode_combo.currentIndex()
        if 0 <= idx < len(_MODES):
            return _MODES[idx][1]
        return DisplayMode.RANGE_COLOR

    def updateProperties(self):
        obj = self.obj_ref()
        if obj is None:
            return

        widgets = self.get_subwidgets()
        for w in widgets:
            w.blockSignals(True)
        self.colormap_combo.blockSignals(True)

        # Znajdź indeks odpowiadający bieżącemu trybowi, pomijając niedostępne
        mode = obj.display_mode
        combo_idx = 0
        for i, (label, dm, need_rgb, need_inten) in enumerate(_MODES):
            if dm == mode:
                combo_idx = i
                break
        self.mode_combo.setCurrentIndex(combo_idx)

        # Wyłącz tryby niedostępne
        for i, (label, dm, need_rgb, need_inten) in enumerate(_MODES):
            available = True
            if need_rgb   and obj._rgb       is None: available = False
            if need_inten and obj._intensity  is None: available = False
            item_flags = self.mode_combo.model().item(i).flags()
            from PyQt5.QtCore import Qt
            if available:
                self.mode_combo.model().item(i).setFlags(
                    item_flags | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            else:
                self.mode_combo.model().item(i).setFlags(
                    item_flags & ~Qt.ItemIsEnabled & ~Qt.ItemIsSelectable)

        is_splat    = mode == DisplayMode.SPLAT
        splat_color = obj._splat_color_mode if is_splat else mode
        is_colormap = splat_color in (DisplayMode.RANGE_COLOR, DisplayMode.INTENSITY) and not is_splat
        is_colormap = is_colormap or (is_splat and splat_color in (DisplayMode.RANGE_COLOR, DisplayMode.INTENSITY))
        is_uniform  = (mode == DisplayMode.UNIFORM) or (is_splat and splat_color == DisplayMode.UNIFORM)

        self.colormap_combo.setCurrentText(
            obj._colormap_name if isinstance(obj._colormap_name, str) else 'skala')
        self.colormap_combo.setEnabled(is_colormap)
        vmin, vmax = obj.get_colormap_range()
        self.colormap_range.setValue((vmin, vmax))
        self.colormap_range.setEnabled(is_colormap)
        self.uniform_color.setValue(obj.uniform_color)
        self.uniform_color.setEnabled(is_uniform)

        # Splat controls
        self.splat_scale.setValue(float(obj.splat_scale))
        self.splat_scale.setEnabled(is_splat)
        # Ustaw splat_color_combo na bieżący tryb koloru splatu
        sc_idx = 0
        for i, (lbl, dm, *_) in enumerate(_SPLAT_COLOR_MODES):
            if dm == obj._splat_color_mode:
                sc_idx = i
                break
        self.splat_color_combo.setCurrentIndex(sc_idx)
        # Wyłącz niedostępne opcje koloru w splat combo
        for i, (lbl, dm, need_rgb, need_inten) in enumerate(_SPLAT_COLOR_MODES):
            avail = True
            if need_rgb   and obj._rgb       is None: avail = False
            if need_inten and obj._intensity  is None: avail = False
            from PyQt5.QtCore import Qt
            item = self.splat_color_combo.model().item(i)
            if avail:
                item.setFlags(item.flags() | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            else:
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled & ~Qt.ItemIsSelectable)
        self.splat_color_combo.setEnabled(is_splat)

        rows, cols = obj.shape
        self.lbl_shape.setText(f"{rows} × {cols}")
        ox, oy, oz = obj.origin
        self.lbl_origin.setText(f"{ox:.3f},  {oy:.3f},  {oz:.3f}")
        self.lbl_az.setText(
            f"{obj.azimuth_range[0]:.1f}  …  {obj.azimuth_range[1]:.1f}")
        self.lbl_el.setText(
            f"{obj.elevation_range[0]:.1f}  …  {obj.elevation_range[1]:.1f}")
        import numpy as np
        n_valid = int(np.count_nonzero(obj._mask))
        self.lbl_pts.setText(f"{n_valid:,}")

        for w in widgets:
            w.blockSignals(False)
        self.colormap_combo.blockSignals(False)

    # --- Sloty ---

    @pyqtSlot(int)
    def on_mode_changed(self, idx):
        obj = self.obj_ref()
        if obj is None or idx < 0 or idx >= len(_MODES):
            return
        obj.display_mode = _MODES[idx][1]
        is_splat    = obj.display_mode == DisplayMode.SPLAT
        splat_color = obj._splat_color_mode
        active_mode = splat_color if is_splat else obj.display_mode
        is_colormap = active_mode in (DisplayMode.RANGE_COLOR, DisplayMode.INTENSITY)
        is_uniform  = active_mode == DisplayMode.UNIFORM
        self.colormap_combo.setEnabled(is_colormap)
        self.colormap_range.setEnabled(is_colormap)
        self.uniform_color.setEnabled(is_uniform)
        self.splat_scale.setEnabled(is_splat)
        self.splat_color_combo.setEnabled(is_splat)
        AP.updateAllViews()

    @pyqtSlot(str)
    def on_colormap_changed(self, name):
        obj = self.obj_ref()
        if obj is None:
            return
        obj.set_colormap(name)
        AP.updateAllViews()

    @pyqtSlot(tuple)
    def on_colormap_range_changed(self, vals):
        obj = self.obj_ref()
        if obj is None:
            return
        obj.vmin, obj.vmax = vals
        AP.updateAllViews()

    @pyqtSlot(tuple)
    def on_uniform_color_changed(self, vals):
        obj = self.obj_ref()
        if obj is None:
            return
        obj.uniform_color = list(vals)
        AP.updateAllViews()

    @pyqtSlot(float)
    def on_splat_scale_changed(self, val):
        obj = self.obj_ref()
        if obj is None:
            return
        obj.splat_scale = val
        AP.updateAllViews()

    @pyqtSlot(int)
    def on_splat_color_changed(self, idx):
        obj = self.obj_ref()
        if obj is None or idx < 0 or idx >= len(_SPLAT_COLOR_MODES):
            return
        obj._splat_color_mode = _SPLAT_COLOR_MODES[idx][1]
        splat_color = obj._splat_color_mode
        is_colormap = splat_color in (DisplayMode.RANGE_COLOR, DisplayMode.INTENSITY)
        is_uniform  = splat_color == DisplayMode.UNIFORM
        self.colormap_combo.setEnabled(is_colormap)
        self.colormap_range.setEnabled(is_colormap)
        self.uniform_color.setEnabled(is_uniform)
        AP.updateAllViews()

