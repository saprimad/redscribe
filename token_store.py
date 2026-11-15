"""Hugging Face credentials: OS keyring only, never application settings."""
from dataclasses import dataclass, field
import os

SERVICE = "RedScribe"
ACCOUNT = "huggingface-token"
# Reject plaintext/third-party fallback stores, including within ChainerBackend.
OS_BACKENDS = {
    "keyring.backends.Windows", "keyring.backends.macOS",
    "keyring.backends.SecretService", "keyring.backends.kwallet",
    "keyring.backends.libsecret",
}


class TokenStoreError(Exception):
    """A sanitised error safe to show without revealing backend diagnostics."""


def _backend():
    try:
        import keyring
        backend = keyring.get_keyring()
        candidates = (backend.backends if type(backend).__module__ == "keyring.backends.chainer"
                      else [backend])
        for candidate in candidates:
            if type(candidate).__module__ in OS_BACKENDS and candidate.priority > 0:
                return candidate
    except Exception:
        pass
    raise TokenStoreError(
        "System credential store unavailable or locked. Install keyring and enable "
        "Windows Credential Manager, macOS Keychain or a Linux desktop keyring. "
        "You can still enter a token for this session."
    ) from None


def load_saved_token() -> str | None:
    try:
        return (_backend().get_password(SERVICE, ACCOUNT) or "").strip() or None
    except TokenStoreError:
        raise
    except Exception:
        raise TokenStoreError("Could not read the saved token. Unlock your system credential store or enter a session token.") from None


def save_token(token: str) -> None:
    token = token.strip()
    if not token or any(char.isspace() for char in token):
        raise TokenStoreError("Paste a single Hugging Face access token without spaces or line breaks.")
    try:
        backend = _backend()
        backend.set_password(SERVICE, ACCOUNT, token)
        if backend.get_password(SERVICE, ACCOUNT) != token:
            raise TokenStoreError("Could not confirm token storage. The entered token remains available for this session.")
    except TokenStoreError:
        raise
    except Exception:
        raise TokenStoreError("Could not save the token. Unlock your system credential store and try again. The token remains available for this session.") from None


def remove_saved_token() -> None:
    try:
        backend = _backend()
        if backend.get_password(SERVICE, ACCOUNT) is not None:
            backend.delete_password(SERVICE, ACCOUNT)
        if backend.get_password(SERVICE, ACCOUNT):
            raise TokenStoreError("Could not confirm removal of the saved token. Try again after unlocking your system credential store.")
    except TokenStoreError:
        raise
    except Exception:
        raise TokenStoreError("Could not remove the saved token. Unlock your system credential store and try again.") from None


@dataclass(frozen=True)
class TokenSelection:
    token: str | None = field(repr=False)
    source: str
    warning: str = ""


def resolve_token(entered: str = "") -> TokenSelection:
    """Priority: session entry, RedScribe keyring, environment, HF login."""
    if entered.strip():
        return TokenSelection(entered.strip(), "entered in app (session only)")
    warning = ""
    try:
        saved = load_saved_token()
        if saved:
            return TokenSelection(saved, "saved in system credential store")
    except TokenStoreError:
        warning = "System credential store unavailable."
    for variable in ("HF_TOKEN", "HUGGINGFACE_HUB_TOKEN"):
        token = os.environ.get(variable, "").strip()
        if token:
            return TokenSelection(token, "found in environment", warning)
    try:
        from huggingface_hub import get_token
        token = get_token()
        if token:
            return TokenSelection(token, "saved Hugging Face login found", warning)
    except Exception:
        warning = (warning + " Could not check Hugging Face login.").strip()
    return TokenSelection(None, "no token found", warning)
