#!/usr/bin/env python
# coding=utf-8

__author__ = "Garrett Bates"
__copyright__ = "© Copyright 2020-2026, PlaidCloud, Inc"
__credits__ = ["Garrett Bates"]
__license__ = "Apache 2.0"
__maintainer__ = "Garrett Bates"
__email__ = "garrett@plaidcloud.com"

"""Loads the configuration file used by plaid apps in kubernetes."""
import os
import yaml
from typing import NamedTuple
from plaidcloud.config.redis import RedisConfig
from plaidcloud.config.rabbitmq import RMQConfig

CONFIG_PATH = os.environ.get('PLAID_CONFIG_PATH', '/etc/plaidcloud/config.yaml')
ENV_OVERRIDE_PREFIX = 'PLAID_CFG'
ENV_OVERRIDE_SEP = '00'


def _apply_env_overrides(cfg: dict) -> None:
    marker = ENV_OVERRIDE_PREFIX + ENV_OVERRIDE_SEP
    for name, raw in os.environ.items():
        if not name.startswith(marker):
            continue
        path = [p for p in name[len(marker):].split(ENV_OVERRIDE_SEP) if p]
        if not path:
            continue
        try:
            value = yaml.safe_load(raw)
        except yaml.YAMLError:
            value = raw
        node = cfg
        for key in path[:-1]:
            if not isinstance(node.get(key), dict):
                node[key] = {}
            node = node[key]
        node[path[-1]] = value


class DatabaseConfig(NamedTuple):
    hostname: str
    port: int
    superuser: str
    password: str
    system: str
    database_name: str = "plaid_data"
    query_params: dict = {}
    cloud_url: str = ""
    iceberg_catalog: str = "iceberg_catalog"
    lakekeeper_url: str = "http://lakekeeper:8181"
    lakekeeper_warehouse: str = ""
    lakekeeper_token: str = ""


class LakehouseConfig(NamedTuple):
    """One of the warehouses a tenant has (sc-23158).

    Mirrors the control plane's Lakehouse record field for field. `id` is assigned by the
    control plane, opaque and immutable — it is the primary key a project's `lakehouse_id`
    names, deliberately not derived from the coordinates, which are mutable.

    ⚠️ `credential_ref` is the NAME of a Vault key, never a credential. Nothing in this
    library resolves it; a caller that wants the password reads that key out of the tenant's
    Vault entry.

    `catalog` and `compute` are nullable by design: the control plane owns neither, and a
    default here would be a stale copy of somebody else's.
    """
    id: str = ""
    name: str = ""
    engine: str = ""
    status: str = ""
    coordinates: dict = {}
    catalog: dict | None = None
    compute: dict | None = None
    credential_ref: str = ""


class EnvironmentConfig(NamedTuple):
    hostname: str = "plaidcloud.io"
    hostnames: list = ["plaidcloud.io"]
    designation: str = "dev"
    tempdir: str = "/tmp"
    verify_ssl: bool = False
    workflow_image: str = ""
    panel_builder_image: str = ""


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
    # In-cluster Keycloak base for server-to-server admin calls; empty ⇒ use `url`.
    # Keeps admin traffic in-cluster (cheaper egress, lower latency). Safe because
    # Keycloak runs hostname-strict=false, deriving the token issuer per request host.
    internal_url: str = ""


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
    workflow_run_history: dict = {}
    entitlements: dict = {}
    stripe_api_key: str = ""
    stripe_tax_key: str = ""
    stripe_webhook_secret: str = ""
    ramp_client_id: str = ""
    ramp_client_secret: str = ""
    client_asset_version: str = ""
    client_bucket_serving: bool = False


class GlobalConfig(NamedTuple):
    client_id: str = ""
    client_secret: str = ""
    url: str = ""
    db_host: str = ""


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

class AIChatHistoryConfig(NamedTuple):
    langchain_db_url: str = ""
    conversation_db_url: str = ""
    username: str = ""
    password: str = ""
    ollama_url: str = ""
    grok_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    gemini_api_key: str = ""


class LokiConfig(NamedTuple):
    host: str = "loki-gateway"
    username: str = "lokiuser"
    password: str = "lokipassword"
    port: int = 3100


class SharedPostgresConfig(NamedTuple):
    backups: dict = {}
    restore: dict = {}
    credentials: dict = {}


class OAuthServiceConfig(NamedTuple):
    client_id: str = ""
    client_secret: str = ""


class OAuthConfig(NamedTuple):
    quickbooks: OAuthServiceConfig = OAuthServiceConfig()
    paycor: OAuthServiceConfig = OAuthServiceConfig()


class StripeConfig(NamedTuple):
    api_key: str = ""
    webhook_secret: str = ""


class EmailConfig(NamedTuple):
    postmark_server_token: str = ""
    postmark_server_id: str = ""
    sender: str = ""


class VaultConfig(NamedTuple):
    enabled: bool = False
    url: str = "http://127.0.0.1:8200"
    token: str = ""
    mount_point: str = "secret"
    tenant_path_prefix: str = "tenants"
    global_path: str = "global"


class SecurityConfig(NamedTuple):
    cookie_secret: str = ""
    step_token_secret: str = ""


class PlaidConfig:
    """Parses a standard configuration file for consumption by python code."""
    def __init__(self):
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, 'r') as stream:
                # Leave exception unhandled. We don't want to start without a valid conf.
                self.cfg = yaml.safe_load(stream) or {}
        else:
            self.cfg = {}
        _apply_env_overrides(self.cfg)

    @property
    def database(self) -> DatabaseConfig:
        db_config = self.cfg.get('database', {})
        return DatabaseConfig(**{k: v for k, v in db_config.items() if k in DatabaseConfig._fields})

    @property
    def lakehouses(self) -> list[LakehouseConfig]:
        """Every lakehouse this tenant has, in the order the control plane recorded them.

        Empty on every tenant whose values file predates the render — an absent collection is
        not an error, it is a tenant that has not been republished yet.
        """
        db_config = self.cfg.get('database') or {}
        return [
            LakehouseConfig(**{k: v for k, v in lakehouse.items() if k in LakehouseConfig._fields})
            for lakehouse in db_config.get('lakehouses') or []
        ]

    @property
    def default_lakehouse_id(self) -> str:
        """The id newly created projects bind to. Empty when the tenant has no collection.

        An id, not a record: a project stores this id, and resolving it against `lakehouses`
        is the caller's business. Matching by id is the only correct resolution — with one
        lakehouse a "first in the list" fallback is indistinguishable from a real answer and
        stops being right exactly when a second one appears.
        """
        return (self.cfg.get('database') or {}).get('default_lakehouse_id') or ""

    @property
    def environment(self) -> EnvironmentConfig:
        env_config = self.cfg.get('environment', {})
        ec = EnvironmentConfig(**{k: v for k, v in env_config.items() if k in EnvironmentConfig._fields})
        # CRL 2023 - Ensures that primary hostname is set based off the `hostnames` parameter if not provided.
        if not env_config.get('hostname') and (ec.hostnames and ec.hostnames != ["plaidcloud.io"]):
            ec = ec._replace(hostname=ec.hostnames[0])
        return ec

    def feature(self, name: str, default=False):
        """Read a feature flag by name. Flags are not declared anywhere — they are whatever
        the tenant's config carries, including UI-set flags merged in via
        PLAID_CFG00features00<name> env overrides."""
        return (self.cfg.get('features') or {}).get(name, default)

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
    def oauth(self) -> OAuthConfig:
        oauth_config = self.cfg.get('oauth', {})
        return OAuthConfig(**{
            k: OAuthServiceConfig(
                **{conf_k: conf_v for conf_k, conf_v in v.items() if conf_k in OAuthServiceConfig._fields}
            ) for k, v in oauth_config.items() if k in OAuthConfig._fields})

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

    @property
    def ai_chat_history(self) -> AIChatHistoryConfig:
        history_config = self.cfg.get('ai_chat_history', {})
        return AIChatHistoryConfig(**{k: v for k, v in history_config.items() if k in AIChatHistoryConfig._fields})

    @property
    def stripe(self) -> StripeConfig:
        stripe_config = self.cfg.get('stripe', {})
        return StripeConfig(**{k: v for k, v in stripe_config.items() if k in StripeConfig._fields})

    @property
    def email(self) -> EmailConfig:
        email_config = self.cfg.get('email', {})
        return EmailConfig(**{k: v for k, v in email_config.items() if k in EmailConfig._fields})

    @property
    def vault(self) -> VaultConfig:
        vault_config = self.cfg.get('vault', {})
        return VaultConfig(**{k: v for k, v in vault_config.items() if k in VaultConfig._fields})

    @property
    def security(self) -> SecurityConfig:
        security_config = self.cfg.get('security', {})
        return SecurityConfig(**{k: v for k, v in security_config.items() if k in SecurityConfig._fields})

    def __str__(self):
        return repr(self)

config = PlaidConfig()  # pylint: disable=invalid-name
