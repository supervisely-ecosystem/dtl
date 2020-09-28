# coding: utf-8

import numpy as np
from copy import deepcopy
from legacy_supervisely_lib.figure.figure_line import FigureLine
from legacy_supervisely_lib.figure.figure_polygon import FigurePolygon
from Layer import Layer
from shapely.geometry import LineString, Polygon


def remove_lines_inside_polygons2(polygons, lines_obj_list, imsize_wh):
    sh_lines = []
    for line_index, line_obj in enumerate(lines_obj_list):
        pack = line_obj.pack()
        coords = pack['points']['exterior']
        sh_line = LineString(coords)
        sh_lines.append({'orig': line_obj, 'sh': sh_line})

    sh_polygons = []
    for polygon in polygons:
        pack_points = polygon.pack()['points']
        c_exterior = pack_points['exterior']
        c_interiors = pack_points['interior']
        poly = Polygon(shell=c_exterior, holes=c_interiors)
        if poly.is_valid == False:
            poly = poly.buffer(0.001)

        sh_polygons.append(poly)

    for poly in sh_polygons:
        line_index = 0
        while line_index < len(sh_lines):
            line = sh_lines[line_index]["sh"]

            sh_lines[line_index]["sh"] = line.difference(poly)
            line_index = line_index + 1

    result = []
    for processed_obj in sh_lines:
        processed_sh_line = processed_obj["sh"]

        if processed_sh_line.geom_type == 'GeometryCollection':
            continue

        if processed_sh_line.geom_type == 'MultiLineString':
            for line in processed_sh_line:
                coords = np.transpose(line.coords.xy)
                class_title = processed_obj['orig'].class_title
                result.extend(FigureLine.from_np_points(class_title, imsize_wh, exterior=coords))
            continue

        if processed_sh_line.geom_type == 'LineString':
            coords = np.transpose(processed_sh_line.coords.xy)
            class_title = processed_obj['orig'].class_title
            result.extend(FigureLine.from_np_points(class_title, imsize_wh, exterior=coords))
            continue

    return result


class DropLinesUnderPolygonLayer(Layer):

    action = 'drop_lines_under_polygon'

    layer_settings = {
        "required": ["settings"],
        "properties": {
            "settings": {
                "type": "object",
                "required": ["lines_class", "polygons_class"],
                "properties": {
                    "lines_class": {
                        "type": "string",
                        "minLength": 1
                    },
                    "polygons_class": {
                        "type": "string",
                        "minLength": 1
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
        polygons_class = self.settings.get('polygons_class')

        lines = []
        polygons = []
        results = []

        for figure in ann['objects']:

            if lines_class == figure.class_title and isinstance(figure, FigureLine):
                lines.append(figure)
                continue

            if polygons_class == figure.class_title and isinstance(figure, FigurePolygon):
                polygons.append(figure)

            results.append(figure)

        lines = remove_lines_inside_polygons2(polygons, lines, image_size_wh)

        results.extend(lines)
        ann['objects'] = results
        yield img_desc, ann
