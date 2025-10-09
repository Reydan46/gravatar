def truncate_middle(text: str, limit: int, head_len: int = None) -> str:
    """
    Возвращает строку, состоящую из первых head_len и последних (limit - head_len) символов исходной строки,
    разделённых маркером ......, если исходная строка превышает limit символов.

    :param text: Исходный текст
    :param limit: Общее количество символов, которое требуется вывести
    :param head_len: Количество символов в шапке (если не указано — берётся половина от limit)
    :return: Обрезанная строка с маркером усечения или исходный текст, если он короче либо равен limit
    """
    if len(text) <= limit:
        return text
    if head_len is None:
        head_len = limit // 2
    tail_len = limit - head_len
    return f"{text[:head_len]}......{text[-tail_len:]}"


def escape_lines(text: str) -> str:
    """
    Экранирует символы переноса строки

    :param text: Исходный текст
    :return: Экранированный текст
    """
    text_modified = text.replace("\n", "\\n")
    text_modified = text_modified.replace("\r", "\\r")
    return text_modified
