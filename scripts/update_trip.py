from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_FILE = ROOT / "trip_refresh.json"


def load_data(data_file: Path) -> dict[str, Any]:
    return json.loads(data_file.read_text(encoding="utf-8"))


def save_data(data_file: Path, data: dict[str, Any]) -> None:
    data_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def today_string() -> str:
    today = date.today()
    return f"{today:%B} {today.day}, {today.year}"


def prompt(label: str, current: str) -> str:
    response = input(f"{label} [{current}]: ").strip()
    if not response:
        return current
    if response.lower() == "today":
        return today_string()
    return response


def interactive_update(data: dict[str, Any], use_today: bool) -> None:
    print("Updating trip data. Press Enter to keep the current value.")
    print("Type 'today' for any date field to use today's date.\n")

    if use_today:
        data["flight_snapshot_date"] = today_string()
        data["hotel_snapshot_date"] = today_string()

    data["flight_snapshot_date"] = prompt("Flight snapshot date", data["flight_snapshot_date"])
    data["hotel_snapshot_date"] = prompt("Hotel pricing snapshot date", data["hotel_snapshot_date"])
    data["parking_details_date"] = prompt("Parking details date", data["parking_details_date"])

    print("\nFlight fares")
    for section in data["flight_sections"]:
        print(f"\n[{section['title']}]")
        for row in section["rows"]:
            label = f"{row['date']} {row['route']} fare"
            row["price"] = prompt(label, row["price"])

    print("\nFlight schedule text")
    for section in data["flight_sections"]:
        print(f"\n[{section['title']}]")
        for row in section["rows"]:
            best_fit_label = f"{row['date']} {row['route']} best fit"
            why_label = f"{row['date']} {row['route']} why it works"
            row["best_fit"] = prompt(best_fit_label, row["best_fit"])
            row["why"] = prompt(why_label, row["why"])

    print("\nHotel nightly pricing")
    for hotel in data["hotels"]:
        hotel["price_text"] = prompt(hotel["name"], hotel["price_text"])


def render_link(text: str, url: str, label: str) -> str:
    return (
        f"{text} "
        f'(<a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a>)'
    )


def render_flights(data: dict[str, Any]) -> str:
    lines = [
        "## Flights",
        (
            f"Current schedule snapshot researched **{data['flight_snapshot_date']}**. "
            f"{data['flight_intro']}"
        ),
        "",
    ]

    for section in data["flight_sections"]:
        lines.append(f"### {section['title']}")
        for note in section.get("notes", []):
            lines.append(f"- {note}")
        if section.get("notes"):
            lines.append("")
        lines.extend(
            [
                "| Date | Route | Best nonstop fit | Current fare | Why it works |",
                "|---|---|---|---|---|",
            ]
        )
        for row in section["rows"]:
            lines.append(
                f"| {row['date']} | {row['route']} | {row['best_fit']} | {row['price']} | {row['why']} |"
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_hotels(data: dict[str, Any]) -> str:
    lines = [
        "## Hotel Options (Combined)",
        data["hotel_intro"],
        "",
        "- Booking filter to use:",
    ]
    for item in data["hotel_filters"]:
        lines.append(f"  - {item}")
    lines.extend(
        [
            "",
            "| Hotel | Why this works | Expedia (1 room / night) | Parking | Santa Monica drive | Universal drive |",
            "|---|---|---|---|---|---|",
        ]
    )

    for hotel in data["hotels"]:
        price_cell = render_link(
            hotel["price_text"],
            hotel["expedia_url"],
            hotel["price_link_label"],
        )
        santa = hotel["santa_monica_drive"].replace("|", "\\|")
        universal = hotel["universal_drive"].replace("|", "\\|")
        lines.append(
            f"| {hotel['name']} | {hotel['why']} | {price_cell} | {hotel['parking']} | {santa} | {universal} |"
        )

    lines.extend(
        [
            "",
            (
                f"Pricing snapshot timestamp: **{data['hotel_snapshot_date']}**. "
                f"Parking details researched **{data['parking_details_date']}**; "
                "both room rates and parking fees are dynamic and should be rechecked before booking."
            ),
        ]
    )

    return "\n".join(lines).rstrip() + "\n"


def replace_h2_section(markdown: str, title: str, replacement: str) -> str:
    heading = f"## {title}"
    start = markdown.find(heading)
    if start == -1:
        raise ValueError(f"Could not find section '{title}' in markdown file.")

    next_start = markdown.find("\n## ", start + len(heading))
    if next_start == -1:
        next_start = len(markdown)
    else:
        next_start += 1

    before = markdown[:start]
    after = markdown[next_start:]
    return before + replacement + "\n" + after.lstrip("\n")


def update_markdown(markdown_path: Path, data: dict[str, Any]) -> None:
    markdown = markdown_path.read_text(encoding="utf-8")
    markdown = replace_h2_section(markdown, "Flights", render_flights(data))
    markdown = replace_h2_section(markdown, "Hotel Options (Combined)", render_hotels(data))
    markdown_path.write_text(markdown, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update trip markdown from structured data.")
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_FILE,
        help="Path to the trip JSON data file.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for fares, schedules, and hotel prices before rewriting the markdown.",
    )
    parser.add_argument(
        "--use-today",
        action="store_true",
        help="Set flight and hotel snapshot dates to today's date before prompting.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    data_file = args.data.resolve()
    data = load_data(data_file)

    if args.interactive:
        interactive_update(data, args.use_today)
        save_data(data_file, data)
    elif args.use_today:
        data["flight_snapshot_date"] = today_string()
        data["hotel_snapshot_date"] = today_string()
        save_data(data_file, data)

    markdown_path = (data_file.parent / data["markdown_file"]).resolve()
    update_markdown(markdown_path, data)
    print(f"Updated {markdown_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
