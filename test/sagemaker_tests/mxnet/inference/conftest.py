# Copyright 2019-2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the "license" file accompanying this file. This file is distributed
# on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.
from __future__ import absolute_import

import json
import logging
import os

import boto3
import pytest

from botocore.exceptions import ClientError
from sagemaker import LocalSession, Session
from sagemaker.mxnet import MXNet
from packaging.version import Version, parse

from .integration import get_ecr_registry
from ... import NO_P4_REGIONS, NO_G5_REGIONS

logger = logging.getLogger(__name__)
logging.getLogger("boto").setLevel(logging.INFO)
logging.getLogger("botocore").setLevel(logging.INFO)
logging.getLogger("factory.py").setLevel(logging.INFO)
logging.getLogger("auth.py").setLevel(logging.INFO)
logging.getLogger("connectionpool.py").setLevel(logging.INFO)

SCRIPT_PATH = os.path.dirname(os.path.realpath(__file__))


def pytest_addoption(parser):
    parser.addoption("--docker-base-name", default="preprod-mxnet-serving")
    parser.addoption("--region", default="us-west-2")
    parser.addoption("--framework-version", default="")
    parser.addoption("--py-version", default="3", choices=["2", "3", "2,3", "37", "38"])
    parser.addoption(
        "--processor", default="cpu", choices=["gpu", "cpu", "neuron", "cpu,gpu", "eia"]
    )
    parser.addoption("--aws-id", default=None)
    parser.addoption("--instance-type", default=None)
    parser.addoption("--accelerator-type", default=None)
    # If not specified, will default to {framework-version}-{processor}-py{py-version}
    parser.addoption("--tag", default=None)
    parser.addoption(
        "--generate-coverage-doc",
        default=False,
        action="store_true",
        help="use this option to generate test coverage doc",
    )
    parser.addoption(
        "--efa",
        action="store_true",
        default=False,
        help="Run only efa tests",
    )
    parser.addoption("--sagemaker-regions", default="us-west-2")


def pytest_configure(config):
    config.addinivalue_line("markers", "efa(): explicitly mark to run efa tests")


def pytest_runtest_setup(item):
    if item.config.getoption("--efa"):
        efa_tests = [mark for mark in item.iter_markers(name="efa")]
        if not efa_tests:
            pytest.skip("Skipping non-efa tests")


def pytest_collection_modifyitems(session, config, items):
    for item in items:
        print(f"item {item}")
        for marker in item.iter_markers(name="team"):
            print(f"item {marker}")
            team_name = marker.args[0]
            item.user_properties.append(("team_marker", team_name))
            print(f"item.user_properties {item.user_properties}")
    if config.getoption("--generate-coverage-doc"):
        from test.test_utils.test_reporting import TestReportGenerator

        report_generator = TestReportGenerator(items, is_sagemaker=True)
        report_generator.generate_coverage_doc(framework="mxnet", job_type="inference")


def pytest_generate_tests(metafunc):
    if "py_version" in metafunc.fixturenames:
        py_version_params = ["py" + v for v in metafunc.config.getoption("--py-version").split(",")]
        metafunc.parametrize("py_version", py_version_params, scope="session")

    if "processor" in metafunc.fixturenames:
        processor_params = metafunc.config.getoption("--processor").split(",")
        metafunc.parametrize("processor", processor_params, scope="session")


# Nightly fixtures
@pytest.fixture(scope="session")
def feature_aws_framework_present():
    pass


@pytest.fixture(scope="session")
def docker_base_name(request):
    return request.config.getoption("--docker-base-name")


@pytest.fixture(scope="session")
def region(request):
    return request.config.getoption("--region")


@pytest.fixture(scope="session")
def framework_version(request):
    return request.config.getoption("--framework-version")


@pytest.fixture(scope="session")
def aws_id(request):
    return request.config.getoption("--aws-id")


@pytest.fixture(scope="session")
def tag(request, framework_version, processor, py_version):
    provided_tag = request.config.getoption("--tag")
    default_tag = "{}-{}-{}".format(framework_version, processor, py_version)
    return provided_tag if provided_tag is not None else default_tag


@pytest.fixture(scope="session")
def instance_type(request, processor):
    provided_instance_type = request.config.getoption("--instance-type")
    default_instance_type = "ml.c5.xlarge" if processor == "cpu" else "ml.g5.4xlarge"
    return provided_instance_type if provided_instance_type is not None else default_instance_type


@pytest.fixture(scope="session")
def accelerator_type(request):
    return request.config.getoption("--accelerator-type")


@pytest.fixture(scope="session")
def docker_image(docker_base_name, tag):
    return "{}:{}".format(docker_base_name, tag)


@pytest.fixture(scope="session")
def ecr_image(aws_id, docker_base_name, tag, region):
    registry = get_ecr_registry(aws_id, region)
    return "{}/{}:{}".format(registry, docker_base_name, tag)


@pytest.fixture(scope="session")
def sagemaker_session(region):
    return Session(boto_session=boto3.Session(region_name=region))


@pytest.fixture(scope="session", name="sagemaker_regions")
def sagemaker_regions(request):
    sagemaker_regions = request.config.getoption("--sagemaker-regions")
    return sagemaker_regions.split(",")


@pytest.fixture(scope="session")
def sagemaker_local_session(region):
    return LocalSession(boto_session=boto3.Session(region_name=region))


@pytest.fixture(scope="session")
def local_instance_type(processor):
    return "local" if processor == "cpu" else "local_gpu"


@pytest.fixture(autouse=True)
def skip_gpu_instance_restricted_regions(region, instance_type):
    if (region in NO_P4_REGIONS and instance_type.startswith("ml.p4")) or (
        region in NO_G5_REGIONS and instance_type.startswith("ml.g5")
    ):
        pytest.skip("Skipping GPU test in region {} to avoid insufficient capacity".format(region))


@pytest.fixture(autouse=True)
def skip_py2_containers(request, tag):
    if request.node.get_closest_marker("skip_py2_containers"):
        if "py2" in tag:
            pytest.skip("Skipping python2 container with tag {}".format(tag))


@pytest.fixture(autouse=True)
def skip_eia_containers(request, docker_base_name):
    if request.node.get_closest_marker("skip_eia_containers"):
        if "eia" in docker_base_name:
            pytest.skip("Skipping eia container with tag {}".format(docker_base_name))


@pytest.fixture(scope="function")
def skip_neuron_containers(request, tag):
    if "neuron" in tag:
        pytest.skip("Skipping neuron container with tag {}".format(tag))


@pytest.fixture(scope="function")
def skip_if_no_neuron(ecr_image, instance_type):
    if "neuron" not in ecr_image:
        pytest.skip("Skipping neuron test for non neuron images")
    if "inf1" not in instance_type:
        pytest.skip("Skipping neuron test for non inf1 instances")

    image_tag = ecr_image.split(":")[1]
    framework_version = parse(image_tag.split("-")[0])
    if framework_version < Version("1.8"):
        pytest.skip("Skipping neuron test for mxnet version < 1.8")


def _get_remote_override_flags():
    try:
        s3_client = boto3.client("s3")
        sts_client = boto3.client("sts")
        account_id = sts_client.get_caller_identity().get("Account")
        result = s3_client.get_object(
            Bucket=f"dlc-cicd-helper-{account_id}", Key="override_tests_flags.json"
        )
        json_content = json.loads(result["Body"].read().decode("utf-8"))
    except ClientError as e:
        logger.warning("ClientError when performing S3/STS operation: {}".format(e))
        json_content = {}
    return json_content


def _is_test_disabled(test_name, build_name, version):
    """
    Expected format of remote_override_flags:
    {
        "CB Project Name for Test Type A": {
            "CodeBuild Resolved Source Version": ["test_type_A_test_function_1", "test_type_A_test_function_2"]
        },
        "CB Project Name for Test Type B": {
            "CodeBuild Resolved Source Version": ["test_type_B_test_function_1", "test_type_B_test_function_2"]
        }
    }

    :param test_name: str Test Function node name (includes parametrized values in string)
    :param build_name: str Build Project name of current execution
    :param version: str Source Version of current execution
    :return: bool True if test is disabled as per remote override, False otherwise
    """
    remote_override_flags = _get_remote_override_flags()
    remote_override_build = remote_override_flags.get(build_name, {})
    if version in remote_override_build:
        return not remote_override_build[version] or any(
            [test_keyword in test_name for test_keyword in remote_override_build[version]]
        )
    return False


@pytest.fixture(autouse=True)
def disable_test(request):
    test_name = request.node.name
    # We do not have a regex pattern to find CB name, which means we must resort to string splitting
    build_arn = os.getenv("CODEBUILD_BUILD_ARN")
    build_name = build_arn.split("/")[-1].split(":")[0] if build_arn else None
    version = os.getenv("CODEBUILD_RESOLVED_SOURCE_VERSION")

    if build_name and version and _is_test_disabled(test_name, build_name, version):
        pytest.skip(f"Skipping {test_name} test because it has been disabled.")


@pytest.fixture(autouse=True)
def skip_test_successfully_executed_before(request):
    """
    "cache/lastfailed" contains information about failed tests only. We're running SM tests in separate threads for each image.
    So when we retry SM tests, successfully executed tests executed again because pytest doesn't have that info in /.cache.
    But the flag "--last-failed-no-failures all" requires pytest to execute all the available tests.
    The only sign that a test passed last time - lastfailed file exists and the test name isn't in that file.
    The method checks whether lastfailed file exists and the test name is not in it.
    """
    test_name = request.node.name
    lastfailed = request.config.cache.get("cache/lastfailed", None)

    if lastfailed is not None and not any(
        test_name in failed_test_name for failed_test_name in lastfailed.keys()
    ):
        pytest.skip(f"Skipping {test_name} because it was successfully executed for this commit")
