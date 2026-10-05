from pathlib import Path
import json

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ANOMALIES_FILE = (
    PROJECT_ROOT / "reports" / "injected_anomalies.csv"
)

CHANGES_FILE = (
    PROJECT_ROOT / "reports" / "cleaning_change_log.csv"
)

REVIEW_FILE = (
    PROJECT_ROOT / "output" / "records_for_review.csv"
)

REPORTS_DIR = PROJECT_ROOT / "reports"


def load_data():
    return (
        pd.read_csv(ANOMALIES_FILE),
        pd.read_csv(CHANGES_FILE),
        pd.read_csv(REVIEW_FILE),
    )


def build_change_keys(changes):
    return set(
        zip(
            changes["customer_id"].astype(str),
            changes["column"].astype(str),
        )
    )


def build_review_keys(review):
    keys = set()

    if "review_reason" not in review.columns:
        return keys

    for _, row in review.iterrows():
        customer_id = str(row["customer_id"])

        reasons = str(
            row.get("review_reason", "")
        ).split(";")

        for reason in reasons:
            reason = reason.strip()

            if not reason or ":" not in reason:
                continue

            field, _ = reason.split(":", 1)

            keys.add(
                (
                    customer_id,
                    field.strip(),
                )
            )

    return keys


def classify_events(
    anomalies,
    change_keys,
    review_keys,
):
    results = []

    for _, event in anomalies.iterrows():

        customer_id = str(
            event["customer_id"]
        )

        column = str(
            event["column"]
        )

        key = (
            customer_id,
            column,
        )

        if key in change_keys:
            outcome = "automatically_corrected"

        elif key in review_keys:
            outcome = "flagged_for_review"

        else:
            outcome = "not_actioned"

        results.append(
            {
                "customer_id":
                    customer_id,

                "column":
                    column,

                "anomaly_type":
                    event["anomaly_type"],

                "outcome":
                    outcome,
            }
        )

    return pd.DataFrame(results)


def find_unexpected_changes(
    anomalies,
    changes,
):
    injected_keys = set(
        zip(
            anomalies[
                "customer_id"
            ].astype(str),

            anomalies[
                "column"
            ].astype(str),
        )
    )

    unexpected = changes[
        ~changes.apply(
            lambda row: (
                str(row["customer_id"]),
                str(row["column"]),
            ) in injected_keys,
            axis=1,
        )
    ].copy()

    return unexpected


def build_report(
    event_results,
    unexpected_changes,
):
    outcome_counts = (
        event_results["outcome"]
        .value_counts()
        .to_dict()
    )

    total = len(event_results)

    corrected = outcome_counts.get(
        "automatically_corrected",
        0,
    )

    reviewed = outcome_counts.get(
        "flagged_for_review",
        0,
    )

    not_actioned = outcome_counts.get(
        "not_actioned",
        0,
    )

    addressed = corrected + reviewed

    return {
        "total_injected_events":
            int(total),

        "automatically_corrected":
            int(corrected),

        "flagged_for_review":
            int(reviewed),

        "not_actioned":
            int(not_actioned),

        "addressed_events":
            int(addressed),

        "addressed_rate_percent":
            round(
                addressed / total * 100,
                2,
            )
            if total
            else 0.0,

        "automatic_correction_rate_percent":
            round(
                corrected / total * 100,
                2,
            )
            if total
            else 0.0,

        "review_rate_percent":
            round(
                reviewed / total * 100,
                2,
            )
            if total
            else 0.0,

        "unexpected_normalization_operations":
            int(len(unexpected_changes)),
    }


def main():
    print(
        "Validating injected anomaly events..."
    )
    print()

    (
        anomalies,
        changes,
        review,
    ) = load_data()

    change_keys = build_change_keys(
        changes
    )

    review_keys = build_review_keys(
        review
    )

    event_results = classify_events(
        anomalies,
        change_keys,
        review_keys,
    )

    unexpected_changes = (
        find_unexpected_changes(
            anomalies,
            changes,
        )
    )

    report = build_report(
        event_results,
        unexpected_changes,
    )

    event_file = (
        REPORTS_DIR
        / "anomaly_event_results.csv"
    )

    unexpected_file = (
        REPORTS_DIR
        / "unexpected_changes.csv"
    )

    json_file = (
        REPORTS_DIR
        / "anomaly_event_validation.json"
    )

    text_file = (
        REPORTS_DIR
        / "anomaly_event_validation.txt"
    )

    event_results.to_csv(
        event_file,
        index=False,
        encoding="utf-8-sig",
    )

    unexpected_changes.to_csv(
        unexpected_file,
        index=False,
        encoding="utf-8-sig",
    )

    with open(
        json_file,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
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
            "ANOMALY EVENT VALIDATION\n"
        )

        file.write(
            "=" * 50 + "\n\n"
        )

        for key, value in report.items():
            file.write(
                f"{key}: {value}\n"
            )

    print(
        "Validation completed."
    )
    print()

    for key, value in report.items():
        print(
            f"{key}: {value}"
        )

    print()
    print(
        f"Report: {text_file}"
    )

    print(
        f"Unexpected changes: "
        f"{unexpected_file}"
    )


if __name__ == "__main__":
    main()