# -*- coding: utf-8 -*-
"""Tests for schedule API endpoints."""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from api.app import create_app


def _make_client():
    temp_dir = tempfile.TemporaryDirectory()
    return temp_dir, TestClient(create_app(static_dir=Path(temp_dir.name)))


class ScheduleStatusEndpointTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._temp_dir, cls.client = _make_client()

    @classmethod
    def tearDownClass(cls):
        cls._temp_dir.cleanup()

    @patch("api.v1.endpoints.schedule.ScheduledTaskLogRepository")
    def test_get_schedule_status_returns_200(self, MockRepo):
        mock_repo = MagicMock()
        MockRepo.return_value = mock_repo
        mock_repo.get_recent.return_value = []

        resp = self.client.get("/api/v1/schedule/status")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("recent_logs", body)
        self.assertIn("next_runs", body)
        self.assertIn("health", body)

    @patch("api.v1.endpoints.schedule.ScheduledTaskLogRepository")
    def test_get_schedule_status_with_logs(self, MockRepo):
        mock_repo = MagicMock()
        MockRepo.return_value = mock_repo
        mock_entry = MagicMock()
        mock_entry.to_dict.return_value = {
            "id": 1,
            "task_name": "watchlist_analysis",
            "status": "success",
        }
        mock_repo.get_recent.return_value = [mock_entry]

        resp = self.client.get("/api/v1/schedule/status")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(len(body["recent_logs"]), 1)
        self.assertEqual(body["recent_logs"][0]["task_name"], "watchlist_analysis")


class ScheduleTriggerEndpointTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._temp_dir, cls.client = _make_client()

    @classmethod
    def tearDownClass(cls):
        cls._temp_dir.cleanup()

    @patch("src.core.scheduled_task_lock.acquire_task_lock")
    @patch("src.core.scheduled_task_lock.release_task_lock")
    @patch("api.v1.endpoints.schedule.get_task_queue")
    def test_trigger_watchlist_returns_202_with_task_id(
        self, mock_get_queue, mock_release, mock_acquire
    ):
        mock_acquire.return_value = MagicMock()
        mock_task = MagicMock()
        mock_task.task_id = "abc123"
        mock_task.trace_id = "abc123"
        mock_get_queue.return_value.submit_background_task.return_value = mock_task

        resp = self.client.post(
            "/api/v1/schedule/trigger",
            json={"task": "watchlist"},
        )
        self.assertEqual(resp.status_code, 202)
        body = resp.json()
        self.assertEqual(body["task"], "watchlist")
        self.assertEqual(body["task_id"], "abc123")
        self.assertEqual(body["status"], "accepted")
        mock_get_queue.return_value.submit_background_task.assert_called_once()
        # The lock stays held by the background task; released on submit failure only.
        mock_release.assert_not_called()

    @patch("src.core.market_review_lock.try_acquire_market_review_lock")
    @patch("src.core.market_review_lock.release_market_review_lock")
    @patch("api.v1.endpoints.schedule.get_task_queue")
    def test_trigger_market_review_returns_202(
        self, mock_get_queue, mock_release, mock_acquire
    ):
        mock_acquire.return_value = MagicMock()
        mock_task = MagicMock()
        mock_task.task_id = "def456"
        mock_task.trace_id = "def456"
        mock_get_queue.return_value.submit_background_task.return_value = mock_task

        resp = self.client.post(
            "/api/v1/schedule/trigger",
            json={"task": "market_review"},
        )
        self.assertEqual(resp.status_code, 202)
        body = resp.json()
        self.assertEqual(body["task"], "market_review")
        self.assertEqual(body["task_id"], "def456")
        mock_release.assert_not_called()

    @patch("src.core.scheduled_task_lock.acquire_task_lock")
    @patch("src.core.scheduled_task_lock.release_task_lock")
    @patch("api.v1.endpoints.schedule.get_task_queue")
    def test_trigger_submit_failure_releases_lock(
        self, mock_get_queue, mock_release, mock_acquire
    ):
        mock_acquire.return_value = MagicMock()
        mock_get_queue.return_value.submit_background_task.side_effect = RuntimeError(
            "queue full"
        )

        client = TestClient(
            self.client.app, raise_server_exceptions=False
        )
        resp = client.post(
            "/api/v1/schedule/trigger",
            json={"task": "watchlist"},
        )
        self.assertEqual(resp.status_code, 500)
        mock_release.assert_called_once()

    def test_trigger_invalid_task(self):
        resp = self.client.post(
            "/api/v1/schedule/trigger",
            json={"task": "invalid_task"},
        )
        self.assertEqual(resp.status_code, 400)

    @patch("src.core.scheduled_task_lock.acquire_task_lock")
    def test_trigger_duplicate_task(self, mock_acquire):
        mock_acquire.return_value = None
        resp = self.client.post(
            "/api/v1/schedule/trigger",
            json={"task": "watchlist"},
        )
        self.assertEqual(resp.status_code, 409)

    @patch("src.core.market_review_lock.try_acquire_market_review_lock")
    def test_trigger_duplicate_market_review(self, mock_acquire):
        mock_acquire.return_value = None
        resp = self.client.post(
            "/api/v1/schedule/trigger",
            json={"task": "market_review"},
        )
        self.assertEqual(resp.status_code, 409)

    @patch("api.v1.endpoints.schedule._run_watchlist_task")
    @patch("api.v1.endpoints.schedule.ScheduledTaskLogRepository")
    @patch("src.core.scheduled_task_lock.release_task_lock")
    def test_watchlist_background_wrapper_writes_task_log(
        self, mock_release, MockRepo, mock_run
    ):
        from api.v1.endpoints.schedule import _run_watchlist_background

        mock_repo = MagicMock()
        MockRepo.return_value = mock_repo

        _run_watchlist_background(MagicMock(), MagicMock())

        statuses = [c.kwargs["status"] for c in mock_repo.save.call_args_list]
        self.assertEqual(statuses, ["running", "success"])
        mock_run.assert_called_once()
        mock_release.assert_called_once()

    @patch("api.v1.endpoints.schedule._run_watchlist_task")
    @patch("api.v1.endpoints.schedule.ScheduledTaskLogRepository")
    @patch("src.core.scheduled_task_lock.release_task_lock")
    def test_watchlist_background_wrapper_logs_failure(
        self, mock_release, MockRepo, mock_run
    ):
        from api.v1.endpoints.schedule import _run_watchlist_background

        mock_run.side_effect = RuntimeError("boom")
        mock_repo = MagicMock()
        MockRepo.return_value = mock_repo

        _run_watchlist_background(MagicMock(), MagicMock())

        statuses = [c.kwargs["status"] for c in mock_repo.save.call_args_list]
        self.assertEqual(statuses, ["running", "failed"])
        mock_release.assert_called_once()


class ScheduleLogsEndpointTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._temp_dir, cls.client = _make_client()

    @classmethod
    def tearDownClass(cls):
        cls._temp_dir.cleanup()

    @patch("api.v1.endpoints.schedule.ScheduledTaskLogRepository")
    def test_get_logs_returns_200(self, MockRepo):
        mock_repo = MagicMock()
        MockRepo.return_value = mock_repo
        mock_repo.get_recent.return_value = []

        resp = self.client.get("/api/v1/schedule/logs")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertIn("total", body)
        self.assertIn("logs", body)

    @patch("api.v1.endpoints.schedule.ScheduledTaskLogRepository")
    def test_get_logs_pagination(self, MockRepo):
        mock_repo = MagicMock()
        MockRepo.return_value = mock_repo
        mock_repo.get_recent.return_value = []

        resp = self.client.get("/api/v1/schedule/logs?page=2&page_size=10")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["page"], 2)
        self.assertEqual(body["page_size"], 10)
