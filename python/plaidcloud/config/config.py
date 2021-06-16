#!/usr/bin/env python
# coding=utf-8

__author__ = "Garrett Bates"
__copyright__ = "© Copyright 2020-2021, Tartan Solutions, Inc"
__credits__ = ["Garrett Bates"]
__license__ = "Apache 2.0"
__version__ = "0.1.9"
__maintainer__ = "Garrett Bates"
__email__ = "garrett.bates@tartansolutions.com"
__status__ = "Development"

"""Loads the configuration file used by plaid apps in kubernetes."""
import os
import yaml
from typing import NamedTuple
from plaidcloud.config.redis import RedisConfig
from plaidcloud.config.rabbitmq import RMQConfig

CONFIG_PATH = os.environ.get('PLAID_CONFIG_PATH', '/etc/plaidcloud/config.yaml')


class DatabaseConfig(NamedTuple):
    hostname: str
    port: int
    superuser: str
    password: str
    system: str


class EnvironmentConfig(NamedTuple):
    hostname: str = "plaidcloud.io"
    designation: str = "dev"
    tempdir: str = "/tmp"
    verify_ssl: bool = False


class FeatureConfig(NamedTuple):
    async_copy: bool = True
    backward_compatible_state: bool = True
    decrypted_accounts: bool = True
    enable_cors: bool = False
    fast_clean_csv: bool = True
    flashback: bool = True
    google_login: bool = True
    table_update_recreate: bool = True
    use_numeric_cast: bool = True


class ServiceConfig(NamedTuple):
    auth: str = "http://plaid-auth.plaid"
    client: str = "http://plaid-client.plaid"
    cron: str = "http://plaid-cron.plaid"
    data_explorer: str = "http://plaid-data-explorer.plaid"
    docs: str = "http://plaid-docs.plaid"
    flashback: str = "http://plaid-flashback.plaid/rpc"
    monitor: str = "http://plaid-monitor.plaid"
    plaidxl: str = "http://plaid-plaidxl.plaid"
    rpc: str = "http://plaid-rpc.plaid/json-rpc"
    superset: str = "http://plaid-superset.plaid"
    workflow: str = "http://plaid-workflow.plaid"


class PlaidConfig:
    """Parses a standard configuration file for consumption by python code."""
    def __init__(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as stream:
                # Leave exception unhandled. We don't want to start without a valid conf.
                self.cfg = yaml.safe_load(stream)
        else:
            self.cfg = {}

    @property
    def database(self) -> DatabaseConfig:
        db_config = self.cfg.get('database', {})
        return DatabaseConfig(**db_config)

    @property
    def environment(self) -> EnvironmentConfig:
        env_config = self.cfg.get('environment', {})
        return EnvironmentConfig(**env_config)

    @property
    def features(self) -> FeatureConfig:
        feature_config = self.cfg.get('features', {})
        return FeatureConfig(**feature_config)

    # @property
    # def kubernetes(self):
    #     """Configuration settings for kube-apiserver monitor."""
    #     k8s_config = self.cfg.get('kubernetes', {})
    #     return KubernetesConfig(**k8s_config)

    @property
    def rabbitmq(self) -> RMQConfig:
        """Configuration settings for RabbitMQ connection."""
        return RMQConfig(self.cfg)

    @property
    def redis(self) -> RedisConfig:
        return RedisConfig(self.cfg)

    @property
    def service_urls(self) -> ServiceConfig:
        svc_config = self.cfg.get('services', {})
        return ServiceConfig(**svc_config)

    def __str__(self):
        return repr(self)

config = PlaidConfig()  # pylint: disable=invalid-name
