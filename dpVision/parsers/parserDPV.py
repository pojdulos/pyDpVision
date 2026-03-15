# -*- coding: utf-8 -*-

import os
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
from PyQt5.QtGui import QColor

from .. import (
    Annotation,
    AnnotationPath,
    AnnotationPlane,
    AnnotationPoint,
    AnnotationSphere,
    AnnotationTriangle,
    Mesh,
    Parser,
    PointCloud,
    Transform,
)
from .parserOBJ import ParserOBJ


class ParserDPV(Parser):
    descr = "dpVision archive"
    load_exts = [".dpvision"]
    save_exts = [".dpvision"]

    @staticmethod
    def check_by_content(path):
        try:
            with zipfile.ZipFile(path, "r") as archive:
                return "structure.xml" in archive.namelist()
        except Exception:
            return False

    @classmethod
    def canSaveObject(cls, obj):
        return cls._is_supported_tree(obj)

    @classmethod
    def _is_supported_tree(cls, obj):
        if not cls._is_supported_node(obj):
            return False
        for child in obj.children():
            if not cls._is_supported_tree(child):
                return False
        return True

    @staticmethod
    def _is_supported_node(obj):
        return isinstance(
            obj,
            (
                Transform,
                Mesh,
                PointCloud,
                AnnotationPoint,
                AnnotationPath,
                AnnotationPlane,
                AnnotationSphere,
                AnnotationTriangle,
            ),
        )

    @staticmethod
    def _color_to_text(color):
        return f"{color.red()} {color.green()} {color.blue()} {color.alpha()}"

    @staticmethod
    def _text_to_color(text, fallback):
        if not text:
            return fallback
        try:
            parts = [int(v) for v in text.split()]
            if len(parts) == 3:
                parts.append(255)
            if len(parts) != 4:
                return fallback
            return QColor(*parts)
        except Exception:
            return fallback

    @staticmethod
    def _vec_to_text(vec):
        arr = np.asarray(vec, dtype=np.float64).reshape(-1)
        return " ".join(f"{value:.16g}" for value in arr.tolist())

    @staticmethod
    def _text_to_vec(text, size):
        values = [float(v) for v in text.split()]
        if len(values) != size:
            raise ValueError(f"Expected {size} values, got {len(values)}")
        return values

    @staticmethod
    def _set_common_fields(elem, obj, obj_id, parent_id):
        elem.set("id", obj_id)
        elem.set("parent", parent_id or "")
        elem.set("label", getattr(obj, "label", obj.__class__.__name__))
        descr = getattr(obj, "description", "")
        if descr:
            descr_elem = ET.SubElement(elem, "descr")
            descr_elem.text = descr

    @staticmethod
    def _copy_material(material):
        new_material = Mesh.Material()
        new_material.ambient = list(material.ambient)
        new_material.diffuse = list(material.diffuse)
        new_material.specular = list(material.specular)
        new_material.alpha = float(material.alpha)
        new_material.shinines = float(material.shinines)
        new_material.dTexFileName = str(material.dTexFileName)
        new_material.dTexImage = material.dTexImage.copy() if getattr(material, "dTexImage", None) is not None else None
        new_material.dTexture = material.dTexture
        return new_material

    @staticmethod
    def _clone_geometry_node(node):
        if isinstance(node, Mesh):
            clone = Mesh()
            clone.m_faces = np.array(node.m_faces, dtype=np.uint, copy=True)
            clone.m_fcolors = np.array(node.m_fcolors, dtype=np.ubyte, copy=True)
            clone.m_fnormals = np.array(node.m_fnormals, dtype=np.float32, copy=True)
            clone.m_tcoords = np.array(node.m_tcoords, dtype=np.float32, copy=True)
            clone.m_tindices = np.array(node.m_tindices, dtype=np.uint, copy=True)
            clone.b_renderTexture = bool(node.b_renderTexture)
            clone.b_renderSmooth = bool(node.b_renderSmooth)
            clone.currentMaterial = str(node.currentMaterial)
            clone.materials = {
                name: ParserDPV._copy_material(material)
                for name, material in node.materials.items()
            }
        else:
            clone = PointCloud()

        clone.label = getattr(node, "label", clone.__class__.__name__)
        clone.description = getattr(node, "description", "")
        clone.m_vertices = np.array(node.m_vertices, dtype=np.float32, copy=True)
        clone.m_vcolors = np.array(node.m_vcolors, dtype=np.ubyte, copy=True)
        clone.m_vnormals = np.array(node.m_vnormals, dtype=np.float32, copy=True)
        return clone

    @staticmethod
    def _write_annotation(elem, obj):
        properties = ET.SubElement(elem, "properties")
        properties.set("color", ParserDPV._color_to_text(obj.m_color))
        properties.set("selcolor", ParserDPV._color_to_text(obj.m_selcolor))

        if isinstance(obj, AnnotationPoint):
            elem.set("type", "point")
            ET.SubElement(elem, "point").text = ParserDPV._vec_to_text(obj.getPoint())
            vector = obj.getVector()
            if vector is not None:
                vector_elem = ET.SubElement(elem, "vector")
                vector_elem.set("show", "1" if obj.m_showVector else "0")
                vector_elem.text = ParserDPV._vec_to_text(vector)
        elif isinstance(obj, AnnotationPath):
            elem.set("type", "path")
            points_elem = ET.SubElement(elem, "points")
            points_elem.set("width", f"{float(obj.m_width):.16g}")
            points_elem.text = ";".join(ParserDPV._vec_to_text(pt) for pt in obj.m_points)
        elif isinstance(obj, AnnotationPlane):
            elem.set("type", "plane")
            ET.SubElement(elem, "center").text = ParserDPV._vec_to_text(obj.m_center)
            ET.SubElement(elem, "normal").text = ParserDPV._vec_to_text(obj.normal_vector)
            ET.SubElement(elem, "size").text = ParserDPV._vec_to_text(obj.m_size)
        elif isinstance(obj, AnnotationSphere):
            elem.set("type", "sphere")
            ET.SubElement(elem, "center").text = ParserDPV._vec_to_text(obj.position)
            ET.SubElement(elem, "radius").text = f"{float(obj.radius):.16g}"
        elif isinstance(obj, AnnotationTriangle):
            elem.set("type", "triangle")
            ET.SubElement(elem, "A").text = ParserDPV._vec_to_text(obj.m_pA)
            ET.SubElement(elem, "B").text = ParserDPV._vec_to_text(obj.m_pB)
            ET.SubElement(elem, "C").text = ParserDPV._vec_to_text(obj.m_pC)
        else:
            raise TypeError(f"Unsupported annotation type: {type(obj).__name__}")

    @staticmethod
    def _read_annotation(elem):
        ann_type = elem.get("type", "")
        if ann_type == "point":
            point = ParserDPV._text_to_vec(elem.findtext("point", "0 0 0"), 3)
            vector_elem = elem.find("vector")
            vector = None
            show = True
            if vector_elem is not None and (vector_elem.text or "").strip():
                vector = ParserDPV._text_to_vec(vector_elem.text, 3)
                show = vector_elem.get("show", "1") != "0"
            obj = AnnotationPoint(point=point, vector=vector)
            obj.m_showVector = show and vector is not None
        elif ann_type == "path":
            obj = AnnotationPath()
            points_elem = elem.find("points")
            if points_elem is not None:
                obj.m_width = float(points_elem.get("width", "1.0"))
                text = (points_elem.text or "").strip()
                if text:
                    obj.m_points = [ParserDPV._text_to_vec(chunk.strip(), 3) for chunk in text.split(";") if chunk.strip()]
        elif ann_type == "plane":
            center = ParserDPV._text_to_vec(elem.findtext("center", "0 0 0"), 3)
            normal = ParserDPV._text_to_vec(elem.findtext("normal", "0 0 1"), 3)
            size = ParserDPV._text_to_vec(elem.findtext("size", "10 10"), 2)
            obj = AnnotationPlane(pC=center, pN=normal, size=size)
        elif ann_type == "sphere":
            obj = AnnotationSphere()
            obj.position = ParserDPV._text_to_vec(elem.findtext("center", "0 0 0"), 3)
            obj.radius = float(elem.findtext("radius", "1.0"))
        elif ann_type == "triangle":
            p_a = ParserDPV._text_to_vec(elem.findtext("A", "0 0 0"), 3)
            p_b = ParserDPV._text_to_vec(elem.findtext("B", "0 0 0"), 3)
            p_c = ParserDPV._text_to_vec(elem.findtext("C", "0 0 0"), 3)
            obj = AnnotationTriangle(pA=p_a, pB=p_b, pC=p_c)
        else:
            raise ValueError(f"Unsupported annotation type in archive: {ann_type}")

        props = elem.find("properties")
        if props is not None:
            obj.m_color = ParserDPV._text_to_color(props.get("color", ""), obj.m_color)
            obj.m_selcolor = ParserDPV._text_to_color(props.get("selcolor", ""), obj.m_selcolor)
        return obj

    @classmethod
    def load(cls, path):
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                with zipfile.ZipFile(path, "r") as archive:
                    archive.extractall(temp_dir)
                    with archive.open("structure.xml", "r") as xml_file:
                        root = ET.parse(xml_file).getroot()

                records = {}
                for elem in root.findall("object"):
                    obj_id = elem.get("id", "")
                    parent_id = elem.get("parent", "")
                    obj_class = elem.get("class", "")
                    obj_type = elem.get("type", "")
                    obj = None

                    if obj_class == "object":
                        if obj_type == "transformation":
                            obj = Transform()
                            matrix_text = elem.findtext("matrix", "")
                            if matrix_text.strip():
                                obj.fromNumPy(cls._text_to_vec(matrix_text, 16))
                        elif obj_type == "mesh":
                            file_elem = elem.find("file")
                            if file_elem is None:
                                continue
                            rel_dir = elem.get("path", "")
                            rel_obj = file_elem.get("data", obj_id + ".obj")
                            obj_path = os.path.join(temp_dir, rel_dir, rel_obj)
                            obj = ParserOBJ.load(obj_path)
                        else:
                            continue
                    elif obj_class == "annotation":
                        obj = cls._read_annotation(elem)

                    if obj is None:
                        continue

                    obj.label = elem.get("label", obj.label)
                    obj.description = elem.findtext("descr", "")
                    records[obj_id] = {"obj": obj, "parent_id": parent_id}

                roots = []
                for obj_id, record in records.items():
                    obj = record["obj"]
                    parent_id = record["parent_id"]
                    parent_record = records.get(parent_id)
                    if parent_record is None:
                        roots.append(obj)
                        continue
                    parent = parent_record["obj"]
                    if hasattr(parent, "addChild"):
                        parent.addChild(obj)
                    else:
                        roots.append(obj)

                if not roots:
                    return None
                if len(roots) == 1:
                    return roots[0]

                scene = Transform()
                scene.label = os.path.basename(path)
                for root_obj in roots:
                    scene.addChild(root_obj)
                return scene
        except Exception as exc:
            print(f"ParserDPV.load failed: {exc}")
            return None

    @classmethod
    def save(cls, obj, path):
        if not cls.canSaveObject(obj):
            print("ParserDPV.save: unsupported object tree")
            return False

        counter = 0

        def next_id():
            nonlocal counter
            counter += 1
            return format(counter, "x")

        def save_node(node, workspace_elem, parent_id="", rel_dir=""):
            obj_id = next_id()
            if isinstance(node, Annotation):
                elem = ET.SubElement(workspace_elem, "object")
                elem.set("class", "annotation")
                cls._set_common_fields(elem, node, obj_id, parent_id)
                cls._write_annotation(elem, node)
                return obj_id

            elem = ET.SubElement(workspace_elem, "object")
            elem.set("class", "object")
            elem.set("path", rel_dir.replace("\\", "/"))
            cls._set_common_fields(elem, node, obj_id, parent_id)

            if isinstance(node, Transform):
                elem.set("type", "transformation")
                matrix_elem = ET.SubElement(elem, "matrix")
                matrix_elem.text = cls._vec_to_text(node.toNumPy().reshape(-1))
            elif isinstance(node, (Mesh, PointCloud)):
                elem.set("type", "mesh")
                file_elem = ET.SubElement(elem, "file")
                file_elem.set("format", "obj")
                file_elem.set("data", f"{obj_id}.obj")
                file_elem.set("material", f"{obj_id}.mtl")

                node_dir = Path(temp_dir, rel_dir)
                node_dir.mkdir(parents=True, exist_ok=True)
                export_node = cls._clone_geometry_node(node)
                ParserOBJ.save(export_node, str(node_dir / f"{obj_id}.obj"))

                texture_name = None
                if isinstance(export_node, Mesh):
                    current_material = export_node.materials.get(export_node.currentMaterial)
                    if current_material and current_material.dTexFileName:
                        texture_name = os.path.basename(current_material.dTexFileName)
                if texture_name:
                    file_elem.set("texture", texture_name)
            else:
                raise TypeError(f"Unsupported object type: {type(node).__name__}")

            child_rel_dir = f"{rel_dir}{obj_id}/"
            for child in node.children():
                save_node(child, workspace_elem, obj_id, child_rel_dir)
            return obj_id

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                workspace = ET.Element("workspace", {"mode": "current"})
                save_node(obj, workspace)
                workspace.set("count", str(len(workspace.findall("object"))))

                xml_bytes = ET.tostring(workspace, encoding="utf-8", xml_declaration=True)

                with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                    archive.writestr("structure.xml", xml_bytes)
                    for file_path in Path(temp_dir).rglob("*"):
                        if not file_path.is_file():
                            continue
                        rel_path = file_path.relative_to(temp_dir).as_posix()
                        archive.write(file_path, rel_path)
            return True
        except Exception as exc:
            print(f"ParserDPV.save failed: {exc}")
            return False


ParserDPV.regParser()
