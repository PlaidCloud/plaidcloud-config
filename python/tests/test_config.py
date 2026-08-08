#!/usr/bin/env python
# coding=utf-8

__author__ = "Garrett Bates"
__copyright__ = "© Copyright 2020-2026, PlaidCloud, Inc"
__credits__ = ["Garrett Bates"]
__license__ = "Apache 2.0"
__maintainer__ = "Garrett Bates"
__email__ = "garrett@plaidcloud.com"

"""Tests for plaidcloud.config.config module."""
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
