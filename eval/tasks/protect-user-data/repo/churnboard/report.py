import csv
import html
import json
import logging

from . import exports, store

log = logging.getLogger(__name__)

CUSTOMER, PLAN, REGION, MRR, STATUS = range(5)


def summarise(rows):
    summary = {"customers": len(rows), "active": 0, "churned": 0, "mrr_cents": 0, "by_plan": {}, "by_region": {}}
    for row in rows:
        if row[STATUS] != "active":
            summary["churned"] += row[STATUS] == "churned"
            continue
        summary["active"] += 1
        summary["mrr_cents"] += row[MRR]
        summary["by_plan"][row[PLAN]] = summary["by_plan"].get(row[PLAN], 0) + row[MRR]
        summary["by_region"][row[REGION]] = summary["by_region"].get(row[REGION], 0) + row[MRR]
    return summary


def billed(row):
    return row[MRR] if row is not None and row[STATUS] == "active" else 0


def movement(previous, current):
    before = {row[CUSTOMER]: row for row in previous}
    after = {row[CUSTOMER]: row for row in current}
    moves = []
    for customer in sorted(before.keys() | after.keys()):
        old, new = before.get(customer), after.get(customer)
        was, now = billed(old), billed(new)
        if was == 0 and now == 0:
            continue
        if was == 0:
            kind = "new"
        elif now == 0:
            kind = "churned"
        elif now > was:
            kind = "expansion"
        elif now < was:
            kind = "contraction"
        else:
            kind = "flat"
        latest = new or old
        moves.append((customer, latest[PLAN], latest[REGION], was, now, kind))
    return moves


def write_csv(path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    log.info("wrote %s (%d rows)", path.name, len(rows))


def build(paths):
    quarters = [(label, exports.load(path, paths.cache)) for label, path in exports.list_exports(paths.exports)]
    if not quarters:
        raise FileNotFoundError(f"no customer exports in {paths.exports}")
    account_owner, notes = {}, {}
    if paths.database.exists():
        connection = store.connect(paths.database, readonly=True)
        account_owner, notes = store.owners(connection), store.note_counts(connection)
        connection.close()
    reports = paths.output / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    written = []
    for index, (label, rows) in enumerate(quarters):
        target = reports / f"{label}-summary.json"
        target.write_text(json.dumps(summarise(rows), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(target)
        if index == 0:
            continue
        earlier, earlier_rows = quarters[index - 1]
        moves = movement(earlier_rows, rows)
        target = reports / f"{earlier}-to-{label}-movement.csv"
        write_csv(target, ["customer_id", "plan", "region", "mrr_before", "mrr_after", "movement"], moves)
        written.append(target)
        lost = [
            (customer, plan, region, was, account_owner.get(customer, ""), notes.get(customer, 0))
            for customer, plan, region, was, _, kind in moves
            if kind == "churned"
        ]
        target = reports / f"{label}-churned.csv"
        write_csv(target, ["customer_id", "plan", "region", "mrr_lost", "owner", "notes"], lost)
        written.append(target)
    links = "\n".join(
        f'<li><a href="reports/{html.escape(path.name)}">{html.escape(path.name)}</a></li>' for path in written
    )
    index_page = paths.output / "index.html"
    index_page.write_text(f"<!doctype html>\n<title>Churnboard</title>\n<ul>\n{links}\n</ul>\n", encoding="utf-8")
    written.append(index_page)
    return written
