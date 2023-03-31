import click
import os
from git import Repo


@click.command()
def main():
    
    repo = get_repo()

    # Get all Java files in the repository
    java_files = []
    for root, dirs, files in os.walk(repo.working_tree_dir):
        for file in files:
            if file.endswith(".java"):
                java_files.append(file)
    
    # List the Java files from the repository if there are any
    # if java_files:
    #     click.echo("The Java files in the repository are:")
    #     for file in java_files:
    #         click.echo(file)
    #     click.echo("Total number of Java files: " + str(len(java_files)))
    # else:
    #     click.echo("No Java files found in the repository.")
    click.echo("Total number of Java files: " + str(len(java_files)))


    # Get commit history of the repository
    for commit in repo.iter_commits():
        print(f"commit: {commit.hexsha}")
        print(f"author: {commit.author}")
        print(f"date: {commit.committed_datetime}")
        print(f"message: {commit.message}")
        print()

    return java_files

def get_repo():
    choice = click.prompt("Clone a new repository or choose a local repository", type=click.Choice(['clone', 'local'], case_sensitive=False))
    
    # User chooses to clone a new repository
    if choice == 'clone':
        url = click.prompt("Enter URL for GitHub repository")
        default_path = os.path.expanduser("~") + "/repos"
        path = click.prompt("Enter path to clone the repository or press enter to use the default path", default=default_path, type=click.Path(exists=True, file_okay=False, dir_okay=True, writable=True))
        repo = Repo.clone_from(url, path)
        click.echo(f"Repository cloned to {repo.working_tree_dir}")

    # User chooses to use a local repository  
    elif choice == 'local':
        path = click.prompt("Enter path to local repository", type=click.Path(exists=True, file_okay=False, dir_okay=True))
        repo = Repo(path)
        click.echo(f"Repository at {repo.working_tree_dir}")

        return repo
    
# Get all the java files in the repository
def get_java_files(repo):
    java_files = []
    for root, dirs, files in os.walk(repo.working_tree_dir):
        for file in files:
            if file.endswith(".java"):
                java_files.append(file)
    
    return java_files


    
if __name__ == '__main__':
    main()
