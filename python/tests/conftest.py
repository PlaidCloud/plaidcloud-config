#!/usr/bin/env python
# coding=utf-8

__author__ = "Garrett Bates"
__copyright__ = "© Copyright 2020-2026, PlaidCloud, Inc"
__credits__ = ["Garrett Bates"]
__license__ = "Apache 2.0"
__maintainer__ = "Garrett Bates"
__email__ = "garrett@plaidcloud.com"

import sys
import pytest
import yaml


SAMPLE_CONFIG = {
    "database": {
        "hostname": "db-host",
        "port": 5432,
        "superuser": "admin",
        "password": "secret",
        "system": "postgresql",
        "database_name": "mydb",
        "query_params": {"sslmode": "require"},
        "cloud_url": "https://cloud.example.com",
        "iceberg_catalog": "my_catalog",
        "lakekeeper_url": "http://lakekeeper:8181",
        "lakekeeper_warehouse": "wh1",
        "lakekeeper_token": "tok123",
    },
    "environment": {
        "hostname": "app.example.com",
        "hostnames": ["app.example.com", "app2.example.com"],
        "designation": "staging",
        "tempdir": "/var/tmp",
        "verify_ssl": True,
        "workflow_image": "plaid/workflow:latest",
    },
    "features": {
        "async_copy": False,
        "backward_compatible_state": False,
        "decrypted_accounts": False,
        "enable_cors": True,
        "fast_clean_csv": False,
        "flashback": False,
        "google_login": False,
        "table_update_recreate": False,
        "use_numeric_cast": False,
    },
    "keycloak": {
        "url": "https://auth.example.com",
        "host": "auth.example.com",
        "realm": "TestRealm",
        "client_name": "test-client",
        "admin_id": "admin",
        "admin_secret": "adminsecret",
        "realm_admin_id": "realm-admin",
        "realm_secret": "realmsecret",
        "keycloak_issuer": "https://auth.example.com/realms/TestRealm",
        "db_url": "postgresql://keycloak:5432/keycloak",
    },
    "tenant": {
        "github_token": "ghp_test",
        "github_repo": "PlaidCloud/test",
        "github_branch": "main",
        "id": "tenant-1",
        "version": "1.0.0",
        "name": "Test Tenant",
        "memo": "test memo",
        "init_mode": "standard",
        "workspace_id": "ws-1",
        "cloud_id": 42,
        "apps": ["app1", "app2"],
        "services": {"svc1": "http://svc1"},
        "google": {"project": "gcp-proj"},
        "aws": {"region": "us-east-1"},
        "azure": {"subscription": "sub-1"},
        "private_cloud": {},
        "use_proxy_download": True,
        "source_tenant": "src-tenant",
        "source_url": "https://source.example.com",
        "source_client_id": "src-id",
        "source_client_secret": "src-secret",
        "app_logo_url": "logo.png",
        "splash_screen_logo_url": "splash.png",
        "superset_logo_url": "superset.png",
    },
    "services": {
        "auth": "http://auth:8080",
        "client": "http://client:8080",
        "cron": "http://cron:8080",
        "data_explorer": "http://data-explorer:8080",
        "docs": "http://docs:8080",
        "flashback": "http://flashback:8080/rpc",
        "monitor": "http://monitor:8080",
        "plaidxl": "http://plaidxl:8080",
        "rpc": "http://rpc:8080/json-rpc",
        "superset": "http://superset:8080",
        "workflow": "http://workflow:8080",
    },
    "opensearch": {
        "host": "opensearch.example.com",
        "username": "osuser",
        "password": "ospass",
        "port": 9201,
    },
    "superset": {
        "username": "superset_admin",
        "password": "superset_pass",
        "db_url": "postgresql://superset:5432/superset",
        "use_events_handler": False,
    },
    "ai_chat_history": {
        "langchain_db_url": "postgresql://langchain:5432/langchain",
        "conversation_db_url": "postgresql://conv:5432/conv",
        "username": "chatuser",
        "password": "chatpass",
        "grok_api_key": "grok-api-secret",
        "openai_api_key": "openapi-secret"
    },
    "loki": {
        "host": "loki.example.com",
        "username": "lokiadmin",
        "password": "lokipass",
        "port": 3200,
    },
    "postgres": {
        "backups": {"enabled": True},
        "restore": {"latest": True},
        "credentials": {"user": "pg", "password": "pgpass"},
    },
    "oauth": {
        "quickbooks": {
            "client_id": "qb-id",
            "client_secret": "qb-secret",
        },
        "paycor": {
            "client_id": "pc-id",
            "client_secret": "pc-secret",
        },
    },
    "plaidcloud-global": {
        "client_id": "global-id",
        "client_secret": "global-secret",
        "url": "https://global.example.com",
        "db_host": "global-db",
    },
    "rabbitmq": {
        "hostname": "rmq-host",
        "port": 5673,
        "management_port": 15673,
        "master": {
            "username": "master_user",
            "password": "master_pass",
            "default_vhost": "/",
        },
        "private": {
            "username": "private_user",
            "password": "private_pass",
            "default_vhost": "plaidcloud",
        },
        "public": {
            "username": "public_user",
            "password": "public_pass",
            "default_vhost": "plaidcloud-public",
        },
    },
    "redis": {
        "socket_timeout": 1,
        "urls": [
            {"session": "redis://plaid-redis-master/0"},
            {"cron_jobs": "redis://plaid-redis-master/1"},
        ],
    },
    "stripe": {
        "api_key": "sk_test_123",
        "webhook_secret": "whsec_test_456",
    },
    "email": {
        "postmark_server_token": "pmk-server-token",
        "postmark_server_id": "pmk-server-id",
        "sender": "no-reply@example.com",
    },
    "vault": {
        "enabled": True,
        "url": "http://vault:8200",
        "token": "vault-token",
        "mount_point": "kv",
        "tenant_path_prefix": "tenants",
        "global_path": "global",
    },
}


def _get_config_module():
    """Get the actual config module, bypassing __init__.py's 'from .config import config'
    which shadows the submodule name with the PlaidConfig singleton."""
    # Force import of the submodule
    import plaidcloud.config.config  # noqa: F811
    return sys.modules['plaidcloud.config.config']


@pytest.fixture
def config_file(tmp_path):
    """Write SAMPLE_CONFIG to a temp YAML file and return the path."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(SAMPLE_CONFIG, default_flow_style=False))
    return str(config_path)


@pytest.fixture
def plaid_config(config_file, monkeypatch):
    """Return a PlaidConfig loaded from the sample config file."""
    config_mod = _get_config_module()
    monkeypatch.setattr(config_mod, "CONFIG_PATH", config_file)
    return config_mod.PlaidConfig()


@pytest.fixture
def empty_config(tmp_path, monkeypatch):
    """Return a PlaidConfig loaded from an empty config file."""
    config_path = tmp_path / "empty.yaml"
    config_path.write_text("")
    config_mod = _get_config_module()
    monkeypatch.setattr(config_mod, "CONFIG_PATH", str(config_path))
    return config_mod.PlaidConfig()


@pytest.fixture
def missing_config(monkeypatch):
    """Return a PlaidConfig when no config file exists."""
    config_mod = _get_config_module()
    monkeypatch.setattr(config_mod, "CONFIG_PATH", "/nonexistent/path/config.yaml")
    return config_mod.PlaidConfig()
