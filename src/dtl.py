import os
import sys

import supervisely_lib as sly
from net import Net

my_app = sly.AppService()

task_id = os.environ["TASK_ID"]
WORKSPACE_ID = int(os.environ['context.workspaceId'])


def main():
    my_app.run(initial_events=[{"command": "do"}, {"command": "stop"}])
    #my_app.wait_all()

    test_path = os.path.join(os.path.dirname(sys.argv[0]), 'segm.json')
    test_graph_json = sly.json.load_json_file(test_path)
    test_graph = Net(test_graph_json)
    print("finish")


if __name__ == "__main__":
    sly.main_wrapper("main", main)