from pathlib import Path
import json
import re

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

BEFORE_FILE = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "customers_raw.csv"
)

AFTER_FILE = (
    PROJECT_ROOT
    / "output"
    / "customers_clean.csv"
)

REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

VALID_PHONE_PREFIXES = {"70", "75", "76", "77", "78"}


def is_missing(value):
    return pd.isna(value) or str(value).strip() == ""


def valid_phone(value):
    if is_missing(value):
        return False

    value = str(value).strip()

    return (
        re.fullmatch(r"\d{9}", value) is not None
        and value[:2] in VALID_PHONE_PREFIXES
    )


def valid_email(value):
    if is_missing(value):
        return False

    value = str(value).strip()

    pattern = (
        r"^[A-Za-z0-9._%+-]+@"
        r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    )

    return re.fullmatch(pattern, value) is not None


def measure(df):
    phone_missing = int(
        df["phone"].apply(is_missing).sum()
    )

    phone_invalid = int(
        (
            ~df["phone"].apply(is_missing)
            & ~df["phone"].apply(valid_phone)
        ).sum()
    )

    email_missing = int(
        df["email"].apply(is_missing).sum()
    )

    email_invalid = int(
        (
            ~df["email"].apply(is_missing)
            & ~df["email"].apply(valid_email)
        ).sum()
    )

    city_missing = int(
        df["city"].apply(is_missing).sum()
    )

    duplicate_rows = int(
        df["customer_id"]
        .duplicated(keep=False)
        .sum()
    )

    duplicate_groups = int(
        df.loc[
            df["customer_id"].duplicated(
                keep=False
            ),
            "customer_id",
        ].nunique()
    )

    return {
        "rows": int(len(df)),
        "unique_customer_ids": int(
            df["customer_id"].nunique()
        ),
        "duplicate_rows": duplicate_rows,
        "duplicate_groups": duplicate_groups,
        "phone_missing": phone_missing,
        "phone_invalid_or_nonstandard": phone_invalid,
        "email_missing": email_missing,
        "email_invalid": email_invalid,
        "city_missing": city_missing,
    }


def reduction(before, after):
    if before == 0:
        return 0.0

    return round(
        (before - after) / before * 100,
        2,
    )


def main():
    before_df = pd.read_csv(BEFORE_FILE)
    after_df = pd.read_csv(AFTER_FILE)

    before = measure(before_df)
    after = measure(after_df)

    comparison = {
        "before": before,
        "after": after,
        "improvements": {
            "rows_removed_as_duplicates":
                before["rows"] - after["rows"],

            "duplicate_rows_reduction_percent":
                reduction(
                    before["duplicate_rows"],
                    after["duplicate_rows"],
                ),

            "phone_format_issues_reduction_percent":
                reduction(
                    before[
                        "phone_invalid_or_nonstandard"
                    ],
                    after[
                        "phone_invalid_or_nonstandard"
                    ],
                ),

            "email_invalid_reduction_percent":
                reduction(
                    before["email_invalid"],
                    after["email_invalid"],
                ),
        },
    }

    json_file = (
        REPORTS_DIR
        / "before_after_comparison.json"
    )

    text_file = (
        REPORTS_DIR
        / "before_after_comparison.txt"
    )

    with open(
        json_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            comparison,
            file,
            ensure_ascii=False,
            indent=2,
        )

    with open(
        text_file,
        "w",
        encoding="utf-8",
    ) as file:
        file.write(
            "DATA CLEANING — BEFORE VS AFTER\n"
        )
        file.write("=" * 45 + "\n\n")

        file.write(
            f"{'METRIC':35}"
            f"{'BEFORE':>10}"
            f"{'AFTER':>10}\n"
        )

        file.write("-" * 55 + "\n")

        metrics = [
            ("Rows", "rows"),
            (
                "Unique customer IDs",
                "unique_customer_ids",
            ),
            (
                "Rows in duplicate groups",
                "duplicate_rows",
            ),
            (
                "Duplicate ID groups",
                "duplicate_groups",
            ),
            (
                "Missing phones",
                "phone_missing",
            ),
            (
                "Invalid/nonstandard phones",
                "phone_invalid_or_nonstandard",
            ),
            (
                "Missing emails",
                "email_missing",
            ),
            (
                "Invalid emails",
                "email_invalid",
            ),
            (
                "Missing cities",
                "city_missing",
            ),
        ]

        for label, key in metrics:
            file.write(
                f"{label:35}"
                f"{before[key]:>10}"
                f"{after[key]:>10}\n"
            )

        file.write("\nIMPROVEMENTS\n")
        file.write("-" * 55 + "\n")

        for key, value in comparison[
            "improvements"
        ].items():
            file.write(
                f"{key}: {value}\n"
            )

    print("Before/after comparison completed.")
    print()

    print(
        f"{'METRIC':35}"
        f"{'BEFORE':>10}"
        f"{'AFTER':>10}"
    )

    print("-" * 55)

    for label, key in [
        ("Rows", "rows"),
        (
            "Unique customer IDs",
            "unique_customer_ids",
        ),
        (
            "Rows in duplicate groups",
            "duplicate_rows",
        ),
        (
            "Invalid/nonstandard phones",
            "phone_invalid_or_nonstandard",
        ),
        (
            "Invalid emails",
            "email_invalid",
        ),
    ]:
        print(
            f"{label:35}"
            f"{before[key]:>10}"
            f"{after[key]:>10}"
        )

    print()
    print(f"Report: {text_file}")


if __name__ == "__main__":
    main()