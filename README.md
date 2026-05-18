# Head2Head

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
