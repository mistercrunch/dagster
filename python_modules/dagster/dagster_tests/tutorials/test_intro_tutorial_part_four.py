# pylint: disable=W0622,W0614,W0401
from dagster import *


@solid(config_def=ConfigDefinition(types.String))
def hello_world(info):
    print(info.config)
    return info.config


def define_pipeline():
    return PipelineDefinition(solids=[hello_world])


def test_tutorial_part_four():

    result = execute_pipeline(
        define_pipeline(),
        config.Environment(solids={'hello_world': config.Solid('Hello, World!')}),
    )

    assert result.success
    assert len(result.result_list) == 1
    assert result.result_for_solid('hello_world').transformed_value() is 'Hello, World!'
    return result


if __name__ == '__main__':
    test_tutorial_part_four()
