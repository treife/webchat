class InvalidMessageContent(Exception):
    pass


def process_message_content(s: str) -> str:
    r = s.strip()
    if not r:
        raise InvalidMessageContent('Message content can not be empty')
    return r
