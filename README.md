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
$ git-blame-project <path_to_my_repository>
```

Currently, the `<path_to_my_repository>` must be the path to the **root** of the
[Github](https://github.com/) for which you would like to run the tool.  If the
path does not exist, is not a [Github](https://github.com/) repository or is
not the **root** of the [Github](https://github.com/) repository, an error
will be raised.

### Arguments

There are several arguments which allow you to customize the tool's usage
and analysis.

#### `analysis`

The `--analysis` argument is used to inform the tool what analyses you would
like to perform.  The `--analysis` argument can be provided as a single value or
multiple values, but all value(s) must refer to the slug of an implemented
analysis type.

Multiple values are provided as a string of comma separated values:

```bash
$ git-blame-project <path_to_my_repository> --analysis=line_blame,contributions_by_line
```

Currently, there are (2) analysis types: `line_blame` and `contributions_by_line`.

##### `line_blame` Analysis

This analysis type analyzes the blame of every line in the project and outputs
data that optionally shows the contributor of every line, the commit number,
the date and time at which the commit happened, the line of code itself and
the line number of the line in the file.

##### `line_blame_columns`

The `--line_blame_columns` argument defines what columns should be used to
display the tabular data in the output of this analysis.  The
`--line_blame_columns` argument can be provided as a single value or multiple
values, but all value(s) must refer to a valid column.

Multiple values are provided as a string of comma separated values:

```bash
$ git-blame-project <path_to_my_repository> --line_blame_columns=code,datetime
```

**Valid Values**: code, datetime, contributor, line_no, commit
**Default Value**: `code,datetime,contributor,line_no,commit`
