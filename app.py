from __future__ import annotations

import os
import uuid
from urllib.parse import urlencode

from flask import Flask, jsonify, redirect, render_template, request, session, url_for

from racedata.core.models import AthleteRef, Race
from racedata.providers.rtrt.client import RtrtClient, SessionCredentials
from racedata.providers.rtrt.service import RtrtProvider
from racedata.providers.rtrt.points import event_display_name_from_conf
from racedata.providers.rtrt.ulink import credentials_for_ulink, parse_ulink_url, resolve_ulink
from src.view_models import build_grid_view

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-head2head-secret")


def _session_credentials(app_id: str) -> SessionCredentials:
    stored = session.get("rtrt_credentials")
    if stored and stored.get("app_id") == app_id:
        return SessionCredentials(app_id=stored["app_id"], token=stored["token"])
    creds = SessionCredentials.from_env() or SessionCredentials.new_session(app_id)
    session["rtrt_credentials"] = {"app_id": creds.app_id, "token": creds.token}
    return creds


def _provider_for_app(app_id: str) -> RtrtProvider:
    return RtrtProvider(RtrtClient(_session_credentials(app_id)))


def _race_from_session() -> Race | None:
    data = session.get("race")
    if not data:
        return None
    return Race(
        event_key=data["event_key"],
        display_name=data.get("display_name", data["event_key"]),
        app_id=data.get("app_id", ""),
    )


def _store_race(race: Race) -> None:
    session["race"] = {
        "event_key": race.event_key,
        "display_name": race.display_name,
        "app_id": race.app_id,
    }


def _parse_pids() -> list[str]:
    raw = request.args.get("pids", "")
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _load_athletes(provider: RtrtProvider, race: Race, pids: list[str]) -> list[AthleteRef]:
    athletes: list[AthleteRef] = []
    for pid in pids:
        athlete = provider.fetch_profile(race, pid)
        if athlete:
            athletes.append(athlete)
    return athletes


def _course_options(provider: RtrtProvider, race: Race, seed_pid: str | None) -> tuple[list[dict], str | None]:
    courses = provider.list_courses(race)
    labels = provider.course_labels(race)
    options = [{"id": course.id, "label": labels.get(course.id, course.label)} for course in courses]

    selected = request.args.get("course")
    if selected:
        return options, selected

    if seed_pid:
        detected = provider.detect_courses_in_splits(race, seed_pid)
        if len(detected) == 1:
            return options, detected[0]
        if detected:
            from racedata.providers.rtrt.points import default_course_from_splits

            raw = provider.fetch_raw_splits(race, seed_pid)
            return options, default_course_from_splits(raw)

    if len(options) == 1:
        return options, options[0]["id"]
    return options, None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/import", methods=["POST"])
def import_ulink():
    ulink = (request.form.get("ulink") or "").strip()
    if not ulink:
        return render_template("index.html", error="Please paste a share link."), 400

    try:
        temp_creds = SessionCredentials.new_session("placeholder")
        temp_client = RtrtClient(temp_creds)
        resolution = resolve_ulink(temp_client, ulink)
    except ValueError as exc:
        return render_template("index.html", error=str(exc)), 400

    creds = credentials_for_ulink(resolution)
    session["rtrt_credentials"] = {"app_id": creds.app_id, "token": creds.token}
    provider = RtrtProvider(RtrtClient(creds))

    profile = provider.fetch_profile(
        Race(resolution.event_key, resolution.event_key, app_id=resolution.app_id),
        resolution.profile_id,
    )
    display_name = resolution.event_key
    try:
        conf = provider.fetch_conf(resolution.event_key)
        if title := event_display_name_from_conf(conf):
            display_name = title
    except Exception:
        pass

    race = Race(
        event_key=resolution.event_key,
        display_name=display_name,
        app_id=resolution.app_id,
    )
    _store_race(race)

    params = {
        "pids": resolution.profile_id,
        "appid": resolution.app_id,
    }
    if profile and profile.name:
        session["seed_name"] = profile.name
    return redirect(f"/compare?{urlencode(params)}")


@app.route("/compare")
def compare():
    race = _race_from_session()
    app_id = request.args.get("appid") or (race.app_id if race else "")
    pids = _parse_pids()

    if not race or not app_id or not pids:
        return redirect(url_for("index"))

    if race.app_id != app_id:
        race = Race(event_key=race.event_key, display_name=race.display_name, app_id=app_id)
        _store_race(race)

    provider = _provider_for_app(app_id)
    athletes = _load_athletes(provider, race, pids)
    if not athletes:
        return render_template("index.html", error="Could not load athletes for this link."), 400

    course_options, selected_course = _course_options(provider, race, pids[0])
    labels = provider.course_labels(race)
    course_label = labels.get(selected_course, selected_course) if selected_course else None

    splits_by_profile = {
        athlete.profile_id: provider.fetch_splits(
            race,
            athlete.profile_id,
            entry_id=athlete.entry_id,
            course_id=selected_course,
        )
        for athlete in athletes
    }

    grid = build_grid_view(
        race,
        athletes,
        splits_by_profile,
        baseline_index=0,
        course_label=course_label,
        available_courses=course_options,
        selected_course=selected_course,
    )
    return render_template("compare.html", grid=grid, app_id=app_id)


@app.route("/api/search")
def api_search():
    race = _race_from_session()
    app_id = request.args.get("appid") or (race.app_id if race else "")
    query = (request.args.get("q") or "").strip()
    if not race or not app_id:
        return jsonify({"error": "Race context missing."}), 400
    if len(query) < 2:
        return jsonify({"results": []})

    provider = _provider_for_app(app_id)
    results = provider.search_athletes(race, query)
    return jsonify(
        {
            "results": [
                {
                    "profile_id": athlete.profile_id,
                    "entry_id": athlete.entry_id,
                    "name": athlete.name,
                    "bib": athlete.bib,
                    "division": athlete.division,
                }
                for athlete in results
            ]
        }
    )


@app.route("/api/athlete")
def api_athlete():
    race = _race_from_session()
    app_id = request.args.get("appid") or (race.app_id if race else "")
    pid = (request.args.get("pid") or "").strip()
    course = request.args.get("course")
    if not race or not app_id or not pid:
        return jsonify({"error": "Missing parameters."}), 400

    provider = _provider_for_app(app_id)
    athlete = provider.fetch_profile(race, pid)
    if not athlete:
        return jsonify({"error": "Athlete not found."}), 404

    splits = provider.fetch_splits(
        race,
        pid,
        entry_id=athlete.entry_id,
        course_id=course,
    )
    return jsonify(
        {
            "athlete": {
                "profile_id": athlete.profile_id,
                "entry_id": athlete.entry_id,
                "name": athlete.name,
                "bib": athlete.bib,
                "division": athlete.division,
            },
            "splits": [
                {
                    "segment_id": split.segment_id,
                    "label": split.label,
                    "clock_time": split.clock_time,
                    "leg_time": split.leg_time,
                    "clock_seconds": split.clock_seconds,
                    "leg_seconds": split.leg_seconds,
                }
                for split in splits
            ],
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
