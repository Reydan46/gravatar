import base64
import datetime
import re
from typing import Optional

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.x509.oid import NameOID

from config.constants import CRYPTO_RSA_CONFIG
from modules.crypto.crypto_key_manager import (
    get_jwk_alg_from_crypto_conf,
    refresh_keys,
)
from shared_memory.shm_crypto import (
    shm_crypto_get_last_rotation,
    shm_crypto_get_public_key,
)


def get_public_key_jwk() -> dict:
    """
    Возвращает публичный RSA-ключ в формате JWK (JSON Web Key) из shared memory и время окончания его срока действия

    :return: Словарь с полями формата JWK для публичного RSA-ключа и доп. полями last_rotation и key_rotation_period
    """
    refresh_keys()
    last_rotation = shm_crypto_get_last_rotation()
    public_key = shm_crypto_get_public_key()
    numbers = public_key.public_numbers()
    n_bytes = numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")
    e_bytes = numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")
    n_b64 = base64.urlsafe_b64encode(n_bytes).rstrip(b"=").decode("ascii")
    e_b64 = base64.urlsafe_b64encode(e_bytes).rstrip(b"=").decode("ascii")
    alg_val = get_jwk_alg_from_crypto_conf(CRYPTO_RSA_CONFIG)
    jwk = {
        "kty": "RSA",
        "alg": alg_val,
        "use": "enc",
        "n": n_b64,
        "e": e_b64,
        "lr": last_rotation,
        "krp": CRYPTO_RSA_CONFIG["key_rotation_period"],
    }
    return jwk


def _pem_to_oneline_base64(pem_string: str) -> str:
    """
    Преобразует строку в формате PEM в однострочный Base64.

    Удаляет заголовки/подписи PEM и все переносы строк.

    :param pem_string: Строка в формате PEM.
    :return: Однострочная строка Base64.
    """
    no_headers = re.sub(r"-----(BEGIN|END) [A-Z ]+-----", "", pem_string)
    oneline = "".join(no_headers.split())
    return oneline


def _oneline_base64_to_pem(base64_string: str, pem_type: str) -> str:
    """
    Преобразует однострочный Base64 в строку формата PEM.

    :param base64_string: Однострочная строка Base64.
    :param pem_type: Тип PEM, например, 'PRIVATE KEY' или 'CERTIFICATE'.
    :return: Строка в формате PEM.
    """
    wrapped_base64 = "\n".join(
        base64_string[i : i + 64] for i in range(0, len(base64_string), 64)
    )
    return f"-----BEGIN {pem_type}-----\n{wrapped_base64}\n-----END {pem_type}-----\n"


def generate_private_key() -> str:
    """
    Генерирует новый приватный ключ RSA 2048 бит.

    :return: Приватный ключ в формате PEM (однострочный Base64).
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    return _pem_to_oneline_base64(private_key_pem)


def generate_cert_from_key(private_key_pem_oneline: str) -> str:
    """
    Генерирует самоподписанный сертификат на основе существующего приватного ключа.

    :param private_key_pem_oneline: Приватный ключ в формате PEM (однострочный Base64).
    :return: Сертификат x509 в формате PEM (однострочный Base64).
    :raises ValueError: если ключ имеет неверный формат.
    """
    try:
        private_key_pem = _oneline_base64_to_pem(private_key_pem_oneline, "PRIVATE KEY")
        private_key = serialization.load_pem_private_key(
            private_key_pem.encode("utf-8"), password=None
        )
    except Exception as e:
        raise ValueError(f"Invalid private key format: {e}")

    public_key = private_key.public_key()
    subject = issuer = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "BY"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Minsk"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Minsk"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Gravatar SP"),
            x509.NameAttribute(NameOID.COMMON_NAME, "gravatar.saml.sp"),
        ]
    )
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(public_key)
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
        .not_valid_after(
            datetime.datetime.now(datetime.timezone.utc)
            + datetime.timedelta(days=365 * 10)
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(public_key), critical=False
        )
        .sign(private_key, hashes.SHA256())
    )
    certificate_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    return _pem_to_oneline_base64(certificate_pem)
