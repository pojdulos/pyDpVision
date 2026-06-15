# pyDpVision

`pyDpVision` is an early Python reimplementation of the original [`dpVision`](https://github.com/pojdulos/dpVision) project.

This repository should be treated as an experimental development environment, not as a stable application. The long-term goal is to explore a Python-based version of the platform, but the project is still at a very early stage and a large part of the intended functionality is incomplete, untested, broken, or simply not implemented yet.

At the moment, the codebase is best understood as a sandbox for architecture experiments, rendering experiments, parser work, and feature prototyping around scientific and medical 3D data.

## Project Status

- very early stage of development
- many features do not work yet
- APIs, behavior, file formats, and internal structure may change without notice
- the repository may contain partially working prototypes, abandoned ideas, and research code

If you are browsing this repository, the safest assumption is that everything here is work in progress.

## Intended Scope

The project is meant to evolve into a Python desktop environment for 3D scientific visualization, with a focus on data such as:

- point clouds
- triangle meshes
- volumetric medical data such as CT and MRI
- experimental research workflows and visualization tools

The current codebase already contains the beginnings of a Qt/OpenGL application, scene objects, parsers, and sample data, but it should not be considered production-ready.

Some parts of the repository are intended to cover workflows around:

- scene hierarchies and transformable objects
- OpenGL-based interactive visualization
- parsers for meshes, point clouds, images, and volumetric data
- experimental plugin-style extensions

## Plugins

The application includes an experimental plugin mechanism and scans the `plugins/` directory for plugin entry points.

This repository currently contains a very simple example plugin in `plugins/myPlugin01/`. It should be treated as a minimal integration example rather than a finished feature. Its main value is to show the current plugin entry structure and how a plugin can attach itself to the application menu and lifecycle.

## Running It

If you still want to inspect or try the current state locally:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

There is also a simple setup script:

```powershell
setup.bat
```

## Repository Layout

```text
main.py             application entry point
dpVision/           main package
sample_data/        sample assets and input data
plugins/            plugin area and experimental extensions
```

## Warning

This repository is provided strictly as-is.

- no guarantee of correctness
- no guarantee of completeness
- no guarantee of stability
- no guarantee of backward compatibility
- no guarantee of fitness for any particular purpose
- no guarantee of continued maintenance, support, or updates

Do not rely on it for production, clinical, diagnostic, safety-critical, or decision-critical use.

This codebase is a research and development prototype. It may contain serious bugs, invalid assumptions, incomplete implementations, and misleading results.

By using this repository, you accept that you do so entirely at your own risk.

To the maximum extent permitted by applicable law, the authors and contributors disclaim any warranties, express or implied, and shall not be liable for any claim, damage, loss, data loss, malfunction, or any direct, indirect, incidental, consequential, or other liability arising from the use of this code, the generated data, or any conclusions derived from it.

## License

See [LICENSE](./LICENSE).
