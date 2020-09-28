# coding: utf-8

from copy import deepcopy
from Layer import Layer

from legacy_supervisely_lib.project.tags_lib import tag_name_from_json, tag_value_from_json


class TagLayer(Layer):
    action = 'tag'

    # TODO add a way to specify meta information for the added tag.
    # TODO support all tag value types.
    layer_settings = {
        "required": ["settings"],
        "properties": {
            "settings": {
                "type": "object",
                "required": ["tag", "action"],
                "properties": {
                    "tag": {
                        "maxItems": 1,
                        "oneOf": [
                            {"type": "string"},
                            {
                                "type": "object",
                                "required": ["name"],
                                "properties": {
                                    "name": {"type": "string"},
                                    "value": {"type": "string"}
                                }
                            }
                        ]
                    },
                    "action": {
                        "type": "string",
                        "enum": ["add", "delete"]
                    }
                }
            }
        }
    }

    def __init__(self, config):
        Layer.__init__(self, config)
        if self.is_action_delete:
            # TODO factor out string constants.
            if isinstance(self.tag_json, dict) and 'value' in self.tag_json:
                # TODO relax this. Will require more detailed logic on how to modify the meta (c.f. get_removed_tags()).
                raise ValueError('Tag removal is only supported by name. Restriction by value is not supported.')

    @property
    def is_action_add(self):
        return self.settings['action'] == 'add'

    @property
    def is_action_delete(self):
        return self.settings['action'] == 'delete'

    @property
    def tag_json(self):
        return self.settings['tag']

    def get_added_tags(self):
        return [self.tag_json] if self.is_action_add else []

    def get_removed_tags(self):
        return [self.tag_json] if self.is_action_delete else []

    # TODO Refactor. All tag modification operations must be done inside Annotation.
    def process(self, data_el):
        img_desc, ann_orig = data_el
        ann = deepcopy(ann_orig)

        modified_tag_name = tag_name_from_json(self.tag_json)
        matching_by_name = {tag_name_from_json(tag): tag for tag in ann.tags
                            if tag_name_from_json(tag) == modified_tag_name}

        if self.is_action_add:
            if len(matching_by_name) == 0:
                ann.tags = ann.tags + [self.tag_json]
            else:
                if any(tag_value_from_json(tag) != tag_value_from_json(self.tag_json) for tag in matching_by_name):
                    raise ValueError(
                        'Trying to add tag value, but a tag with the same name and conflicting value exists: {}'.format(
                            str(matching_by_name)))
        if self.is_action_delete:
            ann.tags = [tag for tag in ann.tags if tag_name_from_json(tag) not in matching_by_name]
        yield img_desc, ann
