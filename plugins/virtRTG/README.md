# virtRTG

`virtRTG` is a `pyDpVision` plugin for synthetic X-ray projection from 3D scene
data. It is aimed at research and technical experimentation around virtual
radiography, especially for volumetric medical data and hybrid volume/mesh
scenes.

## What it does

- projects `Volumetric` sources onto a virtual detector,
- supports cone-beam and parallel-beam setups,
- supports hybrid scenes with both volumes and meshes,
- provides configurable detector geometry, source geometry, and presentation,
- supports multiple presentation styles such as raw, digital, and film-like,
- supports projected annotation overlays,
- includes geometry presets, export helpers, and benchmark/demo utilities.

## Main capabilities

### Projection backend

- detector geometry built from center/normal/up vectors,
- configurable detector resolution and pixel size,
- cone-beam or parallel-beam projection,
- optional depth-window clipping,
- quality profiles for faster draft runs or higher-quality output.

### Source models

- volumetric X-ray source with interpolated sampling,
- optional exact voxel traversal via Siddon-style integration,
- mesh X-ray source with analytic ray-triangle intersection,
- projected mesh intersection backend for detector-space experiments.

### Physics and presentation

- simplified attenuation mapping from CT-like scalar values,
- Beer-Lambert style intensity conversion,
- optional heuristic energy and distance falloff terms,
- raw, digital radiography, and film-like presentation models,
- robust percentile-based normalization and optional windowing.

### Workflow integration

- `VirtualXRay` scene object integrated into the `pyDpVision` object tree,
- property panel for interactive setup and simulation,
- geometry presets in JSON,
- PNG, TIFF, and DICOM export helpers,
- synthetic demos and performance benchmarks.

## Typical use

Inside `pyDpVision`, the plugin is used through the `VirtualXRay` object and its
property panel:

1. load or create one or more `Volumetric` or `Mesh` objects,
2. create a `VirtualXRay` object,
3. choose a geometry preset or configure detector/source parameters manually,
4. tune sampling, physics, and presentation settings,
5. run the simulation and inspect or export the result.

## Project status

This plugin is currently best treated as a research and development tool rather
than a clinical or production radiography simulator.

Current strengths:

- flexible experimentation with geometry and appearance,
- readable Python implementation of the main projection pipeline,
- plugin-local test scaffold for the pure numeric backend,
- explicit attribution notes for major algorithmic references.

Current limitations:

- the physical model is simplified and partly heuristic,
- GUI integration is tied to the `pyDpVision` host application,
- OpenGL and Qt behavior are not covered by the current automated tests,
- some advanced backends are still experimental and should be validated case by case.

## Repository layout

```text
plugins/virtRTG/
  pluginMain.py              # plugin registration and menu integration
  virtualXRay.py             # scene object coordinating the whole RTG workflow
  benchmark.py               # demos and performance helpers
  gui/
    propVirtualXRay.py       # Qt property panel for VirtualXRay
  xray/
    xrayProjection.py        # geometry, physics, projector, scene API
    xraySource.py            # volumetric and mesh source backends
    xrayPresentation.py      # presentation models
    xrayAnnotationOverlay.py # projected overlay primitives
    xrayHelpers.py           # math and transform helpers
  presets/
    xray_geometry_presets.json
  docs/
    THIRD_PARTY_ATTRIBUTION.md
  tests/
    README.md
```

## Tests

A plugin-local `pytest` scaffold lives in `tests/` and currently focuses on the
pure numeric backend under `xray/`.

Already covered:

- geometry helpers,
- clipping helpers,
- scalar preprocessing and physics response,
- presentation models.

Planned next:

- volumetric source fixtures and Siddon tests,
- mesh-source fixtures and intersection parity tests,
- lightweight end-to-end backend projection tests.

See [tests/README.md](C:/praca/pyDpVision/plugins/virtRTG/tests/README.md:1) for
details.

## Documentation

- algorithm and attribution notes:
  [docs/THIRD_PARTY_ATTRIBUTION.md](C:/praca/pyDpVision/plugins/virtRTG/docs/THIRD_PARTY_ATTRIBUTION.md:1)
- plugin-local test notes:
  [tests/README.md](C:/praca/pyDpVision/plugins/virtRTG/tests/README.md:1)

## If this becomes a standalone repository

This README is already written in that direction. The next practical steps would
be:

- define installation and dependency instructions independent of `pyDpVision`,
- separate host-specific integration from backend-only code more explicitly,
- add CI for the `tests/` suite,
- provide one minimal reproducible example script outside the GUI path.
