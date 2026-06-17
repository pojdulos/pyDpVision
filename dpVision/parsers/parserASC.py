# -*- coding: utf-8 -*-
"""
Parser plików .asc z skanerów laserowych.

Format (10 kolumn, separator tab):
  X  Y  Z  intensity  range  R  G  B  az_deg  el_deg

  - X Y Z      : współrzędne kartezjańskie [m]
  - intensity  : intensywność 0–255
  - range      : odległość od skanera [m]  (redundantna, obliczalna z XYZ)
  - R G B      : kolor 0–255
  - az_deg     : kąt poziomy [°]  (monotonicznie rosnący = pozycja w wierszu)
  - el_deg     : kąt pionowy [°]  (z szumem enkodera)
"""

import os
import numpy as np

from .. import Parser
from ..pointCloud import PointCloud


class ParserASC(Parser):
    descr     = 'ASC laser scan files'
    load_exts = ['.asc']

    @staticmethod
    def load(path):
        print(f"parserASC.load('{path}')", flush=True)
        try:
            data = np.loadtxt(path, dtype=np.float32)
        except Exception as e:
            print(f"Błąd wczytywania ASC: {e}", flush=True)
            return None

        if data.ndim == 1:
            data = data[np.newaxis, :]

        n_cols = data.shape[1]
        if n_cols < 3:
            print(f"Za mało kolumn ({n_cols}), oczekiwano ≥3", flush=True)
            return None

        pc = PointCloud()
        pc.label = os.path.basename(path)
        pc.m_vertices = data[:, :3]          # X Y Z

        # Kolor: kolumny 5-7 (R G B) lub kolumna 3 jako intensywność grayscale
        if n_cols >= 8:
            r = data[:, 5].astype(np.uint8)
            g = data[:, 6].astype(np.uint8)
            b = data[:, 7].astype(np.uint8)
            a = np.full(len(r), 255, dtype=np.uint8)
            pc.m_vcolors = np.stack([r, g, b, a], axis=1)
        elif n_cols >= 4:
            # sama intensywność
            intens = data[:, 3]
            i_min, i_max = float(intens.min()), float(intens.max())
            if i_max > i_min:
                intens = (intens - i_min) / (i_max - i_min)
            c = (intens * 255).astype(np.uint8)
            a = np.full(len(c), 255, dtype=np.uint8)
            pc.m_vcolors = np.stack([c, c, c, a], axis=1)

        print(f"  Wczytano {len(pc.m_vertices):,} punktów", flush=True)
        return pc

    @staticmethod
    def inPlugin():
        return False


ParserASC.regParser()
