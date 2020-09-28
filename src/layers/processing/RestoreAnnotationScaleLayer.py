# coding: utf-8

from copy import deepcopy

from Layer import Layer
from legacy_supervisely_lib.figure.image_resizer import ImageResizer


class RestoreAnnotationScaleLayer(Layer):

    action = 'restore_annotation_scale'

    layer_settings = {
        "required": ["settings"],
        "properties": {
            "settings": {
                "type": "object",
                "properties": {
                    "classes": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                }
            }
        }
    }

    def __init__(self, config):
        Layer.__init__(self, config)

    def process(self, data_el):
        img_desc, ann_orig = data_el
        img_wh = ann_orig.image_size_wh
        ann = deepcopy(ann_orig)

        if ann_orig.get('ann_size_wh') is not None:
            old_ann_size = ann_orig.get('ann_size_wh')

            resizer = ImageResizer(src_size_wh=old_ann_size, res_size_wh=img_wh, keep=False)

            selected_classes = self.settings.get('classes')

            if selected_classes is None:
                for fig in ann['objects']:
                    fig.resize(resizer)
            else:
                for fig in ann['objects']:
                    if fig.class_title in selected_classes:
                        fig.resize(resizer)
            del ann['ann_size_wh']
        yield img_desc, ann
