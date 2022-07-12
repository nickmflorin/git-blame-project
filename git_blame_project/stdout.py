import click


def warning(message):
    # TODO: Make "Warning" bold.
    click.secho(f"Warning: {message}", fg="yellow")


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
