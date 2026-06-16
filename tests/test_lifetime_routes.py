import app as app_module
from racedata.lifetime.models import LifetimeAthleteProfile, LifetimeRaceResult


class FakeLifetimeProvider:
    def search_athletes(self, query: str) -> list[LifetimeAthleteProfile]:
        return [
            LifetimeAthleteProfile(
                provider="usat",
                athlete_id="182151",
                display_name="Joe Navratil",
                first_name="Joe",
                last_name="Navratil",
                age=50,
                gender="Male",
                location="Middleton, Wisconsin",
            )
        ]

    def fetch_profile(self, athlete_id: str) -> LifetimeAthleteProfile | None:
        profiles = {
            "182151": LifetimeAthleteProfile(
                provider="usat",
                athlete_id="182151",
                display_name="Joe Navratil",
                first_name="Joe",
                last_name="Navratil",
                age=50,
                gender="Male",
                location="Wisconsin",
            ),
            "2722919": LifetimeAthleteProfile(
                provider="usat",
                athlete_id="2722919",
                display_name="Kevin Navratil",
                first_name="Kevin",
                last_name="Navratil",
                age=45,
                gender="Male",
                location="Madison, Wisconsin",
            ),
        }
        return profiles.get(athlete_id)

    def fetch_all_results(self, athlete_id: str) -> list[LifetimeRaceResult]:
        shared = LifetimeRaceResult(
            provider="usat",
            athlete_id=athlete_id,
            event_id="100",
            race_id="200",
            result_id=f"{athlete_id}-shared",
            event_name="Shared Event",
            race_name="Sprint Tri",
            race_date="2025-06-01",
            position=10 if athlete_id == "182151" else 12,
            ranking=100.0 if athlete_id == "182151" else 95.0,
            finish_time="1:00:00.000" if athlete_id == "182151" else "1:01:00.000",
            finish_seconds=3600.0 if athlete_id == "182151" else 3660.0,
        )
        unique = LifetimeRaceResult(
            provider="usat",
            athlete_id=athlete_id,
            event_id=f"9{athlete_id}",
            race_id=f"8{athlete_id}",
            result_id=f"{athlete_id}-solo",
            event_name="Solo Event",
            race_name="Duathlon",
            race_date="2024-01-01",
            position=5,
            ranking=90.0,
            finish_time="2:00:00.000",
            finish_seconds=7200.0,
        )
        return [shared, unique]


def test_lifetime_search_returns_disambiguation_fields(monkeypatch):
    monkeypatch.setattr(app_module, "lifetime_provider_for", lambda _provider: FakeLifetimeProvider())
    client = app_module.app.test_client()
    response = client.get("/api/lifetime/search?q=Navratil&provider=usat")
    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload["results"]) == 1
    result = payload["results"][0]
    assert result["athlete_id"] == "182151"
    assert result["display_name"] == "Joe Navratil"
    assert result["age"] == 50
    assert result["location"] == "Middleton, Wisconsin"


def test_lifetime_compare_renders_shared_races(monkeypatch):
    monkeypatch.setattr(app_module, "lifetime_provider_for", lambda _provider: FakeLifetimeProvider())
    client = app_module.app.test_client()
    response = client.get("/lifetime/compare?a=182151&b=2722919&provider=usat")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Shared Event" in html
    assert "Joe Navratil" in html
    assert "Kevin Navratil" in html
    assert "Solo Event" not in html
    assert "lifetime-table" in html
    assert "athlete-a-stack" in html
    assert "sortable" in html


def test_lifetime_compare_requires_two_athletes():
    client = app_module.app.test_client()
    response = client.get("/lifetime/compare?a=182151&provider=usat")
    assert response.status_code == 400
