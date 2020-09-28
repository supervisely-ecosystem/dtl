# coding: utf-8

from copy import deepcopy

import numpy as np
from legacy_supervisely_lib.figure.figure_bitmap import FigureBitmap

from Layer import Layer
from classes_utils import ClassConstants


# converts ALL types to FigureBitmap
class RasterisationLayer(Layer):

    action = 'rasterize'

    layer_settings = {
        "required": ["settings"],
        "properties": {
            "settings": {
                "type": "object",
                "required": ["classes_mapping"],
                "properties": {
                    "classes_mapping": {
                        "type": "object",
                        "patternProperties": {
                            ".*": {"type": "string"}
                        }
                    }
                }
            }
        }
    }

    def __init__(self, config):
        Layer.__init__(self, config)

    def define_classes_mapping(self):
        for old_class, new_class in self.settings['classes_mapping'].items():
            self.cls_mapping[old_class] = {'title': new_class, 'shape': 'bitmap'}
        self.cls_mapping[ClassConstants.OTHER] = ClassConstants.DEFAULT

    def process(self, data_el):
        img_desc, ann_orig = data_el
        ann = deepcopy(ann_orig)
        imsize_wh = ann.image_size_wh
        shape_hw = imsize_wh[::-1]

        rasterised_mask = np.zeros(shape_hw, dtype=np.uint16)
        key_to_cls = {}

        new_figures = []

        for i, fig in enumerate(ann['objects']):
            if fig.class_title in self.settings['classes_mapping']:
                fig.draw(rasterised_mask, i + 1)
                key_to_cls[i + 1] = fig.class_title
            else:
                new_figures.append(fig)


        for inst in np.unique(rasterised_mask)[1:]:
            mask = rasterised_mask == inst
            old_class = key_to_cls[inst]
            figures = FigureBitmap.from_mask(self.settings['classes_mapping'][old_class], imsize_wh, (0, 0), mask)
            new_figures.extend(figures)

        ann['objects'] = new_figures

        yield img_desc, ann
