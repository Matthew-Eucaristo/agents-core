# Export formats

`salesreport` can print an order report in three formats. Pick one with the
`--format` option:

```
python3 -m salesreport samples/orders.json --format csv
```

| Format | Function  | Class          | Notes                                   |
| ------ | --------- | -------------- | --------------------------------------- |
| text   | `to_text` | `TextExporter` | Aligned table, the default              |
| json   | `to_json` | `JsonExporter` | Array with one object per row           |
| csv    | `to_csv`  | `CsvExporter`  | Header line, RFC 4180 quoting           |

## CSV details

- The first line holds the column names in the order they first appear.
- Cells with a comma, a double quote or a line break are quoted.
- A double quote inside a cell is written twice.
- A missing cell is left empty.
- No rows gives an empty string.

## Adding a format

1. Write a class that derives from `Exporter` and implements `export(rows)`.
2. Decorate it with `@register_exporter("<format>")`.
3. Add a `to_<format>(rows)` wrapper so the command line can find it.
4. Add tests to `tests/test_exporter.py`.
