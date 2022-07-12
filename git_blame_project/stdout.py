import click


class TerminalCodes:
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

    @classmethod
    def underline(cls, text):
        return cls.UNDERLINE + text + cls.END

    @classmethod
    def bold(cls, text):
        return cls.BOLD + text + cls.END


def warning(message):
    prefix = TerminalCodes.bold("Warning:")
    click.secho(f"{prefix} {message}", fg="yellow")


def error(message):
    prefix = TerminalCodes.bold("Error:")
    click.secho(f"{prefix} {message}", fg="red")


def inconsistent_output_location_warning(outputdir, outputfile):
    warning(
        f"The output directory {str(outputdir)} is inconsistent "
        f"with the location of the provided output file, "
        f"{str(outputfile)}.  Remember, only one of the output "
        "file or the output directory are used. \n"
        f"The provided output directory {str(outputdir)} will be "
        "ignored as the location defined by the output file "
        "will be used."
    )
