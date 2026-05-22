# Head2Head

[![Deploy to Fly.io](https://github.com/Tapin42/head2head/actions/workflows/deploy-fly.yml/badge.svg)](https://github.com/Tapin42/head2head/actions/workflows/deploy-fly.yml)

Compare RTRT.me athlete splits side-by-side from a share link.

## Local development

```bash
cd ../racedata && pip install -e ".[dev]"
cd ../head2head && pip install -r requirements.txt
export FLASK_APP=app.py
flask run --port 8080
```

## Tests

```bash
pytest
```

## Fly.io deploy

Vendor the sibling `racedata` package into the Docker build context, then deploy:

```bash
./scripts/vendor-racedata.sh
fly deploy
```

Set `SECRET_KEY` in Fly secrets for production sessions.

## Usage

1. Open `/` and paste an RTRT ulink (e.g. `https://rtrt.me/ulink/.../tracker/.../focus`).
2. The shared athlete loads as the baseline row.
3. Search by name or bib to add competitors.
4. Drag rows to change the baseline athlete.
5. Share the URL — `pids` order determines row order (`pids[0]` = baseline).

## Share from other apps (Android)

1. Open Head2Head in **Chrome**.
2. Tap **Install** when the banner appears (or Chrome menu → **Install app**).
3. In RTRT or Sportstats, tap **Share** on a race link and choose **Head2Head**.

Works after the one-time install. No Play Store needed.

## License

MIT License. See [LICENSE](LICENSE).
