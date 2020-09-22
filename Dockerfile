FROM docker.deepsystems.io/supervisely/five/base-py-sdk-internal:apps

RUN  pip install torch==1.6.0+cpu torchvision==0.7.0+cpu -f https://download.pytorch.org/whl/torch_stable.html