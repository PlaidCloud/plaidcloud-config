#!/usr/bin/env python
# coding=utf-8

__author__ = "Garrett Bates"
__copyright__ = "© Copyright 2020-2021, Tartan Solutions, Inc"
__credits__ = ["Garrett Bates"]
__license__ = "Apache 2.0"
__version__ = "0.1.11"
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
    database_name: str = "plaid_data"
    query_params: dict = {}
    cloud_url: str = ""


class EnvironmentConfig(NamedTuple):
    hostname: str = "plaidcloud.io"
    hostnames: list = ["plaidcloud.io"]
    designation: str = "dev"
    tempdir: str = "/tmp"
    verify_ssl: bool = False
    workflow_image: str = ""


class KeycloakConfig(NamedTuple):
    url: str = "https://plaidcloud.io/auth"
    host: str = "plaidcloud.io"
    realm: str = "PlaidCloud"
    client_name: str = "plaidcloud-login"
    admin_id: str = "admin-cli"
    admin_secret: str = ""
    realm_admin_id: str = "admin-cli"
    realm_secret: str = ""
    keycloak_issuer: str = "https://plaidcloud.io/auth/realms/PlaidCloud"
    db_url: str = ""


# Tenant Config Object
class TenantConfig(NamedTuple):
    github_token: str = ""
    github_repo: str = ""
    github_branch: str = ""
    id: str = ""
    version: str = ""
    name: str = ""
    memo: str = ""
    init_mode: str = ""
    workspace_id: str = ""
    cloud_id: int = 0
    apps: list = []
    services: dict = {}
    google: dict = {}
    aws: dict = {}
    azure: dict = {}
    private_cloud: dict = {}
    use_proxy_download: bool = False
    source_tenant: str = ""
    source_url: str = ""
    source_client_id: str = ""
    source_client_secret: str = ""
    app_logo_url: str = "resource/plaid/images/logo-header.png"
    splash_screen_logo_url: str = "resource/plaid/images/logo-login.png"
    superset_logo_url: str = "/static/assets/images/plaidcloud.png"

class GlobalConfig(NamedTuple):
    client_id: str = ""
    client_secret: str = ""
    url: str = ""
    db_host: str = ""


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


class OpenSearchConfig(NamedTuple):
    host: str = ""
    username: str = "plaidlog"
    password: str = ""
    port: int = 9200


class SupersetConfig(NamedTuple):
    username: str = "admin"
    password: str = ""
    db_url: str = ""
    use_events_handler: bool = True


class LokiConfig(NamedTuple):
    host: str = "loki-gateway"
    username: str = "lokiuser"
    password: str = "lokipassword"
    port: int = 3100


class SharedPostgresConfig(NamedTuple):
    backups: dict = {}
    restore: dict = {}
    credentials: dict = {}


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
        return DatabaseConfig(**{k: v for k, v in db_config.items() if k in DatabaseConfig._fields})

    @property
    def environment(self) -> EnvironmentConfig:
        env_config = self.cfg.get('environment', {})
        ec = EnvironmentConfig(**{k: v for k, v in env_config.items() if k in EnvironmentConfig._fields})
        # CRL 2023 - Ensures that primary hostname is set based off the `hostnames` parameter if not provided.
        if not env_config.get('hostname') and (ec.hostnames and ec.hostnames != ["plaidcloud.io"]):
            ec = ec._replace(hostname=ec.hostnames[0])
        return ec

    @property
    def features(self) -> FeatureConfig:
        feature_config = self.cfg.get('features', {})
        return FeatureConfig(**{k: v for k, v in feature_config.items() if k in FeatureConfig._fields})

    @property
    def keycloak(self) -> KeycloakConfig:
        keycloak_config = self.cfg.get('keycloak', {})
        return KeycloakConfig(**{k: v for k, v in keycloak_config.items() if k in KeycloakConfig._fields})

    @property
    def tenant(self) -> TenantConfig:
        tenant_config = self.cfg.get('tenant', {})
        return TenantConfig(**{k: v for k, v in tenant_config.items() if k in TenantConfig._fields})

    @property
    def opensearch(self) -> OpenSearchConfig:
        opensearch_config = self.cfg.get('opensearch', {})
        return OpenSearchConfig(**{k: v for k, v in opensearch_config.items() if k in OpenSearchConfig._fields})

    @property
    def loki(self) -> LokiConfig:
        loki_config = self.cfg.get('loki', {})
        return LokiConfig(**{k: v for k, v in loki_config.items() if k in LokiConfig._fields})

    @property
    def plaidcloud_global(self) -> GlobalConfig:
        global_config = self.cfg.get('plaidcloud-global', {})
        return GlobalConfig(**{k: v for k, v in global_config.items() if k in GlobalConfig._fields})
    
    @property
    def postgres(self) -> SharedPostgresConfig:
        postgres_config = self.cfg.get('postgres', {})
        return SharedPostgresConfig(**{k: v for k, v in postgres_config.items() if k in SharedPostgresConfig._fields})

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
        return ServiceConfig(**{k: v for k, v in svc_config.items() if k in ServiceConfig._fields})

    @property
    def superset(self) -> SupersetConfig:
        superset_config = self.cfg.get('superset', {})
        return SupersetConfig(**{k: v for k, v in superset_config.items() if k in SupersetConfig._fields})

    def __str__(self):
        return repr(self)

config = PlaidConfig()  # pylint: disable=invalid-name
