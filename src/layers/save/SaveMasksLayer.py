# coding: utf-8

import os.path as osp
from copy import deepcopy

import cv2
import numpy as np
from legacy_supervisely_lib.utils import imaging
from legacy_supervisely_lib.utils import os_utils

from Layer import Layer

import supervisely_lib as sly

# save to archive, with GTs and checks
class SaveMasksLayer(Layer):
    # out_dir, flag_name, mapping_name
    odir_flag_mapping = [
        ('masks_machine', 'masks_machine', 'gt_machine_color'),
        ('masks_human', 'masks_human', 'gt_human_color'),
    ]

    action = 'save_masks'

    layer_settings = {
        "required": ["settings"],
        "properties": {
            "settings": {
                "type": "object",
                "required": [
                    "masks_machine",
                    "masks_human"
                ],
                "properties": {
                    "gt_machine_color": {
                        "type": "object",
                        "patternProperties": {
                            ".*": {"$ref": "#/definitions/color"}
                        },
                    },
                    "gt_human_color": {
                        "type": "object",
                        "patternProperties": {
                            ".*": {"$ref": "#/definitions/color"}
                        }
                    },
                    "images": {  # Deprecated
                        "type": "boolean"
                    },
                    "annotations": {  # Deprecated
                        "type": "boolean"
                    },
                    "masks_machine": {
                        "type": "boolean"
                    },
                    "masks_human": {
                        "type": "boolean"
                    },
                }
            }
        }
    }

    @classmethod
    def draw_colored_mask(cls, ann, cls_mapping):
        w, h = ann.image_size_wh
        res_img = np.zeros((h, w, 3), dtype=np.uint8)
        for fig in ann['objects']:
            color = cls_mapping.get(fig.class_title)
            if color is None:
                continue  # ignore now
            fig.draw(res_img, color)
        return res_img

    def __init__(self, config, output_folder, net):
        Layer.__init__(self, config)

        if 'gt_machine_color' in self.settings:
            for cls in self.settings['gt_machine_color']:
                col = self.settings['gt_machine_color'][cls]
                # @TODO: is it required?
                # if np.min(col) != np.max(col):
                #     raise ValueError('"gt_machine_color"s should have equal rgb values, e.g.: [3, 3, 3].')
                if np.min(col) < 0:
                    raise ValueError('Minimum "gt_machine_color" should be [0, 0, 0].')

        for _, flag_name, mapping_name in self.odir_flag_mapping:
            if self.settings[flag_name]:
                if mapping_name not in self.settings:
                    raise ValueError("Color mapping {} required if {} is true.".format(mapping_name, flag_name))
                # @TODO: maybe check if all classes are present

        target_arr = ['masks_machine', 'masks_human']
        target_determ = any((self.settings[x] for x in target_arr))
        if not target_determ:
            raise ValueError("Some output target ({}) should be set to true.".format(', '.join(target_arr)))

        self.output_folder = output_folder
        self.net = net

        self.out_project = sly.Project(directory=output_folder, mode=sly.OpenMode.CREATE)

        # Deprecate warning
        for param in ['images', 'annotations']:
            if param in self.settings:
                sly.logger.warning("'save_masks' layer: '{}' parameter is deprecated. Skipped.".format(param))

    def is_archive(self):
        return True

    def requires_image(self):
        # res = self.settings['masks_human'] is True  # don't use img otherwise
        return True

    def validate_dest_connections(self):
        pass

    def process(self, data_el):
        img_desc, ann = data_el
        free_name = self.net.get_free_name(img_desc)
        new_dataset_name = img_desc.get_res_ds_name()

        for out_dir, flag_name, mapping_name in self.odir_flag_mapping:
            if not self.settings[flag_name]:
                continue
            cls_mapping = self.settings[mapping_name]

            # hack to draw 'black' regions
            if flag_name == 'masks_human':
                cls_mapping = {k: (1, 1, 1) if max(v) == 0 else v for k, v in cls_mapping.items()}

            img = self.draw_colored_mask(ann, cls_mapping)

            if flag_name == 'masks_human':
                orig_img = img_desc.read_image()
                comb_img = imaging.overlay_images(orig_img, img, 0.5)

                sep = np.array([[[0, 255, 0]]] * orig_img.shape[0], dtype=np.uint8)
                img = np.hstack((orig_img, sep, comb_img))

            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            output_img_path = osp.join(self.output_folder, new_dataset_name, out_dir, free_name + '.png')
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
