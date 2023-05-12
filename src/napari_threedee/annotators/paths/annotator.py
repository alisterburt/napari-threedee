import napari
from napari.layers import Image, Points, Shapes
from napari.layers.utils.layer_utils import features_to_pandas_dataframe
import numpy as np
from typing import Optional, Dict

from napari_threedee._backend.threedee_model import N3dComponent
from napari_threedee.annotators.paths.constants import (
    PATH_ID_FEATURES_KEY,
    PATH_COLOR_FEATURES_KEY,
)
from napari_threedee.utils.mouse_callbacks import add_point_on_plane
from napari_threedee.utils.napari_utils import add_mouse_callback_safe, \
    remove_mouse_callback_safe


class PathAnnotator(N3dComponent):
    def __init__(
        self,
        viewer: napari.Viewer,
        image_layer: Optional[Image] = None,
        points_layer: Optional[Points] = None,
        enabled: bool = False
    ):
        self.viewer = viewer

        self.image_layer = image_layer
        self.points_layer = points_layer
        self.shapes_layer = None

        self.auto_fit_spline = True

        if image_layer is not None:
            self.set_layers(self.image_layer)

        self.enabled = enabled

    def activate_new_path_mode(self, event=None) -> None:
        if self.points_layer is None:
            return
        df = features_to_pandas_dataframe(self.points_layer.features)
        if len(df) == 0:
            new_path_id = 0
        else:
            new_path_id = np.max(df[PATH_ID_FEATURES_KEY]) + 1
        self.points_layer.selected_data = {}
        self.points_layer.current_properties = {PATH_ID_FEATURES_KEY: [new_path_id]}

    def _mouse_callback(self, viewer, event):
        if (self.image_layer is None) or (self.points_layer is None):
            return
        add_point_on_plane(
            viewer=viewer,
            event=event,
            points_layer=self.points_layer,
            image_layer=self.image_layer
        )

    def _create_points_layer(self) -> Points:
        from napari_threedee.data_models import N3dPaths
        layer = N3dPaths(data=[]).as_layer()
        return layer

    def _create_shapes_layer(self) -> Shapes:
        return Shapes(
            ndim=self.image_layer.data.ndim,
            name="n3d paths (smooth fit)",
            edge_color="green"
        )

    def set_layers(self, image_layer: napari.layers.Image):
        self.image_layer = image_layer
        if self.image_layer is not None:
            if self.points_layer is None:
                self.points_layer = self._create_points_layer()
            if self.points_layer not in self.viewer.layers:
                self.viewer.add_layer(self.points_layer)
            if self.shapes_layer is None:
                self.shapes_layer = self._create_shapes_layer()
            if self.shapes_layer not in self.viewer.layers:
                self.viewer.add_layer(self.shapes_layer)
            self._draw_paths()

    def _on_enable(self):
        if self.points_layer is not None:
            add_mouse_callback_safe(
                self.viewer.mouse_drag_callbacks, self._mouse_callback
            )
            self.points_layer.events.data.connect(self._on_point_data_changed)
            self.viewer.bind_key('n', self.activate_new_path_mode, overwrite=True)
            self.viewer.layers.selection.active = self.image_layer

    def _on_disable(self):
        remove_mouse_callback_safe(
            self.viewer.mouse_drag_callbacks, self._mouse_callback
        )
        if self.points_layer is not None:
            self.points_layer.events.data.disconnect(
                self._on_point_data_changed
            )
        self.viewer.bind_key('n', None, overwrite=True)

    def _on_point_data_changed(self, event=None):
        if self.auto_fit_spline is True:
            self._draw_paths()

    def _get_path_colors(self) -> Dict[int, np.ndarray]:
        self.points_layer.features[PATH_COLOR_FEATURES_KEY] = \
            list(self.points_layer.face_color)
        grouped_points_features = self.points_layer.features.groupby(
            PATH_ID_FEATURES_KEY
        )
        path_colors = dict()
        for path_id, path_df in grouped_points_features:
            path_colors[path_id] = path_df[PATH_COLOR_FEATURES_KEY].iloc[0]
        return path_colors

    def _clear_shapes_layer(self):
        """Delete all shapes in the shapes layer."""
        if self.shapes_layer is None:
            return
        n_shapes = len(self.shapes_layer.data)
        self.shapes_layer.selected_data = set(np.arange(n_shapes))
        self.shapes_layer.remove_selected()

    def _draw_paths(self):
        from napari_threedee.data_models import N3dPaths
        paths = N3dPaths.from_layer(self.points_layer)
        spline_colors = self._get_path_colors()
        self._clear_shapes_layer()
        for path, color in zip(paths, spline_colors.values()):
            if len(path) >= 2:
                points = path.sample(n=2000)
                self.shapes_layer.add_paths(points, edge_color=color)
