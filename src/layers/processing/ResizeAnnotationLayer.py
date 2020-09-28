# coding: utf-8

from copy import deepcopy

from Layer import Layer
from legacy_supervisely_lib.figure.image_resizer import ImageResizer
from legacy_supervisely_lib.figure.figure_bitmap import FigureBitmap


class ResizeAnnotationLayer(Layer):

    action = 'resize_annotation'

    layer_settings = {
        "required": ["settings"],
        "properties": {
            "settings": {
                "type": "object",
                "required": ["width", "height", "aspect_ratio"],
                "properties": {
                    "classes": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "width": {
                        "type": "integer",
                        "minimum": -1
                    },
                    "height": {
                        "type": "integer",
                        "minimum": -1
                    },
                    "aspect_ratio": {
                        "type": "object",
                        "required": ["keep"],
                        "properties": {
                            "keep": {
                                "type": "boolean"
                            }
                        }
                    }
                }
            }
        }
    }

    def __init__(self, config):
        Layer.__init__(self, config)
        if self.settings['height'] * self.settings['width'] == 0:
            raise RuntimeError(self, '"height" and "width" should be != 0.')
        if self.settings['height'] + self.settings['width'] == -2:
            raise RuntimeError(self, '"height" and "width" cannot be both set to -1.')
        if self.settings['height'] * self.settings['width'] < 0:
            if not self.settings['aspect_ratio']['keep']:
                raise RuntimeError(self, '"keep" "aspect_ratio" should be set to "true" '
                                         'when "width" or "height" is -1.')

    def process(self, data_el):
        img_desc, ann_orig = data_el
        img_wh = ann_orig.image_size_wh

        keep = self.settings['aspect_ratio']['keep']
        set_size_wh = (self.settings['width'], self.settings['height'])

        resizer = ImageResizer(src_size_wh=img_wh, res_size_wh=set_size_wh, keep=keep)
        ann = deepcopy(ann_orig)

        selected_classes = self.settings.get('classes')

        if selected_classes is None:
            for fig in ann['objects']:
                fig.resize(resizer)
        else:
            for fig in ann['objects']:
                if fig.class_title in selected_classes:
                    fig.resize(resizer)

        objects = []
        for fig in ann['objects']:
            if isinstance(fig, FigureBitmap):
                _, mask = fig.get_origin_mask()
                if mask is None:
                    continue
            objects.append(fig)

        ann['objects'] = objects
        ann['ann_size_wh'] = [resizer.new_w, resizer.new_h]

        yield img_desc, ann
