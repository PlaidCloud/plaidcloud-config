#!/usr/bin/env python
# coding=utf-8

__author__ = "Garrett Bates"
__copyright__ = "© Copyright 2020-2026, PlaidCloud, Inc"
__credits__ = ["Garrett Bates"]
__license__ = "Apache 2.0"
__maintainer__ = "Garrett Bates"
__email__ = "garrett@plaidcloud.com"

"""Tests for plaidcloud.config.config module."""
import logging
import re
import sys
import yaml
import pytest

# The package __init__.py shadows the submodule name with the PlaidConfig singleton,
# so we access the actual module object through sys.modules.
import plaidcloud.config.config  # noqa: F811
config_mod = sys.modules['plaidcloud.config.config']

DatabaseConfig = config_mod.DatabaseConfig
EnvironmentConfig = config_mod.EnvironmentConfig
KeycloakConfig = config_mod.KeycloakConfig
TenantConfig = config_mod.TenantConfig
GlobalConfig = config_mod.GlobalConfig
ServiceConfig = config_mod.ServiceConfig
OpenSearchConfig = config_mod.OpenSearchConfig
SupersetConfig = config_mod.SupersetConfig
AIChatHistoryConfig = config_mod.AIChatHistoryConfig
LokiConfig = config_mod.LokiConfig
SharedPostgresConfig = config_mod.SharedPostgresConfig
OAuthConfig = config_mod.OAuthConfig
OAuthServiceConfig = config_mod.OAuthServiceConfig
StripeConfig = config_mod.StripeConfig
EmailConfig = config_mod.EmailConfig
VaultConfig = config_mod.VaultConfig
SecurityConfig = config_mod.SecurityConfig
PlaidConfig = config_mod.PlaidConfig


# ---------------------------------------------------------------------------
# PlaidConfig initialization
# ---------------------------------------------------------------------------

class TestPlaidConfigInit:

    def test_loads_yaml_from_file(self, plaid_config):
        assert isinstance(plaid_config.cfg, dict)
        assert "database" in plaid_config.cfg

    def test_missing_config_file(self, missing_config):
        assert missing_config.cfg == {}

    def test_empty_config_file(self, empty_config):
        # yaml.safe_load("") returns None, but PlaidConfig normalizes to {}
        assert empty_config.cfg == {}
        # Properties that have all-default fields should still work
        env = empty_config.environment
        assert env.hostname == "plaidcloud.io"

    def test_str_repr(self, plaid_config):
        result = str(plaid_config)
        assert result == repr(plaid_config)


# ---------------------------------------------------------------------------
# DatabaseConfig
# ---------------------------------------------------------------------------

class TestDatabaseConfig:

    def test_full_config(self, plaid_config):
        db = plaid_config.database
        assert isinstance(db, DatabaseConfig)
        assert db.hostname == "db-host"
        assert db.port == 5432
        assert db.superuser == "admin"
        assert db.password == "secret"
        assert db.system == "postgresql"
        assert db.database_name == "mydb"
        assert db.query_params == {"sslmode": "require"}
        assert db.cloud_url == "https://cloud.example.com"
        assert db.iceberg_catalog == "my_catalog"
        assert db.lakekeeper_url == "http://lakekeeper:8181"
        assert db.lakekeeper_warehouse == "wh1"
        assert db.lakekeeper_token == "tok123"

    def test_defaults(self, missing_config):
        # DatabaseConfig has required fields (hostname, port, superuser, password, system)
        # With missing config, database section is {}, so constructing with no args should fail
        # unless those keys exist. Let's verify the property doesn't crash with empty config.
        with pytest.raises(TypeError):
            _ = missing_config.database

    def test_extra_keys_ignored(self, tmp_path, monkeypatch):
        """Extra keys in YAML that don't match NamedTuple fields are filtered out."""
        cfg = {
            "database": {
                "hostname": "h",
                "port": 1234,
                "superuser": "su",
                "password": "pw",
                "system": "pg",
                "unknown_field": "should_be_ignored",
            }
        }
        config_path = tmp_path / "cfg.yaml"
        config_path.write_text(yaml.dump(cfg))
        mod = sys.modules['plaidcloud.config.config']
        monkeypatch.setattr(mod, "CONFIG_PATH", str(config_path))
        pc = PlaidConfig()
        db = pc.database
        assert db.hostname == "h"
        assert not hasattr(db, "unknown_field")


# ---------------------------------------------------------------------------
# EnvironmentConfig
# ---------------------------------------------------------------------------

class TestEnvironmentConfig:

    def test_full_config(self, plaid_config):
        env = plaid_config.environment
        assert isinstance(env, EnvironmentConfig)
        assert env.hostname == "app.example.com"
        assert env.hostnames == ["app.example.com", "app2.example.com"]
        assert env.designation == "staging"
        assert env.tempdir == "/var/tmp"
        assert env.verify_ssl is True
        assert env.workflow_image == "plaid/workflow:latest"

    def test_defaults(self, missing_config):
        env = missing_config.environment
        assert env.hostname == "plaidcloud.io"
        assert env.designation == "dev"
        assert env.verify_ssl is False

    def test_hostname_fallback_from_hostnames(self, tmp_path, monkeypatch):
        """When hostname is not set but hostnames is, hostname should default to the first hostname."""
        cfg = {
            "environment": {
                "hostnames": ["first.example.com", "second.example.com"],
            }
        }
        config_path = tmp_path / "cfg.yaml"
        config_path.write_text(yaml.dump(cfg))
        mod = sys.modules['plaidcloud.config.config']
        monkeypatch.setattr(mod, "CONFIG_PATH", str(config_path))
        pc = PlaidConfig()
        env = pc.environment
        assert env.hostname == "first.example.com"

    def test_hostname_no_fallback_when_explicitly_set(self, tmp_path, monkeypatch):
        """When hostname IS explicitly set, it should not be overridden."""
        cfg = {
            "environment": {
                "hostname": "explicit.example.com",
                "hostnames": ["other.example.com"],
            }
        }
        config_path = tmp_path / "cfg.yaml"
        config_path.write_text(yaml.dump(cfg))
        mod = sys.modules['plaidcloud.config.config']
        monkeypatch.setattr(mod, "CONFIG_PATH", str(config_path))
        pc = PlaidConfig()
        env = pc.environment
        assert env.hostname == "explicit.example.com"

    def test_hostname_no_fallback_when_hostnames_is_default(self, tmp_path, monkeypatch):
        """When hostnames equals the default, hostname should not be overridden."""
        cfg = {
            "environment": {
                "hostnames": ["plaidcloud.io"],
            }
        }
        config_path = tmp_path / "cfg.yaml"
        config_path.write_text(yaml.dump(cfg))
        mod = sys.modules['plaidcloud.config.config']
        monkeypatch.setattr(mod, "CONFIG_PATH", str(config_path))
        pc = PlaidConfig()
        env = pc.environment
        assert env.hostname == "plaidcloud.io"


# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------

class TestFeatureFlags:

    def test_reads_flags_from_config(self, plaid_config):
        assert plaid_config.feature("sample_flag_on") is True
        assert plaid_config.feature("sample_flag_off") is False

    def test_reads_flag_added_at_runtime(self, plaid_config):
        plaid_config.cfg["features"]["experimental_x"] = True
        assert plaid_config.feature("experimental_x") is True

    def test_default_when_absent(self, missing_config):
        assert missing_config.feature("nope") is False
        assert missing_config.feature("nope", "d") == "d"

    def test_default_when_features_block_empty(self, tmp_path, monkeypatch):
        """A `features:` key rendered with no children loads as None, not {}, so the
        default must survive an explicitly empty block as well as a missing one."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text("features:\n")
        mod = sys.modules["plaidcloud.config.config"]
        monkeypatch.setattr(mod, "CONFIG_PATH", str(config_path))
        assert PlaidConfig().feature("anything", "fallback") == "fallback"

    def test_env_override_end_to_end(self, config_file, monkeypatch):
        mod = sys.modules["plaidcloud.config.config"]
        monkeypatch.setattr(mod, "CONFIG_PATH", config_file)
        monkeypatch.setenv("PLAID_CFG00features00new_flag", "true")
        cfg = PlaidConfig()
        assert cfg.feature("new_flag") is True


# ---------------------------------------------------------------------------
# KeycloakConfig
# ---------------------------------------------------------------------------

class TestKeycloakConfig:

    def test_full_config(self, plaid_config):
        kc = plaid_config.keycloak
        assert isinstance(kc, KeycloakConfig)
        assert kc.url == "https://auth.example.com"
        assert kc.realm == "TestRealm"
        assert kc.client_name == "test-client"
        assert kc.admin_secret == "adminsecret"
        assert kc.db_url == "postgresql://keycloak:5432/keycloak"
        assert kc.internal_url == "http://keycloak.internal.svc:8080"

    def test_defaults(self, missing_config):
        kc = missing_config.keycloak
        assert kc.realm == "PlaidCloud"
        assert kc.client_name == "plaidcloud-login"
        assert kc.internal_url == ""


# ---------------------------------------------------------------------------
# TenantConfig
# ---------------------------------------------------------------------------

class TestTenantConfig:

    def test_full_config(self, plaid_config):
        t = plaid_config.tenant
        assert isinstance(t, TenantConfig)
        assert t.github_token == "ghp_test"
        assert t.id == "tenant-1"
        assert t.cloud_id == 42
        assert t.apps == ["app1", "app2"]
        assert t.use_proxy_download is True
        assert t.stripe_api_key == "sk_tenant_test"
        assert t.stripe_tax_key == "txi_tenant_test"
        assert t.stripe_webhook_secret == "whsec_tenant_test"
        assert t.ramp_client_id == "ramp_id_test"
        assert t.ramp_client_secret == "ramp_secret_test"
        assert t.client_asset_version == "v-test-123"
        assert t.client_bucket_serving is True
        assert t.workflow_run_history == {
            "writer_user": "wfh_writer",
            "writer_password": "wpw",
            "reader_user": "wfh_reader",
            "reader_password": "rpw",
        }
        assert t.entitlements == {
            "flag.ml_library": True,
            "limit.builders": 25,
            "set.auth_methods": ["google", "ms", "saml"],
        }

    def test_defaults(self, missing_config):
        t = missing_config.tenant
        assert t.github_token == ""
        assert t.apps == []
        assert t.cloud_id == 0
        assert t.stripe_api_key == ""
        assert t.stripe_tax_key == ""
        assert t.stripe_webhook_secret == ""
        assert t.ramp_client_id == ""
        assert t.ramp_client_secret == ""
        assert t.client_asset_version == ""
        assert t.client_bucket_serving is False
        assert t.workflow_run_history == {}
        assert t.entitlements == {}


# ---------------------------------------------------------------------------
# GlobalConfig
# ---------------------------------------------------------------------------

class TestGlobalConfig:

    def test_full_config(self, plaid_config):
        g = plaid_config.plaidcloud_global
        assert isinstance(g, GlobalConfig)
        assert g.client_id == "global-id"
        assert g.url == "https://global.example.com"
        assert g.db_host == "global-db"

    def test_defaults(self, missing_config):
        g = missing_config.plaidcloud_global
        assert g.client_id == ""
        assert g.url == ""


# ---------------------------------------------------------------------------
# ServiceConfig
# ---------------------------------------------------------------------------

class TestServiceConfig:

    def test_full_config(self, plaid_config):
        svc = plaid_config.service_urls
        assert isinstance(svc, ServiceConfig)
        assert svc.auth == "http://auth:8080"
        assert svc.rpc == "http://rpc:8080/json-rpc"

    def test_defaults(self, missing_config):
        svc = missing_config.service_urls
        assert svc.auth == "http://plaid-auth.plaid"


# ---------------------------------------------------------------------------
# OpenSearchConfig
# ---------------------------------------------------------------------------

class TestOpenSearchConfig:

    def test_full_config(self, plaid_config):
        os_cfg = plaid_config.opensearch
        assert isinstance(os_cfg, OpenSearchConfig)
        assert os_cfg.host == "opensearch.example.com"
        assert os_cfg.username == "osuser"
        assert os_cfg.port == 9201

    def test_defaults(self, missing_config):
        os_cfg = missing_config.opensearch
        assert os_cfg.host == ""
        assert os_cfg.port == 9200


# ---------------------------------------------------------------------------
# SupersetConfig
# ---------------------------------------------------------------------------

class TestSupersetConfig:

    def test_full_config(self, plaid_config):
        ss = plaid_config.superset
        assert isinstance(ss, SupersetConfig)
        assert ss.username == "superset_admin"
        assert ss.use_events_handler is False

    def test_defaults(self, missing_config):
        ss = missing_config.superset
        assert ss.username == "admin"
        assert ss.use_events_handler is True


# ---------------------------------------------------------------------------
# AIChatHistoryConfig
# ---------------------------------------------------------------------------

class TestAIChatHistoryConfig:

    def test_full_config(self, plaid_config):
        ai = plaid_config.ai_chat_history
        assert isinstance(ai, AIChatHistoryConfig)
        assert ai.langchain_db_url == "postgresql://langchain:5432/langchain"
        assert ai.username == "chatuser"
        assert ai.anthropic_api_key == "anthropic-secret"
        assert ai.gemini_api_key == "gemini-secret"

    def test_defaults(self, missing_config):
        ai = missing_config.ai_chat_history
        assert ai.langchain_db_url == ""
        assert ai.anthropic_api_key == ""
        assert ai.gemini_api_key == ""


# ---------------------------------------------------------------------------
# LokiConfig
# ---------------------------------------------------------------------------

class TestLokiConfig:

    def test_full_config(self, plaid_config):
        loki = plaid_config.loki
        assert isinstance(loki, LokiConfig)
        assert loki.host == "loki.example.com"
        assert loki.port == 3200

    def test_defaults(self, missing_config):
        loki = missing_config.loki
        assert loki.host == "loki-gateway"
        assert loki.port == 3100


# ---------------------------------------------------------------------------
# SharedPostgresConfig
# ---------------------------------------------------------------------------

class TestSharedPostgresConfig:

    def test_full_config(self, plaid_config):
        pg = plaid_config.postgres
        assert isinstance(pg, SharedPostgresConfig)
        assert pg.backups == {"enabled": True}
        assert pg.credentials == {"user": "pg", "password": "pgpass"}

    def test_defaults(self, missing_config):
        pg = missing_config.postgres
        assert pg.backups == {}
        assert pg.restore == {}


# ---------------------------------------------------------------------------
# OAuthConfig
# ---------------------------------------------------------------------------

class TestOAuthConfig:

    def test_full_config(self, plaid_config):
        oa = plaid_config.oauth
        assert isinstance(oa, OAuthConfig)
        assert isinstance(oa.quickbooks, OAuthServiceConfig)
        assert oa.quickbooks.client_id == "qb-id"
        assert oa.quickbooks.client_secret == "qb-secret"
        assert oa.paycor.client_id == "pc-id"

    def test_defaults(self, missing_config):
        oa = missing_config.oauth
        assert oa.quickbooks == OAuthServiceConfig()
        assert oa.paycor == OAuthServiceConfig()

    def test_extra_oauth_keys_ignored(self, tmp_path, monkeypatch):
        """Extra keys in OAuth sub-configs are filtered out."""
        cfg = {
            "oauth": {
                "quickbooks": {
                    "client_id": "qb",
                    "client_secret": "qbs",
                    "extra_field": "ignored",
                },
            }
        }
        config_path = tmp_path / "cfg.yaml"
        config_path.write_text(yaml.dump(cfg))
        mod = sys.modules['plaidcloud.config.config']
        monkeypatch.setattr(mod, "CONFIG_PATH", str(config_path))
        pc = PlaidConfig()
        assert pc.oauth.quickbooks.client_id == "qb"


# ---------------------------------------------------------------------------
# StripeConfig
# ---------------------------------------------------------------------------

class TestStripeConfig:

    def test_full_config(self, plaid_config):
        stripe = plaid_config.stripe
        assert isinstance(stripe, StripeConfig)
        assert stripe.api_key == "sk_test_123"
        assert stripe.webhook_secret == "whsec_test_456"

    def test_defaults(self, missing_config):
        stripe = missing_config.stripe
        assert stripe.api_key == ""
        assert stripe.webhook_secret == ""


# ---------------------------------------------------------------------------
# EmailConfig
# ---------------------------------------------------------------------------

class TestEmailConfig:

    def test_full_config(self, plaid_config):
        email = plaid_config.email
        assert isinstance(email, EmailConfig)
        assert email.postmark_server_token == "pmk-server-token"
        assert email.postmark_server_id == "pmk-server-id"
        assert email.sender == "no-reply@example.com"

    def test_defaults(self, missing_config):
        email = missing_config.email
        assert email.postmark_server_token == ""
        assert email.postmark_server_id == ""
        assert email.sender == ""


# ---------------------------------------------------------------------------
# VaultConfig
# ---------------------------------------------------------------------------

class TestVaultConfig:

    def test_full_config(self, plaid_config):
        vault = plaid_config.vault
        assert isinstance(vault, VaultConfig)
        assert vault.enabled is True
        assert vault.url == "http://vault:8200"
        assert vault.token == "vault-token"
        assert vault.mount_point == "kv"

    def test_defaults(self, missing_config):
        vault = missing_config.vault
        assert vault.enabled is False
        assert vault.url == "http://127.0.0.1:8200"
        assert vault.token == ""


# ---------------------------------------------------------------------------
# SecurityConfig
# ---------------------------------------------------------------------------

class TestSecurityConfig:

    def test_full_config(self, plaid_config):
        sec = plaid_config.security
        assert isinstance(sec, SecurityConfig)
        assert sec.cookie_secret == "cookie-sign-secret"
        assert sec.step_token_secret == "step-sign-secret"

    def test_defaults(self, missing_config):
        sec = missing_config.security
        assert sec.cookie_secret == ""
        assert sec.step_token_secret == ""


# ---------------------------------------------------------------------------
# RabbitMQ and Redis via PlaidConfig
# ---------------------------------------------------------------------------

class TestRabbitMQViaPlaidConfig:

    def test_rabbitmq_property(self, plaid_config):
        from plaidcloud.config.rabbitmq import RMQConfig
        rmq = plaid_config.rabbitmq
        assert isinstance(rmq, RMQConfig)
        assert rmq.hostname == "rmq-host"


class TestRedisViaPlaidConfig:

    def test_redis_property(self, plaid_config):
        from plaidcloud.config.redis import RedisConfig
        rc = plaid_config.redis
        assert isinstance(rc, RedisConfig)
        assert "session" in rc.urls


# ---------------------------------------------------------------------------
# LakehouseConfig (sc-23158)
# ---------------------------------------------------------------------------

# A rendered `database:` block exactly as the tenant chart emits it once cp-rest
# writes the collection: the single warehouse a tenant runs today, plus a second
# one so ordering and id-matching are actually exercised.
LAKEHOUSE_CFG = {
    "database": {
        "hostname": "starrocks-fe-service",
        "port": 9030,
        "superuser": "root",
        "password": "pw",
        "system": "starrocks",
        "default_lakehouse_id": "lh-2222",
        "lakehouses": [
            {
                "id": "lh-1111",
                "name": "Databend",
                "engine": "databend",
                "status": "retired",
                "coordinates": {"hostname": "plaid-databend-query", "port": 8000, "database_name": ""},
                "catalog": None,
                "compute": None,
                "credential_ref": "lakehouse_admin_password",
            },
            {
                "id": "lh-2222",
                "name": "StarRocks",
                "engine": "starrocks",
                "status": "active",
                "coordinates": {"hostname": "starrocks-fe-service", "port": 9030, "database_name": ""},
                "catalog": None,
                "compute": None,
                "credential_ref": "lakehouse_admin_password",
            },
        ],
    }
}


# THE RECORD EVERY TENANT ON THE FLEET CARRIES. Copied key-for-key from cp-rest's
# `lakehouse_tools.mint_tenant_lakehouse`, which emits exactly these eight keys: NO
# `superuser`, NO `disabled`, and `catalog: None` because cp-rest does not own the
# Iceberg/Lakekeeper coordinates. Tests that patch a superuser onto a record are testing a
# precondition production does not have.
MINTED_LAKEHOUSE_CFG = {
    "database": {
        # The tenant's own block, which is what a provisioned record re-describes. The
        # lakekeeper_url is the per-release Service the chart actually renders
        # (configmap-tenant.yaml), NOT DatabaseConfig's class default.
        "hostname": "starrocks-fe-service",
        "port": 9030,
        "superuser": "root",
        "password": "tenant-pw",
        "system": "starrocks",
        "iceberg_catalog": "tenant_catalog",
        "lakekeeper_url": "http://plaid-tenant-lakekeeper:8181",
        "lakekeeper_warehouse": "tenant_wh",
        "lakekeeper_token": "tenant-token",
        "cloud_url": "postgresql://c1:pw@plaid-shared-postgres:5432/cloud_1",
        "default_lakehouse_id": "lh-mint",
        "lakehouses": [
            {
                "id": "lh-mint",
                "name": "StarRocks",
                "engine": "starrocks",
                "status": "provisioning",
                "coordinates": {"hostname": "starrocks-fe-service", "port": 9030,
                                "database_name": ""},
                "catalog": None,
                "compute": None,
                "credential_ref": "lakehouse_admin_password",
            },
        ],
    }
}


# A record exactly as cp-rest's `build_customer_lakehouse` emits one: `disabled` and
# `superuser` at top level beside the nested coordinate/catalog/compute blocks.
# `id` and `credential_ref` are a real `mint_lakehouse_id` shape — `lh-` plus 32 hex. That is
# load-bearing, not decoration: cp-rest's `is_credential_ref` anchors on exactly that pattern,
# and it is how a customer record is told apart from a provisioned one.
CUSTOMER_ID = "lh-0123456789abcdef0123456789abcdef"
CUSTOMER_LAKEHOUSE_CFG = {
    "database": {
        # Present so a test can prove these are NOT inherited by a customer record.
        "hostname": "starrocks-fe-service",
        "port": 9030,
        "superuser": "root",
        "password": "tenant-pw",
        "system": "starrocks",
        "lakekeeper_url": "http://plaid-tenant-lakekeeper:8181",
        "lakekeeper_token": "tenant-token",
        "cloud_url": "postgresql://c1:pw@plaid-shared-postgres:5432/cloud_1",
        "default_lakehouse_id": CUSTOMER_ID,
        "lakehouses": [
            {
                "id": CUSTOMER_ID,
                "name": "Customer Snowflake",
                "engine": "snowflake",
                "status": "active",
                "disabled": True,
                "superuser": "SVC_PLAID",
                "coordinates": {"hostname": "acme-x1.snowflakecomputing.com", "port": None,
                                "database_name": "PLAID_DATA"},
                "catalog": None,
                "compute": {"warehouse": "PLAID_WH", "role": "PLAID_ROLE", "http_path": None},
                "credential_ref": f"lakehouse_{CUSTOMER_ID}_password",
            },
        ],
    }
}


# The OTHER customer engine, and the one the superuser rule turns on. cp-rest's
# `_REQUIRED_CONNECTION_FIELDS['databricks']` is ('hostname', 'http_path') — NO superuser —
# because the only correct principal is the literal `token` and `superuser` is rendered into
# the Git-committed values file, so demanding it invites an operator to paste the PAT there.
DATABRICKS_ID = "lh-fedcba9876543210fedcba9876543210"
DATABRICKS_LAKEHOUSE_CFG = {
    "database": {
        "hostname": "starrocks-fe-service",
        "port": 9030,
        "superuser": "root",
        "password": "tenant-pw",
        "system": "starrocks",
        "lakekeeper_url": "http://plaid-tenant-lakekeeper:8181",
        "lakekeeper_token": "tenant-token",
        "default_lakehouse_id": DATABRICKS_ID,
        "lakehouses": [
            {
                "id": DATABRICKS_ID,
                "name": "Customer Databricks",
                "engine": "databricks",
                "status": "active",
                "disabled": False,
                "superuser": "",
                "coordinates": {"hostname": "acme.cloud.databricks.com", "port": 443,
                                "database_name": ""},
                "catalog": None,
                "compute": {"warehouse": None, "role": None,
                            "http_path": "/sql/1.0/warehouses/abc123"},
                "credential_ref": f"lakehouse_{DATABRICKS_ID}_password",
            },
        ],
    }
}


def _config_from(tmp_path, monkeypatch, cfg):
    config_path = tmp_path / "cfg.yaml"
    config_path.write_text(yaml.dump(cfg))
    mod = sys.modules['plaidcloud.config.config']
    monkeypatch.setattr(mod, "CONFIG_PATH", str(config_path))
    return PlaidConfig()


class TestLakehouseCollectionIsInertUntilDeclared:
    """The property the rollout order rests on: a `lakehouses:` block can appear in a rendered
    config.yaml before anything reads it, because DatabaseConfig filters keys it does not
    declare. Without this, a values render landing ahead of a config-library bump would raise
    TypeError inside `cfg.database` in every plaid pod on the tenant."""

    def test_database_still_parses_with_the_collection_present(self, tmp_path, monkeypatch):
        db = _config_from(tmp_path, monkeypatch, LAKEHOUSE_CFG).database
        assert db.hostname == "starrocks-fe-service"
        assert db.system == "starrocks"

    def test_the_collection_is_not_a_database_field(self, tmp_path, monkeypatch):
        # Read through `lakehouses` / `default_lakehouse_id`, never `cfg.database`.
        db = _config_from(tmp_path, monkeypatch, LAKEHOUSE_CFG).database
        assert "lakehouses" not in db._fields
        assert "default_lakehouse_id" not in db._fields


class TestLakehouses:

    def test_parses_every_modelled_field(self, tmp_path, monkeypatch):
        lakehouses = _config_from(tmp_path, monkeypatch, LAKEHOUSE_CFG).lakehouses
        assert [lakehouse.id for lakehouse in lakehouses] == ["lh-1111", "lh-2222"]
        starrocks = lakehouses[1]
        assert isinstance(starrocks, config_mod.LakehouseConfig)
        assert starrocks.name == "StarRocks"
        assert starrocks.engine == "starrocks"
        assert starrocks.status == "active"
        assert starrocks.coordinates == {
            "hostname": "starrocks-fe-service", "port": 9030, "database_name": ""}
        assert starrocks.catalog is None
        assert starrocks.compute is None
        assert starrocks.credential_ref == "lakehouse_admin_password"

    def test_absent_collection_is_empty_not_an_error(self, missing_config, plaid_config):
        # A tenant that has not been republished has no collection. Not a failure.
        assert missing_config.lakehouses == []
        assert plaid_config.lakehouses == []

    def test_extra_keys_ignored(self, tmp_path, monkeypatch):
        # Same forward-compatibility as every other block: the control plane may add a field
        # before this library declares it.
        cfg = {"database": {"lakehouses": [{"id": "lh-1", "role": "primary"}]}}
        lakehouse, = _config_from(tmp_path, monkeypatch, cfg).lakehouses
        assert lakehouse.id == "lh-1"
        assert not hasattr(lakehouse, "role")

    @pytest.mark.usefixtures("fresh_warnings")
    def test_extra_keys_are_dropped_out_loud(self, tmp_path, monkeypatch, caplog):
        # Ignored is not the same as unnoticed. `disabled` and `superuser` went missing here
        # for a release because the filter discarded them without a word.
        cfg = {"database": {"lakehouses": [{"id": "lh-1", "role": "primary", "tier": "gold"}]}}
        with caplog.at_level(logging.WARNING, logger="plaidcloud.config.config"):
            assert _config_from(tmp_path, monkeypatch, cfg).lakehouses
        assert "lh-1" in caplog.text
        assert "role, tier" in caplog.text

    @pytest.mark.usefixtures("fresh_warnings")
    def test_the_warning_does_not_repeat_per_read(self, tmp_path, monkeypatch, caplog):
        # `lakehouses` is a PROPERTY and plaid re-reads it on every project resolution. A
        # warning that repeats per read floods exactly the rollout window it exists to report,
        # and a flood is as unreadable as silence.
        cfg = {"database": {"lakehouses": [{"id": "lh-1", "role": "primary"}]}}
        parsed = _config_from(tmp_path, monkeypatch, cfg)
        with caplog.at_level(logging.WARNING, logger="plaidcloud.config.config"):
            for _ in range(5):
                assert parsed.lakehouses
        assert caplog.text.count("lh-1") == 1

    @pytest.mark.usefixtures("fresh_warnings")
    def test_a_fully_declared_record_says_nothing(self, tmp_path, monkeypatch, caplog):
        # The warning has to be a signal, not a per-pod-start constant.
        with caplog.at_level(logging.WARNING, logger="plaidcloud.config.config"):
            assert _config_from(tmp_path, monkeypatch, CUSTOMER_LAKEHOUSE_CFG).lakehouses
        assert caplog.text == ""

    def test_parses_the_fields_cp_rest_emits_at_top_level(self, tmp_path, monkeypatch):
        # `build_customer_lakehouse` emits `disabled` and `superuser` beside the nested blocks.
        # Dropped, a disabled lakehouse reads as enabled and a DSN is built with no principal.
        lakehouse, = _config_from(tmp_path, monkeypatch, CUSTOMER_LAKEHOUSE_CFG).lakehouses
        assert lakehouse.disabled is True
        assert lakehouse.superuser == "SVC_PLAID"

    def test_disabled_defaults_to_false_when_absent(self, tmp_path, monkeypatch):
        # The provisioned record every tenant already carries does not stamp `disabled`, so the
        # zero value has to be the one that leaves that lakehouse usable.
        starrocks = _config_from(tmp_path, monkeypatch, LAKEHOUSE_CFG).lakehouses[1]
        assert starrocks.disabled is False
        assert starrocks.superuser == ""

    def test_credential_ref_is_a_key_name_not_a_credential(self, tmp_path, monkeypatch):
        # Nothing here resolves the ref, and no field carries a secret — the record is safe to
        # commit to the values file in Git, which is exactly where it comes from.
        lakehouses = _config_from(tmp_path, monkeypatch, LAKEHOUSE_CFG).lakehouses
        assert all(lakehouse.credential_ref == "lakehouse_admin_password" for lakehouse in lakehouses)
        assert "password" not in config_mod.LakehouseConfig._fields


class TestDefaultLakehouseId:

    def test_reads_the_id(self, tmp_path, monkeypatch):
        assert _config_from(tmp_path, monkeypatch, LAKEHOUSE_CFG).default_lakehouse_id == "lh-2222"

    def test_empty_when_absent(self, missing_config, plaid_config):
        assert missing_config.default_lakehouse_id == ""
        assert plaid_config.default_lakehouse_id == ""

    def test_is_not_the_first_lakehouse(self, tmp_path, monkeypatch):
        # A "first in the list" fallback is indistinguishable from a correct answer while a
        # tenant has one lakehouse, and silently wrong the moment it has two.
        cfg = {"database": {"lakehouses": [{"id": "lh-1"}, {"id": "lh-2"}]}}
        assert _config_from(tmp_path, monkeypatch, cfg).default_lakehouse_id == ""


class TestResolveLakehouse:
    """`resolve_lakehouse` — the connectable form of a lakehouse record.

    The contract under test is `plaid.core.data.orm.build_lakehouse_dsns`, which reads
    `system`, `superuser`, `hostname`, `port`, `database_name`, `query_params` and `password`
    off whatever it is handed, and `orm.lakehouse_fingerprint`, which iterates
    `DatabaseConfig._fields`.
    """

    def _resolve(self, tmp_path, monkeypatch, cfg, password="pw", **overrides):
        """Resolve the one lakehouse in `cfg` against that same config's `database:` block —
        the pairing production has, rather than a hand-built default."""
        parsed = _config_from(tmp_path, monkeypatch, cfg)
        lakehouse, = parsed.lakehouses
        return config_mod.resolve_lakehouse(
            lakehouse._replace(**overrides), parsed.database, password)

    # --- the record the fleet actually carries -----------------------------------------

    def test_a_minted_record_inherits_the_tenant_superuser(self, tmp_path, monkeypatch):
        # `mint_tenant_lakehouse` emits NO `superuser`. Resolving without a fallback yields a
        # blank principal and a DSN nothing can authenticate.
        resolved = self._resolve(tmp_path, monkeypatch, MINTED_LAKEHOUSE_CFG)
        assert resolved.superuser == "root"

    def test_a_minted_record_inherits_the_tenant_lakekeeper(self, tmp_path, monkeypatch):
        # `catalog: None` must NOT mean DatabaseConfig's class defaults: the class default
        # `http://lakekeeper:8181` names no Service in a tenant namespace, and
        # `_lakehouse_coordinate` reads a stamped lakehouse with no fallback to cfg.database.
        resolved = self._resolve(tmp_path, monkeypatch, MINTED_LAKEHOUSE_CFG)
        assert resolved.lakekeeper_url == "http://plaid-tenant-lakekeeper:8181"
        assert resolved.iceberg_catalog == "tenant_catalog"
        assert resolved.lakekeeper_warehouse == "tenant_wh"

    def test_a_minted_record_inherits_the_tenant_lakekeeper_token(self, tmp_path, monkeypatch):
        # `LakehouseCatalog` has no token field at all, so inheritance is the only source.
        resolved = self._resolve(tmp_path, monkeypatch, MINTED_LAKEHOUSE_CFG)
        assert resolved.lakekeeper_token == "tenant-token"

    def test_a_minted_record_resolves_while_provisioning(self, tmp_path, monkeypatch):
        # `create_tenant` mints `status='provisioning'` and only flips it when the tenant
        # reaches running, so bootstrap MUST be able to connect to build the warehouse.
        parsed = _config_from(tmp_path, monkeypatch, MINTED_LAKEHOUSE_CFG)
        assert parsed.lakehouses[0].status == "provisioning"
        assert self._resolve(tmp_path, monkeypatch, MINTED_LAKEHOUSE_CFG).hostname

    def test_a_minted_record_is_not_a_customer_lakehouse(self, tmp_path, monkeypatch):
        lakehouse, = _config_from(tmp_path, monkeypatch, MINTED_LAKEHOUSE_CFG).lakehouses
        assert config_mod.is_customer_lakehouse(lakehouse) is False

    # --- a customer record inherits nothing --------------------------------------------

    def test_a_customer_record_is_recognised(self, tmp_path, monkeypatch):
        lakehouse, = _config_from(tmp_path, monkeypatch, CUSTOMER_LAKEHOUSE_CFG).lakehouses
        assert config_mod.is_customer_lakehouse(lakehouse) is True

    @pytest.mark.parametrize("ref", [
        "lakehouse_admin_password",                     # the legacy provisioned key
        "lakehouse_user_alice_password",                # a per-user key, id would be 'user_alice'
        "lakehouse_lh-notrealhex_password",             # right prefix, wrong body
        "lakehouse_lh-0123456789ABCDEF0123456789ABCDEF_password",   # uppercase hex
        "lakehouse_lh-0123456789abcdef0123456789abcde_password",    # 31 hex, not 32
        f"lakehouse_{CUSTOMER_ID}_password ",           # trailing whitespace
        f"lakehouse_{CUSTOMER_ID}_password\n",          # trailing newline: `$` matches before it
        f"x lakehouse_{CUSTOMER_ID}_password",          # embedded, not the whole key
        "",
    ])
    def test_only_a_minted_credential_ref_is_a_customer_lakehouse(self, ref):
        # cp-rest calls this anchoring load-bearing: a loose `lakehouse_.*_password` also
        # matches the legacy shared key and every per-user key, which would flip the tenant's
        # own warehouse to "customer" and strip its inheritance.
        assert config_mod.is_customer_lakehouse(
            config_mod.LakehouseConfig(id="x", credential_ref=ref)) is False

    def test_the_credential_ref_pattern_is_cp_rests_verbatim(self):
        # This is a SECOND copy of `lakehouse_tools._CREDENTIAL_REF_RE` with no shared source,
        # and cp-rest documents the exact anchoring as load-bearing. Pinned as a string so any
        # edit here is deliberate and gets checked against the other copy — including edits
        # that are behaviourally equivalent under `fullmatch` and would otherwise slip through.
        pattern = getattr(config_mod, "_CUSTOMER_CREDENTIAL_REF")
        assert pattern.pattern == r'^lakehouse_lh-[0-9a-f]{32}_password$'
        assert pattern.flags & re.IGNORECASE == 0

    def test_a_customer_record_does_not_inherit_the_tenant_lakekeeper(self, tmp_path, monkeypatch):
        # Falling back to the tenant's own StarRocks coordinates for a warehouse PlaidCloud
        # does not run is the "answers for the wrong warehouse" failure.
        resolved = self._resolve(tmp_path, monkeypatch, CUSTOMER_LAKEHOUSE_CFG, disabled=False)
        assert resolved.lakekeeper_url != "http://plaid-tenant-lakekeeper:8181"
        assert resolved.lakekeeper_token == ""

    def test_a_customer_catalog_is_absent_not_a_fabricated_default(self, tmp_path, monkeypatch):
        # `catalog: None` is cp-rest's default and its only way to say "no catalog".
        # DatabaseConfig's class defaults are NOT that: `http://lakekeeper:8181` names a
        # Service that exists in no tenant namespace, so serving it here invents a coordinate.
        resolved = self._resolve(tmp_path, monkeypatch, CUSTOMER_LAKEHOUSE_CFG, disabled=False)
        assert resolved.lakekeeper_url == ""
        assert resolved.iceberg_catalog == ""
        assert resolved.lakekeeper_warehouse == ""

    def test_a_customer_snowflake_keeps_its_own_drivername(self, tmp_path, monkeypatch):
        # `system` selects the SQLAlchemy driver. The tenant default is 'starrocks' here, so
        # sourcing it from there instead of the record would build `starrocks://` against a
        # Snowflake account with nothing to show for it.
        parsed = _config_from(tmp_path, monkeypatch, CUSTOMER_LAKEHOUSE_CFG)
        assert parsed.database.system == "starrocks"
        resolved = self._resolve(tmp_path, monkeypatch, CUSTOMER_LAKEHOUSE_CFG, disabled=False)
        assert resolved.system == "snowflake"

    # --- Databricks: an engine that takes no configured principal ------------------------

    def test_a_databricks_record_needs_no_recorded_superuser(self, tmp_path, monkeypatch):
        # cp-rest's `_REQUIRED_CONNECTION_FIELDS['databricks']` is ('hostname', 'http_path').
        # Refusing a blank superuser here would refuse a shape the control plane accepts and
        # this story exists to support.
        resolved = self._resolve(tmp_path, monkeypatch, DATABRICKS_LAKEHOUSE_CFG)
        assert resolved.superuser == "token"

    def test_a_databricks_record_keeps_its_own_drivername(self, tmp_path, monkeypatch):
        resolved = self._resolve(tmp_path, monkeypatch, DATABRICKS_LAKEHOUSE_CFG)
        assert resolved.system == "databricks"
        assert resolved.hostname == "acme.cloud.databricks.com"

    def test_a_databricks_http_path_rides_query_params(self, tmp_path, monkeypatch):
        resolved = self._resolve(tmp_path, monkeypatch, DATABRICKS_LAKEHOUSE_CFG)
        assert resolved.query_params == {"http_path": "/sql/1.0/warehouses/abc123"}

    def test_the_engine_principal_beats_an_inherited_one(self, tmp_path, monkeypatch):
        # Precedence between the engine constant and inheritance is only observable when BOTH
        # are populated, which needs a Databricks record carrying the legacy (provisioned)
        # credential ref — reachable only by hand-editing a values file, but that is exactly
        # where a wrong answer would go unnoticed. There is no `root` account on a Databricks
        # warehouse, so the constant has to win.
        parsed = _config_from(tmp_path, monkeypatch, DATABRICKS_LAKEHOUSE_CFG)
        assert parsed.database.superuser == "root"
        lakehouse, = parsed.lakehouses
        hand_edited = lakehouse._replace(credential_ref="lakehouse_admin_password")
        assert config_mod.is_customer_lakehouse(hand_edited) is False
        resolved = config_mod.resolve_lakehouse(hand_edited, parsed.database, "pw")
        assert resolved.superuser == "token"

    def test_a_customer_snowflake_with_no_superuser_is_refused(self, tmp_path, monkeypatch):
        # Snowflake DOES require a principal (`_REQUIRED_CONNECTION_FIELDS`), and there is no
        # tenant principal that means anything on a warehouse the customer owns.
        with pytest.raises(ValueError, match="no connection principal"):
            self._resolve(tmp_path, monkeypatch, CUSTOMER_LAKEHOUSE_CFG,
                          disabled=False, superuser="")

    def test_a_customer_record_keeps_its_own_superuser(self, tmp_path, monkeypatch):
        resolved = self._resolve(tmp_path, monkeypatch, CUSTOMER_LAKEHOUSE_CFG, disabled=False)
        assert resolved.superuser == "SVC_PLAID"

    def test_a_recorded_superuser_beats_the_tenant_default(self, tmp_path, monkeypatch):
        # Precedence is only observable on a PROVISIONED record, where the tenant default is
        # populated too. Inheritance fills a gap; it does not override what the record says.
        parsed = _config_from(tmp_path, monkeypatch, MINTED_LAKEHOUSE_CFG)
        assert parsed.database.superuser == "root"
        resolved = self._resolve(tmp_path, monkeypatch, MINTED_LAKEHOUSE_CFG,
                                 superuser="recorded_admin")
        assert resolved.superuser == "recorded_admin"

    # --- the DSN contract ---------------------------------------------------------------

    def test_returns_a_database_config(self, tmp_path, monkeypatch):
        # The TYPE and not just the attributes: `lakehouse_fingerprint` builds the engine-cache
        # key from `DatabaseConfig._fields`, so a record of another type drops whatever it does
        # not declare out of the key and two lakehouses quietly share one engine.
        resolved = self._resolve(tmp_path, monkeypatch, MINTED_LAKEHOUSE_CFG)
        assert isinstance(resolved, DatabaseConfig)

    def test_every_field_build_lakehouse_dsns_reads(self, tmp_path, monkeypatch):
        resolved = self._resolve(tmp_path, monkeypatch, MINTED_LAKEHOUSE_CFG)
        assert resolved.system == "starrocks"
        assert resolved.superuser == "root"
        assert resolved.hostname == "starrocks-fe-service"
        assert resolved.port == 9030
        assert resolved.database_name == ""
        assert resolved.query_params == {}
        assert resolved.password == "pw"

    def test_carries_the_control_plane_id(self, tmp_path, monkeypatch):
        # plaid's `assigned_lakehouse_id` reads `lakehouse_id` off the record. Without it,
        # every member of a >1-lakehouse collection answers '' and every project binding fails
        # to resolve.
        assert self._resolve(tmp_path, monkeypatch, MINTED_LAKEHOUSE_CFG).lakehouse_id == "lh-mint"

    def test_the_password_comes_from_the_caller_not_the_record(self, tmp_path, monkeypatch):
        # `credential_ref` is a Vault key NAME. Nothing here resolves it, so the credential
        # cannot come from anywhere but the argument — not the record, not the tenant default.
        resolved = self._resolve(tmp_path, monkeypatch, MINTED_LAKEHOUSE_CFG,
                                 password="from-vault")
        assert resolved.password == "from-vault"

    def test_snowflake_coordinates_carry_no_port(self, tmp_path, monkeypatch):
        # A Snowflake account URL takes no port; `URL.create` accepts None and omits it.
        resolved = self._resolve(tmp_path, monkeypatch, CUSTOMER_LAKEHOUSE_CFG, disabled=False)
        assert resolved.port is None
        assert resolved.hostname == "acme-x1.snowflakecomputing.com"
        assert resolved.database_name == "PLAID_DATA"

    def test_a_null_database_name_does_not_become_the_string_none(self, tmp_path, monkeypatch):
        resolved = self._resolve(
            tmp_path, monkeypatch, MINTED_LAKEHOUSE_CFG,
            coordinates={"hostname": "h", "port": 1, "database_name": None})
        assert resolved.database_name == ""

    def test_compute_becomes_query_params(self, tmp_path, monkeypatch):
        # Snowflake selects compute with warehouse/role, Databricks with http_path; both ride
        # the DSN query string.
        resolved = self._resolve(tmp_path, monkeypatch, CUSTOMER_LAKEHOUSE_CFG, disabled=False)
        assert resolved.query_params == {"warehouse": "PLAID_WH", "role": "PLAID_ROLE"}

    def test_empty_compute_members_are_absent_not_blank(self, tmp_path, monkeypatch):
        # cp-rest's `missing_connection_fields` treats '' as absent. Forwarding it renders
        # `?role=`, which asks the vendor to assume a role named ''.
        resolved = self._resolve(
            tmp_path, monkeypatch, CUSTOMER_LAKEHOUSE_CFG, disabled=False,
            compute={"warehouse": "PLAID_WH", "role": "", "http_path": None})
        assert resolved.query_params == {"warehouse": "PLAID_WH"}

    def test_an_explicitly_empty_catalog_member_survives(self, tmp_path, monkeypatch):
        # An operator setting this to '' is saying "no Iceberg here". A truthiness filter
        # would discard that and substitute the tenant's catalog.
        resolved = self._resolve(
            tmp_path, monkeypatch, MINTED_LAKEHOUSE_CFG,
            catalog={"iceberg_catalog": "", "lakekeeper_url": "", "lakekeeper_warehouse": ""})
        assert resolved.iceberg_catalog == ""
        assert resolved.lakekeeper_url == ""

    def test_a_populated_catalog_wins(self, tmp_path, monkeypatch):
        resolved = self._resolve(
            tmp_path, monkeypatch, MINTED_LAKEHOUSE_CFG,
            catalog={"iceberg_catalog": "ice2", "lakekeeper_url": "http://lk-b:8181",
                     "lakekeeper_warehouse": "wh2"})
        assert resolved.iceberg_catalog == "ice2"
        assert resolved.lakekeeper_url == "http://lk-b:8181"
        assert resolved.lakekeeper_warehouse == "wh2"

    def test_a_partial_catalog_inherits_only_what_it_omits(self, tmp_path, monkeypatch):
        resolved = self._resolve(tmp_path, monkeypatch, MINTED_LAKEHOUSE_CFG,
                                 catalog={"iceberg_catalog": "ice2"})
        assert resolved.iceberg_catalog == "ice2"
        assert resolved.lakekeeper_url == "http://plaid-tenant-lakekeeper:8181"

    def test_cloud_url_is_never_per_lakehouse(self, tmp_path, monkeypatch):
        # One shared-Postgres catalog per tenant, read from `cfg.database` by
        # `orm.build_shared_dsns`. Neither the record nor the tenant default may seed it here:
        # both carry one in this fixture, and the resolved record must still be blank.
        parsed = _config_from(tmp_path, monkeypatch, MINTED_LAKEHOUSE_CFG)
        assert parsed.database.cloud_url
        resolved = self._resolve(
            tmp_path, monkeypatch, MINTED_LAKEHOUSE_CFG,
            coordinates={"hostname": "h", "port": 1, "database_name": "",
                         "cloud_url": "postgresql://sneaky/x"})
        assert resolved.cloud_url == ""

    # --- refusals -----------------------------------------------------------------------

    def test_a_disabled_lakehouse_is_refused(self, tmp_path, monkeypatch):
        # This is the only seam in this library where the flag can bite. Returning something
        # connectable here is what makes `disabled` decoration.
        with pytest.raises(ValueError, match=CUSTOMER_ID):
            self._resolve(tmp_path, monkeypatch, CUSTOMER_LAKEHOUSE_CFG)

    def test_a_retired_lakehouse_is_not_refused(self, tmp_path, monkeypatch):
        # `retired` stops NEW project bindings; the projects already there still read.
        resolved = self._resolve(tmp_path, monkeypatch, MINTED_LAKEHOUSE_CFG, status="retired")
        assert resolved.hostname == "starrocks-fe-service"

    def test_a_record_naming_no_host_is_refused(self, tmp_path, monkeypatch):
        # Otherwise this renders `starrocks://root:pw@/`, which fails as a connection error a
        # long way from the config that caused it.
        with pytest.raises(ValueError, match="names no warehouse"):
            self._resolve(tmp_path, monkeypatch, MINTED_LAKEHOUSE_CFG, coordinates={})

    def test_a_record_naming_no_engine_is_refused(self, tmp_path, monkeypatch):
        with pytest.raises(ValueError, match="names no warehouse"):
            self._resolve(tmp_path, monkeypatch, MINTED_LAKEHOUSE_CFG, engine="")

    def test_a_null_coordinates_block_is_refused(self, tmp_path, monkeypatch):
        with pytest.raises(ValueError, match="names no warehouse"):
            self._resolve(tmp_path, monkeypatch, MINTED_LAKEHOUSE_CFG, coordinates=None)

    def test_a_blank_hostname_is_refused(self, tmp_path, monkeypatch):
        # Whitespace is not a host. Unstripped it passes the emptiness check and renders
        # `starrocks://root:pw@%20%20%20:9030/`.
        with pytest.raises(ValueError, match="names no warehouse"):
            self._resolve(tmp_path, monkeypatch, MINTED_LAKEHOUSE_CFG,
                          coordinates={"hostname": "   ", "port": 9030, "database_name": ""})
