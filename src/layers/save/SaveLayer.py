# coding: utf-8

import os.path as osp
from copy import deepcopy

import cv2
import numpy as np
from legacy_supervisely_lib.figure import color_utils
from legacy_supervisely_lib.figure.figure_bitmap import FigureBitmap
from legacy_supervisely_lib.figure.figure_polygon import FigurePolygon
from legacy_supervisely_lib.utils import imaging
from legacy_supervisely_lib.utils import os_utils

from Layer import Layer

import supervisely_lib as sly


# save to archive
class SaveLayer(Layer):

    action = 'save'

    layer_settings = {
        "required": ["settings"],
        "properties": {
            "settings": {
                "type": "object",
                "properties": {
                    "images": {  # Deprecated
                        "type": "boolean"
                    },
                    "annotations": {  # Deprecated
                        "type": "boolean"
                    },
                    "visualize": {
                        "type": "boolean"
                    }
                }
            }
        }
    }

    @classmethod
    def draw_colored_mask(cls, ann, color_mapping):
        w, h = ann.image_size_wh
        line_w = int((max(w, h) + 1) / 300)
        line_w = max(line_w, 1)
        res_img = np.zeros((h, w, 3), dtype=np.uint8)

        for fig in ann['objects']:
            color = color_mapping.get(fig.class_title)
            if color is None:
                continue  # ignore now
            if isinstance(fig, FigureBitmap) or isinstance(fig, FigurePolygon):
                fig.draw(res_img, color)
            else:
                fig.draw_contour(res_img, color, line_w)

        return res_img

    def __init__(self, config, output_folder, net):
        Layer.__init__(self, config)
        self.output_folder = output_folder
        self.net = net
        self.out_project = sly.Project(directory=output_folder, mode=sly.OpenMode.CREATE)

        # Deprecate warning
        for param in ['images', 'annotations']:
            if param in self.settings:
                sly.logger.warning("'save' layer: '{}' parameter is deprecated. Skipped.".format(param))

    def is_archive(self):
        return True

    def requires_image(self):
        return True

    def validate_dest_connections(self):
        pass

    def process(self, data_el):
        img_desc, ann = data_el
        free_name = self.net.get_free_name(img_desc)
        new_dataset_name = img_desc.get_res_ds_name()

        if self.settings.get('visualize'):
            out_meta = self.net.get_result_project_meta()
            cls_mapping = {}
            for cls_descr in out_meta.classes:
                color_s = cls_descr.get('color')
                if color_s is not None:
                    color = color_utils.hex2rgb(color_s)
                else:
                    color = color_utils.get_random_color()
                cls_mapping[cls_descr['title']] = color

            # hack to draw 'black' regions
            cls_mapping = {k: (1, 1, 1) if max(v) == 0 else v for k, v in cls_mapping.items()}

            vis_img = self.draw_colored_mask(ann, cls_mapping)
            orig_img = img_desc.read_image()
            comb_img = imaging.overlay_images(orig_img, vis_img, 0.5)

            sep = np.array([[[0, 255, 0]]] * orig_img.shape[0], dtype=np.uint8)
            img = np.hstack((orig_img, sep, comb_img))

            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            output_img_path = osp.join(self.output_folder, new_dataset_name, 'visualize', free_name + '.png')
            os_utils.ensure_base_path(output_img_path)
            cv2.imwrite(output_img_path, img)

        ann_to_save = deepcopy(ann)
        ann_to_save.normalize_figures()
        packed_ann = ann_to_save.pack()

        dataset_name = img_desc.get_res_ds_name()
        if not self.out_project.datasets.has_key(dataset_name):
            self.out_project.create_dataset(dataset_name)
        out_dataset = self.out_project.datasets.get(dataset_name)

        out_item_name = free_name + img_desc.get_image_ext()

        # net _always_ downloads images
        if img_desc.need_write():
            out_dataset.add_item_np(out_item_name, img_desc.image_data, ann=packed_ann)
        else:
            out_dataset.add_item_file(out_item_name, img_desc.get_img_path(), ann=packed_ann)

        yield ([img_desc, ann],)
