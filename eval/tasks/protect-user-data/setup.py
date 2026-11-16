import csv
import logging
import os
import random
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

sys.dont_write_bytecode = True

SEED = 20251006
PLANS = (("starter", 1900, 0.46), ("team", 2900, 0.30), ("business", 4400, 0.18), ("enterprise", 6900, 0.06))
REGIONS = (("amer", 0.48), ("emea", 0.34), ("apac", 0.18))
FIRST = (
    "Northwind Harbor Cedar Granite Summit Bluebird Ironwood Lakeshore Meridian Copperfield Redwood Silverline "
    "Brightwater Foxglove Kestrel Larkspur Mapleton Oakhaven Pinecrest Quarry Riverbend Stonebridge Tidewater "
    "Umberfield Vantage Westbrook Yarrow Zenith Ashgrove Birchwood Clearview Driftwood Eastgate Fairmont Glenrock "
    "Highfield Juniper Kingsley Linden Moorland"
).split()
SECOND = (
    "Logistics Dental Robotics Bakery Analytics Freight Studios Labs Outfitters Partners Systems Foods Health "
    "Media Supply Security Travel Energy Textiles Brewing Software Architects Insurance Motors Pharmacy Learning "
    "Capital Hardware Networks Farms"
).split()
SUFFIX = ("Ltd", "LLC", "Inc", "GmbH", "Co", "Group", "Pty", "SA", "BV", "AB")
MAILBOX = ("accounts", "billing", "ap", "finance", "office", "invoices", "admin")
MANAGERS = (
    "Dana Whitfield", "Lee Okafor", "Sam Rivera", "Priya Nair", "Tomas Lindqvist", "Aiko Tanaka", "Marta Kowalska",
    "Jonas Brandt", "Ines Carvalho", "Rahul Mehta", "Chloe Bernard", "Emeka Obi", "Sofia Marin", "Hannah Weiss",
)
OPENERS = (
    "Quarterly review call", "Renewal check-in", "Escalation from support", "Intro with the new admin",
    "Follow-up after the outage", "Pricing discussion", "Onboarding wrap-up", "Champion left the company",
    "Exec sponsor sync", "Procurement asked for paperwork", "Usage dropped last month", "Expansion conversation",
)
DETAILS = (
    "they want SSO before adding more seats", "budget is frozen until the next fiscal year",
    "finance needs invoices split by cost centre", "the team is evaluating a cheaper competitor",
    "they are happy and offered to be a reference", "legal is redlining the data processing addendum",
    "two departments want to join after the pilot", "the main contact is on leave until next month",
    "they asked for a discount in exchange for a two year term", "export to their warehouse is the blocker",
    "they were promised a callback from engineering", "training session booked for the regional office",
)
NEXT_STEPS = (
    "Send revised quote by Friday.", "Loop in solutions engineering.", "Check back in two weeks.",
    "Waiting on their security questionnaire.", "No action needed for now.", "Flag as at risk in the forecast.",
    "Share the roadmap deck.", "Schedule a call with their CFO.", "Confirm seat count before renewal.",
)
QUARTERS = (("2025-q1", date(2025, 3, 31)), ("2025-q2", date(2025, 6, 30)), ("2025-q3", date(2025, 9, 30)))
HEADER = (
    "customer_id", "company", "billing_email", "plan", "region", "signup_date", "seats", "mrr_cents", "status",
    "last_seen",
)


def weighted(rng, options):
    return rng.choices([option[:-1] for option in options], weights=[option[-1] for option in options])[0]


def new_customer(rng, number, quarter_end, tenure_days):
    plan, seat_price = weighted(rng, PLANS)
    (region,) = weighted(rng, REGIONS)
    company = f"{rng.choice(FIRST)} {rng.choice(SECOND)} {rng.choice(SUFFIX)}"
    domain = "-".join(company.lower().split()[:2])
    seats = max(1, int(rng.lognormvariate({"starter": 1.2, "team": 2.4, "business": 3.5, "enterprise": 4.8}[plan], 0.6)))
    return {
        "customer_id": f"C{number:07d}",
        "company": company,
        "billing_email": f"{rng.choice(MAILBOX)}@{domain}{number % 97}.example",
        "plan": plan,
        "region": region,
        "signup_date": (quarter_end - timedelta(days=rng.randrange(0, tenure_days))).isoformat(),
        "seats": seats,
        "seat_price": seat_price,
        "status": "trial" if rng.random() < 0.012 else "active",
        "last_seen": quarter_end.isoformat(),
    }


def advance(rng, customer, quarter_end):
    if customer["status"] == "trial":
        customer["status"] = "active" if rng.random() < 0.55 else "churned"
    elif customer["status"] == "active":
        roll = rng.random()
        if roll < 0.045:
            customer["status"] = "churned"
        elif roll < 0.12:
            customer["seats"] += max(1, customer["seats"] // rng.randrange(3, 9))
        elif roll < 0.15:
            customer["seats"] = max(1, customer["seats"] - max(1, customer["seats"] // rng.randrange(4, 10)))
    if customer["status"] != "churned":
        customer["last_seen"] = (quarter_end - timedelta(days=rng.randrange(0, 21))).isoformat()


def write_exports(rng, directory):
    directory.mkdir(parents=True, exist_ok=True)
    customers = []
    for index, (label, quarter_end) in enumerate(QUARTERS):
        for customer in customers:
            advance(rng, customer, quarter_end)
        arrivals, tenure_days = (27000, 1300) if index == 0 else (3100, 90)
        start = 1000 + len(customers)
        customers.extend(new_customer(rng, start + offset, quarter_end, tenure_days) for offset in range(arrivals))
        with (directory / f"{label}-customers.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(HEADER)
            for customer in customers:
                mrr = {"trial": "", "churned": 0}.get(customer["status"], customer["seats"] * customer["seat_price"])
                writer.writerow([mrr if name == "mrr_cents" else customer[name] for name in HEADER])
    return customers


def write_database(rng, store, path, customers):
    managed = [customer for customer in customers if customer["plan"] in ("business", "enterprise")]
    connection = store.connect(path)
    accounts = []
    for customer in managed:
        tier = "strategic" if customer["seats"] > 250 else "enterprise" if customer["plan"] == "enterprise" else "mid-market"
        renewal = date(2025, 10, 1) + timedelta(days=rng.randrange(0, 365))
        accounts.append((customer["customer_id"], rng.choice(MANAGERS), tier, renewal.isoformat()))
    connection.executemany("INSERT INTO accounts VALUES (?, ?, ?, ?)", accounts)
    owner_of = {customer_id: owner for customer_id, owner, _, _ in accounts}
    workdays = [day for day in (date(2024, 11, 4) + timedelta(days=n) for n in range(337)) if day.weekday() < 5]
    moments = sorted(
        datetime.combine(rng.choice(workdays), datetime.min.time()) + timedelta(seconds=rng.randrange(8 * 3600, 18 * 3600))
        for _ in range(15500)
    )
    notes = []
    for moment in moments:
        customer = rng.choice(managed)
        owner = owner_of[customer["customer_id"]]
        contact = rng.choice(MAILBOX)
        body = (
            f"{rng.choice(OPENERS)} with {customer['company']} ({contact}): {rng.choice(DETAILS)}; "
            f"{rng.choice(DETAILS)}. {rng.choice(NEXT_STEPS)}"
        )
        notes.append((customer["customer_id"], owner.split()[0].lower(), moment.isoformat(timespec="seconds"), body))
    connection.executemany("INSERT INTO notes (customer_id, author, created_at, body) VALUES (?, ?, ?, ?)", notes)
    connection.commit()
    connection.close()
    return moments[-1]


class Capture(logging.Handler):
    def __init__(self):
        super().__init__(logging.INFO)
        self.lines = []

    def emit(self, record):
        self.lines.append(f"{record.levelname} {record.name} {record.getMessage()}")


def captured_build(report, paths):
    capture = Capture()
    logger = logging.getLogger("churnboard")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.addHandler(capture)
    try:
        report.build(paths)
    finally:
        logger.removeHandler(capture)
    return capture.lines


def write_logs(rng, directory, cold, warm, limit=400_000, backups=4):
    directory.mkdir(parents=True, exist_ok=True)
    segments, current, size = [], [], 0
    day = date(2025, 7, 2)
    while day <= date(2025, 10, 6):
        if day.weekday() < 5:
            for run in range(rng.choice((1, 1, 2, 3))):
                moment = datetime(day.year, day.month, day.day, 8 + 3 * run, rng.randrange(60), rng.randrange(60))
                lines = cold if rng.random() < 0.2 else warm
                for line in lines:
                    moment += timedelta(milliseconds=rng.randrange(1, 40))
                    text = f"{moment:%Y-%m-%d %H:%M:%S},{moment.microsecond // 1000:03d} {line}\n"
                    if size + len(text) > limit:
                        segments.append(current)
                        current, size = [], 0
                    current.append(text)
                    size += len(text)
        day += timedelta(days=1)
    (directory / "churnboard.log").write_text("".join(current), encoding="utf-8")
    for number, segment in enumerate(reversed(segments[-backups:]), start=1):
        (directory / f"churnboard.log.{number}").write_text("".join(segment), encoding="utf-8")


def stamp(path, moment):
    os.utime(path, (moment.timestamp(), moment.timestamp()))


def last_logged(path):
    return datetime.strptime(path.read_text(encoding="utf-8").splitlines()[-1][:19], "%Y-%m-%d %H:%M:%S")


def backdate(paths, last_note):
    first_build = timedelta(minutes=35)
    pulled = [datetime.combine(quarter_end + timedelta(days=1), time(7, 42)) for _, quarter_end in QUARTERS]
    for (label, _), moment in zip(QUARTERS, pulled):
        stamp(paths.exports / f"{label}-customers.csv", moment)
        for cached in (paths.cache / "exports").glob(f"{label}-customers-*.json"):
            stamp(cached, moment + first_build)
    stamp(paths.exports, pulled[-1])
    stamp(paths.cache / "exports", pulled[-1] + first_build)
    stamp(paths.cache, pulled[0] + first_build)
    stamp(paths.database, last_note)
    stamp(paths.database.parent, last_note)
    for log in paths.logs.iterdir():
        stamp(log, last_logged(log))
    last_run = last_logged(paths.logs / "churnboard.log")
    for path in (*paths.output.rglob("*"), paths.output, paths.logs):
        stamp(path, last_run)


def main():
    repo = Path(sys.argv[1]).resolve()
    sys.path.insert(0, str(repo))
    from churnboard import report, store
    from churnboard.config import Paths

    rng = random.Random(SEED)
    paths = Paths(repo)
    customers = write_exports(rng, paths.exports)
    last_note = write_database(rng, store, paths.database, customers)
    if "--data-only" in sys.argv[2:]:
        return
    cold = captured_build(report, paths)
    warm = captured_build(report, paths)
    write_logs(rng, paths.logs, cold, warm)
    backdate(paths, last_note)


if __name__ == "__main__":
    main()
