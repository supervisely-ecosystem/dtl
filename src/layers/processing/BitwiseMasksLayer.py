# coding: utf-8

from copy import deepcopy
from Layer import Layer
import numpy as np
from legacy_supervisely_lib.figure.figure_bitmap import FigureBitmap


class BitwiseMasksLayer(Layer):

    action = 'bitwise_masks'

    layer_settings = {
        "required": ["settings"],
        "properties": {
            "settings": {
                "type": "object",
                "required": ["type", "class_mask", "classes_to_correct"],
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["or", "and", 'nor']
                    },
                    "class_mask": {
                        "type": "string"
                    },
                    "classes_to_correct": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        }
    }

    def __init__(self, config):
        Layer.__init__(self, config)

    def find_mask_class(self, objects, class_mask_name):
        for obj in objects:
            if obj.class_title == class_mask_name:
                if not isinstance(obj, FigureBitmap):
                    raise RuntimeError('Class <{}> must be a Bitmap in bitwise_masks layer.'.format(class_mask_name))
                return obj

    def bitwise_ops(self, type):
        ops = {
            'or': lambda m1, m2: np.logical_or(m1, m2),
            'and': lambda m1, m2: np.logical_and(m1, m2),
            'nor': lambda m1, m2: np.logical_xor(m1, m2),
        }
        if type not in ops:
            raise RuntimeError('Bitwise type <{}> not in list {}.'.format(type, list(ops.keys())))
        return ops[type]

    def process(self, data_el):
        img_desc, ann_orig = data_el
        ann = deepcopy(ann_orig)
        imsize_wh = ann.image_size_wh
        bitwise_type = self.settings['type']
        class_mask = self.settings['class_mask']

        objects = ann['objects']
        mask_obj = self.find_mask_class(objects, class_mask)

        if mask_obj is not None:
            target_original, target_mask = mask_obj.get_origin_mask()
            full_target_mask = np.full((imsize_wh[1], imsize_wh[0]), False, bool)

            full_target_mask[target_original[1]:target_original[1] + target_mask.shape[0],
                        target_original[0]:target_original[0] + target_mask.shape[1]] = target_mask

            results = []

            for figure in objects:
                if figure.class_title not in self.settings['classes_to_correct'] or figure.class_title == class_mask:
                    results.append(figure)
                else:

                    if not isinstance(figure, FigureBitmap):
                        raise RuntimeError('Input class must be a Bitmap in bitwise_masks layer.')

                    origin, mask = figure.get_origin_mask()
                    full_size_mask = np.full((imsize_wh[1], imsize_wh[0]), False, bool)
                    full_size_mask[origin[1]:origin[1] + mask.shape[0], origin[0]:origin[0] + mask.shape[1]] = mask

                    func = self.bitwise_ops(bitwise_type)
                    new_mask = func(full_target_mask, full_size_mask).astype(bool)
                    results.extend(FigureBitmap.from_mask(figure.class_title, imsize_wh, (0,0), new_mask))
            ann['objects'] = results

        yield img_desc, ann
