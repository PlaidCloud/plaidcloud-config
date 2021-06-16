#!/usr/bin/env python
# coding=utf-8

__author__ = "Garrett Bates"
__copyright__ = "© Copyright 2020-2021, Tartan Solutions, Inc"
__credits__ = ["Garrett Bates"]
__license__ = "Apache 2.0"
__version__ = "0.1.9"
__maintainer__ = "Garrett Bates"
__email__ = "garrett.bates@tartansolutions.com"
__status__ = "Development"

from typing import List, Tuple, NamedTuple
from urllib import parse as urlparse

# "redis://plaid-redis-master:6379/0"
# "redis://elaborate_password:plaid-redis-master:6379/0"
# "redis+sentinel://plaid-redis-master:6379/plaid/0"
# "redis+sentinel://elaborate_password:plaid-redis-master:6379/plaid/0"
# "sentinel://plaid-redis-master:6379/plaid/0"
# "sentinel://elaborate_password@plaid-redis-master:6379/plaid/0"
# "sentinel://elaborate_password@plaid-redis-master,different-host:6380/1?name=goof&socket_timeout=2.5"

class ParsedRedisURL(NamedTuple):
    hosts: List[Tuple[str, int]]
    password: str
    socket_timeout: int 
    master: bool
    sentinel: bool
    service_name: str
    database: int = 0
    # options: 


class RedisConfig():

    def __init__(self, cfg):
        self.cfg = cfg.get('redis', {})
        # YAML spec has dynamic content specified as lists, so flatten list of KV pairs into a single dict.
        self.urls = {k: v for d in self.cfg.get('urls', []) for k, v in d.items()}


    def get_url(self, url) -> ParsedRedisURL:
        return self.parse_url(self.urls[url])


    def parse_url(self, url) -> ParsedRedisURL:
        if isinstance(url, str):
            url = urlparse.urlparse(url)

        def is_sentinel(scheme):
            return url.scheme == 'redis+sentinel' or url.scheme == 'sentinel'

        if url.scheme != 'redis' and not is_sentinel(url.scheme):
            raise ValueError('Unsupported scheme: {}'.format(url.scheme))

        def parse_host(s):
            if ':' in s:
                host, port = s.split(':', 1)
                port = int(port)
            else:
                host = s
                port = 26379 if is_sentinel(url.scheme) else 6379
            return host, port

        if '@' in url.netloc:
            auth, hostspec = url.netloc.split('@', 1)
        else:
            auth = None
            hostspec = url.netloc

        if auth and ':' in auth:
            _, password = auth.split(':', 1)
        elif auth:
            password = auth
        else:
            password = None

        hosts = [parse_host(s) for s in hostspec.split(',')]

        query_string_options = {
            'db': int,
            'service_name': str,
            'client_type': str,
            'socket_timeout': float,
            'socket_connect_timeout': float,
        }
        options = {}

        for name, value in urlparse.parse_qs(url.query).items():
            if name in query_string_options:
                option_type = query_string_options[name]
                # Query string param may be defined multiple times, or with multiple values, so pick the last entry
                options[name] = option_type(value[-1])

        path = url.path
        if path.startswith('/'):
            path = path[1:]
        if path == '':
            path_parts = []
        else:
            # Remove empty strings for non-sentinel paths, like '/0'
            path_parts = [part for part in path.split('/') if part]

        if 'service_name' in options:
            service_name = options.pop('service_name')
        elif len(path_parts) >= 2:
            service_name = path_parts[0]
        else:
            service_name = None

        if is_sentinel(url.scheme) and not service_name:
            raise ValueError("Sentinel URL has no service name specified. Please add it to the URL's path.")

        client_type = options.pop('client_type', 'master')
        if client_type not in ('master', 'slave'):
            raise ValueError('Client type must be either master or slave, got {!r}')

        db = 0
        if 'db' not in options:
            if len(path_parts) >= 2:
                db = int(path_parts[1])
            elif len(path_parts) == 1:
                db = int(path_parts[0])

        return ParsedRedisURL(
            hosts=hosts,
            password=password,
            socket_timeout=options.get("socket_timeout", 1),
            sentinel=is_sentinel(url.scheme),
            master=(client_type == "master"),
            service_name=service_name,
            database=db,
        )
