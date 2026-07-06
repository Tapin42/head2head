from __future__ import annotations

import json
import os
import re
from urllib.parse import urlencode

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, session, url_for

from racedata.core.models import AthleteRef, Race
from racedata.core.split_filter import main_point_names_from_conf
from racedata.providers.factory import provider_for_race
from racedata.providers.rtrt.client import RtrtClient, SessionCredentials
from racedata.providers.rtrt.points import event_display_name_from_conf, pointorder_for_course
from racedata.providers.rtrt.service import RtrtProvider
from racedata.providers.sportstats.link import CheckpointCol
from racedata.resolve import ShareResolution, resolve_share_url
from racedata.lifetime.h2h import find_common_races
from racedata.providers.usat.client import UsatRateLimitError
from racedata.providers.usat.service import UsatLifetimeProvider
from src.lifetime_view import build_lifetime_compare_view
from src.view_models import build_grid_view

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-head2head-secret")

_URL_IN_TEXT_RE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)

_LIFETIME_PROVIDERS = {
    "usat": UsatLifetimeProvider,
}

USAT_RATE_LIMIT_MESSAGE = "USAT is temporarily limiting requests; try again in a minute."


def lifetime_provider_for(provider_name: str):
    factory = _LIFETIME_PROVIDERS.get(provider_name)
    if not factory:
        raise ValueError(f"Unsupported lifetime provider: {provider_name}")
    return factory()


def _profile_to_json(profile) -> dict:
    return {
        "athlete_id": profile.athlete_id,
        "display_name": profile.display_name,
        "first_name": profile.first_name,
        "last_name": profile.last_name,
        "age": profile.age,
        "gender": profile.gender,
        "location": profile.location,
        "provider": profile.provider,
    }


def _session_credentials(app_id: str) -> SessionCredentials:
    stored = session.get("rtrt_credentials")
    if stored and stored.get("app_id") == app_id:
        return SessionCredentials(app_id=stored["app_id"], token=stored["token"])
    creds = SessionCredentials.from_env() or SessionCredentials.new_session(app_id)
    session["rtrt_credentials"] = {"app_id": creds.app_id, "token": creds.token}
    return creds


def _race_from_session() -> Race | None:
    data = session.get("race")
    if not data:
        return None
    return Race(
        event_key=data["event_key"],
        display_name=data.get("display_name", data["event_key"]),
        provider=data.get("provider", "rtrt"),
        app_id=data.get("app_id", ""),
    )


def _sportstats_cols_from_session() -> tuple[CheckpointCol, ...]:
    raw = session.get("sportstats_cols") or []
    cols: list[CheckpointCol] = []
    for item in raw:
        if isinstance(item, dict) and item.get("cid"):
            cols.append(
                CheckpointCol(
                    cid=str(item["cid"]),
                    label=str(item.get("label", item["cid"])),
                    cho=str(item.get("cho", "0")),
                    fc=str(item.get("fc", "")),
                )
            )
    return tuple(cols)


def _mtec_event_id_from_session() -> str:
    return str((session.get("race") or {}).get("event_id") or "")


def _store_race(race: Race, *, rid: str = "", slug: str = "", event_id: str = "") -> None:
    payload = {
        "provider": race.provider,
        "event_key": race.event_key,
        "display_name": race.display_name,
        "app_id": race.app_id,
    }
    if rid:
        payload["rid"] = rid
    if slug:
        payload["slug"] = slug
    if event_id:
        payload["event_id"] = event_id
    session["race"] = payload


def _store_share_resolution(resolution: ShareResolution) -> None:
    if resolution.race.provider == "sportstats":
        _store_race(
            resolution.race,
            rid=resolution.race.event_key,
            slug=resolution.slug,
        )
        session["sportstats_cols"] = [
            {"cid": col.cid, "label": col.label, "cho": col.cho, "fc": col.fc}
            for col in resolution.checkpoint_cols
        ]
        if resolution.race_title:
            session["race"]["race_title"] = resolution.race_title
    elif resolution.race.provider == "mtec":
        _store_race(
            resolution.race,
            slug=resolution.slug,
            event_id=resolution.event_id,
        )
        if resolution.race_title:
            session["race"]["race_title"] = resolution.race_title
    else:
        _store_race(resolution.race)
    if resolution.credentials:
        session["rtrt_credentials"] = {
            "app_id": resolution.credentials.app_id,
            "token": resolution.credentials.token,
        }


def _provider_for_session() -> RtrtProvider | object:
    race = _race_from_session()
    if not race:
        raise ValueError("Race context missing")
    if race.provider == "sportstats":
        return provider_for_race(race, sportstats_cols=_sportstats_cols_from_session())
    if race.provider == "mtec":
        return provider_for_race(race, mtec_event_id=_mtec_event_id_from_session())
    return provider_for_race(race, rtrt_credentials=_session_credentials(race.app_id))


def _sportstats_hidden_segment_ids_from_session() -> set[str]:
    return {
        str(col["cid"])
        for col in (session.get("sportstats_cols") or [])
        if isinstance(col, dict) and col.get("cho") != "1"
    }


def _sportstats_subtitle_from_session() -> str | None:
    title = (session.get("race") or {}).get("race_title", "")
    return title.strip() or None


def _mtec_subtitle_from_session() -> str | None:
    return _sportstats_subtitle_from_session()


def _mtec_leaderboard_url(race_id: str, slug: str) -> str:
    return f"https://www.mtecresults.com/race/leaderboard/{race_id}/{slug}"


def _mtec_params_from_session() -> dict[str, str]:
    data = session.get("race") or {}
    if data.get("provider") != "mtec":
        return {}
    params: dict[str, str] = {}
    race_id = data.get("event_key", "")
    event_id = data.get("event_id", "")
    slug = data.get("slug", "")
    if race_id:
        params["race"] = str(race_id)
    if event_id:
        params["event"] = str(event_id)
    if slug:
        params["slug"] = slug
    return params


def _sportstats_leaderboard_url(slug: str, rid: str) -> str:
    return f"https://sportstats.one/event/{slug}/leaderboard/{rid}/"


def _sportstats_params_from_session() -> dict[str, str]:
    data = session.get("race") or {}
    if data.get("provider") != "sportstats":
        return {}
    params: dict[str, str] = {}
    rid = data.get("rid") or data.get("event_key")
    slug = data.get("slug", "")
    if rid:
        params["rid"] = str(rid)
    if slug:
        params["slug"] = slug
    return params


def _ensure_sportstats_context_from_query() -> bool:
    rid = (request.args.get("rid") or "").strip()
    slug = (request.args.get("slug") or "").strip()
    if not rid or not slug:
        return False

    race_data = session.get("race") or {}
    session_rid = str(race_data.get("rid") or race_data.get("event_key") or "")
    session_slug = str(race_data.get("slug") or "")
    cols = session.get("sportstats_cols") or []
    needs_refresh = (
        race_data.get("provider") != "sportstats"
        or session_rid != rid
        or session_slug != slug
        or not cols
    )
    if not needs_refresh:
        return True

    try:
        resolution = resolve_share_url(_sportstats_leaderboard_url(slug, rid))
    except ValueError:
        return False
    if resolution.provider != "sportstats" or resolution.race.event_key != rid:
        return False
    _store_share_resolution(resolution)
    return True


def _ensure_mtec_context_from_query() -> bool:
    race_id = (request.args.get("race") or "").strip()
    event_id = (request.args.get("event") or "").strip()
    slug = (request.args.get("slug") or "").strip()
    if not race_id or not event_id or not slug:
        return False

    race_data = session.get("race") or {}
    needs_refresh = (
        race_data.get("provider") != "mtec"
        or str(race_data.get("event_key") or "") != race_id
        or str(race_data.get("event_id") or "") != event_id
        or str(race_data.get("slug") or "") != slug
    )
    if not needs_refresh:
        return True

    try:
        resolution = resolve_share_url(_mtec_leaderboard_url(race_id, slug))
    except ValueError:
        return False
    if resolution.provider != "mtec" or resolution.race.event_key != race_id:
        return False
    _store_share_resolution(resolution)
    return True


def _race_from_request() -> Race | None:
    if request.args.get("rid") and request.args.get("slug"):
        if not _ensure_sportstats_context_from_query():
            return None
    if request.args.get("race") and request.args.get("event") and request.args.get("slug"):
        if not _ensure_mtec_context_from_query():
            return None
    return _race_from_session()


def _compare_template_extras(*, race: Race) -> dict[str, str]:
    if race.provider == "sportstats":
        race_data = session.get("race") or {}
        rid = request.args.get("rid") or race_data.get("rid") or race_data.get("event_key") or ""
        slug = request.args.get("slug") or race_data.get("slug") or ""
        return {
            "sportstats_rid": str(rid),
            "sportstats_slug": slug,
            "mtec_race_id": "",
            "mtec_event_id": "",
            "mtec_slug": "",
        }
    if race.provider == "mtec":
        race_data = session.get("race") or {}
        return {
            "sportstats_rid": "",
            "sportstats_slug": "",
            "mtec_race_id": str(race_data.get("event_key") or ""),
            "mtec_event_id": str(race_data.get("event_id") or ""),
            "mtec_slug": str(race_data.get("slug") or ""),
        }
    return {
        "sportstats_rid": "",
        "sportstats_slug": "",
        "mtec_race_id": "",
        "mtec_event_id": "",
        "mtec_slug": "",
    }


def _parse_pids() -> list[str]:
    raw = request.args.get("pids", "")
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def _load_athletes(provider: object, race: Race, pids: list[str]) -> list[AthleteRef]:
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


def _extract_share_link(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        return ""
    if raw.startswith(("http://", "https://")):
        return raw
    match = _URL_IN_TEXT_RE.search(raw)
    return match.group(0) if match else raw


def _import_and_redirect(ulink: str):
    try:
        resolution = resolve_share_url(ulink)
    except ValueError as exc:
        return render_template("index.html", error=str(exc)), 400

    _store_share_resolution(resolution)

    if resolution.provider == "sportstats":
        if resolution.seed_profile_id:
            provider = _provider_for_session()
            profile = provider.fetch_profile(resolution.race, resolution.seed_profile_id)
            if profile and profile.name:
                session["seed_name"] = profile.name
        params: dict[str, str] = {
            "rid": resolution.race.event_key,
            "slug": resolution.slug,
        }
        if resolution.seed_profile_id:
            params["pids"] = resolution.seed_profile_id
        return redirect(f"/compare?{urlencode(params)}")

    if resolution.provider == "mtec":
        if resolution.seed_profile_id:
            provider = _provider_for_session()
            profile = provider.fetch_profile(resolution.race, resolution.seed_profile_id)
            if profile and profile.name:
                session["seed_name"] = profile.name
        params = {
            "race": resolution.race.event_key,
            "event": resolution.event_id,
            "slug": resolution.slug,
        }
        if resolution.seed_profile_id:
            params["pids"] = resolution.seed_profile_id
        return redirect(f"/compare?{urlencode(params)}")

    creds = resolution.credentials
    if not creds:
        return render_template("index.html", error="Could not resolve RTRT credentials."), 400

    provider = RtrtProvider(RtrtClient(creds))
    profile = provider.fetch_profile(resolution.race, resolution.seed_profile_id or "")
    display_name = resolution.race.event_key
    try:
        conf = provider.fetch_conf(resolution.race.event_key)
        if title := event_display_name_from_conf(conf):
            display_name = title
    except Exception:
        pass

    race = Race(
        event_key=resolution.race.event_key,
        display_name=display_name,
        provider="rtrt",
        app_id=resolution.race.app_id,
    )
    _store_race(race)

    params = {
        "pids": resolution.seed_profile_id or "",
        "appid": resolution.race.app_id,
    }
    if profile and profile.name:
        session["seed_name"] = profile.name
    return redirect(f"/compare?{urlencode(params)}")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/share", methods=["GET"])
def share_import():
    raw_url = (request.args.get("url") or "").strip()
    raw_text = (request.args.get("text") or "").strip()
    ulink = _extract_share_link(raw_url or raw_text)
    if not ulink:
        return render_template("index.html", error="No share link found."), 400
    return _import_and_redirect(ulink)


@app.route("/import", methods=["POST"])
def import_ulink():
    ulink = (request.form.get("ulink") or "").strip()
    if not ulink:
        return render_template("index.html", error="Please paste a share link."), 400
    return _import_and_redirect(ulink)


@app.route("/manifest.webmanifest")
def manifest():
    return send_from_directory(
        app.static_folder,
        "manifest.webmanifest",
        mimetype="application/manifest+json",
    )


@app.route("/sw.js")
def service_worker():
    response = send_from_directory(app.static_folder, "sw.js", mimetype="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    response.headers["Cache-Control"] = "no-cache"
    return response


@app.route("/compare")
def compare():
    pids = _parse_pids()
    race = _race_from_request()

    if not race:
        if request.args.get("rid") and request.args.get("slug"):
            return render_template(
                "index.html",
                error="Could not load this Sportstats race. Check the link and try again.",
            ), 400
        if request.args.get("race") and request.args.get("event"):
            return render_template(
                "index.html",
                error="Could not load this MTEC race. Check the link and try again.",
            ), 400
        return redirect(url_for("index"))

    is_rtrt = race.provider == "rtrt"
    app_id = request.args.get("appid") or (race.app_id if is_rtrt else "")

    if is_rtrt and not app_id:
        return redirect(url_for("index"))

    if is_rtrt and race.app_id != app_id:
        race = Race(
            event_key=race.event_key,
            display_name=race.display_name,
            provider="rtrt",
            app_id=app_id,
        )
        _store_race(race)

    provider = _provider_for_session()

    if not pids:
        subtitle = None
        hidden_segment_ids: set[str] = set()
        if race.provider == "sportstats":
            subtitle = _sportstats_subtitle_from_session()
            hidden_segment_ids = _sportstats_hidden_segment_ids_from_session()
        elif race.provider == "mtec":
            subtitle = _mtec_subtitle_from_session()
        grid = build_grid_view(
            race,
            [],
            {},
            baseline_index=0,
            course_label=subtitle,
            available_courses=[],
            selected_course=None,
            hidden_segment_ids=hidden_segment_ids,
        )
        return render_template(
            "compare.html",
            grid=grid,
            app_id=app_id,
            empty_grid=True,
            **_compare_template_extras(race=race),
        )

    athletes = _load_athletes(provider, race, pids)
    if not athletes:
        return render_template("index.html", error="Could not load athletes for this link."), 400

    if is_rtrt:
        course_options, selected_course = _course_options(provider, race, pids[0])
        labels = provider.course_labels(race)
        course_label = labels.get(selected_course, selected_course) if selected_course else None
    else:
        course_options, selected_course = [], None
        if race.provider == "sportstats":
            course_label = _sportstats_subtitle_from_session()
        else:
            course_label = _mtec_subtitle_from_session()

    splits_by_profile = {
        athlete.profile_id: provider.fetch_splits(
            race,
            athlete.profile_id,
            entry_id=athlete.entry_id,
            course_id=selected_course,
            collapse_intermediates=False,
        )
        for athlete in athletes
    }

    hidden_segment_ids: set[str] = set()
    if is_rtrt:
        conf = provider.fetch_conf(race.event_key)
        main_segment_ids = main_point_names_from_conf(
            pointorder_for_course(conf, selected_course),
            course_id=selected_course,
        )
        hidden_segment_ids = {
            split.segment_id
            for splits in splits_by_profile.values()
            for split in splits
            if split.segment_id not in main_segment_ids
        }
    elif race.provider == "sportstats":
        hidden_segment_ids = {
            split.segment_id
            for splits in splits_by_profile.values()
            for split in splits
            if split.is_intermediate
        }
    else:
        hidden_segment_ids = {
            split.segment_id
            for splits in splits_by_profile.values()
            for split in splits
            if split.is_intermediate
        }

    grid = build_grid_view(
        race,
        athletes,
        splits_by_profile,
        baseline_index=0,
        course_label=course_label,
        available_courses=course_options,
        selected_course=selected_course,
        hidden_segment_ids=hidden_segment_ids,
    )
    return render_template(
        "compare.html",
        grid=grid,
        app_id=app_id,
        empty_grid=False,
        **_compare_template_extras(race=race),
    )


@app.route("/api/lifetime/search")
def api_lifetime_search():
    provider_name = (request.args.get("provider") or "usat").strip().lower()
    query = (request.args.get("q") or "").strip()
    if len(query) < 3:
        return jsonify({"results": []})
    try:
        provider = lifetime_provider_for(provider_name)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    try:
        results = provider.search_athletes(query)
    except UsatRateLimitError:
        return jsonify({"error": USAT_RATE_LIMIT_MESSAGE}), 429
    return jsonify({"results": [_profile_to_json(profile) for profile in results]})


@app.route("/lifetime/compare")
def lifetime_compare():
    provider_name = (request.args.get("provider") or "usat").strip().lower()
    athlete_a_id = (request.args.get("a") or "").strip()
    athlete_b_id = (request.args.get("b") or "").strip()
    if not athlete_a_id or not athlete_b_id:
        return render_template("index.html", error="Select two athletes to compare."), 400
    if athlete_a_id == athlete_b_id:
        return render_template("index.html", error="Choose two different athletes."), 400
    try:
        provider = lifetime_provider_for(provider_name)
    except ValueError as exc:
        return render_template("index.html", error=str(exc)), 400
    try:
        profile_a, results_a = provider.fetch_profile_and_results(athlete_a_id)
        profile_b, results_b = provider.fetch_profile_and_results(athlete_b_id)
    except UsatRateLimitError:
        return render_template("index.html", error=USAT_RATE_LIMIT_MESSAGE), 429
    if not profile_a or not profile_b:
        return render_template("index.html", error="Could not load one or both athletes."), 404
    matches = find_common_races(results_a, results_b)
    view = build_lifetime_compare_view(profile_a, profile_b, matches)
    return render_template("lifetime_compare.html", view=view)


_LIFETIME_PREVIEW_CACHE = os.path.join("/tmp", "lifetime_preview_view.json")


@app.route("/lifetime/preview")
def lifetime_compare_preview():
    try:
        with open(_LIFETIME_PREVIEW_CACHE, encoding="utf-8") as cache_file:
            view = json.load(cache_file)
    except FileNotFoundError:
        return render_template(
            "index.html",
            error="Preview cache missing. Fetch a comparison first while the dev server is running.",
        ), 404
    return render_template("lifetime_compare.html", view=view)


@app.route("/api/search")
def api_search():
    race = _race_from_request()
    if not race:
        return jsonify({"error": "Race context missing."}), 400

    is_rtrt = race.provider == "rtrt"
    app_id = request.args.get("appid") or (race.app_id if is_rtrt else "")
    if is_rtrt and not app_id:
        return jsonify({"error": "Race context missing."}), 400

    query = (request.args.get("q") or "").strip()
    if len(query) < 2:
        return jsonify({"results": []})

    provider = _provider_for_session()
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
    race = _race_from_request()
    if not race:
        return jsonify({"error": "Missing parameters."}), 400

    is_rtrt = race.provider == "rtrt"
    app_id = request.args.get("appid") or (race.app_id if is_rtrt else "")
    pid = (request.args.get("pid") or "").strip()
    course = request.args.get("course")
    if (is_rtrt and not app_id) or not pid:
        return jsonify({"error": "Missing parameters."}), 400

    provider = _provider_for_session()
    athlete = provider.fetch_profile(race, pid)
    if not athlete:
        return jsonify({"error": "Athlete not found."}), 404

    splits = provider.fetch_splits(
        race,
        pid,
        entry_id=athlete.entry_id,
        course_id=course,
        collapse_intermediates=False,
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
