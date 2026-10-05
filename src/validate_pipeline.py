from pathlib import Path
import json

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_FILE = (
    PROJECT_ROOT / "data" / "raw" / "customers_raw.csv"
)

CLEAN_FILE = (
    PROJECT_ROOT / "output" / "customers_clean.csv"
)

REVIEW_FILE = (
    PROJECT_ROOT / "output" / "records_for_review.csv"
)

REMOVED_FILE = (
    PROJECT_ROOT / "output" / "duplicates_removed.csv"
)

ANOMALIES_FILE = (
    PROJECT_ROOT / "reports" / "injected_anomalies.csv"
)

CHANGE_LOG_FILE = (
    PROJECT_ROOT / "reports" / "cleaning_change_log.csv"
)

REPORTS_DIR = PROJECT_ROOT / "reports"


# ============================================================
# CHARGEMENT
# ============================================================

def load_files():
    return {
        "raw": pd.read_csv(RAW_FILE),
        "clean": pd.read_csv(CLEAN_FILE),
        "review": pd.read_csv(REVIEW_FILE),
        "removed": pd.read_csv(REMOVED_FILE),
        "anomalies": pd.read_csv(ANOMALIES_FILE),
        "changes": pd.read_csv(CHANGE_LOG_FILE),
    }


# ============================================================
# VALIDATION
# ============================================================

def validate(files):
    raw = files["raw"]
    clean = files["clean"]
    review = files["review"]
    removed = files["removed"]
    anomalies = files["anomalies"]
    changes = files["changes"]

    # --------------------------------------------------------
    # INTÉGRITÉ DES CLIENTS
    # --------------------------------------------------------

    raw_unique_ids = set(
        raw["customer_id"].dropna().astype(str)
    )

    clean_unique_ids = set(
        clean["customer_id"].dropna().astype(str)
    )

    lost_customer_ids = sorted(
        raw_unique_ids - clean_unique_ids
    )

    unexpected_customer_ids = sorted(
        clean_unique_ids - raw_unique_ids
    )

    # --------------------------------------------------------
    # DOUBLONS
    # --------------------------------------------------------

    remaining_duplicate_rows = int(
        clean["customer_id"]
        .duplicated(keep=False)
        .sum()
    )

    # --------------------------------------------------------
    # ANOMALIES INJECTÉES
    # --------------------------------------------------------

    injected_customer_ids = set(
        anomalies["customer_id"]
        .dropna()
        .astype(str)
    )

    reviewed_customer_ids = set(
        review["customer_id"]
        .dropna()
        .astype(str)
    )

    changed_customer_ids = set(
        changes["customer_id"]
        .dropna()
        .astype(str)
    )

    affected_by_pipeline = (
        reviewed_customer_ids
        | changed_customer_ids
    )

    injected_ids_touched = (
        injected_customer_ids
        & affected_by_pipeline
    )

    injected_ids_untouched = (
        injected_customer_ids
        - affected_by_pipeline
    )

    # --------------------------------------------------------
    # CLIENTS NON INJECTÉS MODIFIÉS
    # --------------------------------------------------------

    non_injected_changed_ids = (
        changed_customer_ids
        - injected_customer_ids
    )

    # --------------------------------------------------------
    # REVUE HUMAINE
    # --------------------------------------------------------

    review_reasons = {}

    if "review_reason" in review.columns:
        for reasons in review[
            "review_reason"
        ].dropna():

            for reason in str(reasons).split(";"):
                reason = reason.strip()

                if not reason:
                    continue

                review_reasons[reason] = (
                    review_reasons.get(
                        reason,
                        0,
                    )
                    + 1
                )

    # --------------------------------------------------------
    # RÉSULTAT
    # --------------------------------------------------------

    return {
        "integrity": {
            "raw_unique_customer_ids":
                len(raw_unique_ids),

            "clean_unique_customer_ids":
                len(clean_unique_ids),

            "lost_customer_ids":
                len(lost_customer_ids),

            "unexpected_customer_ids":
                len(unexpected_customer_ids),

            "remaining_duplicate_rows":
                remaining_duplicate_rows,
        },

        "pipeline_activity": {
            "normalization_operations":
                int(len(changes)),

            "duplicates_removed":
                int(len(removed)),

            "records_for_review":
                int(len(review)),
        },

        "ground_truth": {
            "injected_anomaly_events":
                int(len(anomalies)),

            "customers_with_injected_anomalies":
                len(injected_customer_ids),

            "injected_customer_ids_touched":
                len(injected_ids_touched),

            "injected_customer_ids_untouched":
                len(injected_ids_untouched),

            "non_injected_customer_ids_changed":
                len(non_injected_changed_ids),
        },

        "review_reasons":
            dict(
                sorted(
                    review_reasons.items(),
                    key=lambda item: (
                        -item[1],
                        item[0],
                    ),
                )
            ),

        "validation_flags": {
            "all_customer_ids_preserved":
                len(lost_customer_ids) == 0,

            "no_unexpected_customer_ids":
                len(unexpected_customer_ids) == 0,

            "no_duplicate_customer_ids_after_cleaning":
                remaining_duplicate_rows == 0,
        },
    }


# ============================================================
# EXPORT
# ============================================================

def export_report(report):
    json_file = (
        REPORTS_DIR
        / "pipeline_validation.json"
    )

    text_file = (
        REPORTS_DIR
        / "pipeline_validation.txt"
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
            "PIPELINE VALIDATION REPORT\n"
        )
        file.write("=" * 50 + "\n\n")

        file.write("DATA INTEGRITY\n")
        file.write("-" * 50 + "\n")

        for key, value in report[
            "integrity"
        ].items():
            file.write(
                f"{key}: {value}\n"
            )

        file.write("\nPIPELINE ACTIVITY\n")
        file.write("-" * 50 + "\n")

        for key, value in report[
            "pipeline_activity"
        ].items():
            file.write(
                f"{key}: {value}\n"
            )

        file.write("\nGROUND TRUTH COMPARISON\n")
        file.write("-" * 50 + "\n")

        for key, value in report[
            "ground_truth"
        ].items():
            file.write(
                f"{key}: {value}\n"
            )

        file.write("\nREVIEW REASONS\n")
        file.write("-" * 50 + "\n")

        for key, value in report[
            "review_reasons"
        ].items():
            file.write(
                f"{key}: {value}\n"
            )

        file.write("\nVALIDATION FLAGS\n")
        file.write("-" * 50 + "\n")

        for key, value in report[
            "validation_flags"
        ].items():
            file.write(
                f"{key}: {value}\n"
            )

    return json_file, text_file


# ============================================================
# MAIN
# ============================================================

def main():
    print("Validating cleaning pipeline...")
    print()

    files = load_files()

    report = validate(files)

    json_file, text_file = export_report(
        report
    )

    print("Pipeline validation completed.")
    print()

    flags = report["validation_flags"]

    print(
        "All customer IDs preserved : "
        f"{flags['all_customer_ids_preserved']}"
    )

    print(
        "No unexpected IDs          : "
        f"{flags['no_unexpected_customer_ids']}"
    )

    print(
        "No duplicates after clean  : "
        f"{flags['no_duplicate_customer_ids_after_cleaning']}"
    )

    print()
    print(
        "Normalization operations   : "
        f"{report['pipeline_activity']['normalization_operations']}"
    )

    print(
        "Records for review         : "
        f"{report['pipeline_activity']['records_for_review']}"
    )

    print()
    print(f"Report                     : {text_file}")
    print(f"JSON                       : {json_file}")


if __name__ == "__main__":
    main()