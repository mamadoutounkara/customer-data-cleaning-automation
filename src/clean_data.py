from pathlib import Path
import json
import re
import unicodedata

import pandas as pd


# ============================================================
# CONFIGURATION
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "customers_raw.csv"
OUTPUT_DIR = PROJECT_ROOT / "output"
REPORTS_DIR = PROJECT_ROOT / "reports"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

VALID_PHONE_PREFIXES = {"70", "75", "76", "77", "78"}

CANONICAL_CITIES = [
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
]

CANONICAL_AGENCIES = [
    "Agence Dakar",
    "Agence Thiès",
    "Agence Saint-Louis",
    "Agence Kaolack",
]

CANONICAL_STATUSES = [
    "Actif",
    "Inactif",
    "Prospect",
]


# ============================================================
# OUTILS GÉNÉRAUX
# ============================================================

def is_missing(value):
    return pd.isna(value) or str(value).strip() == ""


def strip_text(value):
    if is_missing(value):
        return pd.NA

    return str(value).strip()


def canonical_key(value):
    """
    Clé de comparaison tolérante :
    espaces retirés + casse neutralisée.
    """
    if is_missing(value):
        return None

    return str(value).strip().casefold()


def build_canonical_map(values):
    return {
        canonical_key(value): value
        for value in values
    }


CITY_MAP = build_canonical_map(CANONICAL_CITIES)
AGENCY_MAP = build_canonical_map(CANONICAL_AGENCIES)
STATUS_MAP = build_canonical_map(CANONICAL_STATUSES)


# ============================================================
# NOMS
# ============================================================

def normalize_person_name(value):
    if is_missing(value):
        return pd.NA

    text = str(value).strip()

    # Réduit les espaces multiples internes.
    text = re.sub(r"\s+", " ", text)

    # Normalisation légère de casse.
    return text.title()


# ============================================================
# TÉLÉPHONES
# ============================================================

def normalize_phone(value):
    """
    Normalise uniquement les formats que l'on peut réparer
    sans inventer d'information.

    Exemples réparables :
    +221771234567
    +221 77 123 45 67
    77-123-45-67
    77 123 45 67

    Les valeurs impossibles à reconstruire restent invalides.
    """

    if is_missing(value):
        return pd.NA, "missing"

    original = str(value).strip()

    # Si des lettres existent, on ne tente pas de deviner.
    if re.search(r"[A-Za-z]", original):
        return original, "invalid"

    digits = re.sub(r"\D", "", original)

    # Retrait de l'indicatif Sénégal si présent.
    if len(digits) == 12 and digits.startswith("221"):
        digits = digits[3:]

    if (
        len(digits) == 9
        and digits[:2] in VALID_PHONE_PREFIXES
    ):
        if digits == original:
            return digits, "valid"

        return digits, "normalized"

    return original, "invalid"


# ============================================================
# EMAILS
# ============================================================

def email_syntax_is_valid(value):
    if is_missing(value):
        return False

    pattern = (
        r"^[A-Za-z0-9._%+-]+@"
        r"[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    )

    return re.fullmatch(
        pattern,
        str(value),
    ) is not None


def normalize_email(value):
    """
    Corrige seulement les transformations sans ambiguïté :
    espaces extérieurs et casse.

    On n'invente jamais @, domaine ou extension.
    """

    if is_missing(value):
        return pd.NA, "missing"

    original = str(value)
    cleaned = original.strip().lower()

    if not email_syntax_is_valid(cleaned):
        return cleaned, "invalid"

    if cleaned != original:
        return cleaned, "normalized"

    return cleaned, "valid"


# ============================================================
# VALEURS CATÉGORIELLES
# ============================================================

def normalize_category(value, mapping):
    if is_missing(value):
        return pd.NA, "missing"

    key = canonical_key(value)

    if key in mapping:
        canonical = mapping[key]

        if str(value) == canonical:
            return canonical, "valid"

        return canonical, "normalized"

    return str(value).strip(), "invalid"


# ============================================================
# DATES
# ============================================================

def normalize_date(value):
    if is_missing(value):
        return pd.NA, "missing"

    parsed = pd.to_datetime(
        value,
        errors="coerce",
    )

    if pd.isna(parsed):
        return str(value), "invalid"

    return parsed.strftime("%Y-%m-%d"), "valid"


# ============================================================
# NETTOYAGE LIGNE PAR LIGNE
# ============================================================

def clean_dataframe(df):
    cleaned = df.copy()

    change_log = []

    # --------------------------------------------------------
    # NOMS
    # --------------------------------------------------------

    for column in ["first_name", "last_name"]:
        for idx in cleaned.index:
            old = cleaned.at[idx, column]
            new = normalize_person_name(old)

            old_compare = (
                None
                if is_missing(old)
                else str(old)
            )

            new_compare = (
                None
                if is_missing(new)
                else str(new)
            )

            if old_compare != new_compare:
                change_log.append(
                    {
                        "row_index": int(idx),
                        "customer_id": cleaned.at[
                            idx,
                            "customer_id",
                        ],
                        "column": column,
                        "action": "normalized",
                        "old_value": old_compare,
                        "new_value": new_compare,
                    }
                )

            cleaned.at[idx, column] = new

    # --------------------------------------------------------
    # TÉLÉPHONES
    # --------------------------------------------------------

    phone_status = []

    for idx in cleaned.index:
        old = cleaned.at[idx, "phone"]

        new, status = normalize_phone(old)

        cleaned.at[idx, "phone"] = new
        phone_status.append(status)

        if status == "normalized":
            change_log.append(
                {
                    "row_index": int(idx),
                    "customer_id": cleaned.at[
                        idx,
                        "customer_id",
                    ],
                    "column": "phone",
                    "action": "normalized",
                    "old_value": old,
                    "new_value": new,
                }
            )

    cleaned["phone_quality"] = phone_status

    # --------------------------------------------------------
    # EMAILS
    # --------------------------------------------------------

    email_status = []

    for idx in cleaned.index:
        old = cleaned.at[idx, "email"]

        new, status = normalize_email(old)

        cleaned.at[idx, "email"] = new
        email_status.append(status)

        if status == "normalized":
            change_log.append(
                {
                    "row_index": int(idx),
                    "customer_id": cleaned.at[
                        idx,
                        "customer_id",
                    ],
                    "column": "email",
                    "action": "normalized",
                    "old_value": old,
                    "new_value": new,
                }
            )

    cleaned["email_quality"] = email_status

    # --------------------------------------------------------
    # CATÉGORIES
    # --------------------------------------------------------

    category_rules = {
        "city": CITY_MAP,
        "agency": AGENCY_MAP,
        "status": STATUS_MAP,
    }

    for column, mapping in category_rules.items():
        quality_values = []

        for idx in cleaned.index:
            old = cleaned.at[idx, column]

            new, quality = normalize_category(
                old,
                mapping,
            )

            cleaned.at[idx, column] = new
            quality_values.append(quality)

            if quality == "normalized":
                change_log.append(
                    {
                        "row_index": int(idx),
                        "customer_id": cleaned.at[
                            idx,
                            "customer_id",
                        ],
                        "column": column,
                        "action": "normalized",
                        "old_value": old,
                        "new_value": new,
                    }
                )

        cleaned[f"{column}_quality"] = (
            quality_values
        )

    # --------------------------------------------------------
    # DATES
    # --------------------------------------------------------

    date_quality = []

    for idx in cleaned.index:
        old = cleaned.at[
            idx,
            "registration_date",
        ]

        new, quality = normalize_date(old)

        cleaned.at[
            idx,
            "registration_date",
        ] = new

        date_quality.append(quality)

    cleaned["registration_date_quality"] = (
        date_quality
    )

    return cleaned, pd.DataFrame(change_log)


# ============================================================
# DÉDOUBLONNAGE
# ============================================================

def deduplicate(df):
    """
    customer_id est ici l'identifiant métier de référence.

    Après normalisation, on conserve une ligne par customer_id.

    Priorité :
    - davantage de coordonnées valides ;
    - puis première occurrence en cas d'égalité.
    """

    working = df.copy()

    working["_quality_score"] = 0

    working["_quality_score"] += (
        working["phone_quality"]
        .isin(["valid", "normalized"])
        .astype(int)
    )

    working["_quality_score"] += (
        working["email_quality"]
        .isin(["valid", "normalized"])
        .astype(int)
    )

    working["_quality_score"] += (
        working["city_quality"]
        .isin(["valid", "normalized"])
        .astype(int)
    )

    duplicate_mask = working[
        "customer_id"
    ].duplicated(keep=False)

    duplicate_candidates = working[
        duplicate_mask
    ].copy()

    working["_original_order"] = range(
        len(working)
    )

    working = working.sort_values(
        by=[
            "customer_id",
            "_quality_score",
            "_original_order",
        ],
        ascending=[
            True,
            False,
            True,
        ],
    )

    deduplicated = working.drop_duplicates(
        subset=["customer_id"],
        keep="first",
    ).copy()

    removed = working[
        working.duplicated(
            subset=["customer_id"],
            keep="first",
        )
    ].copy()

    deduplicated = deduplicated.sort_values(
        "_original_order"
    )

    columns_to_drop = [
        "_quality_score",
        "_original_order",
    ]

    deduplicated = deduplicated.drop(
        columns=columns_to_drop,
        errors="ignore",
    )

    removed = removed.drop(
        columns=columns_to_drop,
        errors="ignore",
    )

    duplicate_candidates = (
        duplicate_candidates.drop(
            columns=["_quality_score"],
            errors="ignore",
        )
    )

    return (
        deduplicated.reset_index(drop=True),
        removed.reset_index(drop=True),
        duplicate_candidates.reset_index(
            drop=True
        ),
    )


# ============================================================
# DOSSIER DE REVUE HUMAINE
# ============================================================

def build_review_file(df):
    review_mask = (
        df["phone_quality"].isin(
            ["missing", "invalid"]
        )
        | df["email_quality"].isin(
            ["missing", "invalid"]
        )
        | df["city_quality"].isin(
            ["missing", "invalid"]
        )
        | df["agency_quality"].isin(
            ["missing", "invalid"]
        )
        | df["status_quality"].isin(
            ["missing", "invalid"]
        )
        | df[
            "registration_date_quality"
        ].isin(["missing", "invalid"])
    )

    review = df[review_mask].copy()

    reasons = []

    for _, row in review.iterrows():
        row_reasons = []

        checks = {
            "phone": row["phone_quality"],
            "email": row["email_quality"],
            "city": row["city_quality"],
            "agency": row["agency_quality"],
            "status": row["status_quality"],
            "registration_date":
                row[
                    "registration_date_quality"
                ],
        }

        for field, quality in checks.items():
            if quality in [
                "missing",
                "invalid",
            ]:
                row_reasons.append(
                    f"{field}:{quality}"
                )

        reasons.append(
            "; ".join(row_reasons)
        )

    review["review_reason"] = reasons

    return review


# ============================================================
# RAPPORT DE NETTOYAGE
# ============================================================

def build_cleaning_report(
    original,
    cleaned_before_dedup,
    final,
    removed_duplicates,
    review,
    change_log,
):
    return {
        "input_rows": int(len(original)),
        "rows_after_cleaning_before_dedup":
            int(len(cleaned_before_dedup)),
        "final_unique_rows":
            int(len(final)),
        "duplicates_removed":
            int(len(removed_duplicates)),
        "records_requiring_review":
            int(len(review)),
        "normalization_changes":
            int(len(change_log)),
        "phone_quality": (
            final["phone_quality"]
            .value_counts(dropna=False)
            .to_dict()
        ),
        "email_quality": (
            final["email_quality"]
            .value_counts(dropna=False)
            .to_dict()
        ),
    }


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def main():
    print("Starting data cleaning pipeline...")
    print()

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            f"Input file not found: {INPUT_FILE}"
        )

    original = pd.read_csv(INPUT_FILE)

    cleaned, change_log = clean_dataframe(
        original
    )

    (
        final,
        removed_duplicates,
        duplicate_candidates,
    ) = deduplicate(cleaned)

    review = build_review_file(final)

    report = build_cleaning_report(
        original=original,
        cleaned_before_dedup=cleaned,
        final=final,
        removed_duplicates=removed_duplicates,
        review=review,
        change_log=change_log,
    )

    # --------------------------------------------------------
    # EXPORT DES DONNÉES
    # --------------------------------------------------------

    clean_csv = (
        OUTPUT_DIR / "customers_clean.csv"
    )

    clean_xlsx = (
        OUTPUT_DIR / "customers_clean.xlsx"
    )

    review_csv = (
        OUTPUT_DIR / "records_for_review.csv"
    )

    removed_csv = (
        OUTPUT_DIR / "duplicates_removed.csv"
    )

    duplicate_candidates_csv = (
        REPORTS_DIR
        / "duplicate_candidates.csv"
    )

    change_log_csv = (
        REPORTS_DIR
        / "cleaning_change_log.csv"
    )

    report_json = (
        REPORTS_DIR
        / "cleaning_report.json"
    )

    final.to_csv(
        clean_csv,
        index=False,
        encoding="utf-8-sig",
    )

    final.to_excel(
        clean_xlsx,
        index=False,
    )

    review.to_csv(
        review_csv,
        index=False,
        encoding="utf-8-sig",
    )

    removed_duplicates.to_csv(
        removed_csv,
        index=False,
        encoding="utf-8-sig",
    )

    duplicate_candidates.to_csv(
        duplicate_candidates_csv,
        index=False,
        encoding="utf-8-sig",
    )

    change_log.to_csv(
        change_log_csv,
        index=False,
        encoding="utf-8-sig",
    )

    with open(
        report_json,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            report,
            file,
            ensure_ascii=False,
            indent=2,
        )

    # --------------------------------------------------------
    # CONSOLE
    # --------------------------------------------------------

    print("Cleaning completed successfully.")
    print()

    print(
        f"Input rows              : "
        f"{len(original)}"
    )

    print(
        f"Unique customer records : "
        f"{len(final)}"
    )

    print(
        f"Duplicates removed      : "
        f"{len(removed_duplicates)}"
    )

    print(
        f"Records for review      : "
        f"{len(review)}"
    )

    print(
        f"Normalization changes   : "
        f"{len(change_log)}"
    )

    print()
    print(f"Clean CSV               : {clean_csv}")
    print(f"Clean Excel             : {clean_xlsx}")
    print(f"Review file             : {review_csv}")
    print(f"Removed duplicates      : {removed_csv}")
    print(f"Cleaning report         : {report_json}")


if __name__ == "__main__":
    main()