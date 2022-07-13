from .models import OutputTypes


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
    OUTPUT_TYPE = (
        "The manner in which results should be outputted.  Can be a single "
        f"value or multiple values.  Valid values are {OutputTypes.HUMANIZED}. "
        "If omitted, the output type will be inferred from the provided "
        "output file.  If this cannot be done, the output will only be "
        "displayed via stdout, but will not be saved to a file."
    )
