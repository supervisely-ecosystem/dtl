# coding: utf-8

import math
from copy import deepcopy
from legacy_supervisely_lib.figure.figure_line import FigureLine
from Layer import Layer


def distance(p1, p2) -> float:
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def get_line_path(line: list) -> float:
    path = 0.0
    for i in range(1, len(line)):
        path += distance(line[i-1], line[i])
    return path


def check_line_by_length(line, min_length, max_length, invert):
    packed = line.pack()
    points = packed['points']['exterior']
    line_length = get_line_path(points)

    result = True
    if min_length is not None:
        result = result and (line_length >= min_length)
    if max_length is not None:
        result = result and (line_length <= max_length)

    if invert is True:
        result = not result
    return result


class DropLinesByLengthLayer(Layer):

    action = 'drop_lines_by_length'

    layer_settings = {
        "required": ["settings"],
        "properties": {
            "settings": {
                "type": "object",
                "required": ["lines_class"],
                "properties": {
                    "lines_class": {
                        "description_en": u"Class-name of lines for processing",
                        "description_ru": u"Название класса линий для обработки",
                        "type": "string",
                        "minLength": 1
                    },
                    "min_length": {
                        "description_en": u"Mininal length for no-deleted line candidate",
                        "description_ru": u"Минимальная длина линии, которая не будет удалена",
                        "type": "number",
                        "minimum": 0
                    },
                    "max_length": {
                        "description_en": u"Maximal length for no-deleted line candidate",
                        "description_ru": u"Максимальная длина линии, которая не будет удалена",
                        "type": "number",
                        "minimum": 0
                    },
                    "invert": {
                        "description_en": u"Invert remove decisions for lines",
                        "description_ru": u"Обратить результаты отбора линий",
                        "type": "boolean"
                    },
                    "resolution_compensation": {
                        "description_en": u"Length compensation for different resolutions",
                        "description_ru": u"Компенсация длины линий при разных разрешениях",
                        "type": "boolean"
                    }
                }
            }
        }
    }

    def __init__(self, config):
        Layer.__init__(self, config)

    def process(self, data_el):
        img_desc, ann_orig = data_el
        ann = deepcopy(ann_orig)
        image_size_wh = ann_orig.image_size_wh

        lines_class = self.settings.get('lines_class')
        min_length = self.settings.get('min_length')
        max_length = self.settings.get('max_length')
        invert_opt = self.settings.get('invert', False)
        resolution_compensation = self.settings.get('resolution_compensation', False)

        if (min_length is None) and (max_length is None):
            raise RuntimeError(self, '"min_length" and/or "max_length" properties should be selected for "delete_lines_by_length" layer')

        if resolution_compensation:
            compensator = image_size_wh[0]/1000.0
            if min_length is not None: min_length *= compensator
            if max_length is not None: max_length *= compensator

        figures = ann['objects']
        results = []

        for figure in figures:
            if not isinstance(figure, FigureLine):
                results.append(figure)
            else:
                if lines_class == figure.class_title:
                    if check_line_by_length(figure, min_length, max_length, invert_opt):
                        results.append(figure)
                else:
                    results.append(figure)

        ann['objects'] = results
        yield img_desc, ann
