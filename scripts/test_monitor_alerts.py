"""Linux incident-state tests; no real credentials, messages or production requests."""

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import deploy_tools as tools
import monitor_alerts as alerts
import monitor_production as monitor


class AlertsTest(unittest.TestCase):
    def test_failure_duplicate_and_recovery(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(alerts, "send") as send:
            state = Path(tmp)
            self.assertFalse(alerts.transition(state, True, []))
            self.assertTrue(alerts.transition(state, False, ["readiness"]))
            self.assertFalse(alerts.transition(state, False, ["different failure"]))
            self.assertTrue(alerts.transition(state, True, []))
            self.assertFalse(alerts.transition(state, True, []))
            self.assertEqual(send.call_count, 2)
            self.assertIn("FAILURE", send.call_args_list[0].args[0])
            self.assertIn("RECOVERED", send.call_args_list[1].args[0])

    def test_delivery_failure_retries_without_marking_sent(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp)
            with mock.patch.object(alerts, "send", side_effect=alerts.AlertError("failed")):
                with self.assertRaises(alerts.AlertError):
                    alerts.transition(state, False, ["ready"])
            self.assertFalse((state / "incident.json").exists())
            with mock.patch.object(alerts, "send") as send:
                alerts.transition(state, False, ["ready"])
                self.assertEqual(send.call_count, 1)
            with mock.patch.object(alerts, "send", side_effect=alerts.AlertError("failed")):
                with self.assertRaises(alerts.AlertError):
                    alerts.transition(state, True, [])
            self.assertTrue(json.loads((state / "incident.json").read_text())["unhealthy"])

    def test_token_not_in_exception(self):
        with mock.patch.dict(os.environ, {"BOT_TOKEN": "never-print-this", "CHAT_ID": "-1"}), \
                mock.patch.object(alerts.urllib.request, "urlopen", side_effect=OSError("never-print-this")):
            with self.assertRaises(alerts.AlertError) as caught:
                alerts.send("test")
            self.assertNotIn("never-print-this", str(caught.exception))

    def test_test_events_are_labelled(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(alerts, "send") as send:
            alerts.transition(Path(tmp), False, ["synthetic"], test=True)
            alerts.transition(Path(tmp), True, [], test=True)
            self.assertTrue(all(call.args[0].startswith("[TEST]") for call in send.call_args_list))

    def test_collection_error_is_retried(self):
        with mock.patch.object(monitor, "collect", side_effect=OSError("secret")) as collect:
            sleep = mock.Mock()
            ok, checks, used = monitor.monitor("local", "unused", Path("unused"), 3, 60, sleep=sleep)
            self.assertFalse(ok)
            self.assertEqual((collect.call_count, sleep.call_count, used), (3, 2, 3))
            self.assertNotIn("secret", checks[0].detail)

    def test_monitor_notifies_only_after_retries(self):
        failed = [tools.Check("readiness", False, "down")]
        with mock.patch.object(monitor, "collect", return_value=failed) as collect, \
                mock.patch.object(monitor.time, "sleep"), \
                mock.patch.object(alerts, "transition") as transition, \
                contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(monitor.main(["--attempts", "3", "--interval", "0", "--telegram-state", "/unused"]), 1)
            self.assertEqual(collect.call_count, 3)
            transition.assert_called_once_with(Path("/unused"), False, ["readiness"])


if __name__ == "__main__":
    unittest.main()
