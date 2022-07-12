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


class HelpText:
    FILE_LIMIT = (
        "If this value is set, the blame will only parse files up until this "
        "number has been reached."
    )
    OUTPUT_COLS = "The columns that should be included in any tabular output."
    OUTPUT_FILE = (
        "The name or path of the file that the output will be saved to.  Only "
        "applicable for commands that only generate one output file.\n"
        "- If an extension is not included, the extension will be inferred "
        "from the `outputtype` option."
        "- If omitted, the output file name will be automatically generated "
        "based on the name of the repository and the current branch."
    )
    OUTPUT_DIR = (
        "The directory which output files will be saved to."
        "The name or path of the file that the output will be saved to.  Only "
        "applicable for commands that only generate one output file.\n"
        "- If an extension is not included, the extension will be inferred "
        "from the `outputtype` option."
        "- If omitted, the output file name will be automatically generated "
        "based on the name of the repository and the current branch."
    )
