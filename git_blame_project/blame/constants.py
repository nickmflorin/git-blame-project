DEFAULT_IGNORE_DIRECTORIES = ['.git']
DEFAULT_IGNORE_FILE_TYPES = [".png", ".jpeg", ".jpg", ".gif", ".svg"]

COMMIT_REGEX = r"([\^a-zA-Z0-9]*)"
DATE_REGEX = r"([0-9]{4})-([0-9]{2})-([0-9]{2})"
TIME_REGEX = r"([0-9]{2}):([0-9]{2}):([0-9]{2})"

REGEX_STRING = COMMIT_REGEX \
    + r"\s*\(([a-zA-Z0-9\s]*)\s*" \
    + DATE_REGEX + r"\s*" \
    + TIME_REGEX + r"\s*" \
    + r"([-+0-9]*)\s*([0-9]*)\)\s*(.*)"
