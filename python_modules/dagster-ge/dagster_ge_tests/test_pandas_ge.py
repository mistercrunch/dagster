import pytest

import pandas as pd

import dagster
import dagster.pandas_kernel as dagster_pd
import dagster_ge
from dagster import (
    config,
    solid,
    execute_pipeline,
    InputDefinition,
    OutputDefinition,
    DependencyDefinition,
)
from dagster.core.errors import (DagsterExecutionFailureReason, DagsterExpectationFailedError)
from dagster.utils.test import script_relative_path


def _sum_solid_impl(num_df):
    sum_df = num_df
    sum_df['sum'] = sum_df['num1'] + sum_df['num2']
    return sum_df


def col_exists(name, col_name):
    return dagster_ge.ge_expectation(name, lambda ge_df: ge_df.expect_column_to_exist(col_name))


@solid(
    inputs=[
        InputDefinition(
            'num_df', dagster_pd.DataFrame, expectations=[col_exists('num1_exists', 'num1')]
        )
    ],
    output=OutputDefinition(dagster_type=dagster_pd.DataFrame)
)
def sum_solid(num_df):
    return _sum_solid_impl(num_df)


@solid(
    inputs=[
        InputDefinition(
            'num_df',
            dagster_pd.DataFrame,
            expectations=[col_exists('failing', 'not_a_column')],
        )
    ],
    output=OutputDefinition(dagster_type=dagster_pd.DataFrame)
)
def sum_solid_fails_input_expectation(num_df):
    return _sum_solid_impl(num_df)


@solid(
    inputs=[
        InputDefinition(
            'num_df',
            dagster_pd.DataFrame,
            expectations=[
                dagster_ge.json_config_expectation(
                    'num_expectations', script_relative_path('num_expectations.json')
                )
            ],
        ),
    ],
    output=OutputDefinition(dagster_type=dagster_pd.DataFrame)
)
def sum_solid_expectations_config(num_df):
    return _sum_solid_impl(num_df)


from dagster.core.utility_solids import define_pass_mem_value


def test_single_node_passing_expectation():
    in_df = pd.DataFrame.from_dict({'num1': [1, 3], 'num2': [2, 4]})
    pipeline = dagster.PipelineDefinition(
        solids=[define_pass_mem_value('value', in_df), sum_solid],
        dependencies={'sum_solid': {
            'num_df': DependencyDefinition('value')
        }}
    )

    result = execute_pipeline(pipeline, config.Environment())
    assert result.success
    assert len(result.result_list) == 2
    assert result.result_list[1].success
    assert result.result_list[1].transformed_value.to_dict('list') == {
        'num1': [1, 3],
        'num2': [2, 4],
        'sum': [3, 7],
    }


def test_single_node_passing_json_config_expectations():
    in_df = pd.DataFrame.from_dict({'num1': [1, 3], 'num2': [2, 4]})
    pipeline = dagster.PipelineDefinition(
        solids=[define_pass_mem_value('value', in_df), sum_solid_expectations_config],
        dependencies={
            sum_solid_expectations_config.name: {
                'num_df': DependencyDefinition('value')
            }
        }
    )

    result = execute_pipeline(pipeline, config.Environment())
    assert result.success
    assert len(result.result_list) == 2
    assert result.result_list[1].success
    assert result.result_list[1].transformed_value.to_dict('list') == {
        'num1': [1, 3],
        'num2': [2, 4],
        'sum': [3, 7],
    }


def test_single_node_failing_expectation():
    in_df = pd.DataFrame.from_dict({'num1': [1, 3], 'num2': [2, 4]})
    pipeline = dagster.PipelineDefinition(
        solids=[define_pass_mem_value('value', in_df), sum_solid_fails_input_expectation],
        dependencies={
            sum_solid_fails_input_expectation.name: {
                'num_df': DependencyDefinition('value')
            }
        }
    )

    # NOTE: this is not what I want to API to be but at least it exercises
    # the code path for now
    with pytest.raises(DagsterExpectationFailedError):
        result = execute_pipeline(pipeline, config.Environment())
        assert not result.success
