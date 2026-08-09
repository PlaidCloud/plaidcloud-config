#!/usr/bin/env python
# coding=utf-8

__author__ = "Garrett Bates"
__copyright__ = "© Copyright 2020-2026, PlaidCloud, Inc"
__credits__ = ["Garrett Bates"]
__license__ = "Apache 2.0"
__maintainer__ = "Garrett Bates"
__email__ = "garrett@plaidcloud.com"

"""Loads the configuration file used by plaid apps in kubernetes."""
import logging
import os
import yaml
from typing import NamedTuple
from plaidcloud.config.redis import RedisConfig
from plaidcloud.config.rabbitmq import RMQConfig

CONFIG_PATH = os.environ.get('PLAID_CONFIG_PATH', '/etc/plaidcloud/config.yaml')
ENV_OVERRIDE_PREFIX = 'PLAID_CFG'
ENV_OVERRIDE_SEP = '00'

logger = logging.getLogger(__name__)


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

    ⚠️ `coordinates`, `catalog` and `compute` stay NESTED, and are unpacked in exactly one
    place — `resolve_lakehouse`. They are not free-form: they are cp-rest's
    `LakehouseCoordinates` / `LakehouseCatalog` / `LakehouseCompute` models
    (`router/tenant.py`), which is the shape the values file actually carries. Promoting
    their members to top-level fields here would not flatten the record, it would stop
    parsing it — a rendered `coordinates:` block would match no declared field and every
    lakehouse would resolve to an empty hostname.
    """
    id: str = ""
    name: str = ""
    engine: str = ""
    status: str = ""
    # `disabled`, not `enabled`, and False is the safe zero value: the provisioned record every
    # tenant carries does not stamp it, so a missing key must read as "on". Dropping it silently
    # (which the field filter did until it was declared) is how an operator-disabled lakehouse
    # comes back connectable.
    disabled: bool = False
    # The connection principal. NOT a coordinate — two logins against one host, port and
    # database are one physical store — so it is top-level, as cp-rest emits it.
    superuser: str = ""
    coordinates: dict = {}
    catalog: dict | None = None
    compute: dict | None = None
    credential_ref: str = ""


#: The `catalog` members that are `DatabaseConfig` fields. Omitted rather than passed empty
#: when the record does not carry them: cp-rest sets `catalog: None` on the warehouses it
#: provisions precisely because it does not own these coordinates, so the answer there is
#: `DatabaseConfig`'s own defaults, not `''`.
_CATALOG_FIELDS = ('iceberg_catalog', 'lakekeeper_url', 'lakekeeper_warehouse')


def resolve_lakehouse(lakehouse: LakehouseConfig, password: str) -> DatabaseConfig:
    """The connectable form of one lakehouse: a `DatabaseConfig`, ready for
    `plaid.core.data.orm.build_lakehouse_dsns`.

    A `DatabaseConfig` and not a widened `LakehouseConfig`, because two consumers read the
    type and not just the attributes. `orm.build_lakehouse_dsns` reads `system`, `superuser`,
    `hostname`, `port`, `database_name`, `query_params` and `password` under those names; and
    `orm.lakehouse_fingerprint` — the engine-cache key — iterates `DatabaseConfig._fields`
    with `getattr(..., None)`, so any other type drops whatever it happens not to declare out
    of the key and lets two lakehouses share one engine. `database_tools`' Iceberg half reads
    `iceberg_catalog` / `lakekeeper_*` off the same record, again under these names.

    `password` is an ARGUMENT because it is not in the record and must not be: a lakehouse
    names its credential with `credential_ref`, a Vault key name, and nothing in this library
    resolves it. The caller supplies the credential it read.

    `cloud_url` is left at its default on purpose — the legacy shared-Postgres catalog is one
    per tenant, is read from `cfg.database` by `orm.build_shared_dsns`, and is not a lakehouse
    coordinate. `lakekeeper_token` is left at its default for the duller reason that the
    control plane's record has no field for it; a StarRocks lakehouse whose Lakekeeper needs a
    token cannot get one through here yet.

    Refuses a disabled lakehouse rather than returning something connectable: this is the only
    seam in this library where that flag can bite, and a kill switch nothing reads is
    decoration. `status` is deliberately NOT refused — `retired` blocks new project bindings
    (cp-rest `LAKEHOUSE_STATUSES`), it does not stop the projects already there from reading.
    """
    if lakehouse.disabled:
        raise ValueError(
            f'lakehouse {lakehouse.id!r} ({lakehouse.name!r}) is disabled and cannot be connected to'
        )
    coordinates = lakehouse.coordinates or {}
    catalog = lakehouse.catalog or {}
    compute = lakehouse.compute or {}
    return DatabaseConfig(
        hostname=coordinates.get('hostname', ''),
        # None for an engine whose URL takes no port (Snowflake); `URL.create` accepts it.
        port=coordinates.get('port'),
        superuser=lakehouse.superuser,
        password=password,
        # `engine` and `system` range over the same words — starrocks, databend, snowflake,
        # databricks (`lakehouse_tools.LAKEHOUSE_ENGINES`, and the chart renders
        # `system: {{ externalDatabase.protocol }}`).
        system=lakehouse.engine,
        # Passed through as the control plane recorded it, including ''. The in-cluster
        # engines render an empty database name, and substituting `DatabaseConfig`'s
        # 'plaid_data' default would be this library guessing a warehouse.
        database_name=coordinates.get('database_name') or '',
        # Compute selection rides the DSN query string: Snowflake picks it with
        # warehouse/role, Databricks with http_path. Unset members serialize as null and
        # would otherwise render as literal 'None' in the URL.
        query_params={k: v for k, v in compute.items() if v is not None},
        **{k: catalog[k] for k in _CATALOG_FIELDS if catalog.get(k)},
    )


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

        Undeclared keys are still dropped rather than raised on, because a values render
        landing ahead of a library bump must not TypeError inside every plaid pod on the
        tenant — that rollout order is what `LakehouseConfig` exists ahead of its consumers
        for. But the drop is LOGGED. Silence is what let cp-rest's `disabled` and `superuser`
        disappear here for a whole release: a record said a warehouse was switched off, this
        filter discarded the key, and the result was a lakehouse that read as enabled with
        nothing anywhere saying otherwise.

        Only lakehouse records are checked. Every other block filters undeclared keys
        deliberately and constantly — `database:` alone carries `lakehouses` and
        `default_lakehouse_id`, which `DatabaseConfig` drops by design — so a library-wide
        warning would be noise on every pod start, and noise is the same as silence.
        """
        lakehouses = []
        for record in (self.cfg.get('database') or {}).get('lakehouses') or []:
            undeclared = sorted(set(record) - set(LakehouseConfig._fields))
            if undeclared:
                logger.warning(
                    'Lakehouse %r carries %s, which this plaidcloud-config does not declare '
                    'and is dropping. Upgrade the library before relying on them.',
                    record.get('id', ''), ', '.join(undeclared),
                )
            lakehouses.append(
                LakehouseConfig(**{k: v for k, v in record.items() if k in LakehouseConfig._fields})
            )
        return lakehouses

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
