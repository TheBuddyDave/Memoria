To run the tests for memory graph retrieval you need to have a Neo4j instance running and the database should be created called `testmemory`. Then run the cypher from `dummy_data_cypher.txt` (copy paste) to create the data in the database.

The dataset is intentionally rich: it contains 3 hubs. 

- Hub 1 is dense and multi-branching (campaign lift analysis)
- Hub 2 is sparser and connected to Hub 1 by a weak bridge edge (supplier lead time analysis)
- Hub 3 is dense but isolated (loyalty response analysis). 

> WARNING: the data in `dummy_data_cypher.txt` must not be changed as the tests rely on it. 