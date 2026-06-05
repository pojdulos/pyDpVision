# virtRTG

`virtRTG` is the pyDpVision plugin responsible for synthetic X-ray projection.
It combines scene integration, a Qt property panel, projection backends, export
helpers, geometry presets, and plugin-local documentation.

## Current structure

```text
plugins/virtRTG/
  pluginMain.py              # plugin registration, menu actions, property-panel hookup
  virtualXRay.py             # scene-tree object integrating geometry, sources, and rendering
  benchmark.py               # demo and benchmark helpers for the RTG backend
  gui/
    propVirtualXRay.py       # Qt property panel for VirtualXRay
  xray/
    xrayProjection.py        # projection geometry, physics, scene orchestration
    xraySource.py            # volumetric and mesh source backends
    xrayPresentation.py      # presentation models for raw/digital/film output
    xrayAnnotationOverlay.py # projected 2D overlay primitives for annotations
    xrayHelpers.py           # small math and transform helpers
  presets/
    xray_geometry_presets.json
  docs/
    THIRD_PARTY_ATTRIBUTION.md
```

## Why this layout is coherent

- Top-level files keep plugin integration visible: entrypoint, main scene object,
  and benchmark utilities remain easy to discover.
- `gui/` isolates Qt-specific code from the projection backend.
- `xray/` groups the computational backend and makes the dependency direction
  clear: `virtualXRay.py` consumes backend modules rather than mixing all logic
  into one file.
- `presets/` keeps editable configuration out of code.
- `docs/` is the right place for attribution and future plugin-local notes.

## Small conventions worth keeping

- Put scene-tree integration and application wiring at plugin root.
- Put reusable backend code under `xray/`.
- Put Qt widgets and property panels under `gui/`.
- Keep benchmark and demo helpers separate from runtime backend code.
- Prefer relative imports inside the plugin so future moves stay local.

## Follow-up ideas

- If plugin-local LaTeX or longer technical notes appear later, keep them under
  `docs/` next to `THIRD_PARTY_ATTRIBUTION.md`.
- If more GUI panels are added, keep one widget family per file inside `gui/`.
- If the backend grows further, `xray/` can later be split into subpackages such
  as `geometry/`, `sources/`, and `presentation/`, but the current size does
  not require that yet.

## Tests

- A plugin-local pytest scaffold lives in `plugins/virtRTG/tests/`.
- The current focus is the pure numeric backend under `xray/`, not Qt or GL.
- The first implemented tests cover geometry helpers, clipping, physics, and
  presentation models.
- Heavier source-backend cases are listed explicitly in
  `tests/unit/test_source_skeleton.py` for incremental follow-up work.
