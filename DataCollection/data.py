import nlp as nlp

import json
import os

from transformers import AutoTokenizer

train_dataset  = nlp.load_dataset('wikisql', split=nlp.Split.TRAIN)
valid_dataset = nlp.load_dataset('wikisql', split=nlp.Split.VALIDATION)

# print(len(train_dataset))
# print(len(valid_dataset))

# Create directories to store the files
os.makedirs("sql_statements", exist_ok=True)
os.makedirs("database_schemas", exist_ok=True)

# tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")


sqls = train_dataset['sql']
for entry in sqls:
        human_readable = entry['human_readable']
        # print(human_readable)

tables = train_dataset['table']

num = 0
# Iterate over the dataset
for entry in train_dataset:
    num += 1
    sql = entry['sql']
    table = entry['table']
    human_readable = sql['human_readable']

    # Extract the SQL statement
    # # Extract the database schema, assuming here we're only interested in 'header' and 'types'
    database_schema = {
        'id': table['id'],
        'header': table['header'],
        'types': table['types']
    }

    # Write the SQL statement to a file
    with open(f'sql_statements/sql_{num}.sql', 'w') as f:
        f.write(human_readable)

    # Write the database schema to a file
    with open(f'database_schemas/schema_{num}.json', 'w') as f:
        json.dump(database_schema, f)

