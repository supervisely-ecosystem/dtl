# coding: utf-8

from copy import deepcopy
import math
import numpy as np
from legacy_supervisely_lib.figure.figure_line import FigureLine
from legacy_supervisely_lib.figure.figure_polygon import FigurePolygon
import cv2

from Layer import Layer
from classes_utils import ClassConstants


def distance(p1, p2) -> float:
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def find_trapeze_sides(imsize_wh, bbox, points):
    w, h = imsize_wh

    points = np.array(points)

    vertices = np.expand_dims(points, axis=1)
    vertices = vertices.astype(np.int)
    vertices = cv2.convexHull(vertices)
    points = np.squeeze(vertices, axis=1)

    triangle = [[w // 2, h // 1.75], [0, 0], [w, 0]]
    triangle = np.expand_dims(triangle, axis=1).astype(np.int)

    points = points.tolist()

    if len(points) == 0:
        return None

    def get_nearest_point(points, target_point):
        nearest_point = points[0]
        nearest_index = 0
        nearest_distance = distance(nearest_point, target_point)
        for index, point in enumerate(points):
            current_distance = distance(point, target_point)
            if current_distance < nearest_distance:
                nearest_distance = current_distance
                nearest_point = point
                nearest_index = index
        return nearest_index, nearest_point

    left_bottom_point_index, left_bottom_point = get_nearest_point(points, (-1000, h * 0.7))
    right_bottom_point_index, right_bottom_point = get_nearest_point(points, (w + 1000, h * 0.7))

    left_line = []
    right_line = []

    if len(points) > 7:
        step = 0

        for index in range(0, len(points)):
            point = points[index]
            inside = cv2.pointPolygonTest(triangle, (point[0], point[1]), False) >= 0

            if step == 0:
                if inside:
                    midpoint = [(points[index][0] + points[index - 1][0]) // 2,
                                (points[index][1] + points[index - 1][1]) // 2]
                    left_line = [left_bottom_point, midpoint]
                    step = 1
                    continue

            if step == 1:
                if inside:
                    continue
                if not inside:
                    step = 2

            if step == 2:
                if inside:
                    continue
                if not inside:
                    midpoint = [(points[index][0] + points[index - 1][0]) // 2,
                                (points[index][1] + points[index - 1][1]) // 2]
                    right_line = [midpoint, right_bottom_point]
                    break

    if len(left_line) == 0:
        _, left_top_point = get_nearest_point(points, (-1000, -1000))
        left_line = [left_top_point, left_bottom_point]

    if len(right_line) == 0:
        _, right_top_point = get_nearest_point(points, (w + 1000, -1000))
        right_line = [right_top_point, right_bottom_point]

    return [left_line, right_line]


class RoadLinesLayer(Layer):

    action = 'road_lines'

    layer_settings = {
        "required": ["settings"],
        "properties": {
            "settings": {
                "type": "object",
                "required": ["road_class", "road_lines_class"],
                "properties": {
                    "min_road_area": {
                        "type": "number",
                        "minimum": 1
                    },
                    "road_class": {
                        "type": "string",
                        "minLength": 1
                    },
                    "road_lines_class": {
                        "type": "string",
                        "minLength": 1
                    },
                }
            }
        }
    }

    def __init__(self, config):
        Layer.__init__(self, config)

    def define_classes_mapping(self):
        new_class = self.settings['road_lines_class']
        self.cls_mapping[ClassConstants.NEW] = [{'title': new_class, 'shape': 'line', 'color': '#000088'}]
        self.cls_mapping[ClassConstants.OTHER] = ClassConstants.DEFAULT

    def process(self, data_el):
        img_desc, ann_orig = data_el
        ann = deepcopy(ann_orig)
        imsize_wh = ann_orig.image_size_wh
        min_road_area = self.settings.get('min_road_area', 1)
        road_class = self.settings['road_class']
        road_lines_class = self.settings['road_lines_class']

        def add_road_lines(figure):
            results = [figure]
            if figure.class_title == road_class:
                if not isinstance(figure, FigurePolygon):
                    raise RuntimeError('Input class must be a Polygon in road_lines layer.')

                road_bbox = figure.get_bbox()

                coef = imsize_wh[0] / 1000
                if road_bbox.area >= min_road_area * coef:
                    points = figure.pack()['points']['exterior']
                    lines = find_trapeze_sides(imsize_wh, road_bbox, points)

                    lines_results = []
                    if lines is not None:
                        lines_results.extend(FigureLine.from_np_points(road_lines_class, imsize_wh, exterior=lines[0]))
                        lines_results.extend(FigureLine.from_np_points(road_lines_class, imsize_wh, exterior=lines[1]))

                    results.extend(lines_results)
            return results

        ann.apply_to_figures(add_road_lines)
        yield img_desc, ann
