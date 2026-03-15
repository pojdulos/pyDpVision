from .. import Parser, Mesh, PointCloud, BaseObject

import os
import struct
import numpy as np
from PyQt5.QtCore import *


PLY_TO_NUMPY = {
    'char': np.int8,
    'uchar': np.uint8,
    'short': np.int16,
    'ushort': np.uint16,
    'int': np.int32,
    'uint': np.uint32,
    'float': np.float32,
    'double': np.float64,
}

PLY_TO_STRUCT = {
    'char': 'b',
    'uchar': 'B',
    'short': 'h',
    'ushort': 'H',
    'int': 'i',
    'uint': 'I',
    'float': 'f',
    'double': 'd',
}


def _parse_ply_header(path):
    elements = []
    current_element = None
    fmt = None
    header_size = 0

    with open(path, 'rb') as f:
        first = f.readline()
        if first.strip() != b'ply':
            raise ValueError("To nie jest plik PLY")
        header_size += len(first)

        while True:
            line = f.readline()
            if not line:
                raise ValueError("Niekompletny nagłówek PLY")
            header_size += len(line)
            txt = line.decode('ascii', errors='replace').strip()
            if not txt or txt.startswith('comment'):
                continue
            if txt == 'end_header':
                break

            parts = txt.split()
            key = parts[0]
            if key == 'format':
                fmt = parts[1]
            elif key == 'element':
                current_element = {
                    'name': parts[1],
                    'count': int(parts[2]),
                    'properties': [],
                }
                elements.append(current_element)
            elif key == 'property':
                if current_element is None:
                    raise ValueError("Property poza sekcją element")
                if parts[1] == 'list':
                    current_element['properties'].append({
                        'kind': 'list',
                        'count_type': parts[2],
                        'item_type': parts[3],
                        'name': parts[4],
                    })
                else:
                    current_element['properties'].append({
                        'kind': 'scalar',
                        'type': parts[1],
                        'name': parts[2],
                    })

    if fmt is None:
        raise ValueError("Brak formatu w nagłówku PLY")
    return fmt, elements, header_size


def _read_ascii_element(lines, start_idx, element):
    rows = []
    idx = start_idx
    for _ in range(element['count']):
        parts = lines[idx].strip().split()
        idx += 1
        cursor = 0
        row = {}
        for prop in element['properties']:
            if prop['kind'] == 'scalar':
                dtype = PLY_TO_NUMPY[prop['type']]
                row[prop['name']] = dtype(parts[cursor]).item()
                cursor += 1
            else:
                count_dtype = PLY_TO_NUMPY[prop['count_type']]
                item_dtype = PLY_TO_NUMPY[prop['item_type']]
                n_items = int(count_dtype(parts[cursor]))
                cursor += 1
                values = [item_dtype(parts[cursor + i]).item() for i in range(n_items)]
                cursor += n_items
                row[prop['name']] = values
        rows.append(row)
    return rows, idx


def _read_binary_scalar_array(f, element, endian):
    dtype_fields = []
    for prop in element['properties']:
        if prop['kind'] != 'scalar':
            return None
        dtype_fields.append((prop['name'], endian + np.dtype(PLY_TO_NUMPY[prop['type']]).str[1:]))
    dtype = np.dtype(dtype_fields)
    return np.fromfile(f, dtype=dtype, count=element['count'])


def _read_binary_element(f, element, endian):
    scalar_data = _read_binary_scalar_array(f, element, endian)
    if scalar_data is not None:
        return scalar_data

    rows = []
    for _ in range(element['count']):
        row = {}
        for prop in element['properties']:
            if prop['kind'] == 'scalar':
                fmt = endian + PLY_TO_STRUCT[prop['type']]
                row[prop['name']] = struct.unpack(fmt, f.read(struct.calcsize(fmt)))[0]
            else:
                count_fmt = endian + PLY_TO_STRUCT[prop['count_type']]
                item_fmt = endian + PLY_TO_STRUCT[prop['item_type']]
                n_items = struct.unpack(count_fmt, f.read(struct.calcsize(count_fmt)))[0]
                values = []
                item_size = struct.calcsize(item_fmt)
                for _ in range(n_items):
                    values.append(struct.unpack(item_fmt, f.read(item_size))[0])
                row[prop['name']] = values
        rows.append(row)
    return rows


def _rows_to_vertex_dict(vertex_rows, element):
    data = {}
    if isinstance(vertex_rows, np.ndarray) and vertex_rows.dtype.names:
        for name in vertex_rows.dtype.names:
            data[name] = np.asarray(vertex_rows[name])
    else:
        for prop in element['properties']:
            if prop['kind'] == 'scalar':
                data[prop['name']] = np.array([row[prop['name']] for row in vertex_rows], dtype=PLY_TO_NUMPY[prop['type']])
    return data


def _extract_vertices(vertex_data):
    aliases = {
        'x': ['x'],
        'y': ['y'],
        'z': ['z'],
    }
    cols = []
    for key in ('x', 'y', 'z'):
        names = aliases[key]
        src = next((name for name in names if name in vertex_data), None)
        if src is None:
            raise ValueError("PLY nie zawiera pełnych współrzędnych x/y/z")
        cols.append(np.asarray(vertex_data[src], dtype=np.float32))
    return np.column_stack(cols).astype(np.float32)


def _extract_normals(vertex_data):
    candidates = [('nx', 'ny', 'nz'), ('normal_x', 'normal_y', 'normal_z')]
    for names in candidates:
        if all(name in vertex_data for name in names):
            cols = [np.asarray(vertex_data[name], dtype=np.float32) for name in names]
            return np.column_stack(cols).astype(np.float32)
    return np.empty((0, 3), dtype=np.float32)


def _normalize_color_channels(channels):
    arr = np.column_stack(channels).astype(np.float32)
    if arr.size == 0:
        return np.empty((0, 4), dtype=np.ubyte)
    if arr.max(initial=0.0) <= 1.0:
        arr *= 255.0
    arr = np.clip(np.round(arr), 0, 255).astype(np.ubyte)
    return arr


def _extract_colors(vertex_data):
    color_sets = [('red', 'green', 'blue', 'alpha'), ('r', 'g', 'b', 'a')]
    rgb_sets = [('red', 'green', 'blue'), ('r', 'g', 'b')]
    for names in color_sets:
        if all(name in vertex_data for name in names):
            cols = [np.asarray(vertex_data[name]) for name in names]
            return _normalize_color_channels(cols)
    for names in rgb_sets:
        if all(name in vertex_data for name in names):
            cols = [np.asarray(vertex_data[name]) for name in names]
            alpha = np.full_like(np.asarray(cols[0], dtype=np.float32), 255.0)
            return _normalize_color_channels(cols + [alpha])
    return np.empty((0, 4), dtype=np.ubyte)


def _extract_texcoords(vertex_data):
    candidates = [('u', 'v'), ('s', 't'), ('texture_u', 'texture_v')]
    for names in candidates:
        if all(name in vertex_data for name in names):
            cols = [np.asarray(vertex_data[name], dtype=np.float32) for name in names]
            return np.column_stack(cols).astype(np.float32)
    return np.empty((0, 2), dtype=np.float32)


def _triangulate_faces(face_rows):
    if not face_rows:
        return np.empty((0, 3), dtype=np.int64)

    triangles = []
    for row in face_rows:
        indices = row.get('vertex_indices')
        if indices is None:
            indices = row.get('vertex_index')
        if indices is None or len(indices) < 3:
            continue
        for i in range(1, len(indices) - 1):
            triangles.append([indices[0], indices[i], indices[i + 1]])
    if not triangles:
        return np.empty((0, 3), dtype=np.int64)
    return np.asarray(triangles, dtype=np.int64)


def _load_ply_data(path, progress_cb=None, status_cb=None):
    fmt, elements, header_size = _parse_ply_header(path)
    if status_cb:
        status_cb("Czytam nagłówek PLY...")
    if progress_cb:
        progress_cb(5)

    element_data = {}
    if fmt == 'ascii':
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
        header_lines = 0
        for line in lines:
            header_lines += 1
            if line.strip() == 'end_header':
                break
        idx = header_lines
        for i, element in enumerate(elements):
            if status_cb:
                status_cb(f"Czytam element '{element['name']}'...")
            rows, idx = _read_ascii_element(lines, idx, element)
            element_data[element['name']] = rows
            if progress_cb:
                progress_cb(10 + int((i + 1) / max(len(elements), 1) * 70))
    else:
        endian = '<' if fmt == 'binary_little_endian' else '>'
        with open(path, 'rb') as f:
            f.seek(header_size)
            for i, element in enumerate(elements):
                if status_cb:
                    status_cb(f"Czytam element '{element['name']}'...")
                element_data[element['name']] = _read_binary_element(f, element, endian)
                if progress_cb:
                    progress_cb(10 + int((i + 1) / max(len(elements), 1) * 70))

    vertex_element = next((e for e in elements if e['name'] == 'vertex'), None)
    if vertex_element is None or 'vertex' not in element_data:
        raise ValueError("PLY nie zawiera elementu 'vertex'")

    vertex_data = _rows_to_vertex_dict(element_data['vertex'], vertex_element)
    vertices = _extract_vertices(vertex_data)
    normals = _extract_normals(vertex_data)
    colors = _extract_colors(vertex_data)
    texcoords = _extract_texcoords(vertex_data)

    face_rows = element_data.get('face', [])
    faces = _triangulate_faces(face_rows if isinstance(face_rows, list) else [])

    if progress_cb:
        progress_cb(90)
    if faces.shape[0]:
        mesh = Mesh()
        mesh.m_vertices = np.ascontiguousarray(vertices, dtype=np.float32)
        mesh.m_faces = np.ascontiguousarray(faces, dtype=np.int64)
        if normals.shape[0] == vertices.shape[0]:
            mesh.m_vnormals = np.ascontiguousarray(normals, dtype=np.float32)
        else:
            mesh.calcVN()
        if colors.shape[0] == vertices.shape[0]:
            mesh.m_vcolors = np.ascontiguousarray(colors, dtype=np.ubyte)
        if texcoords.shape[0] == vertices.shape[0]:
            mesh.m_tcoords = np.ascontiguousarray(texcoords, dtype=np.float32)
            mesh.m_tindices = np.ascontiguousarray(mesh.m_faces, dtype=np.uint32)
        _ = mesh.getBB()
        if progress_cb:
            progress_cb(100)
        return mesh

    cloud = PointCloud()
    cloud.m_vertices = np.ascontiguousarray(vertices, dtype=np.float32)
    if normals.shape[0] == vertices.shape[0]:
        cloud.m_vnormals = np.ascontiguousarray(normals, dtype=np.float32)
    if colors.shape[0] == vertices.shape[0]:
        cloud.m_vcolors = np.ascontiguousarray(colors, dtype=np.ubyte)
    _ = cloud.getBB()
    if progress_cb:
        progress_cb(100)
    return cloud


def _derive_vertex_texcoords(mesh):
    if getattr(mesh, 'm_tcoords', np.empty((0, 2))).shape[0] == 0:
        return np.empty((0, 2), dtype=np.float32)
    if mesh.m_tcoords.shape[0] == mesh.m_vertices.shape[0] and (
        getattr(mesh, 'm_tindices', np.empty((0, 3))).shape[0] == 0 or np.array_equal(mesh.m_tindices, mesh.m_faces)
    ):
        return np.asarray(mesh.m_tcoords, dtype=np.float32)

    if getattr(mesh, 'm_tindices', np.empty((0, 3))).shape != getattr(mesh, 'm_faces', np.empty((0, 3))).shape:
        return np.empty((0, 2), dtype=np.float32)

    texcoords = np.full((mesh.m_vertices.shape[0], 2), np.nan, dtype=np.float32)
    for face, tface in zip(mesh.m_faces, mesh.m_tindices):
        for vidx, tidx in zip(face, tface):
            uv = mesh.m_tcoords[tidx]
            if np.isnan(texcoords[vidx]).any():
                texcoords[vidx] = uv
            elif not np.allclose(texcoords[vidx], uv, atol=1e-6):
                return np.empty((0, 2), dtype=np.float32)
    if np.isnan(texcoords).any():
        return np.empty((0, 2), dtype=np.float32)
    return texcoords


def _iter_exportable_nodes(node):
    if node is None:
        return
    if isinstance(node, (Mesh, PointCloud)):
        yield node
    for child in node.children():
        yield from _iter_exportable_nodes(child)


def _transform_vertices(vertices, matrix):
    if len(vertices) == 0:
        return np.empty((0, 3), dtype=np.float32)
    verts = np.asarray(vertices, dtype=np.float64)
    verts_h = np.hstack([verts, np.ones((len(verts), 1), dtype=np.float64)])
    return (verts_h @ matrix.T)[:, :3].astype(np.float32)


def _transform_normals(normals, matrix):
    if len(normals) == 0:
        return np.empty((0, 3), dtype=np.float32)
    linear = np.asarray(matrix, dtype=np.float64)[:3, :3]
    try:
        transformed = np.asarray(normals, dtype=np.float64) @ np.linalg.inv(linear)
    except np.linalg.LinAlgError:
        transformed = np.asarray(normals, dtype=np.float64)
    norms = np.linalg.norm(transformed, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (transformed / norms).astype(np.float32)


class PLYLoaderWorker(QObject):
    progressChanged = pyqtSignal(int)
    statusChanged = pyqtSignal(str)
    loadingFinished = pyqtSignal(object)
    errorOccurred = pyqtSignal(str)

    def __init__(self, path):
        super().__init__()
        self.path = path
        self._is_running = True

    def stop(self):
        self._is_running = False

    def load_ply(self):
        try:
            obj = _load_ply_data(
                self.path,
                progress_cb=self.progressChanged.emit if self._is_running else None,
                status_cb=self.statusChanged.emit if self._is_running else None,
            )
            obj.label = os.path.basename(self.path)
            if self._is_running:
                self.loadingFinished.emit(obj)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.errorOccurred.emit(str(e))


class ParserPLY(Parser):
    loadingFinished = pyqtSignal(BaseObject)
    errorOccurred = pyqtSignal()

    descr = 'PLY files'
    load_exts = ['.ply']
    save_exts = ['.ply']

    def __init__(self, path):
        super().__init__()
        self.path = path
        self._thread = QThread()
        self._worker = PLYLoaderWorker(path)

    @classmethod
    def is_not_static(cls):
        return True

    @classmethod
    def canSaveObject(cls, obj):
        return any(True for _ in _iter_exportable_nodes(obj))

    def on_loading_finished(self, obj):
        self._thread.quit()
        self._thread.wait()
        self._worker.deleteLater()
        self._thread.deleteLater()
        self.loadingFinished.emit(obj)

    def on_loading_error(self, msg):
        self._thread.quit()
        self._thread.wait()
        self._worker.deleteLater()
        self._thread.deleteLater()
        print(f"Blad wczytywania PLY: {msg}")
        self.errorOccurred.emit()

    def on_stop_loading(self):
        self._worker.stop()
        self._thread.quit()
        self._thread.wait()
        self._worker.deleteLater()
        self._thread.deleteLater()
        self.deleteLater()

    def load_async(self, progressBar=None):
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.load_ply)
        if progressBar is not None:
            self._worker.progressChanged.connect(progressBar.setValue)
        self._worker.loadingFinished.connect(self.on_loading_finished)
        self._worker.errorOccurred.connect(self.on_loading_error)
        self._thread.start()

    @staticmethod
    def load(path):
        try:
            obj = _load_ply_data(path)
            obj.label = os.path.basename(path)
            return obj
        except Exception as e:
            print(f"Blad wczytywania PLY: {e}")
            return None

    @staticmethod
    def save(obj, path):
        nodes = list(_iter_exportable_nodes(obj))
        if not nodes:
            print("ParserPLY.save: brak obiektow do zapisu")
            return False

        vertices_parts = []
        normals_parts = []
        colors_parts = []
        texcoord_parts = []
        faces_parts = []

        has_normals = False
        has_colors = False
        has_texcoords = False
        vertex_offset = 0

        for node in nodes:
            if len(getattr(node, 'm_vertices', [])) == 0:
                continue
            matrix = np.asarray(node.getGlobalTransformation(), dtype=np.float64)
            vertices = _transform_vertices(node.m_vertices, matrix)
            normals = np.empty((0, 3), dtype=np.float32)
            colors = np.empty((0, 4), dtype=np.ubyte)
            texcoords = np.empty((0, 2), dtype=np.float32)

            if getattr(node, 'm_vnormals', np.empty((0, 3))).shape[0] == len(vertices):
                normals = _transform_normals(node.m_vnormals, matrix)
                has_normals = True
            if getattr(node, 'm_vcolors', np.empty((0, 4))).shape[0] == len(vertices):
                colors = np.asarray(node.m_vcolors, dtype=np.ubyte)
                has_colors = True
            if isinstance(node, Mesh):
                texcoords = _derive_vertex_texcoords(node)
                if texcoords.shape[0] == len(vertices):
                    has_texcoords = True

            vertices_parts.append(vertices)
            normals_parts.append(normals)
            colors_parts.append(colors)
            texcoord_parts.append(texcoords)

            if isinstance(node, Mesh) and len(getattr(node, 'm_faces', [])):
                faces = np.asarray(node.m_faces, dtype=np.int64) + vertex_offset
                faces_parts.append(faces)
            vertex_offset += len(vertices)

        if not vertices_parts:
            print("ParserPLY.save: brak wierzcholkow do zapisu")
            return False

        vertices = np.vstack(vertices_parts).astype(np.float32)
        total_vertices = vertices.shape[0]

        if has_normals:
            merged_normals = np.zeros((total_vertices, 3), dtype=np.float32)
            offset = 0
            for verts, normals in zip(vertices_parts, normals_parts):
                n = len(verts)
                if normals.shape[0] == n:
                    merged_normals[offset:offset+n] = normals
                offset += n
        else:
            merged_normals = np.empty((0, 3), dtype=np.float32)

        if has_colors:
            merged_colors = np.full((total_vertices, 4), 255, dtype=np.ubyte)
            merged_colors[:, :3] = 200
            offset = 0
            for verts, colors in zip(vertices_parts, colors_parts):
                n = len(verts)
                if colors.shape[0] == n:
                    merged_colors[offset:offset+n] = colors
                offset += n
        else:
            merged_colors = np.empty((0, 4), dtype=np.ubyte)

        if has_texcoords:
            merged_texcoords = np.zeros((total_vertices, 2), dtype=np.float32)
            offset = 0
            for verts, texcoords in zip(vertices_parts, texcoord_parts):
                n = len(verts)
                if texcoords.shape[0] == n:
                    merged_texcoords[offset:offset+n] = texcoords
                offset += n
        else:
            merged_texcoords = np.empty((0, 2), dtype=np.float32)

        faces = np.vstack(faces_parts).astype(np.int64) if faces_parts else np.empty((0, 3), dtype=np.int64)

        try:
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write("ply\n")
                f.write("format ascii 1.0\n")
                f.write(f"comment Created by pyDpVision for {getattr(obj, 'label', 'object')}\n")
                f.write(f"element vertex {len(vertices)}\n")
                f.write("property float x\n")
                f.write("property float y\n")
                f.write("property float z\n")
                if has_normals:
                    f.write("property float nx\n")
                    f.write("property float ny\n")
                    f.write("property float nz\n")
                if has_colors:
                    f.write("property uchar red\n")
                    f.write("property uchar green\n")
                    f.write("property uchar blue\n")
                    f.write("property uchar alpha\n")
                if has_texcoords:
                    f.write("property float u\n")
                    f.write("property float v\n")
                if len(faces):
                    f.write(f"element face {len(faces)}\n")
                    f.write("property list uchar int vertex_indices\n")
                f.write("end_header\n")

                for i, vert in enumerate(vertices):
                    parts = [f"{vert[0]:.6f}", f"{vert[1]:.6f}", f"{vert[2]:.6f}"]
                    if has_normals:
                        parts.extend([
                            f"{merged_normals[i, 0]:.6f}",
                            f"{merged_normals[i, 1]:.6f}",
                            f"{merged_normals[i, 2]:.6f}",
                        ])
                    if has_colors:
                        parts.extend([str(int(v)) for v in merged_colors[i]])
                    if has_texcoords:
                        parts.extend([f"{merged_texcoords[i, 0]:.6f}", f"{merged_texcoords[i, 1]:.6f}"])
                    f.write(" ".join(parts) + "\n")

                for face in faces:
                    f.write(f"3 {int(face[0])} {int(face[1])} {int(face[2])}\n")
            return True
        except Exception as e:
            print(f"ParserPLY.save: blad zapisu PLY: {e}")
            return False

    @staticmethod
    def inPlugin():
        return False


ParserPLY.regParser()
