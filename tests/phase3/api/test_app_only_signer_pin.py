import unittest
from apps.api.app_only_signer_pin import SignerPin


class SignerPinTests(unittest.TestCase):
    def setUp(self):
        self.key = b"synthetic public material, not a real key"
        self.pin = SignerPin.capture(self.key)

    def test_unchanged(self):
        self.assertTrue(self.pin.current(lambda: self.key))

    def test_different_material(self):
        self.assertFalse(self.pin.current(lambda: b"other material"))

    def test_missing(self):
        def missing():
            raise FileNotFoundError("private path")
        self.assertFalse(self.pin.current(missing))

    def test_permission_failure(self):
        def denied():
            raise PermissionError("private path")
        self.assertFalse(self.pin.current(denied))

    def test_invalid_values(self):
        for value in (None, "text", b"", b"x" * 65537, bytearray(self.key)):
            with self.subTest(value_type=type(value).__name__):
                self.assertFalse(self.pin.matches(value))
                with self.assertRaises(ValueError):
                    SignerPin.capture(value)

    def test_recovery_uses_original_only(self):
        self.assertFalse(self.pin.matches(b"replacement"))
        self.assertTrue(self.pin.matches(self.key))

    def test_repr_redacts_digest_and_material(self):
        self.assertNotIn(self.key.decode(), repr(self.pin))
        self.assertNotIn(self.pin._digest.hex(), repr(self.pin))


if __name__ == "__main__":
    unittest.main()
