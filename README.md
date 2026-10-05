# Customer Data Cleaning & Automation Pipeline



A reproducible Python pipeline for auditing, cleaning, validating, and preparing customer data for CRM import or operational use.



This portfolio project simulates a real-world data quality assignment: a customer database contains duplicate records, inconsistent phone numbers, malformed email addresses, missing values, and inconsistent categorical data.



Instead of blindly modifying every suspicious value, the pipeline follows a safer rule:



> **Automatically normalize what can be corrected with certainty, and isolate ambiguous records for human review.**



---



## Business Problem



Organizations often maintain customer data across spreadsheets, CRM exports, registration forms, and operational systems.



Over time, these datasets can accumulate:



\- duplicate customer records;

\- inconsistent phone number formats;

\- malformed or non-standard email addresses;

\- missing contact information;

\- inconsistent city, agency, or status values;

\- formatting differences caused by manual data entry.



Using such data directly can lead to failed CRM imports, duplicate communications, unreliable reporting, and unnecessary manual work.



This project demonstrates how these issues can be detected and handled through a reproducible Python workflow.



---



## Results



The pipeline processed a synthetic dataset containing **5,000 customer records**.



| Metric | Before | After |

|---|---:|---:|

| Customer records | 5,000 | 4,800 |

| Unique customer IDs | 4,800 | 4,800 |

| Rows in duplicate groups | 398 | 0 |

| Duplicate ID groups | 198 | 0 |

| Missing phone numbers | 83 | 80 |

| Invalid / non-standard phones | 303 | 72 |

| Missing emails | 123 | 120 |

| Invalid emails | 99 | 93 |

| Missing cities | 71 | 70 |



### Key outcomes



\- **200 duplicate records removed**

\- **100% of unique customer IDs preserved**

\- **0 duplicate customer IDs remaining**

\- **76.24% reduction in invalid/non-standard phone formats**

\- **831 normalization operations logged**

\- **425 records isolated for human review**

\- **0 unexpected customer IDs introduced**



Remaining missing or invalid values are intentionally retained when they cannot be corrected safely without additional information.



---



## Pipeline



```text

Raw customer data

&#x20;       |

&#x20;       v

Data quality audit

&#x20;       |

&#x20;       v

Safe normalization

&#x20;       |

&#x20;       v

Validation

&#x20;       |

&#x20;       v

Deduplication

&#x20;       |

&#x20;       +----------------------+

&#x20;       |                      |

&#x20;       v                      v

Clean dataset          Human review queue

&#x20;       |

&#x20;       v

Before / After reporting

```



---



## What the Pipeline Handles



### Phone numbers



Deterministically repairable formats are normalized.



Example:



```text

+221 77 123 45 67

&#x20;       ↓

771234567

```



Values that cannot be reconstructed safely are not invented and are instead flagged for review.



### Email addresses



Safe transformations include:



\- trimming surrounding spaces;

\- converting addresses to lowercase;

\- validating basic email syntax.



A malformed address is not automatically reconstructed when the intended value is ambiguous.



### Duplicate records



Duplicate customer IDs are evaluated and reduced to one record while prioritizing records with higher-quality contact information.



### Categorical data



Cities, agencies, and customer statuses are mapped to canonical values when the transformation is deterministic.



### Human review



Records containing unresolved issues are exported separately so that uncertain corrections can be handled manually.



---



## Data Integrity Checks



The validation stage verifies that cleaning does not damage customer identity.



Current validation results:



```text

All original customer IDs preserved: True

No unexpected customer IDs: True

No duplicate customer IDs after cleaning: True

```



This separation between **automatic correction** and **human review** is intentional: data quality automation should reduce manual work without silently inventing customer information.



---



## Project Structure



```text

data-cleaning-automation/

|

|-- data/

|   `-- sample/

|       `-- customers\_sample.csv

|

|-- reports/

|   |-- before\_after\_comparison.json

|   |-- before\_after\_comparison.txt

|   |-- cleaning\_report.json

|   |-- data\_quality\_before.json

|   |-- data\_quality\_before.txt

|   |-- pipeline\_validation.json

|   `-- pipeline\_validation.txt

|

|-- src/

|   |-- generate\_dataset.py

|   |-- data\_quality\_audit.py

|   |-- clean\_data.py

|   |-- compare\_before\_after.py

|   |-- validate\_pipeline.py

|   `-- validate\_anomaly\_events.py

|

|-- .gitignore

|-- LICENSE

|-- README.md

`-- requirements.txt

```



---



## Technologies



\- Python 3

\- pandas

\- NumPy

\- openpyxl

\- Faker

\- Git



---



## Installation



Clone the repository and create a virtual environment:



```bash

python -m venv .venv

```



### Windows PowerShell



```powershell

.\\.venv\\Scripts\\Activate.ps1

```



Install the dependencies:



```bash

python -m pip install -r requirements.txt

```



---



## Running the Project



Generate the synthetic dataset:



```bash

python src/generate\_dataset.py

```



Run the initial data-quality audit:



```bash

python src/data\_quality\_audit.py

```



Run the cleaning pipeline:



```bash

python src/clean\_data.py

```



Generate the Before vs After comparison:



```bash

python src/compare\_before\_after.py

```



Validate customer-ID integrity:



```bash

python src/validate\_pipeline.py

```



---



## Outputs



The pipeline generates:



```text

output/

|-- customers\_clean.csv

|-- customers\_clean.xlsx

|-- records\_for\_review.csv

`-- duplicates\_removed.csv

```



Detailed reports are generated in:



```text

reports/

```



The generated raw and output datasets are intentionally excluded from Git. A small synthetic sample is provided in `data/sample/`.



---



## Use Cases



The same approach can be adapted to:



\- CRM data cleanup;

\- Excel/CSV database cleaning;

\- customer-list deduplication;

\- contact database standardization;

\- migration preparation;

\- recurring data-quality checks;

\- automated operational reporting.



---



## Important Note



The dataset used in this repository is **synthetic** and generated specifically for demonstration purposes.



It contains no real customer or confidential organizational data.



---



## Author



**Mamadou Tounkara**



Mathematical Sciences | Data Cleaning | Automation | Reporting



---



## License



This project is released under the MIT License.


