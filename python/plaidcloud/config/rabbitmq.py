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

class RMQCredentials(NamedTuple):
    """Connection settings for a RabbitMQ instance."""
    username: str
    password: str
    default_vhost: str

class RMQConfig():
    def __init__(self, cfg):
        self.cfg = cfg.get("rabbitmq", {})
        self.hostname: str = self.cfg.get("hostname", "plaid-rabbitmq")
        self.port: int = int(self.cfg.get("port", 5672))
        self.master: RMQCredentials =  RMQCredentials(**self.cfg.get("master", {}))
        self.private: RMQCredentials = RMQCredentials(**self.cfg.get("private", {}))
        self.public: RMQCredentials = RMQCredentials(**self.cfg.get("public", {}))
