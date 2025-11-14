```
📦evaluations
 ┣ 📂assets # from LME
 ┃ ┗ 📜longmemeval_examples.png
 ┣ 📂data # full LME test suites
 ┃ ┣ 📜longmemeval_m_cleaned.json
 ┃ ┣ 📜longmemeval_oracle.json
 ┃ ┗ 📜longmemeval_s_cleaned.json
 ┣ 📂data_ref # raw data files used to generate eval cases
 ┃ ┗ 📜BiotechCropsAllTables2024.csv
 ┣ 📂src # code
 ┃ ┣ 📂evaluation # from LME
 ┃ ┃ ┣ 📜evaluate_qa.py
 ┃ ┃ ┣ 📜print_qa_metrics.py
 ┃ ┃ ┗ 📜print_retrieval_metrics.py
 ┃ ┗ 📂generation # LLM-generated responses
 ┃ ┃ ┣ 📜generate_one.py
 ┃ ┃ ┗ 📜generate_test.py
 ┣ 📂test_json # small eval cases
 ┃ ┣ 📜andrew2_sample.json
 ┃ ┣ 📜andrew_sample.json
 ┃ ┗ 📜one.json
 ┣ 📜.gitignore
 ┣ 📜LICENSE # for LME
 ┣ 📜README.md
 ┣ 📜directory.md
```