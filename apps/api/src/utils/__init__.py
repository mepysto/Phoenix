"""Utility functions for Phoenix API.

Import submodules directly (e.g. ``from src.utils.geo import ...``). This
package intentionally re-exports nothing: eagerly importing utils.geojson
pulled in services -> repositories -> utils.geo and created an import cycle.
"""
