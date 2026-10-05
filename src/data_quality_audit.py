from pathlib import Path
import json
import re

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "customers_raw.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"

REPORTS_DIR.mkdir(parents=True, exist_ok=True)

EXPECTED_COLUMNS = [
    "customer_id",
    "first_name",
    "last_name",
    "phone",
    "email",
    "city",
    "agency",
    "status",
    "registration_date",
    "injected_duplicate_type",
]

VALID_PHONE_PREFIXES = {"70", "75", "76", "77", "78"}

VALID_CITIES = {
    "Dakar",
    "Thiès",
    "Saint-Louis",
    "Kaolack",
    "Ziguinchor",
    "Diourbel",
    "Louga",
    "Fatick",
    "Matam",
    "Kolda",
}

VALID_AGENCIES = {
    "Agence Dakar",
    "Agence Thiès",
    "Agence Saint-Louis",
    "Agence Kaolack",
}

VALID_STATUSES = {
    "Actif",
    "Inactif",
    "Prospect",
}


# ============================================================
# OUTILS DE VALIDATION
# ============================================================

def is_missing(value):
    return pd.isna(value) or str(value).strip() == ""


def is_valid_phone(value):
    """
    Validation stricte du format brut attendu :
    exactement 9 chiffres et préfixe autorisé.
    """
    if is_missing(value):
        return False

    phone = str(value).strip()

    if not re.fullmatch(r"\d{9}", phone):
        return False

    return phone[:2] in VALID_PHONE_PREFIXES


def is_valid_email(value):
    """
    Contrôle syntaxique simple et volontairement lisible.
    Ce n'est pas une vérification d'existence de l'adresse.
    """
    if is_missing(value):
        return False

    email = str(value).strip()

    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"

    return re.fullmatch(pattern, email) is not None


def has_outer_spaces(value):
    if is_missing(value):
        return False

    text = str(value)

    return text != text.strip()


def normalize_text_for_comparison(value):
    if is_missing(value):
        return None

    return str(value).strip().casefold()


# ============================================================
# CHARGEMENT
# ============================================================

def load_data():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    return pd.read_csv(INPUT_FILE)


# ============================================================
# AUDIT DU SCHÉMA
# ============================================================

def audit_schema(df):
    actual_columns = df.columns.tolist()

    missing_columns = [
        column
        for column in EXPECTED_COLUMNS
        if column not in actual_columns
    ]

    unexpected_columns = [
        column
        for column in actual_columns
        if column not in EXPECTED_COLUMNS
    ]

    return {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "missing_expected_columns": missing_columns,
        "unexpected_columns": unexpected_columns,
    }


# ============================================================
# VALEURS MANQUANTES
# ============================================================

def audit_missing_values(df):
    results = {}

    for column in df.columns:
        count = int(
            df[column]
            .apply(is_missing)
            .sum()
        )

        results[column] = {
            "count": count,
            "percentage": round(
                count / len(df) * 100,
                2,
            ),
        }

    return results


# ============================================================
# DOUBLONS
# ============================================================

def audit_duplicates(df):
    duplicated_customer_ids = int(
        df["customer_id"].duplicated(
            keep=False
        ).sum()
    )

    duplicate_id_groups = int(
        df.loc[
            df["customer_id"].duplicated(
                keep=False
            ),
            "customer_id",
        ].nunique()
    )

    exact_business_duplicates = int(
        df.duplicated(
            subset=[
                "customer_id",
                "first_name",
                "last_name",
                "phone",
                "email",
                "city",
                "agency",
                "status",
                "registration_date",
            ],
            keep=False,
        ).sum()
    )

    return {
        "rows_with_duplicated_customer_id":
            duplicated_customer_ids,
        "duplicate_customer_id_groups":
            duplicate_id_groups,
        "rows_in_exact_duplicate_groups":
            exact_business_duplicates,
    }


# ============================================================
# TÉLÉPHONES
# ============================================================

def audit_phones(df):
    missing_mask = df["phone"].apply(is_missing)

    invalid_mask = (
        ~missing_mask
        & ~df["phone"].apply(is_valid_phone)
    )

    valid_mask = (
        ~missing_mask
        & df["phone"].apply(is_valid_phone)
    )

    return {
        "missing": int(missing_mask.sum()),
        "valid_strict_format": int(valid_mask.sum()),
        "invalid_or_nonstandard":
            int(invalid_mask.sum()),
    }


# ============================================================
# EMAILS
# ============================================================

def audit_emails(df):
    missing_mask = df["email"].apply(is_missing)

    invalid_mask = (
        ~missing_mask
        & ~df["email"].apply(is_valid_email)
    )

    valid_mask = (
        ~missing_mask
        & df["email"].apply(is_valid_email)
    )

    outer_spaces_mask = (
        ~missing_mask
        & df["email"].apply(has_outer_spaces)
    )

    return {
        "missing": int(missing_mask.sum()),
        "valid_syntax": int(valid_mask.sum()),
        "invalid_syntax": int(invalid_mask.sum()),
        "with_outer_spaces":
            int(outer_spaces_mask.sum()),
    }


# ============================================================
# TEXTE / NORMALISATION
# ============================================================

def audit_text_quality(df):
    results = {}

    for column in [
        "first_name",
        "last_name",
        "city",
        "agency",
        "status",
    ]:
        outer_spaces = int(
            df[column]
            .apply(has_outer_spaces)
            .sum()
        )

        results[column] = {
            "values_with_outer_spaces":
                outer_spaces,
        }

    normalized_city = df["city"].apply(
        normalize_text_for_comparison
    )

    canonical_city_map = {
        city.casefold(): city
        for city in VALID_CITIES
    }

    nonstandard_city_mask = (
        normalized_city.notna()
        & ~normalized_city.isin(
            canonical_city_map.keys()
        )
    )

    exact_noncanonical_city_mask = (
        df["city"].notna()
        & df["city"].astype(str).str.strip().isin(
            VALID_CITIES
        )
        == False
    )

    results["city"][
        "nonstandard_after_case_insensitive_comparison"
    ] = int(nonstandard_city_mask.sum())

    results["city"][
        "not_in_canonical_exact_form"
    ] = int(exact_noncanonical_city_mask.sum())

    return results


# ============================================================
# DOMAINES MÉTIER
# ============================================================

def audit_business_domains(df):
    agency_invalid = int(
        (
            ~df["agency"].isin(VALID_AGENCIES)
            & df["agency"].notna()
        ).sum()
    )

    status_invalid = int(
        (
            ~df["status"].isin(VALID_STATUSES)
            & df["status"].notna()
        ).sum()
    )

    return {
        "invalid_agency_values": agency_invalid,
        "invalid_status_values": status_invalid,
    }


# ============================================================
# DATES
# ============================================================

def audit_dates(df):
    parsed_dates = pd.to_datetime(
        df["registration_date"],
        errors="coerce",
    )

    invalid_dates = int(
        (
            parsed_dates.isna()
            & df["registration_date"].notna()
        ).sum()
    )

    return {
        "invalid_registration_dates":
            invalid_dates,
    }


# ============================================================
# SCORE DE QUALITÉ
# ============================================================

def calculate_quality_score(
    df,
    missing,
    duplicates,
    phones,
    emails,
):
    """
    Score démonstratif pour le portfolio.

    Il ne prétend pas être une norme universelle.
    Il donne un indicateur synthétique reproductible.
    """

    total_cells = len(df) * len(df.columns)

    missing_count = sum(
        item["count"]
        for item in missing.values()
    )

    duplicate_rows = duplicates[
        "rows_with_duplicated_customer_id"
    ]

    invalid_phones = phones[
        "invalid_or_nonstandard"
    ]

    invalid_emails = emails[
        "invalid_syntax"
    ]

    penalties = (
        missing_count
        + duplicate_rows
        + invalid_phones
        + invalid_emails
    )

    score = 100 * (
        1 - penalties / total_cells
    )

    return round(
        max(0, min(100, score)),
        2,
    )


# ============================================================
# RAPPORT
# ============================================================

def build_report(df):
    schema = audit_schema(df)
    missing = audit_missing_values(df)
    duplicates = audit_duplicates(df)
    phones = audit_phones(df)
    emails = audit_emails(df)
    text_quality = audit_text_quality(df)
    business_domains = audit_business_domains(df)
    dates = audit_dates(df)

    quality_score = calculate_quality_score(
        df,
        missing,
        duplicates,
        phones,
        emails,
    )

    return {
        "dataset": {
            "file": str(INPUT_FILE),
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
        },
        "schema": schema,
        "missing_values": missing,
        "duplicates": duplicates,
        "phones": phones,
        "emails": emails,
        "text_quality": text_quality,
        "business_domains": business_domains,
        "dates": dates,
        "quality_score": quality_score,
    }


# ============================================================
# EXPORTS
# ============================================================

def export_report(report):
    json_file = (
        REPORTS_DIR
        / "data_quality_before.json"
    )

    summary_file = (
        REPORTS_DIR
        / "data_quality_before.txt"
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
        summary_file,
        "w",
        encoding="utf-8",
    ) as file:
        file.write(
            "DATA QUALITY AUDIT — BEFORE CLEANING\n"
        )
        file.write("=" * 45 + "\n\n")

        file.write(
            f"Rows: {report['dataset']['rows']}\n"
        )

        file.write(
            f"Columns: {report['dataset']['columns']}\n"
        )

        file.write(
            "Quality score: "
            f"{report['quality_score']} / 100\n\n"
        )

        file.write("DUPLICATES\n")
        file.write("-" * 20 + "\n")

        for key, value in report[
            "duplicates"
        ].items():
            file.write(
                f"{key}: {value}\n"
            )

        file.write("\nPHONES\n")
        file.write("-" * 20 + "\n")

        for key, value in report[
            "phones"
        ].items():
            file.write(
                f"{key}: {value}\n"
            )

        file.write("\nEMAILS\n")
        file.write("-" * 20 + "\n")

        for key, value in report[
            "emails"
        ].items():
            file.write(
                f"{key}: {value}\n"
            )

        file.write("\nMISSING VALUES\n")
        file.write("-" * 20 + "\n")

        for column, values in report[
            "missing_values"
        ].items():
            file.write(
                f"{column}: "
                f"{values['count']} "
                f"({values['percentage']}%)\n"
            )

    return json_file, summary_file


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def main():
    print("Running data quality audit...")
    print()

    df = load_data()

    report = build_report(df)

    json_file, summary_file = export_report(
        report
    )

    print("Audit completed successfully.")
    print()
    print(
        f"Rows                 : {len(df)}"
    )
    print(
        f"Columns              : {len(df.columns)}"
    )
    print(
        "Quality score        : "
        f"{report['quality_score']} / 100"
    )
    print(
        "Duplicate ID rows    : "
        f"{report['duplicates']['rows_with_duplicated_customer_id']}"
    )
    print(
        "Invalid/nonstandard phones: "
        f"{report['phones']['invalid_or_nonstandard']}"
    )
    print(
        "Invalid emails       : "
        f"{report['emails']['invalid_syntax']}"
    )
    print()
    print(
        f"JSON report          : {json_file}"
    )
    print(
        f"Text summary         : {summary_file}"
    )


if __name__ == "__main__":
    main()