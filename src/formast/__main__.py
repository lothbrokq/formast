import click
import os
from tree_sitter import Language, Parser
import sys
import base64
import hashlib
import logging
from pathlib import Path

log = logging.getLogger(__name__)

## Uncomment this block if you don't have the language file yet, first time running formast
# Language.build_library(
#     # Store the library in the `build` directory
#     'build/my-languages.so',

#     # Include one or more languages
#     [
#         '../../vendor/tree-sitter-java'
#     ]
# )

# Load the language (assuming the language is created, if not run the commented code above)
language_file = Path(__file__).absolute().parent.parent.parent / 'build' / 'my-languages.so'
JAVA_LANGUAGE = Language(str(language_file), 'java')

@click.command()
@click.option("--writetoken", is_flag=True, help="Write the new file with the tokenized content")
@click.option("--writeast", is_flag=True, help="Write the new file with the AST content")
@click.option("--writerelativeast", is_flag=True, help="Write the AST content with relative positions")
@click.option("--writecompastsort", is_flag=True, help="Write the new file with the compressed AST content and sorted hashing")
@click.option("--overwrite", is_flag=True, help="Overwrite the original .java file with the new content")
@click.option("-v", "--verbose", count=True, help="Increase output verbosity")
@click.argument("file_path", type=str) 

## Formast 
def formast(file_path, writetoken, writeast, writerelativeast, writecompastsort, overwrite, verbose):

    # initialize logging
    logging.basicConfig(level=verbose)

    log.debug("Using language file: %s", language_file)
    parser = Parser()
    parser.set_language(JAVA_LANGUAGE)

    if (file_path == "-"):
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            process(Path(line.strip()), parser, overwrite, writetoken, writeast, writerelativeast, writecompastsort)
            log.info("processed %s" % line)
            sys.stdout.write("ok\n")
            sys.stdout.flush()
    else:
        process(Path(file_path), parser, overwrite, writetoken, writeast, writerelativeast, writecompastsort)
        
def process(file_path, parser, overwrite, writetoken, writeast, writerelativeast, writecompastsort):

    log.info(f"Processing {file_path}...")
    
    ## Handling options 
    # Token based
    if writetoken:  
        with open(file_path, 'r', encoding='utf-8') as f:
            src = f.read()
        tree = parser.parse(src.encode("utf8"))
        with open(file_path.with_suffix(".ast"),'w', encoding='utf-8') as f:
            for node in traverse(tree):
                if node.child_count == 0:
                    f.write(node.text.decode('utf-8'))
                    f.write("\n")
    # AST based
    elif writeast:
        with open(file_path, "rb") as f:
            code = f.read()
        tree = parser.parse(code)
        ast_code = process_tree_ast(tree)
        with open(file_path.with_suffix(".ast"), 'w', encoding='utf-8') as f:
            f.write(ast_code)
    # Sorted and compressed AST based
    elif writecompastsort:
        with open(file_path, "rb") as f:
            code = f.read()
        tree = parser.parse(code)
        ast_code = process_tree_comp_sorted(tree)
        with open(file_path.with_suffix(".ast"), 'w', encoding='utf-8') as f:
            f.write(ast_code)
    # Relative AST based
    elif writerelativeast:
        with open(file_path, "rb") as f:
            code = f.read()
        tree = parser.parse(code)
        ast_code = process_tree_ast_relatively(tree)
        with open(file_path.with_suffix(".ast"), 'w', encoding='utf-8') as f:
            f.write(ast_code)

    log.info(f"Done with {file_path}...")

    # If overwrite is true, overwrite the original .java file with the .ast content
    if overwrite:
        file_path.unlink()
        os.rename(file_path.with_suffix('.ast'), file_path)
        log.info("Original .java file overwritten with .ast content!")
    
    log.info("File saved!")

## Tree traversal function
def traverse(tree):
    cursor = tree.walk()
    descend = [True]

    while True:
        if descend[-1]:
            yield cursor.node
        if descend[-1] and cursor.goto_first_child():
            descend[-1] = False
            descend.append(True)
        elif cursor.goto_next_sibling():
            descend[-1] = True
        elif cursor.goto_parent():
            descend.pop()
        else:
            break

# Process the tree into an AST
def process_tree_ast(tree):
    if tree is None:
        raise ValueError("The tree object must not be None")

    lines = []

    def process_node(node):
        if node is None:
            raise ValueError("The tree object does not have the expected structure")

        line = ""

        if node.children:
            children = []
            for child in node.children:
                child_result = process_node(child)
                if child_result is not None:
                    children.append(child_result)
            line = 'B {} {}'.format(node.type, ' '.join(map(str, children)))
        else:
            try:
                text = node.text.decode('utf-8')
            except UnicodeDecodeError:
                raise ValueError("The text of the leaf nodes must be encoded using utf-8")
            line = 'L {}'.format(text)

        lines.append('{}'.format(line))

        return len(lines) - 1

    process_node(tree.root_node)
    return '\n'.join(lines)

## Processes the tree relatively
def process_tree_ast_relatively(tree):
    if tree is None:
        raise ValueError("The tree object must not be None")

    lines = []

    def process_node(node):
        if node is None:
            raise ValueError("The tree object does not have the expected structure")

        line = ""

        if node.children:
            children = []
            for child in node.children:
                child_result = process_node(child)
                if child_result is not None:
                    children.append(child_result)
            line = 'B {} {}'.format(node.type, ' '.join(map(lambda x: str(x - len(lines)), children)))
        else:
            try:
                text = node.text.decode('utf-8')
            except UnicodeDecodeError:
                raise ValueError("The text of the leaf nodes must be encoded using utf-8")
            line = 'L {}'.format(text)

        lines.append('{}'.format(line))

        return len(lines) - 1

    process_node(tree.root_node)
    return '\n'.join(lines)

# Show every instance of the program just once as an AST, and hash the values
def process_tree_comp_sorted(tree):
    if tree is None:
        raise ValueError("The tree object must not be None")

    lookup = {}
    lines = []

    def process_node_sorted(node):
        if node is None:
            raise ValueError("The tree object does not have the expected structure")

        line = ""

        if node.children:
            children = []
            for child in node.children:
                child_result = process_node_sorted(child)
                if child_result is not None:
                    children.append(child_result)
            line = 'B {} {}'.format(node.type, ' '.join(map(str, children)))
        else:
            try:
                text = node.text.decode('utf-8')
            except UnicodeDecodeError:
                raise ValueError("The text of the leaf nodes must be encoded using utf-8")
            line = 'L {}'.format(text)

        idx = lookup.get(line)
        if idx is not None:
            return idx

        hash_object = hashlib.sha256(line.encode('utf-8'))
        hash_value = int.from_bytes(hash_object.digest()[:8], byteorder='big', signed=True)
        idx = base64.urlsafe_b64encode(hash_value.to_bytes(8, byteorder='big', signed=True)).rstrip(b'=').decode('ascii')
        lines.append('{} {}'.format(idx, line))
        lookup[line] = idx

        return idx

    process_node_sorted(tree.root_node)
    sorted_lines = sorted(lines, key=lambda x: x.split()[0])
    return '\n'.join(sorted_lines)    

## Check if the file is a java file
def is_java_file(file_path):
    return os.path.splitext(file_path)[1] == '.java'

if __name__ == "__main__":
    formast()