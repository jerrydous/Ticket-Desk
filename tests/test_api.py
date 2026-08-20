import os
import time

import httpx
import pytest

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")


@pytest.fixture(scope="session")
def api() -> httpx.Client:
    deadline = time.time() + 60
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with httpx.Client(base_url=BASE_URL, timeout=5.0) as probe:
                response = probe.get("/healthz")
                if response.status_code == 200 and response.json().get("db") == "up":
                    break
        except Exception as exc:  # noqa: BLE001 - wait until api is ready
            last_error = exc
        time.sleep(1)
    else:
        raise RuntimeError(f"API not ready at {BASE_URL}: {last_error}")

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        yield client


def test_create_ticket(api: httpx.Client) -> None:
    response = api.post(
        "/tickets",
        json={"title": "修登录页", "assignee": "intern", "priority": "high"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "修登录页"
    assert body["assignee"] == "intern"
    assert body["priority"] == "high"
    assert body["status"] == "open"
    assert "id" in body
    assert "created_at" in body


def test_create_ticket_missing_title_returns_400(api: httpx.Client) -> None:
    response = api.post("/tickets", json={"assignee": "intern"})
    assert response.status_code == 400
    assert response.json() == {"error": "wrong_parameter"}


def test_mark_ticket_done_does_not_affect_other_tickets(api: httpx.Client) -> None:
    created_ids: list[int] = []
    for title in ["隔离-A", "隔离-B", "隔离-C"]:
        created = api.post("/tickets", json={"title": title, "assignee": "intern"})
        assert created.status_code == 201
        created_ids.append(created.json()["id"])

    target_id = created_ids[0]
    other_ids = created_ids[1:]

    response = api.post(f"/tickets/{target_id}/done")
    assert response.status_code == 200
    assert response.json()["status"] == "done"

    for ticket_id in other_ids:
        other = api.get(f"/tickets/{ticket_id}")
        assert other.status_code == 200
        assert other.json()["status"] == "open"
        assert other.json()["id"] == ticket_id


def test_mark_ticket_done_twice_returns_409(api: httpx.Client) -> None:
    created = api.post(
        "/tickets",
        json={"title": "重复完成", "assignee": "intern"},
    )
    assert created.status_code == 201
    ticket_id = created.json()["id"]

    first = api.post(f"/tickets/{ticket_id}/done")
    assert first.status_code == 200

    second = api.post(f"/tickets/{ticket_id}/done")
    assert second.status_code == 409
    assert second.json() == {"error": "already_done"}


def test_add_note_to_missing_ticket_returns_404(api: httpx.Client) -> None:
    response = api.post("/tickets/999999/notes", json={"body": "复现了，准备改"})
    assert response.status_code == 404
    assert response.json() == {"error": "ticket_not_found"}


def test_block_ticket(api: httpx.Client) -> None:
    created = api.post(
        "/tickets",
        json={"title": "阻塞工单", "assignee": "intern"},
    )
    assert created.status_code == 201
    ticket_id = created.json()["id"]

    response = api.post(f"/tickets/{ticket_id}/block")
    assert response.status_code == 200
    assert response.json()["id"] == ticket_id
    assert response.json()["status"] == "blocked"

    fetched = api.get(f"/tickets/{ticket_id}")
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "blocked"


def test_block_ticket_twice_is_idempotent(api: httpx.Client) -> None:
    created = api.post(
        "/tickets",
        json={"title": "重复阻塞", "assignee": "intern"},
    )
    assert created.status_code == 201
    ticket_id = created.json()["id"]

    first = api.post(f"/tickets/{ticket_id}/block")
    assert first.status_code == 200
    assert first.json()["status"] == "blocked"

    second = api.post(f"/tickets/{ticket_id}/block")
    assert second.status_code == 200
    assert second.json()["status"] == "blocked"
    assert second.json()["id"] == ticket_id


def test_block_missing_ticket_returns_404(api: httpx.Client) -> None:
    response = api.post("/tickets/999999/block")
    assert response.status_code == 404
    assert response.json() == {"error": "ticket_not_found"}
