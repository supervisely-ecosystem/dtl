import os
import supervisely_lib as sly

my_app = sly.AppService()

task_id = os.environ["TASK_ID"]
WORKSPACE_ID = int(os.environ['context.workspaceId'])
PROJECT_ID = int(os.environ['modal.state.slyProjectId'])


@my_app.callback("do")
@sly.timeit
def do(**kwargs):
    pass


def main():
    my_app.run(initial_events=[{"command": "do"}, {"command": "stop"}])
    my_app.wait_all()


if __name__ == "__main__":
    sly.main_wrapper("main", main)