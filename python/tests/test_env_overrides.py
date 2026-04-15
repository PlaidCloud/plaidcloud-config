#!/usr/bin/env python
# coding=utf-8

__author__ = "Garrett Bates"
__copyright__ = "© Copyright 2020-2026, PlaidCloud, Inc"
__credits__ = ["Garrett Bates"]
__license__ = "Apache 2.0"
__maintainer__ = "Garrett Bates"
__email__ = "garrett@plaidcloud.com"

"""Tests for env-var override injection in plaidcloud.config.config."""
import sys
import pytest

import plaidcloud.config.config  # noqa: F401
config_mod = sys.modules['plaidcloud.config.config']
PlaidConfig = config_mod.PlaidConfig


@pytest.fixture
def clean_env(monkeypatch):
    for k in list(__import__('os').environ):
        if k.startswith(config_mod.ENV_OVERRIDE_PREFIX + config_mod.ENV_OVERRIDE_SEP):
            monkeypatch.delenv(k, raising=False)
    return monkeypatch


def test_override_existing_leaf(plaid_config, clean_env):
    clean_env.setenv("PLAID_CFG00database00password", "injected")
    cfg = PlaidConfig()
    # plaid_config fixture set CONFIG_PATH already
    assert cfg.cfg['database']['password'] == 'injected'
    assert cfg.database.password == 'injected'


def test_add_new_nested_path(plaid_config, clean_env):
    clean_env.setenv("PLAID_CFG00brand00new00key", "hello")
    cfg = PlaidConfig()
    assert cfg.cfg['brand']['new']['key'] == 'hello'


def test_yaml_type_coercion(plaid_config, clean_env):
    clean_env.setenv("PLAID_CFG00features00async_copy", "false")
    clean_env.setenv("PLAID_CFG00database00port", "6543")
    cfg = PlaidConfig()
    assert cfg.cfg['features']['async_copy'] is False
    assert cfg.cfg['database']['port'] == 6543
    assert cfg.features.async_copy is False
    assert cfg.database.port == 6543


def test_no_env_vars_no_change(plaid_config, clean_env):
    from tests.conftest import SAMPLE_CONFIG
    cfg = PlaidConfig()
    assert cfg.cfg == SAMPLE_CONFIG


def test_intermediate_non_dict_replaced(plaid_config, clean_env):
    # database.password exists as a string; override a deeper path through it.
    clean_env.setenv("PLAID_CFG00database00password00nested", "x")
    cfg = PlaidConfig()
    assert cfg.cfg['database']['password'] == {'nested': 'x'}


def test_missing_config_with_overrides(missing_config, clean_env):
    clean_env.setenv("PLAID_CFG00vault00token", "vtok")
    cfg = PlaidConfig()
    assert cfg.cfg == {'vault': {'token': 'vtok'}}
    assert cfg.vault.token == 'vtok'


def test_prefix_without_path_ignored(plaid_config, clean_env):
    clean_env.setenv("PLAID_CFG00", "orphan")
    cfg = PlaidConfig()
    assert '' not in cfg.cfg
