import logging
import os
import pathlib
import socket
import sys

from datetime import UTC, datetime
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from config.constants import LOG_CONFIG

logger = logging.getLogger(LOG_CONFIG['main_logger_name'] + ".dev")


def get_ssl_context() -> tuple[str, str]:
    """
    Получает путь до SSL сертификата и ключа. Если переменные окружения не заданы, генерирует самоподписанный сертификат в ./ssl (рядом с /dev), используя расширения файлов, подходящие для ОС.

    :return: Кортеж (путь к сертификату, путь к ключу)
    """
    cert_file = os.environ.get("DEV_HTTPS_CERT")
    key_file = os.environ.get("DEV_HTTPS_KEY")

    base_dir = pathlib.Path(__file__).parent.parent.resolve()
    ssl_dir = base_dir / "ssl"
    ssl_dir.mkdir(mode=0o755, exist_ok=True)

    is_windows = sys.platform.startswith("win")
    cert_ext = ".crt" if is_windows else ".pem"
    key_ext = ".key" if is_windows else "key.pem"

    cert_path = ssl_dir / f"dev{cert_ext}"
    key_path = ssl_dir / f"dev{key_ext}"

    if cert_file and key_file and os.path.exists(cert_file) and os.path.exists(key_file):
        logger.info(f"Using provided SSL certificate: {cert_file} / {key_file}")
        return cert_file, key_file

    if not cert_path.exists() or not key_path.exists():
        logger.info("Generating self-signed SSL certificate for developer proxy server")
        _generate_self_signed_cert(cert_path, key_path)

    return str(cert_path), str(key_path)


def _generate_self_signed_cert(cert_path: pathlib.Path, key_path: pathlib.Path) -> None:
    """
    Генерирует самоподписанный SSL сертификат и сохраняет его вместе с ключом по указанным путям.

    :param cert_path: Путь для сохранения сертификата
    :param key_path: Путь для сохранения приватного ключа
    :return: None
    """
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    hostname = socket.gethostname()
    alt_names = [
        x509.DNSName("localhost"),
        x509.DNSName("127.0.0.1"),
        x509.DNSName(hostname),
    ]

    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"BY"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Minsk"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"Minsk"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Gravatar Dev"),
        x509.NameAttribute(NameOID.COMMON_NAME, hostname),
    ])

    not_before = datetime(1950, 1, 1, tzinfo=UTC)
    not_after = datetime(9999, 12, 31, 23, 59, 59, tzinfo=UTC)

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
        .add_extension(
            x509.SubjectAlternativeName(alt_names), critical=False
        )
        .sign(key, hashes.SHA256())
    )

    with open(key_path, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
