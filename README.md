# git-blame-project

A CLI tool for applying `blame` to an entire repository or project in order to
gain insights about the static contributions of a project.

**Note: This project is actively being developed, and is not ready to be used yet.**

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

```bash
$ git-blame-project <path_to_my_repository>
```
