"""Credential lifecycle and fallback tests; no real tokens or OS stores used."""
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import token_store as store


class TokenStoreTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {}, clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.hub = patch.dict(sys.modules, {"huggingface_hub": SimpleNamespace(get_token=lambda: None)})
        self.hub.start()
        self.addCleanup(self.hub.stop)

    def test_save_load_and_remove_across_calls(self):
        values = {}
        backend = Mock()
        backend.set_password.side_effect = lambda s, a, t: values.update({(s, a): t})
        backend.get_password.side_effect = lambda s, a: values.get((s, a))
        backend.delete_password.side_effect = lambda s, a: values.pop((s, a))
        with patch.object(store, "_backend", return_value=backend):
            store.save_token(" hf_example_only ")
            self.assertEqual(store.load_saved_token(), "hf_example_only")
            store.remove_saved_token()
            self.assertIsNone(store.load_saved_token())
            store.remove_saved_token()  # Already removed is a successful no-op.
        self.assertEqual(backend.delete_password.call_count, 1)

    def test_session_entry_does_not_access_or_write_keyring(self):
        with patch.object(store, "_backend") as backend:
            self.assertEqual(store.resolve_token(" session ").token, "session")
            backend.assert_not_called()

    def test_saved_token_takes_precedence_over_environment(self):
        os.environ["HF_TOKEN"] = "environment"
        with patch.object(store, "load_saved_token", return_value="saved"):
            self.assertEqual(store.resolve_token().token, "saved")

    def test_unavailable_keyring_falls_back_to_environment(self):
        os.environ["HF_TOKEN"] = "environment"
        with patch.object(store, "load_saved_token", side_effect=store.TokenStoreError("locked")):
            result = store.resolve_token()
        self.assertEqual(result.token, "environment")
        self.assertTrue(result.warning)

    def test_environment_alias_and_hf_login(self):
        with patch.object(store, "load_saved_token", return_value=None):
            os.environ["HUGGINGFACE_HUB_TOKEN"] = "legacy-environment"
            self.assertEqual(store.resolve_token().token, "legacy-environment")
            os.environ.clear()
            with patch.dict(sys.modules, {"huggingface_hub": SimpleNamespace(get_token=lambda: "login")}):
                self.assertEqual(store.resolve_token().token, "login")

    def test_missing_token_is_not_an_error(self):
        with patch.object(store, "load_saved_token", return_value=None):
            self.assertIsNone(store.resolve_token().token)

    def test_missing_keyring_dependency(self):
        with patch.dict(sys.modules, {"keyring": None}):
            with self.assertRaises(store.TokenStoreError):
                store.load_saved_token()

    def test_only_native_backend_is_selected_from_chain(self):
        Native = type("Keyring", (), {"__module__": "keyring.backends.Windows", "priority": 5})
        Plaintext = type("PlaintextKeyring", (), {"__module__": "keyrings.alt.file", "priority": 9})
        Chain = type("ChainerBackend", (), {"__module__": "keyring.backends.chainer"})
        chain = Chain()
        native = Native()
        chain.backends = [Plaintext(), native]
        with patch.dict(sys.modules, {"keyring": SimpleNamespace(get_keyring=lambda: chain)}):
            self.assertIs(store._backend(), native)

    def test_plaintext_null_and_fail_backends_are_rejected(self):
        for module in ("keyrings.alt.file", "keyring.backends.null", "keyring.backends.fail"):
            backend = type("Keyring", (), {"__module__": module, "priority": 10})()
            with self.subTest(module=module), patch.dict(sys.modules, {"keyring": SimpleNamespace(get_keyring=lambda: backend)}):
                with self.assertRaises(store.TokenStoreError):
                    store.save_token("hf_example_only")

    def test_backend_errors_never_expose_token_in_displayed_error(self):
        backend = Mock()
        for operation, action in (("set_password", lambda: store.save_token("hf_example_only")),
                                  ("get_password", store.load_saved_token),
                                  ("delete_password", store.remove_saved_token)):
            backend.reset_mock(side_effect=True)
            getattr(backend, operation).side_effect = RuntimeError("secret hf_example_only")
            with self.subTest(operation=operation), patch.object(store, "_backend", return_value=backend):
                with self.assertRaises(store.TokenStoreError) as error:
                    action()
                self.assertNotIn("hf_example_only", str(error.exception))

    def test_save_and_remove_require_confirmation_from_backend(self):
        backend = Mock()
        backend.get_password.return_value = "unchanged"
        with patch.object(store, "_backend", return_value=backend):
            with self.assertRaises(store.TokenStoreError):
                store.save_token("replacement")
            with self.assertRaises(store.TokenStoreError):
                store.remove_saved_token()

    def test_empty_and_multiline_tokens_are_not_written(self):
        with patch.object(store, "_backend") as backend:
            for token in ("", "  ", "hf_one\nhf_two", "hf_one two"):
                with self.subTest(token=token), self.assertRaises(store.TokenStoreError):
                    store.save_token(token)
            backend.assert_not_called()

    def test_selection_repr_hides_secret(self):
        self.assertNotIn("hf_example_only", repr(store.TokenSelection("hf_example_only", "session")))


if __name__ == "__main__":
    unittest.main()
