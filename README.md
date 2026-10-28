# OfferChain
### Blockchain-Based Job Offer Verification System

OfferChain is a small **educational, single-server Python blockchain prototype**. It demonstrates how a SHA-256 fingerprint and linked blocks can detect changes to job offer information compared with a locally registered record. It is **not** a distributed blockchain, an identity service, or proof that a job offer is genuine.

## Problem and objectives
Fraudulent or modified offers may look legitimate. This project demonstrates registering a fingerprint of some offer fields and checking later whether the submitted fields match that fingerprint. Its goals are to teach normalization, hashing, linked blocks, integrity checks, JSON persistence, and a simple Flask interface.

## Features
- Dashboard with live ledger counts, recent metadata and integrity status.
- Registration with a server-generated ID; one new block per offer.
- Verification: `VERIFIED`, `MISMATCH`, `NOT_FOUND`, or `CHAIN_INVALID`.
- Explorer with genesis block, timestamps, hashes, copy controls and integrity check.
- Local JSON persistence; validation before registration or verification.
- Responsive, keyboard-accessible interface and Python `unittest` tests.

## Stack and architecture
Python 3.10+ (tested with 3.13), Flask 3, HTML, CSS and vanilla JavaScript. Python standard library `hashlib`, `json`, `secrets`, `unicodedata` and `unittest` implement the rest. There is no database, external API, public network, authentication service or third-party frontend library.

```text
OfferChain/
├── app.py                   Flask routes and application factory
├── blockchain.py            Ledger, linking, validation and atomic storage
├── offer_utils.py           Normalization and hashing
├── requirements.txt         Flask only
├── README.md
├── .gitignore
├── data/
│   ├── .gitkeep
│   └── ledger.json          created on first access, ignored by Git
├── templates/index.html
├── static/css/style.css
├── static/js/app.js
└── tests/
    ├── test_blockchain.py
    ├── test_offers.py
    └── test_app.py
```

## How it works
1. Enter six offer fields. The server validates and normalizes them, then creates a unique ID with a UTC date and 64-bit cryptographically random suffix, retrying on collision.
2. The server hashes a canonical JSON object containing `schema_version: 1`, that ID, and the normalized `offer` object. The hash is tied to both ID and fields.
3. The server validates the entire ledger and appends a block holding the offer ID and hash, timestamp, consecutive index and previous block hash. It calculates the block hash from all block fields except `block_hash` itself.
4. To verify, enter the same ID and fields. The server validates the ledger first and then hashes the submitted fields exactly as before. `VERIFIED` means the hashes match, not that a company issued the offer. A different fingerprint returns `MISMATCH`; a syntactically valid but unknown ID returns `NOT_FOUND`.
5. The explorer shows metadata only. It does not contain the original offer details. A new ledger starts with a deterministic genesis block (index 0), which is not an offer.

### Canonicalization
Only `company_name`, `job_title`, `employment_type`, `work_location`, `salary`, and `offer_date` are accepted for an offer; extra or missing keys are rejected. Each value must be a nonempty string; the length limits are 120 characters for company, title, location and salary, 20 for employment type and 10 for date (pre-normalization input is also bounded). Each string is Unicode NFC normalized, leading/trailing whitespace removed, and internal whitespace runs collapsed to one space. Unsupported control/surrogate characters are rejected. **Case is preserved and significant**: `Example` and `example` hash differently. Employment type is case-sensitive and must exactly match `Full-time`, `Part-time`, `Internship`, or `Contract`. Dates must be real dates in `YYYY-MM-DD`. Whitespace and Unicode-equivalent spelling normalize consistently; other changes affect the hash.

The offer payload and block hash use the same canonical JSON (`sort_keys=True`, compact separators, `ensure_ascii=False`, UTF-8) and SHA-256. A block looks like:

```json
{
  "index": 1,
  "timestamp": "2026-10-28T10:00:00+00:00",
  "offer_id": "OFR-20261028-0123456789ABCDEF",
  "offer_hash": "64 lowercase hexadecimal characters",
  "previous_hash": "64 lowercase hexadecimal characters",
  "block_hash": "64 lowercase hexadecimal characters"
}
```

The placeholder strings above describe the actual values, not valid hashes. The fixed genesis timestamp, ID and zero hashes are defined in `blockchain.py`; its hash uses the same algorithm. Validation checks exact block fields, schema, genesis, indices, UTC timestamps, digest format, unique IDs, previous links and recalculated hashes. It cannot detect a complete malicious rewrite with recomputed hashes.

### Persistence and concurrency
The ledger path is resolved relative to the source directory, not the working directory. `data/ledger.json` is created with genesis only if missing; an existing malformed or invalid ledger is **never automatically reset**. Writes use a temporary file in the same directory, flush and `os.replace`. A shared `threading.Lock` protects each path's read-modify-write cycle **inside one Python process**. It does not protect across processes, machines, simultaneous console scripts, or external editors. Run exactly **one web worker/process**, avoid concurrent scripts touching the ledger, and do not run local debug reloader or a second server against the same ledger simultaneously. Multi-worker deployment requires an interprocess locking/storage redesign and is outside this MVP. Filesystem or power failures may still occur; atomic replacement is not a substitute for backups.

**Back up `data/ledger.json` manually before maintenance, redeployment or troubleshooting.** Stop writes before taking/restoring a backup. Never replace an existing ledger with an empty one to hide a problem. A missing ledger is initialized on the first endpoint access, so accidental deletion followed by a request creates a new empty chain; restore the backup before starting the app.

## Windows setup with VS Code
Open the project folder in Visual Studio Code and open a PowerShell terminal:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m unittest discover -s tests -v
python app.py
```

Open <http://127.0.0.1:5000>. The local entry point enables Flask debug mode for development only. Do not expose the debug server to the internet or use it in production. Stop it with `Ctrl+C`.

If PowerShell blocks activation, do not change your execution policy just to run this project; call the interpreter directly:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe app.py
```

Tests use temporary directories and do not touch the development ledger. The debug reloader starts processes for development; run only one server and no other ledger writers at once.

## Usage and demonstration
Use **synthetic information only**. Record these values:

- Company: Example Technologies
- Job title: Software Engineer
- Employment type: Full-time
- Work location: Indore
- Salary / CTC: 600000 INR per annum
- Offer issue date: 2026-10-28

A. Register: submit the fields. Save the generated Offer ID and hash; observe a new block and successful result.  
B. Verify: enter the ID and same fields. Expect **VERIFIED**.  
C. Change salary or title and verify again. Expect **MISMATCH**.  
D. Use a syntactically valid unknown ID, e.g. `OFR-20261028-0000000000000000`. Expect **NOT_FOUND** (unless that extraordinarily unlikely ID exists).  
E. Stop and restart the app; the record should remain.  
F. Run the unit tests: they tamper only with temporary ledgers and verify integrity failure and blocked registration. API tests verify blocked verification. Do not tamper with the real ledger to demonstrate this.  
G. Resize to desktop/mobile and check navigation, cards, forms, results and horizontally scrolling explorer table.  
H. After deploying, repeat registration and verification and confirm the record survives a web-app reload.

## API
All request bodies are JSON, limited to 16 KiB. Client errors produce JSON including `status` and `message`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | App UI |
| GET | `/api/health` | Process and ledger read/chain health |
| POST | `/api/offers` | Six offer fields; 201 and server-generated ID, timestamp, block, full hash and preview |
| POST | `/api/offers/verify` | `offer_id` plus six fields; match, mismatch, or not found (200); chain invalid (409) |
| GET | `/api/offers` | Metadata and total count, newest first |
| GET | `/api/chain/status` | Validation and counts; 409 if invalid |
| GET | `/api/chain/blocks` | Validated block metadata for explorer; 409 if invalid |

Invalid request: 400, oversized body: 413, storage access failure: 503. Chain-invalid registration and verification return 409 and `CHAIN_INVALID`. No original offer fields are returned from the ledger. A structural validation failure may report block position but not local filesystem paths.

## PythonAnywhere free deployment (checked 2026-10-28)
PythonAnywhere's [official free account features](https://help.pythonanywhere.com/pages/FreeAccountsFeatures/) list **one web app with one web worker and one-month expiry**, 512 MiB disk, 100 CPU seconds and two consoles. Availability and restrictions may change; consult the provider. Renew the web app according to the Web tab's instructions, and do not assume permanent uptime. One web worker is important for this app's process-local lock; never add writers in another process. If the free plan or single-worker constraint does not suit you, run the application locally for the demonstration instead; a multi-worker production version requires a different locking/storage design.

1. Create a PythonAnywhere account. In a Bash console, upload the source to `/home/YOURUSERNAME/OfferChain` through Files, or clone your GitHub repository there. Make sure `app.py` is directly inside that directory. Do **not** include a real/confidential ledger in a public repository.
2. In the console, use a supported Python version also available in the Web tab (example: 3.13):

   ```bash
   cd /home/YOURUSERNAME/OfferChain
   mkvirtualenv --python=/usr/bin/python3.13 offerchain-env
   pip install -r requirements.txt
   mkdir -p data
   ```

3. In **Web → Add a new web app**, choose **Manual configuration**, then the same Python version. Set the Virtualenv path to `/home/YOURUSERNAME/.virtualenvs/offerchain-env`. See [official Flask setup](https://help.pythonanywhere.com/pages/Flask/).
4. Click the **WSGI configuration file** link in the Web tab (typically `/var/www/YOURUSERNAME_pythonanywhere_com_wsgi.py` on US accounts; use the actual linked filename). Replace its contents with the following, substituting your username:

   ```python
   import sys
   project = '/home/YOURUSERNAME/OfferChain'
   if project not in sys.path:
       sys.path.insert(0, project)
   from app import application
   ```

   Do not call `app.run()` from WSGI. `application` is the production WSGI object; it does not enable debug mode.
5. Ensure `/home/YOURUSERNAME/OfferChain/data` is writable by your account. The app creates `data/ledger.json` on first access only when absent. To initialize explicitly, while no web worker is writing, run `python -c "from blockchain import Blockchain; print(Blockchain().status())"` from the project directory in the activated virtualenv. If the file already exists this checks it, never resets it. It remains under your home project directory, **not `/tmp`**.
6. Reload the web app in the Web tab and visit the displayed URL, typically `https://YOURUSERNAME.pythonanywhere.com/` (EU accounts may use `YOURUSERNAME.eu.pythonanywhere.com`). Test registration, matching and changed verification, explorer, integrity and reload persistence using fictional data.
7. Before uploading/redeploying, stop writes and download/back up `data/ledger.json` using Files. Do not upload an empty `data` directory or replace the existing ledger accidentally. Confirm the actual upload/Git workflow preserved the file before reloading. Restore only a trusted backup while writes are stopped. This is manual storage, not a managed database.

## Privacy, security and limitations
- **No authentication.** Anyone who can access the site can register as any company; IDs and hashes are visible in the explorer. Registration does not identify or authenticate the registrant. A matching hash is not legal proof, employer verification or a guarantee of authenticity.
- SHA-256 hashes are **not encryption**. An attacker who knows the ID and can guess likely field values can hash guesses and compare them to public hashes. Do not use real confidential offers, personal details or sensitive data in public demonstrations.
- Anyone able to change the file can rewrite the entire chain and recalculate every hash. There is no independent anchor, distributed consensus, trusted timestamp, authorization, audit trail, or tamper-proof storage.
- This is not suitable for real hiring, sensitive information, multiple worker processes or adversarial use. Public deployment allows arbitrary registrations and potential storage abuse. The ledger is only a local demonstration, not immutable or trustless.

## Troubleshooting
- **`py` or `python` not found:** install Python 3.10+ and enable the Windows launcher/PATH; restart VS Code.
- **`No module named flask`:** activate the correct virtualenv or use its explicit Python path, then run `python -m pip install -r requirements.txt`.
- **Port 5000 in use:** stop the other server or start a single alternative development server with `flask --app app run --port 5001`; do not run two writers on one ledger.
- **Integrity invalid / malformed ledger:** stop all writers, make a backup of the file, inspect or restore a known-good backup. The application does not silently repair it.
- **Ledger unavailable / write failure:** verify project `data` directory permissions and free disk space; check server logs for the generic ledger failure. Preserve a backup before changes.
- **PythonAnywhere site fails to load:** verify the Web tab's Python version, virtualenv path, WSGI import and project path; reload and inspect the web error log. See the provider's official Flask guide above.
- **Offer mismatch:** use the same ID, capitalization, employment type, date and wording. Extra whitespace and Unicode canonical equivalents are normalized, but other changes are significant.
