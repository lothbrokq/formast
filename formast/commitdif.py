import csv
import git
import click
#import getfile as gf
from tqdm import tqdm

@click.command()
@click.argument("repo")
@click.argument("output")    
def main(repo, output):
    # Open the output CSV file for writing
    with open(output, "w") as f:
        repo = git.Repo(repo)
        writer = csv.writer(f)

        # Write the header row
        writer.writerow(["commit_hash", "num_additions", "num_deletions", "filename"])

        # Loop through the commits and get the diff stats
        for commit in tqdm(list(repo.iter_commits())):
            if len(parrent := commit.parents) != 1:
                continue

            diff = repo.git.diff(parrent, commit, numstat=True)
            for line in diff.splitlines():
                num_additions, num_deletions, filename = line.split("\t")
                writer.writerow([commit.hexsha, num_additions, num_deletions, filename])

if __name__ == "__main__":
    main()