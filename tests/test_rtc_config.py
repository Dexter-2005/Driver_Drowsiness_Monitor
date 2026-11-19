import unittest
from unittest.mock import patch, Mock

import requests
from src.rtc_config import build_rtc_configuration


class RelayTests(unittest.TestCase):
    def test_local_fallback_without_credentials(self):
        self.assertTrue(build_rtc_configuration()["iceServers"][0]["urls"][0].startswith("stun:"))

    def test_partial_configuration_rejected(self):
        with self.assertRaises(ValueError):
            build_rtc_configuration("key", "")

    @patch("src.rtc_config.requests.post")
    def test_short_lived_credentials_only_reach_client(self, post):
        servers = [{"urls": ["turns:relay:443"], "username": "temporary", "credential": "short-lived"}]
        post.return_value = Mock(json=Mock(return_value={"iceServers": servers}))
        config = build_rtc_configuration("key-id", "private-token")
        self.assertEqual(config, {"iceServers": servers})
        self.assertNotIn("private-token", str(config))
        self.assertEqual(post.call_args.kwargs["timeout"], 10)

    @patch("src.rtc_config.requests.post", side_effect=requests.RequestException("secret-response"))
    def test_failure_does_not_expose_provider_response(self, post):
        with self.assertRaises(RuntimeError) as error:
            build_rtc_configuration("key", "token")
        self.assertNotIn("secret-response", str(error.exception))

    @patch("src.rtc_config.requests.post")
    def test_invalid_provider_payload_rejected(self, post):
        post.return_value = Mock(json=Mock(return_value={"iceServers": []}))
        with self.assertRaises(RuntimeError):
            build_rtc_configuration("key", "token")
