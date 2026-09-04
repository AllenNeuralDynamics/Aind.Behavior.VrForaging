"""Push a day's generated trainer states to the Dataverse curriculum table.

The rig reads its next trainer state from Dataverse, and nothing puts one there: a state is
generated locally and then entered by hand. A mouse whose row is missed silently re-runs the
state already on its rig, which on a closed block cycle opens it in the set it did not end in --
an uncued reversal that reads as perseveration in the data and is invisible in the file tree,
because the generated file is sitting there looking correct.

This pushes a whole directory at once and reads each row back afterwards, so a day's intent is
confirmed against the table rather than against the files that were meant to reach it.

Authentication is MSAL device code flow: the first run prints a code to enter at the URL it
names, and the refresh token is cached so later runs need no interaction. Rows are written as
the signed-in user, so the audit trail names a person rather than a shared service account.

Writes APPEND. Readers take the most recent row per (mouse, task), so a correction is another
push rather than an edit, and superseded rows stay as history.

Examples:
    # Resolve every mouse and show what would be posted, without writing
    uv run python scripts/push_states.py --state-dir local/task_logic_schemas/2026-09-04 --dry-run

    # Push, with a confirmation prompt
    uv run python scripts/push_states.py --state-dir local/task_logic_schemas/2026-09-04
"""

import os
import re
import sys
import time
import warnings
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Any

import msal
import requests
import tyro
import yaml
from aind_behavior_curriculum import TrainerState
from pydantic import BaseModel

#: Where a ``dataverse`` section is looked for, highest priority first. The first three are
#: clabe's own search path, so the two read one configuration rather than drifting apart; the
#: checked-in example comes last, which holds nothing secret and makes a fresh clone work.
CONFIG_FILES = (
    Path("./local/clabe.yml"),
    Path("./clabe.yml"),
    Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "clabe.yml",
    Path(__file__).parent.parent / "examples" / "clabe.yml",
)

DEFAULT_TOKEN_CACHE = Path.home() / ".cache" / "aind-dataverse" / "token_cache.json"

MICE_TABLE = "aibs_dim_mices"
SUGGESTIONS_TABLE = "aibs_fact_mouse_proposed_behavior_sessionses"

#: Generous, because a state is tens of KB of JSON and the environment is remote.
REQUEST_TIMEOUT = 30
GET_RETRIES = 3
RETRY_BACKOFF = 2.0

#: Dataverse caps a multiline text column at 1048576 characters; warn before a state approaches it.
STATE_SIZE_WARN = 900_000


class DataverseSettings(BaseModel):
    """Which Dataverse environment holds the curriculum tables, and which app registration to use."""

    tenant_id: str
    client_id: str
    org: str

    @classmethod
    def resolve(cls) -> "DataverseSettings":
        """Read the first ``dataverse`` config section found, letting the environment override it.

        Returns:
            DataverseSettings: The resolved connection details.

        Raises:
            ValueError: If no section was found and the environment does not supply every field.
        """
        values: dict[str, Any] = {}
        for path in CONFIG_FILES:
            if path.exists():
                section = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get(
                    "dataverse"
                )
                if section:
                    values = dict(section)
                    break
        values |= {
            field: os.environ[f"DATAVERSE_{field.upper()}"]
            for field in ("tenant_id", "client_id", "org")
            if f"DATAVERSE_{field.upper()}" in os.environ
        }
        missing = {"tenant_id", "client_id", "org"} - values.keys()
        if missing:
            searched = ", ".join(str(p) for p in CONFIG_FILES)
            raise ValueError(
                f"No Dataverse settings for {sorted(missing)}. Add a 'dataverse' section to one of "
                f"{searched}, or set DATAVERSE_TENANT_ID / DATAVERSE_CLIENT_ID / DATAVERSE_ORG."
            )
        return cls.model_validate(values)


def _load_cache(path: Path) -> msal.SerializableTokenCache:
    """Return the token cache stored at *path*, empty if there is none."""
    cache = msal.SerializableTokenCache()
    if path.exists():
        cache.deserialize(path.read_text(encoding="utf-8"))
    return cache


def _save_cache(cache: msal.SerializableTokenCache, path: Path) -> None:
    """Persist *cache* if it changed, readable only by its owner."""
    if not cache.has_state_changed:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(cache.serialize(), encoding="utf-8")
    # It holds a refresh token, which is a credential in its own right.
    path.chmod(0o600)


def _strip_html(value: str) -> str:
    """Undo the rich-text wrapping Dataverse applies to a long text column."""
    return unescape(re.sub(r"<[^>]+>", "", value)).strip()


class DataverseClient:
    """Minimal OData client for the curriculum suggestion tables, authenticated as a user."""

    def __init__(self, settings: DataverseSettings, cache_path: Path):
        self._settings = settings
        self._cache_path = cache_path
        self._cache = _load_cache(cache_path)
        self._app = msal.PublicClientApplication(
            client_id=settings.client_id,
            authority=f"https://login.microsoftonline.com/{settings.tenant_id}",
            token_cache=self._cache,
        )

    @property
    def _scope(self) -> str:
        return f"https://{self._settings.org}.crm.dynamics.com/.default"

    @property
    def _api_url(self) -> str:
        return f"https://{self._settings.org}.api.crm.dynamics.com/api/data/v9.2/"

    def sign_in(self) -> str:
        """Return the signed-in username, prompting for a device code only when the cache is cold.

        Returns:
            str: The authenticated user principal name.

        Raises:
            RuntimeError: If the app registration refuses device code flow, or sign-in fails.
        """
        silent = self._silent_token()
        if silent is not None:
            accounts = self._app.get_accounts()
            return (
                str(accounts[0].get("username", "unknown")) if accounts else "unknown"
            )

        flow = self._app.initiate_device_flow(scopes=[self._scope])
        if "user_code" not in flow:
            raise RuntimeError(
                f"Device code flow refused by the app registration: "
                f"{flow.get('error_description', flow.get('error', 'no reason given'))}"
            )
        print(flow["message"], flush=True)
        result = self._app.acquire_token_by_device_flow(flow)
        if "access_token" not in result:
            raise RuntimeError(
                f"Sign-in failed: {result.get('error_description', result.get('error'))}"
            )
        _save_cache(self._cache, self._cache_path)
        return str(
            result.get("id_token_claims", {}).get("preferred_username", "unknown")
        )

    def _silent_token(self) -> str | None:
        """Return a cached or refreshed access token, or ``None`` if the user must sign in."""
        accounts = self._app.get_accounts()
        if not accounts:
            return None
        result = self._app.acquire_token_silent([self._scope], account=accounts[0])
        _save_cache(self._cache, self._cache_path)
        return (
            str(result["access_token"]) if result and "access_token" in result else None
        )

    def _headers(self) -> dict[str, str]:
        token = self._silent_token()
        if token is None:
            raise RuntimeError("Not signed in. Call sign_in() first.")
        return {
            "Authorization": f"Bearer {token}",
            "OData-MaxVersion": "4.0",
            "OData-Version": "4.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _get(self, url: str) -> requests.Response:
        """GET *url*, retrying a timeout or dropped connection with exponential backoff."""
        delay = RETRY_BACKOFF
        for attempt in range(1, GET_RETRIES + 1):
            try:
                response = requests.get(
                    url, headers=self._headers(), timeout=REQUEST_TIMEOUT
                )
                response.raise_for_status()
                return response
            except (
                requests.exceptions.ReadTimeout,
                requests.exceptions.ConnectionError,
            ):
                if attempt == GET_RETRIES:
                    raise
                time.sleep(delay)
                delay *= 2
        raise AssertionError("unreachable")

    def mouse_guid(self, subject_id: str) -> str:
        """Return the Dataverse row id for a mouse, looked up by its readable id."""
        response = self._get(
            f"{self._api_url}{MICE_TABLE}(aibs_mouse_id='{subject_id}')"
        )
        return str(response.json()["aibs_dim_miceid"])

    def latest_suggestion(
        self, subject_guid: str, task_name: str
    ) -> dict[str, Any] | None:
        """Return the newest suggestion row for a mouse and task, or ``None`` if it has none."""
        query = (
            f"?$filter=aibs_task_name eq '{task_name}' and _aibs_mouse_id_value eq '{subject_guid}'"
            "&$orderby=createdon desc&$top=1"
            "&$select=aibs_stage_name,aibs_trainer_state,createdon"
        )
        rows = (
            self._get(f"{self._api_url}{SUGGESTIONS_TABLE}{query}")
            .json()
            .get("value", [])
        )
        return dict(rows[0]) if rows else None

    def append_suggestion(
        self, subject_guid: str, stage_name: str, task_name: str, state_json: str
    ) -> None:
        """Append one suggestion row. Never retried: a repeated POST would append a duplicate."""
        response = requests.post(
            f"{self._api_url}{SUGGESTIONS_TABLE}",
            headers=self._headers(),
            json={
                "aibs_task_name": task_name,
                "aibs_mouse_id@odata.bind": f"/{MICE_TABLE}({subject_guid})",
                "aibs_stage_name": stage_name,
                "aibs_trainer_state": state_json,
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()


def serialize_state(trainer_state: TrainerState) -> str:
    """Return the JSON to store for *trainer_state*, checked for a clean round trip.

    Args:
        trainer_state: The state to serialize.

    Returns:
        str: The serialized state.

    Raises:
        ValueError: If the state carries no stage.
    """
    stage = trainer_state.stage
    if stage is None:
        raise ValueError("trainer state has no stage")
    # The rig reads the stage name off the task and analysis keys on it, so the two must agree.
    stage.task.stage_name = stage.name
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", message="Deserialized versioned field.*", category=UserWarning
        )
        payload = trainer_state.model_dump_json()
        # A row that will not parse back is worse than a refused push, so catch it here.
        TrainerState.model_validate_json(payload, strict=False)
    return payload


def read_state_dir(state_dir: Path) -> dict[str, tuple[Path, TrainerState]]:
    """Load every ``<subject>_<stage_name>.json`` in *state_dir*, keyed by subject.

    Args:
        state_dir: Directory of generated states.

    Returns:
        dict: Subject id to the file it came from and its parsed state.

    Raises:
        ValueError: If the directory is empty, or two files claim the same mouse.
    """
    states: dict[str, tuple[Path, TrainerState]] = {}
    for path in sorted(state_dir.glob("*.json")):
        subject = path.stem.split("_")[0]
        if not subject.isdigit():
            raise ValueError(
                f"{path.name} does not start with a subject id; upload routes on that prefix"
            )
        if subject in states:
            raise ValueError(
                f"{path.name} and {states[subject][0].name} both claim mouse {subject}"
            )
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", message="Deserialized versioned field.*", category=UserWarning
            )
            states[subject] = (
                path,
                TrainerState.model_validate_json(path.read_text(encoding="utf-8")),
            )
    if not states:
        raise ValueError(f"No state files in {state_dir}")
    return states


@dataclass
class PushStates:
    """Push a directory of generated trainer states to Dataverse and read each row back."""

    state_dir: Path
    """Directory of generated states, one ``<subject>_<stage_name>.json`` per mouse."""
    dry_run: bool = False
    """Resolve every mouse and show what would be posted, then stop without writing."""
    yes: bool = False
    """Skip the confirmation prompt, for a run that has already been shown as a dry run."""
    token_cache: Path = DEFAULT_TOKEN_CACHE
    """Where the refresh token is cached, written 0600. Delete it to sign in as someone else."""

    def run(self) -> int:
        """Push every state in the directory. Returns a process exit code."""
        states = read_state_dir(self.state_dir)
        client = DataverseClient(DataverseSettings.resolve(), self.token_cache)
        print(f"Signed in as {client.sign_in()}\n")

        # Every mouse is resolved before anything is written, so a typo in one filename cannot
        # leave the cohort half pushed.
        plan = []
        for subject, (path, state) in states.items():
            payload = serialize_state(state)
            current = client.latest_suggestion(
                client.mouse_guid(subject), state.stage.task.name
            )
            plan.append((subject, path, state, payload, current))

        self._show(plan)
        if self.dry_run:
            print("\nDry run: nothing written.")
            return 0
        if (
            not self.yes
            and input(f"\nPush {len(plan)} state(s)? [y/N] ").strip().lower() != "y"
        ):
            print("Aborted; nothing written.")
            return 1
        return self._push(client, plan)

    @staticmethod
    def _show(
        plan: list[tuple[str, Path, TrainerState, str, dict[str, Any] | None]],
    ) -> None:
        """Print what each mouse currently has in the table and what would replace it."""
        print(f"{'mouse':<8} {'currently':<52} {'to push':<52} {'KB':>6}")
        for subject, _, state, payload, current in plan:
            now = (current or {}).get("aibs_stage_name") or "(none)"
            print(
                f"{subject:<8} {now[:52]:<52} {state.stage.name[:52]:<52} {len(payload) / 1024:>6.0f}"
            )
            if len(payload) > STATE_SIZE_WARN:
                print(
                    f"{'':<8} WARNING: {len(payload)} characters approaches the column limit of 1048576"
                )

    @staticmethod
    def _push(
        client: DataverseClient,
        plan: list[tuple[str, Path, TrainerState, str, dict[str, Any] | None]],
    ) -> int:
        """Append each row, then read it back and compare it against what was sent."""
        failed = []
        for subject, _, state, payload, _ in plan:
            task_name = state.stage.task.name
            guid = client.mouse_guid(subject)
            try:
                client.append_suggestion(guid, state.stage.name, task_name, payload)
            except requests.HTTPError as exc:
                print(f"{subject}  WRITE FAILED: {exc}")
                failed.append(subject)
                continue
            stored = client.latest_suggestion(guid, task_name)
            note = _compare(stored, payload)
            print(f"{subject}  {state.stage.name}  {note}")
            if note != "verified":
                failed.append(subject)
        print()
        if failed:
            print(f"{len(failed)} of {len(plan)} FAILED: {' '.join(failed)}")
            return 1
        print(f"ALL {len(plan)} PUSHED AND VERIFIED")
        return 0


def _compare(stored: dict[str, Any] | None, sent: str) -> str:
    """Say whether the row read back matches what was sent."""
    if stored is None:
        return "MISMATCH: no row came back"
    raw = stored.get("aibs_trainer_state")
    if not raw:
        return "MISMATCH: row has no trainer state"
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", message="Deserialized versioned field.*", category=UserWarning
            )
            round_tripped = TrainerState.model_validate_json(
                _strip_html(raw), strict=False
            ).model_dump_json()
    except Exception as exc:  # noqa: BLE001 - any parse failure is the same answer to the caller
        return f"MISMATCH: stored row will not parse ({type(exc).__name__})"
    return (
        "verified"
        if round_tripped == sent
        else "MISMATCH: stored row differs from what was sent"
    )


if __name__ == "__main__":
    sys.exit(tyro.cli(PushStates).run())
