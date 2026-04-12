"""Tests for plaidcloud.config.redis module."""
import pytest
from plaidcloud.config.redis import RedisConfig, ParsedRedisURL


# ---------------------------------------------------------------------------
# Helper to build a RedisConfig from inline URL data
# ---------------------------------------------------------------------------

def make_redis_config(urls):
    """Build a RedisConfig from a list of {name: url} dicts."""
    cfg = {"redis": {"urls": urls}}
    return RedisConfig(cfg)


# ---------------------------------------------------------------------------
# Standard redis:// URLs
# ---------------------------------------------------------------------------

class TestStandardRedisURL:

    def test_basic_url(self):
        rc = RedisConfig({})
        result = rc.parse_url("redis://plaid-redis-master:6379/0")
        assert result.hosts == [("plaid-redis-master", 6379)]
        assert result.password is None
        assert result.database == 0
        assert result.sentinel is False
        assert result.cluster is False
        assert result.master is True
        assert result.headless is False

    def test_url_with_db_number(self):
        rc = RedisConfig({})
        result = rc.parse_url("redis://host:6379/5")
        assert result.database == 5

    def test_url_without_port(self):
        rc = RedisConfig({})
        result = rc.parse_url("redis://myhost/3")
        assert result.hosts == [("myhost", 6379)]
        assert result.database == 3

    def test_url_with_password(self):
        rc = RedisConfig({})
        result = rc.parse_url("redis://user:mypassword@host:6379/0")
        assert result.password == "mypassword"

    def test_url_with_password_no_user(self):
        rc = RedisConfig({})
        result = rc.parse_url("redis://:secretpass@host:6379/0")
        assert result.password == "secretpass"

    def test_url_no_db_defaults_to_zero(self):
        rc = RedisConfig({})
        result = rc.parse_url("redis://host:6379")
        assert result.database == 0

    def test_default_socket_timeout(self):
        rc = RedisConfig({})
        result = rc.parse_url("redis://host:6379/0")
        assert result.socket_timeout == 1


# ---------------------------------------------------------------------------
# Sentinel URLs
# ---------------------------------------------------------------------------

class TestSentinelURL:

    def test_redis_sentinel_scheme(self):
        rc = RedisConfig({})
        result = rc.parse_url("redis+sentinel://host:26379/mymaster/0")
        assert result.sentinel is True
        assert result.service_name == "mymaster"
        assert result.database == 0
        assert result.hosts == [("host", 26379)]

    def test_sentinel_scheme(self):
        rc = RedisConfig({})
        result = rc.parse_url("sentinel://host:26379/mymaster/1")
        assert result.sentinel is True
        assert result.service_name == "mymaster"
        assert result.database == 1

    def test_sentinel_with_password(self):
        rc = RedisConfig({})
        result = rc.parse_url("sentinel://mypass@host:26379/mymaster/0")
        assert result.password == "mypass"
        assert result.sentinel is True

    def test_sentinel_multiple_hosts(self):
        rc = RedisConfig({})
        result = rc.parse_url("sentinel://pass@host1:26379,host2:26380/mymaster/1")
        assert result.hosts == [("host1", 26379), ("host2", 26380)]
        assert result.service_name == "mymaster"

    def test_sentinel_with_query_service_name(self):
        rc = RedisConfig({})
        result = rc.parse_url("sentinel://host:26379/0?service_name=mymaster")
        assert result.sentinel is True
        assert result.service_name == "mymaster"

    def test_sentinel_default_port(self):
        rc = RedisConfig({})
        result = rc.parse_url("sentinel://host/mymaster/0")
        assert result.hosts == [("host", 26379)]

    def test_sentinel_missing_service_name_raises(self):
        rc = RedisConfig({})
        with pytest.raises(ValueError, match="service name"):
            rc.parse_url("sentinel://host:26379/0")

    def test_sentinel_with_socket_timeout_and_quorum(self):
        rc = RedisConfig({})
        result = rc.parse_url(
            "sentinel://pass@host1,host2:26380/1?service_name=goof&socket_timeout=2.5&quorum=2"
        )
        assert result.socket_timeout == 2.5
        assert result.quorum == 2
        assert result.service_name == "goof"


# ---------------------------------------------------------------------------
# Headless Sentinel URLs
# ---------------------------------------------------------------------------

class TestHeadlessSentinelURL:

    def test_headless_sentinel(self):
        rc = RedisConfig({})
        result = rc.parse_url(
            "sentinel+headless://pass@headless_host:26379/1?service_name=goof&socket_timeout=2.5&quorum=2"
        )
        assert result.headless is True
        assert result.sentinel is True
        assert result.service_name == "goof"
        assert result.quorum == 2


# ---------------------------------------------------------------------------
# Redis Cluster URLs
# ---------------------------------------------------------------------------

class TestRedisClusterURL:

    def test_cluster_url(self):
        rc = RedisConfig({})
        result = rc.parse_url("redis-cluster://host:6379")
        assert result.cluster is True
        assert result.sentinel is False
        assert result.hosts == [("host", 6379)]

    def test_cluster_with_password(self):
        rc = RedisConfig({})
        result = rc.parse_url("redis-cluster://user:clusterpass@host:6379")
        assert result.password == "clusterpass"
        assert result.cluster is True


# ---------------------------------------------------------------------------
# Unsupported schemes
# ---------------------------------------------------------------------------

class TestUnsupportedScheme:

    def test_unsupported_scheme_raises(self):
        rc = RedisConfig({})
        with pytest.raises(ValueError, match="Unsupported scheme"):
            rc.parse_url("http://host:6379/0")

    def test_ftp_scheme_raises(self):
        rc = RedisConfig({})
        with pytest.raises(ValueError, match="Unsupported scheme"):
            rc.parse_url("ftp://host:6379/0")


# ---------------------------------------------------------------------------
# Client type
# ---------------------------------------------------------------------------

class TestClientType:

    def test_master_client(self):
        rc = RedisConfig({})
        result = rc.parse_url("redis://host:6379/0?client_type=master")
        assert result.master is True

    def test_slave_client(self):
        rc = RedisConfig({})
        result = rc.parse_url("redis://host:6379/0?client_type=slave")
        assert result.master is False

    def test_invalid_client_type_raises(self):
        rc = RedisConfig({})
        with pytest.raises(ValueError, match="got 'invalid'"):
            rc.parse_url("redis://host:6379/0?client_type=invalid")


# ---------------------------------------------------------------------------
# Query string options
# ---------------------------------------------------------------------------

class TestQueryStringOptions:

    def test_db_from_query_string(self):
        rc = RedisConfig({})
        result = rc.parse_url("redis://host:6379?db=7")
        assert result.database == 7

    def test_socket_timeout_from_query(self):
        rc = RedisConfig({})
        result = rc.parse_url("redis://host:6379/0?socket_timeout=5.0")
        assert result.socket_timeout == 5.0

    def test_unknown_query_param_ignored(self):
        rc = RedisConfig({})
        result = rc.parse_url("redis://host:6379/0?unknown_param=value")
        assert result.database == 0  # Still works, unknown param is ignored


# ---------------------------------------------------------------------------
# RedisConfig.get_url
# ---------------------------------------------------------------------------

class TestRedisConfigGetUrl:

    def test_get_url_by_name(self):
        rc = make_redis_config([
            {"session": "redis://host:6379/0"},
            {"cache": "redis://host:6379/1"},
        ])
        result = rc.get_url("session")
        assert result.database == 0

        result = rc.get_url("cache")
        assert result.database == 1

    def test_get_url_missing_raises(self):
        rc = make_redis_config([{"session": "redis://host:6379/0"}])
        with pytest.raises(KeyError):
            rc.get_url("nonexistent")


# ---------------------------------------------------------------------------
# RedisConfig URL flattening
# ---------------------------------------------------------------------------

class TestRedisConfigURLFlattening:

    def test_urls_flattened_from_list_of_dicts(self):
        rc = make_redis_config([
            {"url1": "redis://host/0"},
            {"url2": "redis://host/1"},
            {"url3": "redis://host/2"},
        ])
        assert len(rc.urls) == 3
        assert "url1" in rc.urls
        assert "url2" in rc.urls
        assert "url3" in rc.urls

    def test_empty_urls(self):
        rc = RedisConfig({"redis": {}})
        assert rc.urls == {}

    def test_no_redis_section(self):
        rc = RedisConfig({})
        assert rc.urls == {}
