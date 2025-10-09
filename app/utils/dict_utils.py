from typing import Dict, Any


def deep_merge_dicts(
    source: Dict[str, Any], destination: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Рекурсивно сливает два словаря. Значения из source перезаписывают
    значения в destination.

    :param source: Словарь-источник (новые/перезаписываемые значения)
    :param destination: Словарь-цель (базовый, со значениями по умолчанию)
    :return: Слитый словарь
    """
    for key, value in source.items():
        if (
            isinstance(value, dict)
            and key in destination
            and isinstance(destination[key], dict)
        ):
            destination[key] = deep_merge_dicts(value, destination[key])
        else:
            destination[key] = value
    return destination
