import os
import supervisely_lib as sly
import sys

my_app = sly.AppService()

task_id = os.environ["TASK_ID"]
WORKSPACE_ID = int(os.environ['context.workspaceId'])
PROJECT_ID = int(os.environ['modal.state.slyProjectId'])


@my_app.callback("do")
@sly.timeit
def do(**kwargs):
    example_file = os.path.join(os.path.dirname(sys.argv[0]), 'segm.json')
    dtl = sly.json.load_json_file(example_file)
    for layer in dtl:
        pass

def main():
    my_app.run(initial_events=[{"command": "do"}, {"command": "stop"}])
    my_app.wait_all()


if __name__ == "__main__":
    sly.main_wrapper("main", main)