# git-blame-project

A CLI tool for applying `blame` to an entire repository or project in order to
gain insights about the static contributions of a project.

**Note: This project is actively being developed.  As such, it is not perfect - yet.**

## Motivation

Sometimes, having an understanding of who contributed to a repository or project
can be very useful information.  Luckily, [Github](https://github.com/) provides
the ability to analyze contributions to a project by commits, additions or
deletions via the "Insights" tool that a repository is equipped with.

However, there are some drawbacks to this contribution analysis.  Some of these
drawbacks include

1.  The contribution analysis can only be performed on the default branch.
2.  It is not possible to refine the contribution analysis, such as excluding
    files of certain types.

The most important drawback that I noticed was that the contribution analysis
can only be performed by commits, additions or deletions.  In this way, the
analysis does not give us a good indication of what the static contributions are
to the current state of a repository or project.  In other words, the contribution
analysis looks at contributions over time, not necessarily who is responsible for
what code in the current state of the project.

That is okay.  That is probably what [Github](https://github.com/) intended the
tool to be used for, and it works - well.  But I ran into situations where I
needed to better understand who was statically responsible for what portions of
the most recent state of the codebase - not who was responsible for how the
codebase developed over time.

[Github](https://github.com/)'s ability to `blame` a given line of a file was
more in tune with what information I needed to collect for my project - but
there did not seem to be an easy way to perform a `blame` systematically over
every line in an entire project (at least without manually going from file to
file and performing the blame).

Both the need to analyze contributions more statically and the need to
systematically apply `blame` across an entire project motivated the development
of this project, which is effectively a tool to perform a `blame` across every
file in a project or a desired subsection of that project.

## Usage

To run [git-blame-project](https://github.com/nickmflorin/git-blame-project),
simply use the following command:

```bash
$ git-blame-project <analysis_type> <path_to_my_repository> <analysis_arguments> <options>
```

### Analysis Argument

The first argument, `analysis_type`, refers to the specific analysis that the tool will
perform.  Currently, there are (2) different analyses that can be performed:

1. Line Blame Analysis
2. Breakdown Analysis

#### Line Blame Analysis

This analysis type analyzes the blame of every line in the project and outputs
tabular data that shows every single line of code that was analyzed along with
additional information (that can be configured via the `--columns` option).  This
additional information is discussed below under the `--columns` option.

To run this analysis, simply run the following command:

```bash
$ git-blame-project line_blame <path_to_my_repository> <options>
```

**Note:** There are no additional required arguments for the `line_blame` analysis other
than the repository path.

#### Breakdown Analysis

This analysis type analyzes the blame of every line in the project but then outputs the
percentage of lines that fall under each provided attribute.

To run this analysis, simply run the following command:

```bash
$ git-blame-project breakdown <path_to_my_repository> <attributes> <options>
```

For example, if we were to run the analysis as follows:

```bash
$ git-blame-project breakdown <path_to_my_repository> contributor,file_type <options>
```

The output data would first show the percentage of lines that correspond to each distinct
contributor to the repository.  Then, for each contributor, it would show the percentage
of lines of each file type that they contributed.

**Note:** The `attributes` argument is required for the `breakdown` analysis in addition
to the repository path.

The breakdown can be performed by any number of attributes, as long as those attributes are
valid.  For more information on what those attribute are, see the discussion under the
`attributes` argument.

### Repository Path Argument

Currently, the `<path_to_my_repository>` must be the path to the **root** of the
[Github](https://github.com/) for which you would like to run the tool.  If the
path does not exist, is not a [Github](https://github.com/) repository or is
not the **root** of the [Github](https://github.com/) repository, an error
will be raised.

### Arguments

There are several options which allow you to customize the tool's usage
and analysis.

##### `columns` - optional - (Only applicable for `line_blame` analysis)

This option defines what columns should be used to display the tabular data in the output of
this analysis.  The `--columns` option can be provided as a single value or multiple
values, but all value(s) must refer to a valid column.

Multiple values are provided as a string of comma separated values:

```bash
$ git-blame-project line_blame <path_to_my_repository> --columns=code,datetime
```

**Valid Values**: code, datetime, contributor, line_no, commit, file_name, file_path
**Default Value**: `file_name,file_path,code,datetime,contributor,line_no,commit`

#### `output_type` - optional

The `--output_type` argument is used to inform the tool how the results for
each analysis should be outputted.  The `--output_type` argument can be provided
as a single value or multiple values, but all value(s) must refer to a valid
`output_type`.

Multiple values are provided as a string of comma separated values:

```bash
$ git-blame-project line_blame <path_to_my_repository> --output_type=csv,excel
```

**Valid Values**: csv, excel
**Default Value**: `csv`

Currently, there are (2) supported `output_type`(s): `csv` and `excel`.

If the `output_type` is not provided, it will be inferred from the provided
`--output_file` argument.  If it cannot be inferred, either because the
`--output_file` argument was not provided or it does not have an extension,
the default value will be used.

#### `output_file` - optional

The `--output_file` argument informs the tool where the output data from the
analysis should be saved.  It can be provided in the following forms:

1. The full file path with an extension.
2. The full file path without an extension.
3. Just the file name with an extension.
4. Just the file name without an extension.

If the `--output_file` argument is not provided, a default filename will be
used and it will be saved in the directory specfied by the `--output-dir`
argument (if it is provided) or in the root directory of where the tool is
being used.

##### Extension

If the extension is provided, it will be used to infer the `--output_type`
argument in the case that it is not provided.  If the `--output_type` is provided
but it is inconsistent with the extension of the provided `--output_file`
argument, a warning will be issued - but the correct extension will still be
used.

For example, the following would result in a warning being issued but an
output file saved at `/users/john/data/file.csv`:

```bash
$ git-blame-project line_blame <path_to_my_repository> --output_file=/users/john/data/file.xlsx --output_type=csv
```

If multiple values are specified for the `--output_type` but only one extension
is used for the `--output_file` argument, it is okay - the files will still
be saved with the correct extension.

For example, the following would result in a warning being issued but
output files saved at `/users/john/data/file.csv` and `/users/john/data/file.xlsx`:

```bash
$ git-blame-project line_blame <path_to_my_repository> --output_file=/users/john/data/file.xlsx --output_type=csv,excel
```

If the extension is not provided, it will be inferred based on the `--output_type`
argument.  If the `--output_type` argument is not provided, the `output_type` will
default to `csv` in which case the inferred extension will be `csv`.

##### Full Path

If the full file path is not provided, the file will either be saved at
the root of the current directory or in the directory defined by the
`--output_dir` argument if it is provided.

If the full file path is provided, the `--output_dir` is not required - and
providing a `output_dir` that is inconsistent with the file path provided via
the `--output_file` argument will result in a warning being issued.

If the full file path is provided, an error will be raised if the directory
that the file is located in does not exist.

#### `output_dir`

The `--output_dir` argument informs the tool where the files for the output
data that is generated via the analyses should be saved.  If provided, the
directory must exist.  If it does not, an error will be raised.

It is not necessary to provide the `--output_dir` if the `--output_file`
argument specifies the full file path of the file that should be used to
save the resulting data.  If the `--output_dir` argument is provided, and the
`--output_file` argument is provided as a full path, they must be self-consistent.
