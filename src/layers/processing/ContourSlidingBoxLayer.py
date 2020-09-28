# coding: utf-8

from copy import deepcopy
import math

from legacy_supervisely_lib.figure.figure_polygon import FigurePolygon
from legacy_supervisely_lib.figure.figure_rectangle import FigureRectangle
from legacy_supervisely_lib.figure.rectangle import Rect

from Layer import Layer
from classes_utils import ClassConstants


def fix_coord(coord, min_value, max_value):
    return max(min_value, min(max_value, coord))


def simple_distance(p1, p2) -> float:
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def normalize(p1, p2):
    x, y = p2[0] - p1[0], p2[1] - p1[1]
    norm = math.sqrt(x * x + y * y)
    if norm > 0:
        nx = x / norm
        ny = y / norm
    else:
        nx = ny = 0
    return nx, ny


def contour_stepper(lines, step=0.5, eps=0.1):
    path = 0.0
    counter = 0.0

    for point_index in range(1, len(lines)):
        previous_point = lines[point_index-1]
        current_point = lines[point_index]

        vx, vy = normalize(previous_point, current_point)

        current_distance = simple_distance(previous_point, current_point)

        while path < current_distance:
            path = path + eps
            counter = counter + eps
            if(counter >= step):
                counter = 0
                current_pos = [(previous_point[0] + vx * path), (previous_point[1] + vy * path)]
                yield current_pos

        path = path - current_distance


def generate_box(x, y, box_wh, image_wh):
    half_w = box_wh[0] // 2
    half_h = box_wh[1] // 2

    x = fix_coord(x, half_w, (image_wh[0]-1)-half_w)
    y = fix_coord(y, half_h, (image_wh[1]-1)-half_h)

    left = x - half_w
    right = x + half_w

    top = y + half_h
    bottom = y - half_h
    return left, top, right, bottom


def add_boxies_for_contour(figure, image_wh, box_wh, distance, box_class_title):
    boxes = []

    figure_points = figure.pack()['points']['exterior']
    figure_points = figure_points + [figure_points[0]]

    for x, y in contour_stepper(figure_points, step=distance):
        left, top, right, bottom = generate_box(x, y, box_wh, image_wh)

        rect = Rect(left, top, right, bottom)
        box_s = FigureRectangle.from_rect(box_class_title, image_wh, rect)
        boxes.extend(box_s)

    return boxes


class ContourSlidingBoxLayer(Layer):

    action = 'contour_sliding_box'

    layer_settings = {
        "required": ["settings"],
        "properties": {
            "settings": {
                "type": "object",
                "required": ["box", "distance", "classes", "box_class"],
                "properties": {
                    "box": {
                        "type": "object",
                        "uniqueItems": True,
                        "items": {
                            "type": "string",
                            "patternProperties": {
                                "(width)|(height)": {
                                    "type": "string",
                                    "pattern": "^[0-9]+(%)|(px)$"
                                }
                            }
                        }
                    },
                    "distance": {
                        "type": "string",
                        "pattern": "^[0-9]+(%)|(px)$"
                    },
                    "classes": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        }
                    },
                    "box_class": {
                        "type": "string"
                    }
                }
            }
        }
    }

    def __init__(self, config):
        Layer.__init__(self, config)

    def define_classes_mapping(self):
        new_class = self.settings['box_class']
        self.cls_mapping[ClassConstants.NEW] = [{'title': new_class, 'shape': 'rectangle', 'color': '#00EE00'}]
        self.cls_mapping[ClassConstants.OTHER] = ClassConstants.DEFAULT

    def fix_percent(self, value, abs_value):
        if isinstance(value, str):
            if '%' in value:
                value = value.replace('%', '')
                if value.replace('.', '').isdigit():
                    return int(float(value) / 100.0 * abs_value)
            if 'px' in value:
                value = value.replace('px', '')
                if value.isdigit():
                    return int(value)


    def process(self, data_el):
        img_desc, ann_orig = data_el
        ann = deepcopy(ann_orig)
        imsize_wh = ann_orig.image_size_wh

        box_w = self.fix_percent(self.settings["box"]["width"], imsize_wh[0])
        box_h = self.fix_percent(self.settings["box"]["height"], imsize_wh[1])
        box_wh = [box_w, box_h]

        distance = self.fix_percent(self.settings["distance"], min(imsize_wh[0], imsize_wh[1]))

        classes = self.settings["classes"]
        box_class = self.settings["box_class"]

        def add_contour_boxies(figure):
            results = [figure]
            if figure.class_title in classes:
                if not isinstance(figure, FigurePolygon):
                    raise RuntimeError('Input class must be a Polygon in <contour_sliding_box> layer.')

                results.extend(add_boxies_for_contour(figure,
                                                      image_wh=imsize_wh,
                                                      box_wh=box_wh,
                                                      distance=distance,
                                                      box_class_title=box_class))
            return results

        ann.apply_to_figures(add_contour_boxies)
        yield img_desc, ann
