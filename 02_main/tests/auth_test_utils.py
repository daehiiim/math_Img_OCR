import base64
import hashlib
import hmac
import json
import time

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature


def _b64url_encode(raw: bytes) -> str:
    """바이트를 JWT/JWK 호환 base64url 문자열로 변환한다."""
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def encode_segment(payload: dict) -> str:
    """JWT 세그먼트에 들어갈 JSON payload를 인코딩한다."""
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _b64url_encode(raw)


def build_hs256_token(secret: str, subject: str, expires_at: int | None = None) -> str:
    """HS256 테스트 토큰을 생성한다."""
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": subject,
        "role": "authenticated",
        "exp": expires_at or int(time.time()) + 3600,
    }
    signing_input = f"{encode_segment(header)}.{encode_segment(payload)}"
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url_encode(signature)}"


def build_es256_key_pair(kid: str) -> tuple[ec.EllipticCurvePrivateKey, dict]:
    """ES256 서명용 키와 대응 JWKS 항목을 생성한다."""
    private_key = ec.generate_private_key(ec.SECP256R1())
    public_numbers = private_key.public_key().public_numbers()
    jwk = {
        "kty": "EC",
        "crv": "P-256",
        "alg": "ES256",
        "use": "sig",
        "kid": kid,
        "x": _b64url_encode(public_numbers.x.to_bytes(32, "big")),
        "y": _b64url_encode(public_numbers.y.to_bytes(32, "big")),
    }
    return private_key, jwk


def build_es256_token(
    private_key: ec.EllipticCurvePrivateKey,
    kid: str,
    subject: str,
    expires_at: int | None = None,
) -> str:
    """ES256 테스트 토큰을 생성한다."""
    header = {"alg": "ES256", "typ": "JWT", "kid": kid}
    payload = {
        "sub": subject,
        "role": "authenticated",
        "exp": expires_at or int(time.time()) + 3600,
    }
    signing_input = f"{encode_segment(header)}.{encode_segment(payload)}".encode("utf-8")
    der_signature = private_key.sign(signing_input, ec.ECDSA(hashes.SHA256()))
    r_value, s_value = decode_dss_signature(der_signature)
    signature = r_value.to_bytes(32, "big") + s_value.to_bytes(32, "big")
    return f"{signing_input.decode('utf-8')}.{_b64url_encode(signature)}"


class StubJwksResponse:
    """JWKS fetch 응답을 흉내 내는 테스트용 객체다."""

    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = json.dumps(payload)

    def json(self) -> dict:
        """JSON payload를 반환한다."""
        return self._payload

    def raise_for_status(self) -> None:
        """비정상 상태코드면 예외를 발생시킨다."""
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")
