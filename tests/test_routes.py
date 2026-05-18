import app as app_module
from racedata.core.models import AthleteRef, Race, SegmentSplit
from racedata.providers.rtrt.ulink import UlinkResolution


class FakeProvider:
    def fetch_profile(self, race, profile_id):
        return AthleteRef(profile_id=profile_id, entry_id="e1", name="Seed Athlete", bib="101")

    def fetch_conf(self, event_key):
        return {"conf": {"name": "Test Event"}}

    def fetch_splits(self, race, profile_id, **kwargs):
        return [
            SegmentSplit(
                segment_id="SWIM",
                label="Swim",
                clock_time="20:00",
                clock_seconds=1200,
                leg_time="20:00",
                leg_seconds=1200,
            )
        ]

    def list_courses(self, race):
        return []

    def course_labels(self, race):
        return {}

    def detect_courses_in_splits(self, race, profile_id):
        return []


def test_import_redirects_to_compare_with_seed_pid(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(
        app_module,
        "resolve_ulink",
        lambda _client, _url: UlinkResolution(
            app_id="app123",
            event_key="EVENT-2026",
            profile_id="PIDSEED",
        ),
    )
    monkeypatch.setattr(app_module, "RtrtProvider", lambda _client: FakeProvider())

    response = client.post("/import", data={"ulink": "https://rtrt.me/ulink/X/EVENT-2026/tracker/PIDSEED/focus"})
    assert response.status_code == 302
    assert "pids=PIDSEED" in response.headers["Location"]
    assert "appid=app123" in response.headers["Location"]


def test_compare_renders_baseline_and_title(monkeypatch):
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["race"] = {
            "event_key": "EVENT-2026",
            "display_name": "Test Event",
            "app_id": "app123",
        }
        sess["rtrt_credentials"] = {"app_id": "app123", "token": "TOKEN"}

    monkeypatch.setattr(app_module, "RtrtProvider", lambda _client: FakeProvider())

    response = client.get("/compare?pids=PIDSEED&appid=app123")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Test Event" in body
    assert "Seed Athlete" in body
    assert "Baseline" in body
    assert "Swim" in body
