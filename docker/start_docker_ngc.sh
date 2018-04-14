# run image used for ngc
# argument1: username, argument2: $VMPC_DATA_DIR
nvidia-docker run  -v $2:/workspace/pushing_data \
                   -v /home/$1/Documents/visual_mpc:/mount \
                   -v /home/$1/Desktop:/Desktop \
-it \
nvcr.io/ucb_rail8888/tf_mj1.5 \

/bin/bash -c \
"export VMPC_DATA_DIR=/workspace/pushing_data;
/bin/bash"

