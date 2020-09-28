# coding: utf-8

from copy import deepcopy
import numpy as np

from Layer import Layer
from legacy_supervisely_lib.figure.figure_bitmap import FigureBitmap


class MergeMasksLayer(Layer):

    action = 'merge_bitmap_masks'

    layer_settings = {
        "required": ["settings"],
        "properties": {
            "settings": {
                "type": "object",
                "required": ["class"],
                "properties": {
                    "class": {
                        "type": "string"
                    }
                }
            }
        }
    }

    def __init__(self, config):
        Layer.__init__(self, config)

    def merge_bitmaps(self, class_title, masks, imsize_wh):
        base_mask = np.full((imsize_wh[1], imsize_wh[0]), False, bool)
        for figure in masks:
            origin, mask = figure.get_origin_mask()
            full_size_mask = np.full((imsize_wh[1], imsize_wh[0]), False, bool)
            full_size_mask[origin[1]:origin[1] + mask.shape[0], origin[0]:origin[0] + mask.shape[1]] = mask
            base_mask = np.logical_or(base_mask, full_size_mask)

        return FigureBitmap.from_mask(class_title, imsize_wh, [0, 0], base_mask)[0]

    def process(self, data_el):
        img_desc, ann_orig = data_el
        ann = deepcopy(ann_orig)
        imsize_wh = ann.image_size_wh

        class_mask = self.settings['class']

        masks_for_merge = []
        results = []

        objects = ann['objects']

        for figure in objects:
            if figure.class_title == class_mask:
                if not isinstance(figure, FigureBitmap):
                    raise RuntimeError('Input class must be a Bitmap in road_lines layer.')
                masks_for_merge.append(figure)
            else:
                results.append(figure)

        # speed optimize
        if len(masks_for_merge) > 0:
            if len(masks_for_merge) == 1:
                results.append(masks_for_merge[0])
            else:
                total_bitmap_figure = self.merge_bitmaps(class_mask, masks_for_merge, imsize_wh)
                results.append(total_bitmap_figure)

        ann['objects'] = results
        yield img_desc, ann
