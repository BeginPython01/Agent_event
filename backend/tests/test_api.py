"""Tests for the REST API using FastAPI's TestClient (no real server needed)."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from src.agent.actions import log_action
from src.api.app import create_app
from src.db import EventRow, SourceDocument
from src.models import Eligibility, Event, FieldConfidence

LISTING = "https://uni.example/news.html"
SOON = date.today() + timedelta(days=10)


@pytest.fixture
def api(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'api.db'}")
    return TestClient(app), app.state.session_factory


def new_user(client, **profile) -> dict:
    user_id = client.post("/users", json=profile or None).json()["id"]
    return {"X-User-Id": str(user_id)}


def seed_events(Session, *events: Event) -> list[int]:
    """Pretend the pipeline already read a page from LISTING."""
    with Session() as db:
        doc = SourceDocument(source_ref="https://uni.example/detail/1", found_via=LISTING, content_hash="x")
        db.add(doc)
        db.flush()
        rows = [EventRow(document_id=doc.id, name=e.name, category=e.category,
                         registration_deadline=e.registration_deadline, data=e.model_dump(mode="json"))
                for e in events]
        db.add_all(rows)
        db.commit()
        return [r.id for r in rows]


def event(name: str, deadline: date = SOON, **conditions) -> Event:
    return Event(name=name, category="workshop", registration_deadline=deadline,
                 eligibility=Eligibility(**conditions),
                 confidence=FieldConfidence(registration_deadline=1, event_dates=1, eligibility=0.9))


def test_profile_round_trip(api):
    client, _ = api
    me = new_user(client)
    client.put("/me/profile", headers=me, json={"birth_year": 2007, "level": "undergraduate", "interests": ["AI"]})

    profile = client.get("/me/profile", headers=me).json()
    assert profile["birth_year"] == 2007
    assert profile["interests"] == ["AI"]


def test_unknown_user_gets_404(api):
    client, _ = api
    assert client.get("/me/profile", headers={"X-User-Id": "999"}).status_code == 404


def test_watched_urls_add_list_remove(api):
    client, _ = api
    me = new_user(client)
    created = client.post("/me/watched-urls", headers=me, json={"url": LISTING, "follow_pattern": "detail"})
    assert created.status_code == 201

    assert client.post("/me/watched-urls", headers=me, json={"url": LISTING}).status_code == 409  # duplicate
    assert client.post("/me/watched-urls", headers=me, json={"url": "ftp://x"}).status_code == 422  # bad URL
    assert len(client.get("/me/watched-urls", headers=me).json()) == 1

    assert client.delete(f"/me/watched-urls/{created.json()['id']}", headers=me).status_code == 204
    assert client.get("/me/watched-urls", headers=me).json() == []


def test_cannot_delete_someone_elses_url(api):
    client, _ = api
    alice, bob = new_user(client), new_user(client)
    url_id = client.post("/me/watched-urls", headers=alice, json={"url": LISTING}).json()["id"]

    assert client.delete(f"/me/watched-urls/{url_id}", headers=bob).status_code == 404


def test_events_feed_hides_not_eligible_and_past(api):
    client, Session = api
    me = new_user(client, level="undergraduate")
    client.post("/me/watched-urls", headers=me, json={"url": LISTING, "follow_pattern": "detail"})
    seed_events(Session,
                event("Open House อาสา"),
                event("หลักสูตรพยาบาล", allowed_levels=["working"]),
                event("งานที่จบไปแล้ว", deadline=date(2020, 1, 1)))

    names = [e["event"]["name"] for e in client.get("/me/events", headers=me).json()]
    assert names == ["Open House อาสา"]

    everything = client.get("/me/events?include_not_eligible=true", headers=me).json()
    statuses = {e["event"]["name"]: e["eligibility"]["status"] for e in everything}
    assert statuses == {"Open House อาสา": "eligible", "หลักสูตรพยาบาล": "not_eligible"}


def test_events_feed_is_empty_without_sources(api):
    client, Session = api
    seed_events(Session, event("Open House อาสา"))
    me = new_user(client)
    assert client.get("/me/events", headers=me).json() == []


def test_application_board(api):
    client, Session = api
    me = new_user(client)
    client.post("/me/watched-urls", headers=me, json={"url": LISTING, "follow_pattern": "detail"})
    (event_id,) = seed_events(Session, event("Workshop Git"))

    client.put("/me/applications", headers=me, json={"event_id": event_id, "lane": "interested"})
    client.put("/me/applications", headers=me, json={"event_id": event_id, "lane": "applied"})

    board = client.get("/me/applications", headers=me).json()
    assert [(a["event_name"], a["lane"]) for a in board] == [("Workshop Git", "applied")]
    assert client.get("/me/events", headers=me).json()[0]["lane"] == "applied"
    assert client.put("/me/applications", headers=me, json={"event_id": event_id, "lane": "bogus"}).status_code == 422


def test_actions_timeline_newest_first(api):
    client, Session = api
    me = new_user(client)
    user_id = int(me["X-User-Id"])
    with Session() as db:
        log_action(db, [user_id], "read_source", "อ่านหน้า A")
        log_action(db, [user_id], "extract", "เจอ 2 กิจกรรม")
        db.commit()

    actions = client.get("/me/actions", headers=me).json()
    assert [a["summary"] for a in actions] == ["เจอ 2 กิจกรรม", "อ่านหน้า A"]


def test_delete_me_removes_everything(api):
    client, Session = api
    me = new_user(client)
    client.post("/me/watched-urls", headers=me, json={"url": LISTING})
    with Session() as db:
        log_action(db, [int(me["X-User-Id"])], "extract", "x")
        db.commit()

    assert client.delete("/me", headers=me).status_code == 204
    assert client.get("/me/profile", headers=me).status_code == 404
    with Session() as db:
        from sqlalchemy import func, select
        from src.db import AgentAction, WatchedUrl
        assert db.scalar(select(func.count()).select_from(WatchedUrl)) == 0
        assert db.scalar(select(func.count()).select_from(AgentAction)) == 0
