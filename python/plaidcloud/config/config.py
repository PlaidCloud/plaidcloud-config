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
import requests
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
    hostnames: list = ["plaidcloud.io"]
    designation: str = "dev"
    tempdir: str = "/tmp"
    verify_ssl: bool = False


class KeycloakConfig(NamedTuple):
    host: str = "plaidcloud.io"
    realm: str = "PlaidCloud"
    client_name: str = "plaidcloud-login"
    admin_id: str = "admin-cli"
    admin_secret: str = ""
    realm_admin_id: str = "admin-cli"
    realm_secret: str = ""
    keycloak_issuer: str = "https://plaidcloud.io/auth/realms/PlaidCloud"


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
        ec = EnvironmentConfig(**env_config)
        # CRL 2021 - the second check here avoids overwriting dev namespaces.
        if ec.hostnames and ec.hostnames != ["plaidcloud.io"]:
            ec = ec._replace(hostname=ec.hostnames[0])
        return ec

    @property
    def features(self) -> FeatureConfig:
        feature_config = self.cfg.get('features', {})
        return FeatureConfig(**feature_config)

    @property
    def keycloak(self) -> KeycloakConfig:
        keycloak_config = self.cfg.get('keycloak', {})
        return KeycloakConfig(**keycloak_config)

    @property
    def tenant(self) -> TenantConfig:
        tenant_config = self.cfg.get('tenant', {})
        return TenantConfig(**tenant_config)

    @property
    def realm_token(self) -> str:
        """Returns a management admin token for keycloak for the current realm."""
        keycloak_config = self.keycloak
        if not keycloak_config.realm_admin_id or not keycloak_config.realm_secret:
            raise ValueError("Realm admin credentials not set, unable to generate token")

        realm = keycloak_config.realm
        url = f"https://{keycloak_config.host}/auth/realms/{realm}/protocol/openid-connect/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": keycloak_config.realm_admin_id,
            "client_secret": keycloak_config.realm_secret
        }
        token_response = requests.post(url, data=payload, verify=self.environment.verify_ssl)
        token_response.raise_for_status()
        return token_response.json()["access_token"]

    @property
    def keycloak_token(self) -> str:
        """Returns a management admin token for Keycloak, if values are set."""
        keycloak_config = self.keycloak
        if keycloak_config.admin_id and keycloak_config.admin_secret:
            url = f"https://{keycloak_config.host}/auth/realms/master/protocol/openid-connect/token"
            payload = {
                "grant_type": "client_credentials",
                "client_id": keycloak_config.admin_id,
                "client_secret": keycloak_config.admin_secret
            }
            token_response = requests.post(url, data=payload, verify=self.environment.verify_ssl)
            token_response.raise_for_status()
            return token_response.json()["access_token"]
        else:
            raise ValueError("Admin credentials not configured, unable to request token")

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
