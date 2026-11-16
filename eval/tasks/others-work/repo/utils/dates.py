import calendar
import datetime


def parse_date(text):
    return datetime.datetime.strptime(text.strip(), "%Y-%m-%d").date()


def month_bounds(day):
    last = calendar.monthrange(day.year, day.month)[1]
    return day.replace(day=1), day.replace(day=last)


def add_months(day, months):
    total = day.month + months
    year = day.year + total // 12
    month = total % 12
    last = calendar.monthrange(year, month)[1]
    return datetime.date(year, month, min(day.day, last))


def quarter(day):
    return (day.month - 1) // 3 + 1


def business_days_between(start, end):
    count = 0
    current = start
    while current < end:
        if current.weekday() < 5:
            count += 1
        current += datetime.timedelta(days=1)
    return count
