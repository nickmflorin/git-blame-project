from git_blame_project.blame import Analyses
from git_blame_project.models import OutputTypes


class HelpText:
    FILE_LIMIT = (
        "If this value is set, the blame will only parse files up until this "
        "number has been reached."
    )
    IGNORE_DIRS = (
        "Directory names that should be ignored if the file is located inside "
        "them.  Can be a single or multiple values.  If a file exists in any "
        "parent directory with a name included in this option, the file will "
        "be ignored."
    )
    IGNORE_FILE_TYPES = (
        "File types that should be ignored a file of that type is encountered. "
        "Can be a single or multiple values.  Should be specified as a file "
        "extension (or several file extensions), with or without the period."
    )
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
    # Not currently used.
    ANALYSIS = (
        "The type of analyses that should be performed with the project blame. "
        "Can be a single value or multiple values.  Valid values are "
        f"{Analyses.HUMANIZED}. If omitted, the analyses that will be performed "
        "by default is `line_blame`."
    )


class BlameLinesHelpText(HelpText):
    COLUMNS = (
        "The columns that should be included in the tabular output of the "
        "line blame analysis."
    )
