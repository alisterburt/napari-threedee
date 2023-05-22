from napari.layers import Points

import napari_threedee.annotators.paths.constants
from napari_threedee.annotators.paths import PathAnnotator


def test_spline_annotator_instantiation(make_napari_viewer, blobs_layer_4d_plane):
    viewer = make_napari_viewer(ndisplay=3)
    plane_layer = viewer.add_layer(blobs_layer_4d_plane)
    annotator = PathAnnotator(
        viewer=viewer,
        image_layer=plane_layer,
    )
    assert isinstance(annotator.points_layer, Points)
    assert napari_threedee.annotators.paths.constants.PATH_ID_FEATURES_KEY in annotator.points_layer.features
    assert len(annotator.points_layer.data) == 0


def test_add_point(spline_annotator):
    points_layer = spline_annotator.points_layer
    label = napari_threedee.annotators.paths.constants.PATH_ID_FEATURES_KEY

    # start empty
    assert len(points_layer.data) == 0

    # add points, make sure filament id in feature table matches the annotator
    points_layer.add([1, 2, 3, 4])
    assert len(points_layer.data) == 1
    assert points_layer.features[label][0] == 0

    # change filamanet_id in annotator, add point, check matches
    points_layer.add([2, 3, 4, 5])
    assert points_layer.features[label][1] == 0
    assert spline_annotator.active_path_id == 0

    # create new path, make sure id advanced
    spline_annotator.activate_new_path_mode()
    points_layer.add([2, 3, 4, 5])
    assert points_layer.features[label][2] == 1
    assert spline_annotator.active_path_id == 1


def test_get_colors(spline_annotator):
    """Test getting spline colors from the annotator."""
    # add a point. the first spline gets id 0
    points_layer = spline_annotator.points_layer
    points_layer.add([1, 2, 3, 4])

    # create a new spline, this advances the spline id to 1
    spline_annotator.activate_new_path_mode()
    points_layer.add([2, 3, 4, 5])

    spline_colors = spline_annotator._get_path_colors()
    for spline_id in (0, 1):
        # check that both spline ids are in the colors dict
        assert spline_id in spline_colors
