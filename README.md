# formast

A AST formatting tool


## Develop

To run the executable:

```console
pdm run python -m formast <args>
```

How to run: 
```
2>&1 | tee log.txt 

pdm run regit -vv --repo "C:\Users\boran\OneDrive\DTU\BSc Thesis\babyrepos\onlinebookstore" -o "C:\Users\boran\OneDrive\DTU\BSc Thesis\babyrepos\onlinebookstore_ast10" -p '**\*.java' -m mapping.csv -- formast --writeast --overwrite {}


pdm run python .\formast\commitdiff.py -w "C:\Users\boran\OneDrive\DTU\BSc Thesis\babyrepos\onlinebookstore" output_nws.csv

```
