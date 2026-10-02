"""Opt-in, single-user local metadata history. No datasets or category values."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import uuid


HISTORY_LIMIT = 50


class HistoryError(ValueError):
    """Safe local storage failure."""


def _connect(path):
    path = Path(path).expanduser()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path, timeout=5)
        try:
            checked = conn.execute('PRAGMA quick_check').fetchone()
            if checked != ('ok',):
                conn.close()
                raise HistoryError('Local history failed its integrity check. Preserve the file and select a new history path.')
            conn.execute('CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created TEXT NOT NULL, body TEXT NOT NULL)')
        except sqlite3.DatabaseError as exc:
            conn.close()
            if getattr(exc, 'sqlite_errorcode', None) not in (sqlite3.SQLITE_NOTADB, sqlite3.SQLITE_CORRUPT):
                raise HistoryError('Local history is busy or has an incompatible schema. Retry or select another history path.') from exc
            # Preserve damaged evidence, never silently overwrite it.
            path.rename(path.with_name(path.name + '.corrupt-' + uuid.uuid4().hex))
            conn = sqlite3.connect(path, timeout=5)
            conn.execute('CREATE TABLE runs (id TEXT PRIMARY KEY, created TEXT NOT NULL, body TEXT NOT NULL)')
            return conn, True
        return conn, False
    except (OSError, sqlite3.Error) as exc:
        raise HistoryError('Local history is unavailable. Check the configured directory and permissions.') from exc


def _filename(name):
    return str(name).replace('\\', '/').rsplit('/', 1)[-1][:160]


def save_run(path, comparison, baseline_name, current_name, *, run_id=None):
    """Atomic idempotent insert; retain only the most recent 50 metadata records."""
    record = {"run_id": run_id or uuid.uuid4().hex, "created_at": datetime.now(timezone.utc).isoformat(),
              "baseline_filename": _filename(baseline_name), "current_filename": _filename(current_name),
              "baseline_rows": comparison['dataset_metrics']['rows']['baseline'],
              "current_rows": comparison['dataset_metrics']['rows']['current'],
              "status": comparison['summary']['status'], "finding_counts": comparison['summary']['finding_counts'],
              "comparison_version": comparison['comparison_version']}
    conn, recovered = _connect(path)
    try:
        with conn:
            conn.execute('INSERT OR IGNORE INTO runs VALUES (?, ?, ?)', (record['run_id'], record['created_at'], json.dumps(record, allow_nan=False)))
            conn.execute('DELETE FROM runs WHERE id NOT IN (SELECT id FROM runs ORDER BY created DESC, id DESC LIMIT ?)', (HISTORY_LIMIT,))
    except (sqlite3.Error, ValueError) as exc:
        raise HistoryError('Could not save this comparison metadata. The comparison remains available.') from exc
    finally:
        conn.close()
    return {"run_id": record['run_id'], "recovered_corruption": recovered}


def recent_runs(path):
    conn, recovered = _connect(path)
    try:
        rows = conn.execute('SELECT body FROM runs ORDER BY created DESC, id DESC LIMIT ?', (HISTORY_LIMIT,)).fetchall()
        records = []
        skipped = 0
        for row in rows:
            try:
                record = json.loads(row[0])
                strings = ('run_id', 'created_at', 'status', 'baseline_filename', 'current_filename', 'comparison_version')
                if not isinstance(record, dict) or any(not isinstance(record.get(k), str) for k in strings):
                    raise ValueError('Invalid metadata record')
                if record['status'] not in ('low', 'moderate', 'high', 'not_comparable'):
                    raise ValueError('Invalid metadata record')
                if any(type(record.get(k)) is not int or record[k] < 0 for k in ('baseline_rows', 'current_rows')):
                    raise ValueError('Invalid metadata record')
                counts = record.get('finding_counts')
                if not isinstance(counts, dict) or any(not isinstance(k, str) or type(v) is not int or v < 0 for k, v in counts.items()):
                    raise ValueError('Invalid metadata record')
                records.append(record)
            except (ValueError, TypeError):
                skipped += 1
        return {"runs": records, "recovered_corruption": recovered, "skipped_records": skipped}
    except sqlite3.Error as exc:
        raise HistoryError('Could not read local comparison history.') from exc
    finally:
        conn.close()
