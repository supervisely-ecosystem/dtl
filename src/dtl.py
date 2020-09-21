import os
import supervisely_lib as sly

my_app = sly.AppService()

task_id = os.environ["TASK_ID"]
WORKSPACE_ID = int(os.environ['context.workspaceId'])
PROJECT_ID = int(os.environ['modal.state.slyProjectId'])
REMOVE_ORIGINAL_CLASS = bool(os.environ['modal.state.remove'])

_SUFFIX = "(without AnyShape)"

@my_app.callback("do")
@sly.timeit
def do(**kwargs):
    api = sly.Api.from_env()

    # read source project
    src_project = api.project.get_info_by_id(PROJECT_ID)

    if src_project.type != str(sly.ProjectType.IMAGES):
        raise Exception("Project {!r} has type {!r}. App works only with type {!r}"
                        .format(src_project.name, src_project.type, sly.ProjectType.IMAGES))

    src_project_meta_json = api.project.get_meta(src_project.id)
    src_project_meta = sly.ProjectMeta.from_json(src_project_meta_json)

    # check that project has anyshape classes
    find_anyshape = False
    new_classes_lst = []
    for cls in src_project_meta.obj_classes:
        cls: sly.ObjClass
        if cls.geometry_type == sly.AnyGeometry:
            find_anyshape = True
            if REMOVE_ORIGINAL_CLASS is True:
                continue
        new_classes_lst.append(cls.clone())
    dst_classes = sly.ObjClassCollection(new_classes_lst)
    if find_anyshape is False:
        raise Exception("Project {!r} doesn't have classes with shape \"Any\"".format(src_project.name))

    # create destination project
    dst_name = src_project.name if _SUFFIX in src_project.name else src_project.name + _SUFFIX
    dst_project = api.project.create(WORKSPACE_ID, dst_name, description=_SUFFIX, change_name_if_conflict=True)
    sly.logger.info('Destination project is created.',
                    extra={'project_id': dst_project.id, 'project_name': dst_project.name})

    dst_project_meta = src_project_meta.clone(obj_classes=dst_classes)
    api.project.update_meta(dst_project.id, dst_project_meta.to_json())

    def convert_annotation(src_ann, dst_project_meta):
        new_labels = []
        for idx, lbl in enumerate(src_ann.labels):
            lbl: sly.Label
            if lbl.obj_class.geometry_type == sly.AnyGeometry:
                actual_geometry = type(lbl.geometry)

                new_class_name = "{}_{}".format(lbl.obj_class.name, actual_geometry.geometry_name())
                new_class = dst_project_meta.get_obj_class(new_class_name)
                if new_class is None:
                    new_class = sly.ObjClass(name=new_class_name,
                                             geometry_type=actual_geometry,
                                             color=sly.color.random_rgb())
                    dst_project_meta = dst_project_meta.add_obj_class(new_class)
                    api.project.update_meta(dst_project.id, dst_project_meta.to_json())

                if REMOVE_ORIGINAL_CLASS is False:
                    new_labels.append(lbl)
                new_labels.append(lbl.clone(obj_class=new_class))
            else:
                new_labels.append(lbl)
        return src_ann.clone(labels=new_labels), dst_project_meta

    for ds_info in api.dataset.get_list(src_project.id):
        ds_progress = sly.Progress('Dataset: {!r}'.format(ds_info.name), total_cnt=ds_info.images_count)
        dst_dataset = api.dataset.create(dst_project.id, ds_info.name)
        img_infos_all = api.image.get_list(ds_info.id)

        for img_infos in sly.batched(img_infos_all):
            img_names, img_ids, img_metas = zip(*((x.name, x.id, x.meta) for x in img_infos))

            ann_infos = api.annotation.download_batch(ds_info.id, img_ids)
            anns = [sly.Annotation.from_json(x.annotation, src_project_meta) for x in ann_infos]

            new_anns = []
            for ann in anns:
                new_ann, dst_project_meta = convert_annotation(ann, dst_project_meta)
                new_anns.append(new_ann)

            new_img_infos = api.image.upload_ids(dst_dataset.id, img_names, img_ids, metas=img_metas)
            new_img_ids = [x.id for x in new_img_infos]
            api.annotation.upload_anns(new_img_ids, new_anns)

            ds_progress.iters_done_report(len(img_infos))

    api.task.set_output_project(task_id, dst_project.id, dst_project.name)


def main():
    my_app.run(initial_events=[{"command": "do"}, {"command": "stop"}])
    my_app.wait_all()


if __name__ == "__main__":
    sly.main_wrapper("main", main)