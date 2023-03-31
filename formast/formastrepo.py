from contextlib import contextmanager
from pathlib import Path
import shutil
from typing import Callable
import click
import csv
import git
import os
import git_filter_repo as fr
import tempfile
import subprocess
import logging
from dataclasses import dataclass, field

log = logging.getLogger("regit")

# Some code borrowed from https://github.com/newren/git-filter-repo/blob/main/contrib/filter-repo-demos/lint-history


class Executable(click.ParamType):
    name = "executable"

    def convert(self, value, param, ctx):
        if "/" in value:
            exe = Path(value)
            exe = exe.absolute()
            if not os.access(exe, os.X_OK):
                self.fail(f"{value!r} is not an executable file", param, ctx)
        else:
            pp = shutil.which(value)
            if pp is None:
                self.fail(
                    f"Could not find {value!r} on path, add './' if it is a file.",
                    param,
                    ctx,
                )
            exe = Path(pp)
        return exe


@contextmanager
def blob_reader():
    process = subprocess.Popen(
        ["git", "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
    )

    def reader(blob_id):
        assert process.stdin is not None
        assert process.stdout is not None
        process.stdin.write(blob_id + b"\n")
        process.stdin.flush()
        _, _, objsize = process.stdout.readline().split()
        return process.stdout.read(int(objsize) + 1)[:-1]

    yield reader

    if process.stdin is not None:
        process.stdin.close()

    process.wait()


@dataclass
class BlobHandler:
    reader: Callable[[str], bytes]
    filter: fr.RepoFilter | None = None
    blobs_handled: dict[int, int] = field(default_factory=dict)
    is_relevant: Callable[[Path], bool] = lambda _: True
    transform: Callable[[Path, bytes], bytes] = lambda _, b: b

    def __call__(self, commit: fr.Commit, metadata):
        assert self.filter is not None
        for change in commit.file_changes:
            filename = Path(change.filename.decode("utf-8"))
            if change.type == b"D" or not self.is_relevant(filename):
                continue

            if change.blob_id not in self.blobs_handled:
                content = self.reader(change.blob_id)
                blob = fr.Blob(self.transform(filename, content))
                self.filter.insert(blob)
                # Record our handling of the blob and use it for this change
                self.blobs_handled[change.blob_id] = blob.id
            change.blob_id = self.blobs_handled[change.blob_id]


@contextmanager
def tfile(folder, filename, content):
    tmp_file = folder / filename
    with open(tmp_file, "wb") as f:
        f.write(content)
    yield tmp_file
    os.remove(tmp_file)


def transform_program(program: Path, args: tuple[str], folder: Path):
    def callback(file: Path, content: bytes):
        pargs = list(args)
        try:
            ix = pargs.index("{}")
        except ValueError:
            cmd = [program] + pargs
            log.debug("Running cmd %s", cmd)
            return subprocess.run(
                cmd, input=content, capture_output=True, check=True
            ).stdout
        else:
            with tfile(folder, file.name, content) as tmp_file:
                pargs[ix] = str(tmp_file)
                cmd = [program] + pargs
                log.debug("Running cmd %s", cmd)
                subprocess.run(cmd, check=True)
                with open(tmp_file, "rb") as f:
                    return f.read()

    return callback


@click.command()
@click.option("--repo", help="the repo to clone and change", default=None)
@click.option(
    "-o",
    "--output",
    help="The name of the resulting repo",
    type=click.Path(exists=False, path_type=Path),
)
@click.option(
    "-p",
    "--pattern",
    help="the glob-pattern to match files.",
    type=str,
)
@click.option(
    "-m",
    "--mapping",
    help="The file to output the csv mapping to",
    type=click.File("w", lazy=False),
)
@click.option(
    "-v",
    "--verbose",
    help="The verbosity of logging",
    count=True,
)
@click.argument(
    "program",
    # help="The program to execute on each file",
    type=Executable(),
)
@click.argument(
    "args",
    # help="The argurments, choose '{}' to mean the file in question, omit a '{}' to use stdin",
    nargs=-1,
    type=str,
)
def regit(
    repo,
    pattern: str | None,
    output: Path,
    mapping,
    program: Path,
    args: tuple[str],
    verbose: int,
):
    """A simple program that runs a command on every commit on a repo."""

    logging.basicConfig(level=verbose)
    log.debug("Setting verbosity %s", verbose)

    if output is None:
        output = Path(tempfile.mkdtemp())

    if repo is None:
        repo = git.Repo().clone(path=output)
    else:
        repo = git.Repo.clone_from(url=repo, to_path=output)

    os.chdir(output)
    options = fr.FilteringOptions.parse_args([], error_on_empty=False)

    with blob_reader() as br, tempfile.TemporaryDirectory() as folder:
        handler = BlobHandler(
            br,
            is_relevant=lambda a: pattern is None or a.match(pattern),
            transform=transform_program(program, args, Path(folder)),
        )
        filter = fr.RepoFilter(options, commit_callback=handler)
        handler.filter = filter
        filter.run()

        if mapping:
            writer = csv.writer(mapping)
            writer.writerow(["from", "to"])
            for fm, to in filter._commit_renames.items():

                def handle(a):
                    if isinstance(a, bytes):
                        return a.decode()
                    else:
                        log.warning("Unexpected result %s", a)
                        return str(a)

                writer.writerow([handle(m) for m in [fm, to]])

    print(output)


if __name__ == "__main__":
    regit()
