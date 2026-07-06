import app as app_module
from racedata.core.models import AthleteRef, Race, SegmentSplit
from racedata.providers.rtrt.client import SessionCredentials
from racedata.providers.sportstats.link import CheckpointCol
from racedata.resolve import ShareResolution


class FakeProvider:
    def search_athletes(self, race, query):
        return [AthleteRef(profile_id="486", entry_id="486", name="Joe Navratil", bib="486")]

    def fetch_profile(self, race, profile_id):
        return AthleteRef(profile_id=profile_id, entry_id="e1", name="Seed Athlete", bib="101")

    def fetch_conf(self, event_key):
        return {"vconf": {"desc": "Test Event"}}

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

    def fake_resolve(url, **kwargs):
        return ShareResolution(
            provider="rtrt",
            race=Race(
                event_key="EVENT-2026",
                display_name="EVENT-2026",
                provider="rtrt",
                app_id="app123",
            ),
            seed_profile_id="PIDSEED",
            credentials=SessionCredentials(app_id="app123", token="TOKEN"),
        )

    monkeypatch.setattr(app_module, "resolve_share_url", fake_resolve)
    monkeypatch.setattr(app_module, "provider_for_race", lambda *_args, **_kwargs: FakeProvider())

    response = client.post("/import", data={"ulink": "https://rtrt.me/ulink/X/EVENT-2026/tracker/PIDSEED/focus"})
    assert response.status_code == 302
    assert "pids=PIDSEED" in response.headers["Location"]
    assert "appid=app123" in response.headers["Location"]


def test_share_redirects_to_compare_with_seed_pid(monkeypatch):
    client = app_module.app.test_client()

    def fake_resolve(url, **kwargs):
        return ShareResolution(
            provider="rtrt",
            race=Race(
                event_key="EVENT-2026",
                display_name="EVENT-2026",
                provider="rtrt",
                app_id="app123",
            ),
            seed_profile_id="PIDSEED",
            credentials=SessionCredentials(app_id="app123", token="TOKEN"),
        )

    monkeypatch.setattr(app_module, "resolve_share_url", fake_resolve)
    monkeypatch.setattr(app_module, "provider_for_race", lambda *_args, **_kwargs: FakeProvider())

    response = client.get(
        "/share?url=https://rtrt.me/ulink/X/EVENT-2026/tracker/PIDSEED/focus"
    )
    assert response.status_code == 302
    assert "pids=PIDSEED" in response.headers["Location"]
    assert "appid=app123" in response.headers["Location"]


def test_share_extracts_url_from_text_param(monkeypatch):
    client = app_module.app.test_client()
    captured: list[str] = []

    def fake_resolve(url, **kwargs):
        captured.append(url)
        return ShareResolution(
            provider="rtrt",
            race=Race(
                event_key="EVENT-2026",
                display_name="EVENT-2026",
                provider="rtrt",
                app_id="app123",
            ),
            seed_profile_id="PIDSEED",
            credentials=SessionCredentials(app_id="app123", token="TOKEN"),
        )

    monkeypatch.setattr(app_module, "resolve_share_url", fake_resolve)
    monkeypatch.setattr(app_module, "provider_for_race", lambda *_args, **_kwargs: FakeProvider())

    response = client.get(
        "/share?text=Check%20out%20https://rtrt.me/ulink/X/EVENT-2026/tracker/PIDSEED/focus"
    )
    assert response.status_code == 302
    assert captured == ["https://rtrt.me/ulink/X/EVENT-2026/tracker/PIDSEED/focus"]


def test_share_missing_link_returns_error():
    client = app_module.app.test_client()
    response = client.get("/share")
    assert response.status_code == 400
    assert b"No share link found" in response.data


def test_share_invalid_link_returns_error(monkeypatch):
    client = app_module.app.test_client()

    def fake_resolve(url, **kwargs):
        raise ValueError("Unsupported share link.")

    monkeypatch.setattr(app_module, "resolve_share_url", fake_resolve)

    response = client.get("/share?url=https://example.com/not-a-race-link")
    assert response.status_code == 400
    assert b"Unsupported share link" in response.data


def test_share_sportstats_with_focus_preseeds(monkeypatch):
    client = app_module.app.test_client()

    def fake_resolve(url, **kwargs):
        return ShareResolution(
            provider="sportstats",
            race=Race(event_key="146818", display_name="Duathlon", provider="sportstats"),
            seed_profile_id="486",
            checkpoint_cols=(),
            slug="usat-multisport",
        )

    monkeypatch.setattr(app_module, "resolve_share_url", fake_resolve)
    monkeypatch.setattr(app_module, "provider_for_race", lambda *_args, **_kwargs: FakeProvider())

    response = client.get(
        "/share?url=https://sportstats.one/event/usat-multisport/leaderboard/146818?focus=486&type=pid"
    )
    assert response.status_code == 302
    location = response.headers["Location"]
    assert "pids=486" in location
    assert "rid=146818" in location
    assert "slug=usat-multisport" in location


def test_manifest_served_with_correct_type():
    client = app_module.app.test_client()
    response = client.get("/manifest.webmanifest")
    assert response.status_code == 200
    assert response.content_type.startswith("application/manifest+json")
    assert b"share_target" in response.data


def test_service_worker_served_with_scope_header():
    client = app_module.app.test_client()
    response = client.get("/sw.js")
    assert response.status_code == 200
    assert response.content_type.startswith("application/javascript")
    assert response.headers.get("Service-Worker-Allowed") == "/"


def test_import_sportstats_without_focus_redirects_empty_compare(monkeypatch):
    client = app_module.app.test_client()

    def fake_resolve(url, **kwargs):
        return ShareResolution(
            provider="sportstats",
            race=Race(
                event_key="146818",
                display_name="USA Triathlon Multisport",
                provider="sportstats",
            ),
            seed_profile_id=None,
            checkpoint_cols=(),
            slug="usat-multisport",
            event_title="USA Triathlon Multisport",
            race_title="Super Sprint Time Trial Duathlon",
        )

    monkeypatch.setattr(app_module, "resolve_share_url", fake_resolve)

    response = client.post(
        "/import",
        data={"ulink": "https://sportstats.one/event/usat-multisport/leaderboard/146818"},
    )
    assert response.status_code == 302
    location = response.headers["Location"]
    assert "/compare" in location
    assert "pids=" not in location
    assert "appid=" not in location
    assert "rid=146818" in location
    assert "slug=usat-multisport" in location

    with client.session_transaction() as sess:
        assert sess["race"]["provider"] == "sportstats"
        assert sess["race"]["rid"] == "146818"


def test_import_sportstats_with_focus_preseeds(monkeypatch):
    client = app_module.app.test_client()

    def fake_resolve(url, **kwargs):
        return ShareResolution(
            provider="sportstats",
            race=Race(event_key="146818", display_name="Duathlon", provider="sportstats"),
            seed_profile_id="486",
            checkpoint_cols=(),
            slug="usat-multisport",
        )

    monkeypatch.setattr(app_module, "resolve_share_url", fake_resolve)
    monkeypatch.setattr(app_module, "provider_for_race", lambda *_args, **_kwargs: FakeProvider())

    response = client.post(
        "/import",
        data={
            "ulink": "https://sportstats.one/event/usat-multisport/leaderboard/146818?focus=486&type=pid"
        },
    )
    assert response.status_code == 302
    location = response.headers["Location"]
    assert "pids=486" in location
    assert "rid=146818" in location
    assert "slug=usat-multisport" in location


def test_compare_sportstats_restores_race_from_url_without_session(monkeypatch):
    resolve_calls: list[str] = []

    def fake_resolve(url, **kwargs):
        resolve_calls.append(url)
        return ShareResolution(
            provider="sportstats",
            race=Race(
                event_key="146818",
                display_name="USA Triathlon Multisport",
                provider="sportstats",
            ),
            checkpoint_cols=(CheckpointCol("447408", "Run1", cho="1"),),
            slug="usat-multisport",
            race_title="Super Sprint Time Trial Duathlon",
        )

    monkeypatch.setattr(app_module, "resolve_share_url", fake_resolve)
    monkeypatch.setattr(app_module, "provider_for_race", lambda *_args, **_kwargs: FakeProvider())

    client = app_module.app.test_client()
    response = client.get("/compare?pids=486&rid=146818&slug=usat-multisport")
    assert response.status_code == 200
    assert len(resolve_calls) == 1
    assert "usat-multisport" in resolve_calls[0]
    assert "146818" in resolve_calls[0]
    with client.session_transaction() as sess:
        assert sess["race"]["provider"] == "sportstats"
        assert sess["sportstats_cols"]


def test_provider_receives_sportstats_cols_with_cho_from_session(monkeypatch):
    captured: dict = {}

    def capture_provider_for_race(race, **kwargs):
        captured.update(kwargs)
        return FakeProvider()

    monkeypatch.setattr(app_module, "provider_for_race", capture_provider_for_race)

    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["race"] = {
            "provider": "sportstats",
            "event_key": "146818",
            "display_name": "USA Triathlon Multisport",
            "rid": "146818",
        }
        sess["sportstats_cols"] = [
            {"cid": "447408", "label": "Run1", "cho": "1", "fc": ""},
            {"cid": "447407", "label": "Run 0.3mi", "cho": "0", "fc": ""},
        ]

    client.get("/compare?pids=486")
    cols = captured["sportstats_cols"]
    assert cols[0].is_main
    assert not cols[1].is_main


def test_compare_sportstats_shows_intermediate_split_toggle(monkeypatch):
    class SportstatsSplitsProvider(FakeProvider):
        def fetch_splits(self, race, profile_id, **kwargs):
            return [
                SegmentSplit(
                    segment_id="447408",
                    label="Run1",
                    clock_time="3:48",
                    clock_seconds=228,
                    leg_time="3:48",
                    leg_seconds=228,
                    is_intermediate=False,
                ),
                SegmentSplit(
                    segment_id="447407",
                    label="Run 0.3mi",
                    clock_time="1:50",
                    clock_seconds=110,
                    leg_time="1:50",
                    leg_seconds=110,
                    is_intermediate=True,
                ),
            ]

    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["race"] = {
            "provider": "sportstats",
            "event_key": "146818",
            "display_name": "USA Triathlon Multisport",
            "race_title": "Super Sprint Time Trial Duathlon",
            "rid": "146818",
        }
        sess["sportstats_cols"] = [
            {"cid": "447408", "label": "Run1", "cho": "1", "fc": ""},
            {"cid": "447407", "label": "Run 0.3mi", "cho": "0", "fc": ""},
        ]

    monkeypatch.setattr(
        app_module, "provider_for_race", lambda *_args, **_kwargs: SportstatsSplitsProvider()
    )

    response = client.get("/compare?pids=486")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Show intermediate splits" in body
    assert 'data-hidden-by-default="false">Run1' in body
    assert 'data-hidden-by-default="true">Run 0.3mi' in body


def test_compare_empty_pids_sportstats(monkeypatch):
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["race"] = {
            "provider": "sportstats",
            "event_key": "146818",
            "display_name": "USA Triathlon Multisport",
            "race_title": "Super Sprint Time Trial Duathlon",
            "rid": "146818",
            "slug": "usat-multisport",
        }
        sess["sportstats_cols"] = []

    monkeypatch.setattr(app_module, "provider_for_race", lambda *_args, **_kwargs: FakeProvider())

    response = client.get("/compare")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "USA Triathlon Multisport" in body
    assert "Super Sprint Time Trial Duathlon" in body
    assert "Add athlete" in body


def test_api_search_sportstats_without_appid(monkeypatch):
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["race"] = {
            "provider": "sportstats",
            "event_key": "146818",
            "display_name": "Duathlon",
            "rid": "146818",
        }
        sess["sportstats_cols"] = []

    monkeypatch.setattr(app_module, "provider_for_race", lambda *_args, **_kwargs: FakeProvider())

    response = client.get("/api/search?q=jo")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["results"]


def test_compare_renders_baseline_and_title(monkeypatch):
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["race"] = {
            "provider": "rtrt",
            "event_key": "EVENT-2026",
            "display_name": "Test Event",
            "app_id": "app123",
        }
        sess["rtrt_credentials"] = {"app_id": "app123", "token": "TOKEN"}

    monkeypatch.setattr(app_module, "provider_for_race", lambda *_args, **_kwargs: FakeProvider())

    response = client.get("/compare?pids=PIDSEED&appid=app123")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Test Event" in body
    assert "Seed Athlete" in body
    assert "Baseline" in body
    assert "Swim" in body


def test_compare_renders_hidden_split_toggle(monkeypatch):
    class HiddenSplitsProvider(FakeProvider):
        def fetch_conf(self, event_key):
            return {
                "conf": {
                    "pointOrder": [
                        {"course": "courseA", "name": "SWIM", "label": "Swim"},
                    ]
                }
            }

        def detect_courses_in_splits(self, race, profile_id):
            return ["courseA"]

        def fetch_splits(self, race, profile_id, **kwargs):
            return [
                SegmentSplit(
                    segment_id="SWIM",
                    label="Swim",
                    clock_time="20:00",
                    clock_seconds=1200,
                    leg_time="20:00",
                    leg_seconds=1200,
                    course="courseA",
                ),
                SegmentSplit(
                    segment_id="SWIM-1",
                    label="Swim 500m",
                    clock_time="25:00",
                    clock_seconds=1500,
                    leg_time="5:00",
                    leg_seconds=300,
                    course="courseA",
                ),
            ]

    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["race"] = {
            "provider": "rtrt",
            "event_key": "EVENT-2026",
            "display_name": "Test Event",
            "app_id": "app123",
        }
        sess["rtrt_credentials"] = {"app_id": "app123", "token": "TOKEN"}

    monkeypatch.setattr(app_module, "provider_for_race", lambda *_args, **_kwargs: HiddenSplitsProvider())

    response = client.get("/compare?pids=PIDSEED&appid=app123")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Show intermediate splits" in body


def test_api_athlete_requests_uncollapsed_splits(monkeypatch):
    class ApiAthleteProvider(FakeProvider):
        def __init__(self):
            self.last_fetch_kwargs = None

        def fetch_splits(self, race, profile_id, **kwargs):
            self.last_fetch_kwargs = kwargs
            splits = [
                SegmentSplit(
                    segment_id="SWIM",
                    label="Swim",
                    clock_time="20:00",
                    clock_seconds=1200,
                    leg_time="20:00",
                    leg_seconds=1200,
                ),
            ]
            if kwargs.get("collapse_intermediates") is False:
                splits.append(
                    SegmentSplit(
                        segment_id="SWIM-1",
                        label="Swim 500m",
                        clock_time="25:00",
                        clock_seconds=1500,
                        leg_time="5:00",
                        leg_seconds=300,
                    )
                )
            return splits

    provider = ApiAthleteProvider()
    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["race"] = {
            "provider": "rtrt",
            "event_key": "EVENT-2026",
            "display_name": "Test Event",
            "app_id": "app123",
        }
        sess["rtrt_credentials"] = {"app_id": "app123", "token": "TOKEN"}

    monkeypatch.setattr(app_module, "provider_for_race", lambda *_args, **_kwargs: provider)

    response = client.get("/api/athlete?pid=PIDSEED&appid=app123&course=courseA")
    assert response.status_code == 200
    payload = response.get_json()
    assert [split["segment_id"] for split in payload["splits"]] == ["SWIM", "SWIM-1"]
    assert provider.last_fetch_kwargs["collapse_intermediates"] is False


def test_import_mtec_with_focus_preseeds(monkeypatch):
    client = app_module.app.test_client()

    def fake_resolve(url, **kwargs):
        return ShareResolution(
            provider="mtec",
            race=Race(event_key="19019", display_name="Door County Sprint", provider="mtec"),
            seed_profile_id="28278143",
            slug="2025_Door_County_Triathlon-Sprint_-_Individual",
            event_id="5851",
            race_title="2025 Door County Triathlon Sprint - Individual",
        )

    monkeypatch.setattr(app_module, "resolve_share_url", fake_resolve)
    monkeypatch.setattr(app_module, "provider_for_race", lambda *_args, **_kwargs: FakeProvider())

    response = client.post(
        "/import",
        data={
            "ulink": "https://www.mtecresults.com/runner/show?rid=28278143&race=19019",
        },
    )
    assert response.status_code == 302
    location = response.headers["Location"]
    assert "pids=28278143" in location
    assert "race=19019" in location
    assert "event=5851" in location
    assert "slug=2025_Door_County_Triathlon-Sprint_-_Individual" in location


def test_compare_mtec_restores_race_from_url_without_session(monkeypatch):
    resolve_calls: list[str] = []

    def fake_resolve(url, **kwargs):
        resolve_calls.append(url)
        return ShareResolution(
            provider="mtec",
            race=Race(event_key="19019", display_name="Door County Sprint", provider="mtec"),
            slug="2025_Door_County_Triathlon-Sprint_-_Individual",
            event_id="5851",
            race_title="2025 Door County Triathlon Sprint - Individual",
        )

    monkeypatch.setattr(app_module, "resolve_share_url", fake_resolve)
    monkeypatch.setattr(app_module, "provider_for_race", lambda *_args, **_kwargs: FakeProvider())

    client = app_module.app.test_client()
    response = client.get(
        "/compare?pids=28278143&race=19019&event=5851&slug=2025_Door_County_Triathlon-Sprint_-_Individual"
    )
    assert response.status_code == 200
    assert len(resolve_calls) == 1
    assert "mtecresults.com" in resolve_calls[0]
    with client.session_transaction() as sess:
        assert sess["race"]["provider"] == "mtec"
        assert sess["race"]["event_id"] == "5851"


def test_provider_receives_mtec_event_id_from_session(monkeypatch):
    captured: dict = {}

    def capture_provider_for_race(race, **kwargs):
        captured.update(kwargs)
        return FakeProvider()

    monkeypatch.setattr(app_module, "provider_for_race", capture_provider_for_race)

    client = app_module.app.test_client()
    with client.session_transaction() as sess:
        sess["race"] = {
            "provider": "mtec",
            "event_key": "19019",
            "display_name": "Door County Sprint",
            "event_id": "5851",
            "slug": "2025_Door_County_Triathlon-Sprint_-_Individual",
        }

    client.get("/compare?pids=28278143")
    assert captured["mtec_event_id"] == "5851"
