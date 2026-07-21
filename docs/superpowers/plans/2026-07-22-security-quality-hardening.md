# Dashboard Builder Security And Quality Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Protect SQL data-source credentials, constrain user-supplied SQL execution, and make backend tests plus frontend lint/build mandatory in CI.

**Architecture:** Move credential encryption and SQL policy out of the FastAPI router into focused services. Accept structured connection configuration, encrypt the persisted representation, map models to sanitized response schemas, and execute only parser-validated read-only queries through bounded database connections. Keep the existing database column and update the React client to the structured contract.

**Tech Stack:** Python 3.11, FastAPI, Pydantic 2, SQLAlchemy 2, cryptography/Fernet, sqlglot, pytest, React 19, TypeScript 6, Vite 8, Oxlint, GitHub Actions

---

### Task 1: Add Security Configuration And Credential Cipher

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/core/config.py`
- Create: `backend/app/services/credential_cipher.py`
- Create: `backend/tests/test_credential_cipher.py`
- Modify: `backend/tests/conftest.py`
- Modify: `docker-compose.yml`
- Modify: `docker-compose.prod.yml`

- [ ] **Step 1: Add direct runtime dependencies**

Pin direct dependencies for the features actually imported by the application:

```text
cryptography==46.0.5
sqlglot==28.10.1
pymysql==1.1.2
psycopg[binary]==3.3.3
```

Before implementation, confirm these are current compatible releases in the selected Python environment. If the package index resolves a later patch, pin the installed patch and record it in the same commit.

- [ ] **Step 2: Write failing cipher tests**

Create `backend/tests/test_credential_cipher.py`:

```python
import json
from cryptography.fernet import Fernet
import pytest

from app.services.credential_cipher import CredentialCipher, ENCRYPTED_PREFIX


def test_cipher_encrypts_password_and_round_trips():
    cipher = CredentialCipher(Fernet.generate_key().decode())
    config = {
        "db_type": "postgresql",
        "host": "db.example.com",
        "port": 5432,
        "database": "analytics",
        "username": "reader",
        "password": "top-secret",
    }

    stored = cipher.encrypt(config)

    assert stored.startswith(ENCRYPTED_PREFIX)
    assert "top-secret" not in stored
    assert cipher.decrypt(stored) == config


def test_cipher_reads_legacy_plaintext_json():
    cipher = CredentialCipher(Fernet.generate_key().decode())
    legacy = json.dumps({"db_type": "sqlite", "database": "sample.db"})
    assert cipher.decrypt(legacy)["database"] == "sample.db"


def test_cipher_rejects_invalid_key():
    with pytest.raises(ValueError, match="DATASOURCE_ENCRYPTION_KEY"):
        CredentialCipher("not-a-fernet-key")
```

- [ ] **Step 3: Run the focused test to verify red**

```bash
cd backend
python -m pytest tests/test_credential_cipher.py -v
```

Expected: FAIL because `CredentialCipher` does not exist.

- [ ] **Step 4: Implement the focused cipher service**

Create `backend/app/services/credential_cipher.py`:

```python
import json
from cryptography.fernet import Fernet, InvalidToken

ENCRYPTED_PREFIX = "fernet:v1:"


class CredentialCipher:
    def __init__(self, key: str):
        try:
            self._fernet = Fernet(key.encode())
        except (TypeError, ValueError) as exc:
            raise ValueError("DATASOURCE_ENCRYPTION_KEY must be a valid Fernet key") from exc

    def encrypt(self, config: dict) -> str:
        payload = json.dumps(config, separators=(",", ":"), sort_keys=True).encode()
        return ENCRYPTED_PREFIX + self._fernet.encrypt(payload).decode()

    def decrypt(self, stored: str) -> dict:
        try:
            if stored.startswith(ENCRYPTED_PREFIX):
                token = stored.removeprefix(ENCRYPTED_PREFIX).encode()
                payload = self._fernet.decrypt(token).decode()
            else:
                payload = stored
            result = json.loads(payload)
        except (InvalidToken, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Stored data-source credentials are invalid") from exc
        if not isinstance(result, dict):
            raise ValueError("Stored data-source credentials must be an object")
        return result

    @staticmethod
    def public_config(config: dict) -> dict:
        return {key: value for key, value in config.items() if key != "password"}
```

- [ ] **Step 5: Add explicit settings and test fixtures**

Add these fields to `Settings`:

```python
DATASOURCE_ENCRYPTION_KEY: str = ""
SQL_ALLOWED_HOSTS: str = ""
SQL_QUERY_TIMEOUT_SECONDS: int = 10
SQL_MAX_ROWS: int = 1000
SQLITE_DATA_DIR: str = "./data"
```

Extend the model validator so `DEBUG=False` rejects an empty encryption key, a timeout outside `1..60`, or rows outside `1..10000`. In `backend/tests/conftest.py`, set `settings.DATASOURCE_ENCRYPTION_KEY` to `Fernet.generate_key().decode()` before API requests.

Set an explicit development key and local allowed hosts in `docker-compose.yml`. In production Compose, require `${DATASOURCE_ENCRYPTION_KEY:?set DATASOURCE_ENCRYPTION_KEY}` and `${SQL_ALLOWED_HOSTS:-db}` instead of committing a production secret.

- [ ] **Step 6: Verify and commit**

```bash
cd backend
python -m pytest tests/test_credential_cipher.py -v
python -m pytest tests/test_models.py -v
cd ..
git add backend/requirements.txt backend/app/core/config.py backend/app/services/credential_cipher.py backend/tests/test_credential_cipher.py backend/tests/conftest.py docker-compose.yml docker-compose.prod.yml
git commit -m "feat: encrypt data source credentials"
```

Expected: focused tests pass and no Fernet key intended for production is committed.

### Task 2: Introduce Structured And Sanitized Data-Source Schemas

**Files:**
- Modify: `backend/app/schemas/datasource.py`
- Modify: `backend/app/api/datasources.py`
- Modify: `backend/tests/test_datasources.py`
- Modify: `frontend/src/services/dashboard.ts`
- Modify: `frontend/src/pages/DataSourcePage.tsx`
- Modify: `frontend/src/components/SqlQueryEditor.tsx`

- [ ] **Step 1: Write failing API secrecy tests**

Append tests that create an SQL data source with a password, inspect the ORM row, and list data sources:

```python
async def test_sql_credentials_are_encrypted_and_redacted(
    async_client, auth_headers, db_session
):
    payload = {
        "name": "analytics",
        "source_type": "sql",
        "connection_config": {
            "db_type": "postgresql",
            "host": "db.example.com",
            "port": 5432,
            "database": "analytics",
            "username": "reader",
            "password": "top-secret",
        },
    }
    created = await async_client.post("/api/datasources", json=payload, headers=auth_headers)
    assert created.status_code == 201
    assert "top-secret" not in created.text
    assert created.json()["connection"]["username"] == "reader"
    assert "password" not in created.json()["connection"]

    listed = await async_client.get("/api/datasources", headers=auth_headers)
    assert listed.status_code == 200
    assert "top-secret" not in listed.text
```

- [ ] **Step 2: Run the test to verify red**

```bash
cd backend
python -m pytest tests/test_datasources.py::test_sql_credentials_are_encrypted_and_redacted -v
```

Expected: FAIL because the current API accepts a JSON string and returns `connection_config`.

- [ ] **Step 3: Replace stringly typed schemas**

Define these Pydantic contracts in `backend/app/schemas/datasource.py`:

```python
class SQLConnectionConfig(BaseModel):
    db_type: Literal["sqlite", "mysql", "postgresql"]
    host: str | None = None
    port: int | None = Field(default=None, ge=1, le=65535)
    database: str
    username: str | None = None
    password: str | None = Field(default=None, repr=False)


class PublicSQLConnectionConfig(BaseModel):
    db_type: Literal["sqlite", "mysql", "postgresql"]
    host: str | None = None
    port: int | None = None
    database: str
    username: str | None = None


class DataSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    source_type: Literal["csv", "sql"]
    raw_data: str | None = None
    config_json: str = "{}"
    connection_config: SQLConnectionConfig | None = None


class DataSourceResponse(BaseModel):
    id: int
    name: str
    source_type: str
    config_json: str
    created_at: datetime
    connection: PublicSQLConnectionConfig | None = None
```

Do not include `raw_data`, `password`, or encrypted `connection_config` in list/create responses.

- [ ] **Step 4: Add a single response mapper in the router**

Create `_to_response(ds, cipher)` that decrypts SQL configuration, applies `CredentialCipher.public_config`, and constructs `DataSourceResponse`. Use the mapper for create, upload, and list routes. Encrypt `body.connection_config.model_dump(exclude_none=True)` before assigning the ORM field.

- [ ] **Step 5: Update the React contract**

Export typed `DataSource`, `SQLConnectionConfig`, and `PublicSQLConnectionConfig` interfaces from `frontend/src/services/dashboard.ts`. Change `dataSourceService.create` to accept `connection_config?: SQLConnectionConfig`, change `list` to return `DataSource[]`, and send the object directly from `DataSourcePage.tsx` instead of `JSON.stringify`. Remove `connection_config` from `SqlDataSource` in `SqlQueryEditor.tsx`; the editor only needs `id`, `name`, and `source_type`.

- [ ] **Step 6: Verify backend and frontend, then commit**

```bash
cd backend
python -m pytest tests/test_datasources.py -v
cd ../frontend
npm ci
npm run build
cd ..
git add backend/app/schemas/datasource.py backend/app/api/datasources.py backend/tests/test_datasources.py frontend/src/services/dashboard.ts frontend/src/pages/DataSourcePage.tsx frontend/src/components/SqlQueryEditor.tsx frontend/package-lock.json
git commit -m "fix: redact data source credentials"
```

Expected: backend tests pass, frontend builds, and API JSON contains no password or ciphertext.

### Task 3: Parse And Authorize Read-Only SQL

**Files:**
- Create: `backend/app/services/sql_policy.py`
- Create: `backend/tests/test_sql_policy.py`
- Modify: `backend/app/core/config.py`

- [ ] **Step 1: Write failing parser and host-policy tests**

Cover one simple `SELECT`, a `WITH ... SELECT`, multiple statements, `INSERT ... RETURNING`, `SELECT ... INTO`, metadata IP `169.254.169.254`, a private resolved address not explicitly allowed, and an explicitly allowed Docker hostname. Mock `socket.getaddrinfo` so tests do not use the network.

The core assertions are:

```python
policy.validate_query("SELECT id FROM sales")
policy.validate_query("WITH totals AS (SELECT 1 AS n) SELECT n FROM totals")

with pytest.raises(SQLPolicyError, match="single read-only"):
    policy.validate_query("SELECT 1; DELETE FROM users")

with pytest.raises(SQLPolicyError, match="not allowed"):
    policy.validate_host("169.254.169.254")
```

- [ ] **Step 2: Run tests to verify red**

```bash
cd backend
python -m pytest tests/test_sql_policy.py -v
```

Expected: FAIL because the policy module does not exist.

- [ ] **Step 3: Implement SQLPolicy with sqlglot**

Create `SQLPolicyError(ValueError)` and `SQLPolicy`. Parse with the dialect derived from `db_type`, require exactly one expression, require `isinstance(expression, sqlglot.exp.Query)`, and reject any descendant that writes, creates, drops, executes, or selects into a table. Return the normalized SQL string for execution instead of using the original text.

The constructor accepts `allowed_hosts: set[str]`, `sqlite_data_dir: Path`, and a resolver callable for tests. `validate_host` must always reject unspecified, multicast, link-local, and metadata-service addresses; it may allow private or loopback addresses only when the original host is explicitly listed. Resolve hostnames once and validate every returned address.

- [ ] **Step 4: Restrict SQLite paths**

Allow `:memory:` for tests. Resolve other SQLite paths beneath `SQLITE_DATA_DIR` and reject any path whose resolved value is outside that directory:

```python
candidate = (self.sqlite_data_dir / database).resolve()
if not candidate.is_relative_to(self.sqlite_data_dir.resolve()):
    raise SQLPolicyError("SQLite database path is not allowed")
```

- [ ] **Step 5: Verify and commit**

```bash
cd backend
python -m pytest tests/test_sql_policy.py -v
cd ..
git add backend/app/services/sql_policy.py backend/app/core/config.py backend/tests/test_sql_policy.py
git commit -m "feat: enforce read-only SQL policy"
```

### Task 4: Bound SQL Connection And Result Execution

**Files:**
- Create: `backend/app/services/sql_executor.py`
- Create: `backend/tests/test_sql_executor.py`
- Modify: `backend/app/api/datasources.py`
- Modify: `backend/app/schemas/datasource.py`
- Modify: `backend/tests/test_datasources.py`

- [ ] **Step 1: Write failing executor tests**

Use a temporary SQLite database to assert that a query returning more than three rows returns only three rows with `truncated=True`. Add a mocked slow executor test asserting the async route returns HTTP 504 with `{"detail": "SQL query timed out"}` and never includes the connection URL.

- [ ] **Step 2: Define the bounded response**

Extend `SQLExecuteResponse`:

```python
class SQLExecuteResponse(BaseModel):
    columns: list[str]
    rows: list[dict]
    row_count: int
    truncated: bool = False
```

- [ ] **Step 3: Implement a focused synchronous executor**

`SQLExecutor.execute(config, query)` must build URLs with SQLAlchemy `URL.create` so usernames and passwords are encoded correctly. Use `postgresql+psycopg` and `mysql+pymysql` drivers. Configure read-only mode and driver statement timeouts where supported, execute the normalized query, and call `fetchmany(max_rows + 1)`. Return only `max_rows`, set `truncated` from the extra row, stringify non-JSON scalar values, and dispose the engine in `finally`.

- [ ] **Step 4: Integrate policy, cipher, and executor in the route**

The route flow must be:

```python
stored = cipher.decrypt(ds.connection_config)
normalized_query = policy.validate_query(body.query, stored["db_type"])
policy.validate_connection(stored)
result = await asyncio.wait_for(
    asyncio.to_thread(executor.execute, stored, normalized_query),
    timeout=settings.SQL_QUERY_TIMEOUT_SECONDS + 1,
)
```

Map `SQLPolicyError` to HTTP 400, `asyncio.TimeoutError` to HTTP 504, and all driver exceptions to HTTP 502 with `detail="Database query failed"`. Log exception class and data-source ID only; do not log the query, password, or connection URL.

If `ds.connection_config` is legacy plaintext, encrypt it and commit the row after successful execution.

- [ ] **Step 5: Run security and regression tests**

```bash
cd backend
python -m pytest tests/test_sql_executor.py tests/test_sql_policy.py tests/test_datasources.py -v
python -m pytest tests/ -v
```

Expected: all tests pass; DDL/DML/multiple statements fail closed; credentials and driver messages are absent from public responses.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/sql_executor.py backend/app/api/datasources.py backend/app/schemas/datasource.py backend/tests/test_sql_executor.py backend/tests/test_datasources.py
git commit -m "fix: bound SQL data source execution"
```

### Task 5: Enforce Frontend Quality In CI

**Files:**
- Modify: `.github/workflows/test.yml`
- Modify: `frontend/src/pages/DashboardEditorPage.tsx`
- Modify: `frontend/src/pages/DashboardViewPage.tsx`
- Modify: `frontend/src/pages/DataSourcePage.tsx`
- Modify: `frontend/src/components/SqlQueryEditor.tsx`
- Modify: `frontend/src/services/dashboard.ts`

- [ ] **Step 1: Run the current frontend gates**

```bash
cd frontend
npm ci
npm run lint
npm run build
```

Expected: record every current lint or TypeScript failure before editing.

- [ ] **Step 2: Remove unsafe data-source `any` types**

Use the exported `DataSource`, `SQLExecuteResult`, and row types in pages and components. Replace `Record<number, any>` with `Record<number, SQLExecuteResult | DataSourceData>` and catch `unknown` errors through the existing Axios error helper or `axios.isAxiosError`.

- [ ] **Step 3: Re-run local frontend gates**

```bash
npm run lint
npm run build
```

Expected: both commands exit 0 without reducing TypeScript strictness or adding blanket lint disables.

- [ ] **Step 4: Add a frontend CI job**

Add this independent job to `.github/workflows/test.yml`:

```yaml
frontend:
  runs-on: ubuntu-latest
  defaults:
    run:
      working-directory: frontend
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-node@v4
      with:
        node-version: '22'
        cache: npm
        cache-dependency-path: frontend/package-lock.json
    - run: npm ci
    - run: npm run lint
    - run: npm run build
```

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/test.yml frontend/src
git commit -m "ci: validate frontend lint and build"
```

### Task 6: Reconcile Repository Documentation

**Files:**
- Modify: `README.md`
- Modify: `CLAUDE.md`
- Modify: `docs/ARCHITECTURE.md`

- [ ] **Step 1: Replace stale dependency claims**

Read versions from `frontend/package.json` and `backend/requirements.txt`. Update React, Ant Design, ECharts, Vite, TypeScript, Python, FastAPI, and SQLAlchemy references. Mark WebSocket collaboration and PostgreSQL production support as implemented because source and deployment files exist.

- [ ] **Step 2: Remove broken public claims**

Replace the `your-org` badge with the real repository URL. Remove the screenshots table because the referenced files do not exist. Remove the MIT badge and license claim unless a real `LICENSE` file is added with the owner's chosen text; this plan does not invent ownership terms.

- [ ] **Step 3: Document secure SQL configuration**

Add exact environment-variable descriptions for `DATASOURCE_ENCRYPTION_KEY`, `SQL_ALLOWED_HOSTS`, `SQL_QUERY_TIMEOUT_SECONDS`, `SQL_MAX_ROWS`, and `SQLITE_DATA_DIR`. Include the key-generation command:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

State that database accounts must be read-only even though the application also enforces query policy.

- [ ] **Step 4: Validate documentation**

```bash
rg -n "your-org|screenshots/|React 18|Ant Design 5|ECharts 5|\[ \] \*\*Real-time Collaboration|\[ \] \*\*PostgreSQL" README.md CLAUDE.md docs/ARCHITECTURE.md
```

Expected: no stale match remains.

- [ ] **Step 5: Commit**

```bash
git add README.md CLAUDE.md docs/ARCHITECTURE.md
git commit -m "docs: align security and project status"
```

### Task 7: Final Verification And Push Readiness

**Files:**
- Verify only: entire repository

- [ ] **Step 1: Run the backend suite from a clean environment**

```bash
cd backend
python -m pip install -r requirements.txt
python -m pytest tests/ -v
```

Expected: all existing and new tests pass.

- [ ] **Step 2: Run the frontend suite from the lockfile**

```bash
cd frontend
npm ci
npm run lint
npm run build
```

Expected: all commands exit 0.

- [ ] **Step 3: Inspect diffs and tracked secrets**

```bash
git diff --check HEAD~6..HEAD
git grep -n -E "(postgresql|mysql)://[^[:space:]]+:[^[:space:]@]+@|BEGIN (RSA|OPENSSH) PRIVATE KEY"
```

Expected: no real credential or private key is tracked. Development examples must use explicit non-production values.

- [ ] **Step 4: Check remote divergence before handoff**

```bash
git fetch origin master
git rev-list --left-right --count origin/master...HEAD
git status --short
```

Expected: the working tree is clean and the remote side has zero commits not present locally. Do not push if the remote advanced; inspect and integrate remote changes first.
