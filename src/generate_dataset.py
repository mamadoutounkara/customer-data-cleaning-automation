from pathlib import Path
import random
import re

import pandas as pd
from faker import Faker


# ============================================================
# CONFIGURATION
# ============================================================

SEED = 20261005
BASE_RECORDS = 4800
EXACT_DUPLICATES = 100
FUZZY_DUPLICATES = 100

random.seed(SEED)
Faker.seed(SEED)

fake = Faker("fr_FR")
fake.seed_instance(SEED)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
SAMPLE_DIR = PROJECT_ROOT / "data" / "sample"
REPORTS_DIR = PROJECT_ROOT / "reports"

RAW_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# DONNÉES MÉTIER FICTIVES
# ============================================================

CITIES = [
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

AGENCIES = [
    "Agence Dakar",
    "Agence Thiès",
    "Agence Saint-Louis",
    "Agence Kaolack",
]

STATUSES = ["Actif", "Inactif", "Prospect"]


# ============================================================
# GÉNÉRATION DES VALEURS PROPRES
# ============================================================

def make_phone():
    prefix = random.choice(["70", "75", "76", "77", "78"])
    return prefix + "".join(random.choices("0123456789", k=7))


def clean_email_component(value):
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", ".", value)
    return value.strip(".")


def make_email(first_name, last_name, index):
    first = clean_email_component(first_name)
    last = clean_email_component(last_name)

    domain = random.choice(
        ["gmail.com", "outlook.com", "yahoo.fr", "example.com"]
    )

    return f"{first}.{last}{index}@{domain}"


def generate_clean_record(index):
    first_name = fake.first_name()
    last_name = fake.last_name()

    return {
        "customer_id": f"CUST-{index:05d}",
        "first_name": first_name,
        "last_name": last_name,
        "phone": make_phone(),
        "email": make_email(first_name, last_name, index),
        "city": random.choice(CITIES),
        "agency": random.choice(AGENCIES),
        "status": random.choice(STATUSES),
        "registration_date": fake.date_between(
            start_date="-3y",
            end_date="today",
        ).isoformat(),
    }


# ============================================================
# INJECTION D'ANOMALIES
# ============================================================

def add_spaces(value):
    return f"  {value}  "


def alter_case(value):
    return random.choice(
        [
            value.upper(),
            value.lower(),
            value.title(),
        ]
    )


def corrupt_phone(phone):
    transformations = [
        lambda x: f"+221{x}",
        lambda x: f"+221 {x[:2]} {x[2:5]} {x[5:7]} {x[7:]}",
        lambda x: f"{x[:2]}-{x[2:5]}-{x[5:7]}-{x[7:]}",
        lambda x: f"{x[:2]} {x[2:5]} {x[5:7]} {x[7:]}",
        lambda x: x[:-2],
        lambda x: "ABC" + x[:5],
    ]

    return random.choice(transformations)(phone)


def corrupt_email(email):
    transformations = [
        lambda x: f" {x} ",
        lambda x: x.replace("@", ""),
        lambda x: x.replace(".", "", 1),
        lambda x: x.upper(),
        lambda x: x.replace("@", "@@"),
    ]

    return random.choice(transformations)(email)


def inject_anomalies(df):
    audit = []

    def modify_rows(column, count, transformation, anomaly_type):
        available = df.index.tolist()
        selected = random.sample(available, count)

        for idx in selected:
            old_value = df.at[idx, column]
            new_value = transformation(old_value)

            df.at[idx, column] = new_value

            audit.append(
                {
                    "row_index": int(idx),
                    "customer_id": df.at[idx, "customer_id"],
                    "column": column,
                    "anomaly_type": anomaly_type,
                    "original_value": old_value,
                    "modified_value": new_value,
                }
            )

    modify_rows(
        "first_name",
        180,
        add_spaces,
        "extra_spaces",
    )

    modify_rows(
        "last_name",
        180,
        alter_case,
        "inconsistent_case",
    )

    modify_rows(
        "phone",
        300,
        corrupt_phone,
        "phone_format_or_invalid",
    )

    modify_rows(
        "email",
        220,
        corrupt_email,
        "email_format_or_spacing",
    )

    modify_rows(
        "city",
        180,
        alter_case,
        "city_case",
    )

    # Valeurs manquantes
    missing_rules = {
        "phone": 80,
        "email": 120,
        "city": 70,
    }

    for column, count in missing_rules.items():
        selected = random.sample(df.index.tolist(), count)

        for idx in selected:
            old_value = df.at[idx, column]
            df.at[idx, column] = None

            audit.append(
                {
                    "row_index": int(idx),
                    "customer_id": df.at[idx, "customer_id"],
                    "column": column,
                    "anomaly_type": "missing_value",
                    "original_value": old_value,
                    "modified_value": None,
                }
            )

    return df, pd.DataFrame(audit)


# ============================================================
# DOUBLONS
# ============================================================

def add_duplicates(df):
    exact = df.sample(
        n=EXACT_DUPLICATES,
        random_state=SEED,
    ).copy()

    exact["injected_duplicate_type"] = "exact"

    fuzzy = df.sample(
        n=FUZZY_DUPLICATES,
        random_state=SEED + 1,
    ).copy()

    fuzzy["injected_duplicate_type"] = "fuzzy"

    # Les doublons partiels représentent le même client,
    # mais avec une petite variation de saisie.
    for idx in fuzzy.index:
        fuzzy.at[idx, "first_name"] = (
            str(fuzzy.at[idx, "first_name"]).upper()
        )

        if pd.notna(fuzzy.at[idx, "phone"]):
            phone = str(fuzzy.at[idx, "phone"])
            fuzzy.at[idx, "phone"] = f" {phone} "

    original = df.copy()
    original["injected_duplicate_type"] = "original"

    combined = pd.concat(
        [original, exact, fuzzy],
        ignore_index=True,
    )

    combined = combined.sample(
        frac=1,
        random_state=SEED,
    ).reset_index(drop=True)

    return combined


# ============================================================
# PROGRAMME PRINCIPAL
# ============================================================

def main():
    print("Generating fictional customer dataset...")

    records = [
        generate_clean_record(i)
        for i in range(1, BASE_RECORDS + 1)
    ]

    clean_df = pd.DataFrame(records)

    dirty_df, anomaly_audit = inject_anomalies(
        clean_df.copy()
    )

    final_df = add_duplicates(dirty_df)

    raw_csv = RAW_DIR / "customers_raw.csv"
    raw_xlsx = RAW_DIR / "customers_raw.xlsx"
    audit_csv = REPORTS_DIR / "injected_anomalies.csv"
    sample_csv = SAMPLE_DIR / "customers_sample.csv"

    final_df.to_csv(
        raw_csv,
        index=False,
        encoding="utf-8-sig",
    )

    final_df.to_excel(
        raw_xlsx,
        index=False,
    )

    anomaly_audit.to_csv(
        audit_csv,
        index=False,
        encoding="utf-8-sig",
    )

    final_df.head(100).to_csv(
        sample_csv,
        index=False,
        encoding="utf-8-sig",
    )

    print()
    print("Dataset generated successfully.")
    print(f"Base customers       : {BASE_RECORDS}")
    print(f"Exact duplicates     : {EXACT_DUPLICATES}")
    print(f"Fuzzy duplicates     : {FUZZY_DUPLICATES}")
    print(f"Final rows            : {len(final_df)}")
    print(f"Injected anomalies    : {len(anomaly_audit)}")
    print()
    print(f"CSV                   : {raw_csv}")
    print(f"Excel                 : {raw_xlsx}")
    print(f"Audit                 : {audit_csv}")
    print(f"Public sample         : {sample_csv}")


if __name__ == "__main__":
    main()