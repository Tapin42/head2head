from racedata.core.models import Race
from racedata.providers.rtrt.service import RtrtProvider


class FakeClient:
    def __init__(self, payload):
        self.payload = payload

    def post(self, url, data=None):
        if url.endswith("/conf"):
            return {"conf": {"pointOrder": []}}
        return self.payload


def test_fetch_splits_blocks_announcer_even_when_not_collapsing():
    payload = {
        "list": [
            {
                "point": "START",
                "label": "Start",
                "time": "00:00:00.00",
                "legTime": "00:00:00.00",
            },
            {
                "point": "ANNOUNCER",
                "label": "Announcer",
                "time": "00:10:00.00",
                "legTime": "00:10:00.00",
            },
            {
                "point": "SWIM",
                "label": "Swim",
                "time": "00:20:00.00",
                "legTime": "00:10:00.00",
            },
        ]
    }
    provider = RtrtProvider(FakeClient(payload))
    race = Race(event_key="EVENT", display_name="Event", app_id="app")

    splits = provider.fetch_splits(race, "PID1", collapse_intermediates=False)

    assert [split.segment_id for split in splits] == ["START", "SWIM"]
