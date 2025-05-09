## AWS Deep Learning Containers

AWS [Deep Learning Containers (DLCs)](https://docs.aws.amazon.com/deep-learning-containers/latest/devguide/what-is-dlc.html)
are a set of Docker images for training and serving models in TensorFlow, TensorFlow 2, PyTorch, and MXNet.
Deep Learning Containers provide optimized environments with TensorFlow and MXNet, Nvidia CUDA (for GPU instances), and
Intel MKL (for CPU instances) libraries and
are available in the Amazon Elastic Container Registry (Amazon ECR).

The AWS DLCs are used in Amazon SageMaker as the default vehicles for your SageMaker jobs such as training, inference,
transforms etc. They've been tested for machine
learning workloads on Amazon EC2, Amazon ECS and Amazon EKS services as well.

For the list of available DLC images, see [Available Deep Learning Containers Images](available_images.md).
You can find more information on the images available in Sagemaker [here](https://docs.aws.amazon.com/sagemaker/latest/dg/pre-built-containers-frameworks-deep-learning.html)

## License

This project is licensed under the Apache-2.0 License.

`smdistributed.dataparallel` and `smdistributed.modelparallel` are released under the [AWS Customer Agreement](https://aws.amazon.com/agreement/).

## Table of Contents

 [Getting Started](#getting-started)

 [Building your Image](#building-your-image)

 [Running Tests Locally](#running-tests-locally)

### Getting started

We describe here the setup to build and test the DLCs on the platforms Amazon SageMaker, EC2, ECS and EKS.

We take an example of building a ***MXNet GPU python3 training*** container.

* Ensure you have access to an AWS account i.e. [setup](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)
your environment such that awscli can access your account via either an IAM user or an IAM role. We recommend an IAM role for use with AWS.
For the purposes of testing in your personal account, the following managed permissions should suffice: <br>
-- [AmazonEC2ContainerRegistryFullAccess](https://console.aws.amazon.com/iam/home#policies/arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess) <br>
-- [AmazonEC2FullAccess](https://console.aws.amazon.com/iam/home#policies/arn:aws:iam::aws:policy/AmazonEC2FullAccess) <br>
-- [AmazonEKSClusterPolicy](https://console.aws.amazon.com/iam/home#policies/arn:aws:iam::aws:policy/AmazonEKSClusterPolicy) <br>
-- [AmazonEKSServicePolicy](https://console.aws.amazon.com/iam/home#policies/arn:aws:iam::aws:policy/AmazonEKSServicePolicy) <br>
-- [AmazonEKSServiceRolePolicy](https://console.aws.amazon.com/iam/home#policies/arn:aws:iam::aws:policy/AmazonEKSServiceRolePolicy) <br>
-- [AWSServiceRoleForAmazonEKSNodegroup](https://console.aws.amazon.com/iam/home#policies/arn:aws:iam::aws:policy/AWSServiceRoleForAmazonEKSNodegroup) <br>
-- [AmazonSageMakerFullAccess](https://console.aws.amazon.com/iam/home#policies/arn:aws:iam::aws:policy/AmazonSageMakerFullAccess) <br>
-- [AmazonS3FullAccess](https://console.aws.amazon.com/iam/home#policies/arn:aws:iam::aws:policy/AmazonS3FullAccess) <br>
* [Create](https://docs.aws.amazon.com/cli/latest/reference/ecr/create-repository.html) an ECR repository with the name “beta-mxnet-training” in the us-west-2 region
* Ensure you have [docker](https://docs.docker.com/get-docker/) client set-up on your system - osx/ec2

1. Clone the repo and set the following environment variables:
    ```shell script
    export ACCOUNT_ID=<YOUR_ACCOUNT_ID>
    export REGION=us-west-2
    export REPOSITORY_NAME=beta-mxnet-training
    ```
2. Login to ECR
    ```shell script
    aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com
    ```
3. Assuming your working directory is the cloned repo, create a virtual environment to use the repo and install requirements
    ```shell script
    python3 -m venv dlc
    source dlc/bin/activate
    pip install -r src/requirements.txt
    ```
4. Perform the initial setup
    ```shell script
    bash src/setup.sh mxnet
    ```
### Building your image

The paths to the dockerfiles follow a specific pattern e.g., mxnet/training/docker/\<version>/\<python_version>/Dockerfile.<processor>

These paths are specified by the buildspec.yml residing in mxnet/training/buildspec.yml i.e. \<framework>/<training|inference>/buildspec.yml.
If you want to build the dockerfile for a particular version, or introduce a new version of the framework, re-create the
folder structure as per above and modify the buildspec.yml file to specify the version of the dockerfile you want to build.

1. To build all the dockerfiles specified in the buildspec.yml locally, use the command
    ```shell script
    python src/main.py --buildspec mxnet/training/buildspec.yml --framework mxnet
    ```
    The above step should take a while to complete the first time you run it since it will have to download all base layers
    and create intermediate layers for the first time.
    Subsequent runs should be much faster.
2. If you would instead like to build only a single image
    ```shell script
    python src/main.py --buildspec mxnet/training/buildspec.yml \
                       --framework mxnet \
                       --image_types training \
                       --device_types cpu \
                       --py_versions py3
    ```
3. The arguments —image_types, —device_types and —py_versions are all comma separated list who’s possible values are as follows:
    ```shell script
    --image_types <training/inference>
    --device_types <cpu/gpu>
    --py_versions <py2/py3>
    ```
4. For example, to build all gpu, training containers, you could use the following command
    ```shell script
    python src/main.py --buildspec mxnet/training/buildspec.yml \
                       --framework mxnet \
                       --image_types training \
                       --device_types gpu \
                       --py_versions py3
    ```

### Upgrading the framework version
1. Suppose, if there is a new framework version for MXNet (version 1.7.0) then this would need to be changed in the
buildspec.yml file for MXNet training.
    ```yaml
    # mxnet/training/buildspec.yml
      1   account_id: &ACCOUNT_ID <set-$ACCOUNT_ID-in-environment>
      2   region: &REGION <set-$REGION-in-environment>
      3   framework: &FRAMEWORK mxnet
      4   version: &VERSION 1.6.0 *<--- Change this to 1.7.0*
          ................
    ```
2. The dockerfile for this should exist at mxnet/docker/1.7.0/py3/Dockerfile.gpu. This path is dictated by the
docker_file key for each repository.
    ```yaml
    # mxnet/training/buildspec.yml
     41   images:
     42     BuildMXNetCPUTrainPy3DockerImage:
     43       <<: *TRAINING_REPOSITORY
              ...................
     49       docker_file: !join [ docker/, *VERSION, /, *DOCKER_PYTHON_VERSION, /Dockerfile., *DEVICE_TYPE ]

    ```
3. Build the container as described above.
### Adding artifacts to your build context
1. If you are copying an artifact from your build context like this:
    ```dockerfile
    # deep-learning-containers/mxnet/training/docker/1.6.0/py3
    COPY README-context.rst README.rst
    ```
    then README-context.rst needs to first be copied into the build context. You can do this by adding the artifact in
    the framework buildspec file under the context key:
    ```yaml
    # mxnet/training/buildspec.yml
     19 context:
     20   README.xyz: *<---- Object name (Can be anything)*
     21     source: README-context.rst *<--- Path for the file to be copied*
     22     target: README.rst *<--- Name for the object in** the build context*
    ```
2. Adding it under context makes it available to all images. If you need to make it available only for training or
inference images, add it under training_context or inference_context.
    ```yaml
     19   context:
        .................
     23       training_context: &TRAINING_CONTEXT
     24         README.xyz:
     25           source: README-context.rst
     26           target: README.rst
        ...............
    ```
3. If you need it for a single container add it under the context key for that particular image:
    ```yaml
     41   images:
     42     BuildMXNetCPUTrainPy3DockerImage:
     43       <<: *TRAINING_REPOSITORY
              .......................
     50       context:
     51         <<: *TRAINING_CONTEXT
     52         README.xyz:
     53           source: README-context.rst
     54           target: README.rst
    ```
4. Build the container as described above.
### Adding a package
The following steps outline how to add a package to your image. For more information on customizing your container, see [Building AWS Deep Learning Containers Custom Images](custom_images.md).
1. Suppose you want to add a package to the MXNet 1.6.0 py3 GPU docker image, then change the dockerfile from:
    ```dockerfile
    # mxnet/training/docker/1.6.0/py3/Dockerfile.gpu
    139 RUN ${PIP} install --no-cache --upgrade \
    140     keras-mxnet==2.2.4.2 \
    ...........................
    159     ${MX_URL} \
    160     awscli
    ```
    to
    ```dockerfile
    139 RUN ${PIP} install --no-cache --upgrade \
    140     keras-mxnet==2.2.4.2 \
    ...........................
    160     awscli \
    161     octopush
    ```
2. Build the container as described above.

### Running tests locally
As part of your iteration with your PR, sometimes it is helpful to run your tests locally to avoid using too many
extraneous resources or waiting for a build to complete. The testing is supported using pytest.

Similar to building locally, to test locally, you’ll need access to a personal/team AWS account. To test out:

1. Either on an EC2 instance with the deep-learning-containers repo cloned, or on your local machine, make sure you have
the images you want to test locally (likely need to pull them from ECR). Then change directory into the cloned folder.
Install the requirements for tests.
    ```shell script
    cd deep-learning-containers/
    pip install -r src/requirements.txt
    pip install -r test/requirements.txt
    ```
2. In a shell, export environment variable DLC_IMAGES to be a space separated list of ECR uris to be tested. Set
CODEBUILD_RESOLVED_SOURCE_VERSION to some unique identifier that you can use to identify the resources your test spins up.
Set PYTHONPATH as the absolute path to the src/ folder.
Example:
[Note: change the repository name to the one setup in your account]
    ```shell script
    export DLC_IMAGES="$ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/pr-pytorch-training:training-gpu-py3 $ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/pr-mxnet-training:training-gpu-py3"
    export PYTHONPATH=$(pwd)/src
    export CODEBUILD_RESOLVED_SOURCE_VERSION="my-unique-test"
    ```
3. Our pytest framework expects the root dir to be test/dlc_tests, so change directories in your shell to be here
    ```shell script
    cd test/dlc_tests
    ```
4. To run all tests (in series) associated with your image for a given platform, use the following command
    ```shell script
    # EC2
    pytest -s -rA ec2/ -n=auto
    # ECS
    pytest -s -rA ecs/ -n=auto

    #EKS
    cd ../
    export TEST_TYPE=eks
    python test/testrunner.py
    ```
    Remove `-n=auto` to run the tests sequentially.
5. To run a specific test file, provide the full path to the test file
    ```shell script
    pytest -s ecs/mxnet/training/test_ecs_mxnet_training.py
    ```
6. To run a specific test function (in this example we use the cpu dgl ecs test), modify the command to look like so:
    ```shell script
    pytest -s ecs/mxnet/training/test_ecs_mxnet_training.py::test_ecs_mxnet_training_dgl_cpu
    ```

7. To run SageMaker local mode tests, launch a cpu or gpu EC2 instance with latest Deep Learning AMI.
   * Clone your github branch with changes and run the following commands
       ```shell script
       git clone https://github.com/{github_account_id}/deep-learning-containers/
       cd deep-learning-containers && git checkout {branch_name}
       ```
   * Login into the ECR repo where the new docker images built exist
       ```shell script
       $(aws ecr get-login --no-include-email --registry-ids ${aws_id} --region ${aws_region})
       ```
   * Change to the appropriate directory (sagemaker_tests/{framework}/{job_type}) based on framework and job type of the image being tested.
       The example below refers to testing mxnet_training images
       ```shell script
       cd test/sagemaker_tests/mxnet/training/
       pip3 install -r requirements.txt
       ```
   * To run the SageMaker local integration tests (aside from tensorflow_inference), use the pytest command below:
       ```shell script
       python3 -m pytest -v integration/local --region us-west-2 \
       --docker-base-name ${aws_account_id}.dkr.ecr.us-west-2.amazonaws.com/mxnet-inference \
        --tag 1.6.0-cpu-py36-ubuntu18.04 --framework-version 1.6.0 --processor cpu \
        --py-version 3
       ```
   * To test tensorflow_inference py3 images, run the command below:
     ```shell script
     python3 -m  pytest -v integration/local \
     --docker-base-name ${aws_account_id}.dkr.ecr.us-west-2.amazonaws.com/tensorflow-inference \
     --tag 1.15.2-cpu-py36-ubuntu16.04 --framework-version 1.15.2 --processor cpu
     ```
8. To run SageMaker remote tests on your account please setup following pre-requisites

    * Create an IAM role with name “SageMakerRole” in the above account and add the below AWS Manged policies
       ```
       AmazonSageMakerFullAccess
       ```
   *  Change to the appropriate directory (sagemaker_tests/{framework}/{job_type}) based on framework and job type of the image being tested."
       The example below refers to testing mxnet_training images
       ```shell script
       cd test/sagemaker_tests/mxnet/training/
       pip3 install -r requirements.txt
       ```
   *  To run the SageMaker remote integration tests (aside from tensorflow_inference), use the pytest command below:
       ```shell script
       pytest integration/sagemaker/test_mnist.py \
       --region us-west-2 --docker-base-name mxnet-training \
       --tag training-gpu-py3-1.6.0 --framework-version 1.6.0 --aws-id {aws_id} \
       --instance-type ml.g5.12xlarge
       ```
   * For tensorflow_inference py3 images run the below command
      ```shell script
      python3 -m pytest test/integration/sagemaker/test_tfs. --registry {aws_account_id} \
      --region us-west-2  --repo tensorflow-inference --instance-types ml.c5.18xlarge \
      --tag 1.15.2-py3-cpu-build --versions 1.15.2
      ```
9. To run SageMaker benchmark tests on your account please perform the following steps:
    * Create a file named `sm_benchmark_env_settings.config` in the deep-learning-containers/ folder
    * Add the following to the file (commented lines are optional):
        ```shell script
        export DLC_IMAGES="<image_uri_1-you-want-to-benchmark-test>"
        # export DLC_IMAGES="$DLC_IMAGES <image_uri_2-you-want-to-benchmark-test>"
        # export DLC_IMAGES="$DLC_IMAGES <image_uri_3-you-want-to-benchmark-test>"
        export BUILD_CONTEXT=PR
        export TEST_TYPE=benchmark-sagemaker
        export CODEBUILD_RESOLVED_SOURCE_VERSION=$USER
        export REGION=us-west-2
        ```
    * Run:
        ```shell script
        source sm_benchmark_env_settings.config
        ```
    * To test all images for multiple frameworks, run:
        ```shell script
        pip install -r requirements.txt
        python test/testrunner.py
        ```
    * To test one individual framework image type, run:
        ```shell script
        # Assuming that the cwd is deep-learning-containers/
        cd test/dlc_tests
        pytest benchmark/sagemaker/<framework-name>/<image-type>/test_*.py
        ```
    * The scripts and model-resources used in these tests will be located at:
        ```
        deep-learning-containers/test/dlc_tests/benchmark/sagemaker/<framework-name>/<image-type>/resources/
        ```

Note: SageMaker does not support tensorflow_inference py2 images.
