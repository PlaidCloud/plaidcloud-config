"""Tests for plaidcloud.config.rabbitmq module."""
import pytest
from plaidcloud.config.rabbitmq import RMQConfig, RMQCredentials


# ---------------------------------------------------------------------------
# Full config
# ---------------------------------------------------------------------------

class TestRMQConfigFull:

    def test_all_fields(self):
        cfg = {
            "rabbitmq": {
                "hostname": "rmq.example.com",
                "port": 5673,
                "management_port": 15673,
                "master": {
                    "username": "master_u",
                    "password": "master_p",
                    "default_vhost": "/",
                },
                "private": {
                    "username": "private_u",
                    "password": "private_p",
                    "default_vhost": "plaidcloud",
                },
                "public": {
                    "username": "public_u",
                    "password": "public_p",
                    "default_vhost": "plaidcloud-public",
                },
            }
        }
        rmq = RMQConfig(cfg)
        assert rmq.hostname == "rmq.example.com"
        assert rmq.port == 5673
        assert rmq.management_port == 15673

    def test_master_credentials(self):
        cfg = {
            "rabbitmq": {
                "master": {"username": "m", "password": "mp", "default_vhost": "/"},
                "private": {"username": "p", "password": "pp", "default_vhost": "pv"},
                "public": {"username": "u", "password": "up", "default_vhost": "uv"},
            }
        }
        rmq = RMQConfig(cfg)
        assert isinstance(rmq.master, RMQCredentials)
        assert rmq.master.username == "m"
        assert rmq.master.password == "mp"
        assert rmq.master.default_vhost == "/"

    def test_private_credentials(self):
        cfg = {
            "rabbitmq": {
                "master": {"username": "m", "password": "mp", "default_vhost": "/"},
                "private": {"username": "priv", "password": "privp", "default_vhost": "pc"},
                "public": {"username": "u", "password": "up", "default_vhost": "uv"},
            }
        }
        rmq = RMQConfig(cfg)
        assert rmq.private.username == "priv"
        assert rmq.private.default_vhost == "pc"

    def test_public_credentials(self):
        cfg = {
            "rabbitmq": {
                "master": {"username": "m", "password": "mp", "default_vhost": "/"},
                "private": {"username": "p", "password": "pp", "default_vhost": "pv"},
                "public": {"username": "pub", "password": "pubp", "default_vhost": "pub-vhost"},
            }
        }
        rmq = RMQConfig(cfg)
        assert rmq.public.username == "pub"
        assert rmq.public.default_vhost == "pub-vhost"


# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------

class TestRMQConfigDefaults:

    def test_default_hostname(self):
        cfg = {
            "rabbitmq": {
                "master": {"username": "m", "password": "p", "default_vhost": "/"},
                "private": {"username": "p", "password": "pp", "default_vhost": "pv"},
                "public": {"username": "u", "password": "up", "default_vhost": "uv"},
            }
        }
        rmq = RMQConfig(cfg)
        assert rmq.hostname == "plaid-rabbitmq"

    def test_default_port(self):
        cfg = {
            "rabbitmq": {
                "master": {"username": "m", "password": "p", "default_vhost": "/"},
                "private": {"username": "p", "password": "pp", "default_vhost": "pv"},
                "public": {"username": "u", "password": "up", "default_vhost": "uv"},
            }
        }
        rmq = RMQConfig(cfg)
        assert rmq.port == 5672

    def test_default_management_port(self):
        cfg = {
            "rabbitmq": {
                "master": {"username": "m", "password": "p", "default_vhost": "/"},
                "private": {"username": "p", "password": "pp", "default_vhost": "pv"},
                "public": {"username": "u", "password": "up", "default_vhost": "uv"},
            }
        }
        rmq = RMQConfig(cfg)
        assert rmq.management_port == 15672


# ---------------------------------------------------------------------------
# Port type coercion
# ---------------------------------------------------------------------------

class TestRMQConfigPortCoercion:

    def test_string_port_coerced_to_int(self):
        cfg = {
            "rabbitmq": {
                "port": "5673",
                "management_port": "15673",
                "master": {"username": "m", "password": "p", "default_vhost": "/"},
                "private": {"username": "p", "password": "pp", "default_vhost": "pv"},
                "public": {"username": "u", "password": "up", "default_vhost": "uv"},
            }
        }
        rmq = RMQConfig(cfg)
        assert rmq.port == 5673
        assert isinstance(rmq.port, int)
        assert rmq.management_port == 15673
        assert isinstance(rmq.management_port, int)


# ---------------------------------------------------------------------------
# RMQCredentials NamedTuple
# ---------------------------------------------------------------------------

class TestRMQCredentials:

    def test_fields(self):
        cred = RMQCredentials(username="u", password="p", default_vhost="/")
        assert cred.username == "u"
        assert cred.password == "p"
        assert cred.default_vhost == "/"

    def test_is_namedtuple(self):
        cred = RMQCredentials(username="u", password="p", default_vhost="/")
        assert hasattr(cred, "_fields")
        assert set(cred._fields) == {"username", "password", "default_vhost"}


# ---------------------------------------------------------------------------
# Missing rabbitmq section
# ---------------------------------------------------------------------------

class TestRMQConfigMissing:

    def test_no_rabbitmq_section_raises(self):
        """When there's no rabbitmq section, constructing RMQConfig raises
        because RMQCredentials has required fields with no defaults."""
        with pytest.raises(TypeError):
            RMQConfig({})
