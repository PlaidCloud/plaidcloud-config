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
import re
import yaml
from typing import NamedTuple
from plaidcloud.config.redis import RedisConfig
from plaidcloud.config.rabbitmq import RMQConfig

CONFIG_PATH = os.environ.get('PLAID_CONFIG_PATH', '/etc/plaidcloud/config.yaml')
ENV_OVERRIDE_PREFIX = 'PLAID_CFG'
ENV_OVERRIDE_SEP = '00'

logger = logging.getLogger(__name__)

#: (lakehouse id, undeclared keys) already reported by `PlaidConfig.lakehouses`. Process-wide
#: because the warning describes the config file, which does not change under a running pod.
_WARNED_UNDECLARED = set()


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
    # The control-plane id of the lakehouse this describes, for records `resolve_lakehouse`
    # builds. Empty on `cfg.database`, which is the chart's block and names no lakehouse — and
    # empty is what plaid's `assigned_lakehouse_id` already reads for "unassigned". Without it
    # a resolved record cannot be matched back to a project's `lakehouse_id`, so on a tenant
    # with two lakehouses every binding fails to resolve.
    lakehouse_id: str = ""


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
    (`router/tenant.py`), which is the shape the values file carries. Top-level twins would
    parse — they would just sit at their defaults, unfed by any rendered record — so the
    reason not to add them is that they would be a second, always-empty answer to a question
    `coordinates` already answers, not that the record would fail to load.
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


#: A customer-owned lakehouse, identified as cp-rest identifies one
#: (`lakehouse_tools.is_credential_ref`): its credential lives in the per-lakehouse vault-only
#: namespace. Anything else is PlaidCloud-provisioned. Keyed on the credential ref rather than
#: `engine` because that is what cp-rest's own `reconcile_default_lakehouse` keys on; an engine
#: test would misfile the first customer StarRocks.
#:
#: The `lh-` plus 32 lowercase hex anchoring is cp-rest's and is load-bearing there: a looser
#: `lakehouse_.*_password` also matches `lakehouse_admin_password` and every
#: `lakehouse_user_<name>_password`. This is a SECOND copy of that pattern with no shared
#: source — if cp-rest's `mint_lakehouse_id` shape ever changes, both must move together.
#:
#: It FAILS OPEN, deliberately: anything unrecognised (absent, empty, legacy, uppercase hex,
#: hand-edited) reads as PlaidCloud-provisioned and inherits the tenant block. That is the
#: right way round for the shapes cp-rest emits, where the only non-matching ref is the legacy
#: provisioned one. On a hand-edited values file it means a malformed customer ref inherits
#: the tenant's superuser and Lakekeeper token; cp-rest cannot produce that, and failing the
#: other way would refuse every real provisioned record.
_CUSTOMER_CREDENTIAL_REF = re.compile(r'^lakehouse_lh-[0-9a-f]{32}_password$')

#: The principal to use when an engine's record carries none, for engines that conventionally
#: take a constant rather than a configured account. cp-rest omits `superuser` from Databricks'
#: required set on purpose — the field is rendered into the Git-committed values file, so
#: demanding it invites an operator to paste the PAT there.
#:
#: `token` is the PAT convention, corroborated by cp-rest's comment and by plaid's own fixtures
#: (`databricks://token:x@host:443/default`). It is NOT universal: Databricks OAuth M2M
#: authenticates a service principal by client id, and plaid's own customer-connection builder
#: (`connection.py` `_form_connection_string`) takes the username from `db_user` rather than
#: hardcoding anything. So this is a DEFAULT, not a rule — a record that names a `superuser`
#: always wins, which is the only escape hatch a non-PAT auth mode has.
_FIXED_PRINCIPAL = {'databricks': 'token'}

#: What a customer record inherits: nothing. The empty `superuser` is what makes a genuinely
#: missing principal raise, and the Iceberg coordinates are EMPTY rather than
#: `DatabaseConfig`'s class defaults — those name `http://lakekeeper:8181`, a Service that
#: exists in no tenant namespace. Empty is also what plaid reads as "no Iceberg half": a
#: truthy URL sends `drop_schema` and the `getattr(db, 'LAKEKEEPER_URL', None)` probes down
#: the Iceberg branch, so a fabricated default would aim them at a Lakekeeper this warehouse
#: has nothing to do with. All three are spelled out even though `lakekeeper_warehouse`'s
#: class default is already '' — so that a change to `DatabaseConfig`'s defaults cannot
#: silently re-fabricate one of them.
_NO_INHERITANCE = DatabaseConfig(hostname="", port=None, superuser="", password="", system="",
                                 iceberg_catalog="", lakekeeper_url="", lakekeeper_warehouse="",
                                 lakekeeper_token="")


def resolve_lakehouse(lakehouse: LakehouseConfig, tenant_default: DatabaseConfig,
                      password: str) -> DatabaseConfig:
    """The connectable form of one lakehouse, for `orm.build_lakehouse_dsns`.

    A `DatabaseConfig` because the TYPE is read: `orm.lakehouse_fingerprint` builds the
    engine-cache key from `DatabaseConfig._fields`, so another type drops fields out of the
    key and lets two lakehouses share one engine.

    `tenant_default` is `cfg.database`, and it is the inheritance base ONLY for a
    PlaidCloud-provisioned record — which re-describes the warehouse `cfg.database` already
    addresses. `mint_tenant_lakehouse` emits no `superuser` and `catalog: None`, so without
    that a fleet-standard record resolves to a blank principal and to the class-default
    `lakekeeper_url`, which names no Service in a tenant namespace. A customer record inherits
    nothing: falling back to the tenant's own warehouse for one PlaidCloud does not run is the
    "answers for the wrong warehouse while looking like it worked" failure.

    `password` is an argument: the record names a Vault key, and nothing here resolves it.

    Refuses a disabled lakehouse, and one that names no warehouse at all. `status` is NOT
    refused — `provisioning` is what `create_tenant` mints and what bootstrap must connect to
    in order to build the warehouse, and `retired` still serves the projects already on it.
    """
    if lakehouse.disabled:
        raise ValueError(
            f'lakehouse {lakehouse.id!r} ({lakehouse.name!r}) is disabled and cannot be connected to'
        )
    coordinates = lakehouse.coordinates or {}
    hostname = (coordinates.get('hostname') or '').strip()
    if not lakehouse.engine or not hostname:
        raise ValueError(
            f'lakehouse {lakehouse.id!r} ({lakehouse.name!r}) names no warehouse: '
            f'engine={lakehouse.engine!r}, coordinates.hostname={hostname!r}'
        )

    customer = is_customer_lakehouse(lakehouse)
    inherited = _NO_INHERITANCE if customer else tenant_default
    superuser = (lakehouse.superuser or _FIXED_PRINCIPAL.get(lakehouse.engine)
                 or inherited.superuser)
    if not superuser:
        raise ValueError(
            f'lakehouse {lakehouse.id!r} ({lakehouse.name!r}) names no connection principal: '
            f'the record has no superuser, engine {lakehouse.engine!r} has no fixed one, and '
            + ('a customer record inherits none' if customer
               else 'the tenant default has none either')
        )
    catalog = lakehouse.catalog or {}
    return DatabaseConfig(
        lakehouse_id=lakehouse.id,
        hostname=hostname,
        # None for an engine whose URL takes no port (Snowflake); `URL.create` accepts it.
        port=coordinates.get('port'),
        superuser=superuser,
        password=password,
        # `engine` and `system` range over the same words — starrocks, databend, snowflake,
        # databricks — and the chart renders `system: {{ externalDatabase.protocol }}`.
        system=lakehouse.engine,
        # As recorded, including ''. The in-cluster engines render an empty database name, so
        # substituting 'plaid_data' would be this library guessing.
        database_name=coordinates.get('database_name') or '',
        # Compute rides the DSN query string. Empty is absent, as in cp-rest's
        # `missing_connection_fields`; forwarding it renders `?role=`.
        query_params={k: v for k, v in (lakehouse.compute or {}).items() if v},
        # `.get(k, default)` and not truthiness: an operator setting these to '' is saying
        # this lakehouse has no Iceberg half, and that has to survive.
        iceberg_catalog=catalog.get('iceberg_catalog', inherited.iceberg_catalog),
        lakekeeper_url=catalog.get('lakekeeper_url', inherited.lakekeeper_url),
        lakekeeper_warehouse=catalog.get('lakekeeper_warehouse', inherited.lakekeeper_warehouse),
        # `LakehouseCatalog` has no token field, so inheritance is the only source.
        lakekeeper_token=inherited.lakekeeper_token,
        # cloud_url is deliberately absent: one shared-Postgres catalog per tenant, read from
        # `cfg.database` by `orm.build_shared_dsns`, never a lakehouse coordinate.
    )


def is_customer_lakehouse(lakehouse: LakehouseConfig) -> bool:
    """Whether the customer owns this warehouse, rather than PlaidCloud provisioning it."""
    return bool(_CUSTOMER_CREDENTIAL_REF.fullmatch(lakehouse.credential_ref or ''))


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

        Undeclared keys are dropped rather than raised on, so a values render can land ahead
        of a library bump without a TypeError in every plaid pod (the rollout order
        `test_extra_keys_ignored` pins). But the drop is LOGGED, once per record-and-key-set:
        this is a property that plaid re-reads on every project resolution, and a per-read
        warning floods the very window it exists to report. Silence is what let `disabled` and
        `superuser` disappear here; a flood is the same as silence.

        Lakehouse records only — every other block drops undeclared keys by design
        (`database:` carries `lakehouses` and `default_lakehouse_id`, which `DatabaseConfig`
        is supposed to filter).
        """
        lakehouses = []
        for record in (self.cfg.get('database') or {}).get('lakehouses') or []:
            undeclared = sorted(set(record) - set(LakehouseConfig._fields))
            seen = (record.get('id', ''), tuple(undeclared))
            if undeclared and seen not in _WARNED_UNDECLARED:
                _WARNED_UNDECLARED.add(seen)
                logger.warning(
                    'Lakehouse %r carries %s, which this plaidcloud-config does not declare '
                    'and is dropping. Upgrade the library before relying on them.',
                    seen[0], ', '.join(undeclared),
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
