from collections.abc import Hashable
from typing import Any, List


def list_to_lookup(lst: List[Any], key: str) -> dict:
    """
    Преобразует список словарей в словарь по значению ключа key.

    :param lst: Список словарей
    :param key: Ключ для уникальности
    :return: Словарь, где ключ - значение поля key
    """
    return {d[key]: d for d in lst if isinstance(d, dict) and key in d}


def extract_lookup_key(item: Any) -> Any:
    """
    Получает ключ для сравнения элементов списка (если словарь — по первому ключу, иначе сам объект).

    :param item: Элемент списка
    :return: Значение ключа для lookup
    """
    if isinstance(item, dict) and item:
        first_key = next(iter(item))
        return first_key, item[first_key]
    if isinstance(item, Hashable):
        return item
    return id(item)


def diff_dicts(old: dict, new: dict) -> dict:
    """
    Сравнивает два словаря любого уровня вложенности и возвращает различия.

    :param old: Старый словарь
    :param new: Новый словарь
    :return: Словарь с ключами add/del/chg
    """
    diff: dict = {"add": {}, "del": {}, "chg": {}}
    all_keys = set(old.keys()) | set(new.keys())

    for k in all_keys:
        if k not in old:
            diff["add"][k] = new[k]
        elif k not in new:
            diff["del"][k] = old[k]
        else:
            old_val, new_val = old[k], new[k]
            if isinstance(old_val, dict) and isinstance(new_val, dict):
                subdiff = diff_dicts(old_val, new_val)
                if subdiff:
                    for cat in subdiff:
                        if subdiff[cat]:
                            diff[cat][k] = subdiff[cat]
            elif isinstance(old_val, list) and isinstance(new_val, list):
                old_lookup = {extract_lookup_key(item): item for item in old_val}
                new_lookup = {extract_lookup_key(item): item for item in new_val}

                add = [v for u, v in new_lookup.items() if u not in old_lookup]
                delete = [v for u, v in old_lookup.items() if u not in new_lookup]

                chg = []
                for u in set(old_lookup) & set(new_lookup):
                    if old_lookup[u] != new_lookup[u]:
                        if isinstance(old_lookup[u], dict) and isinstance(
                            new_lookup[u], dict
                        ):
                            subdiff = diff_dicts(old_lookup[u], new_lookup[u])
                            if subdiff:
                                chg.append(
                                    {
                                        "old": old_lookup[u],
                                        "new": new_lookup[u],
                                        "diff": subdiff,
                                    }
                                )
                        else:
                            chg.append({"old": old_lookup[u], "new": new_lookup[u]})

                if add:
                    diff["add"][k] = add
                if delete:
                    diff["del"][k] = delete
                if chg:
                    diff["chg"][k] = chg
            elif old_val != new_val:
                diff["chg"][k] = {"old": old_val, "new": new_val}

    # Удаляем пустые секции
    diff = {key: val for key, val in diff.items() if val}
    return diff
