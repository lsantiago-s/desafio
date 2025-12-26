# Documentation

## Vector Store Indexing (build_index.py)

The ```scripts/build_index.py``` script runs the indexing pipeline that builds and populates the vector store (ChromaDB) from an input file containing the execution parameters.

### What the script does (overview)

When ```build_index.py``` is executed, the pipeline:

1) Reads execution arguments from an input file (by default indexer/build_index_input.txt, passed via the CLI).
2) Initializes the ChromaDB collection (directory under data/chroma/ and configured collection name).
3) Initializes the embedder according to the project’s embedding configuration.
4) For each article listed in the input:
    - Identifies the source type (pdf, url, or text).
    - Ingests the content (downloading or reading when necessary).
    - Cleans and normalizes the text.
    - Performs chunking using the configured chunk_size and chunk_overlap.
5) Persists the generated chunks locally in data/processed/ as .jsonl files.
6) Upserts the chunks into the ChromaDB collection.
7) Generates and saves traceability artifacts:
    - Stats (processing statistics)
    - Manifest (document and chunk manifest)

### How to run (indexing only)

To run only the indexing step (without starting the agent or MCP server), use:
```python3 -m scripts.build_index $(cat inputs/build_index_input.txt)```

## MCP Server

We expose the vector store via an MCP server, implemented using FastMCP over STDIO. FastMCP was chosen over the lower-level official Python SDK due to its reduced boilerplate, as it abstracts away much of the MCP protocol handling, allowing tools to be defined directly as Python functions using decorators. STDIO transport was used because we're doing local agent deployment.

### Available tools

#### search_articles

Search indexed scientific articles by semantic similarity.

Input:

- query (string): free-text query

Output:

- list of objects with:

  - id (string): document id
  - title (string)
  - area (string)
  - score (float)

#### get_article_content

Retrieve the content of an indexed article.

Input:

- id (string): document id

Output:

- object with:
  - id (string)
  - title (string)
  - area (string)
  - content (string): concatenated chunks with page/offset traceability

## AGENT (CLASSIFICATION, EXTRACTION, AND REVIEW)

The agent is the component responsible for orchestrating the entire cognitive pipeline of the system: article ingestion, context retrieval via MCP, scientific area classification, structured information extraction, and critical review generation.

It is implemented as a *multi-agent graph using LangGraph* (picked for its widespread use), where each node has a clearly defined responsibility and communicates through a shared state object (```AgentState```).

### HIGH-LEVEL WORKFLOW

At a high level, the agent executes the following steps:

1) Input normalization
    - The agent accepts articles as URL, local PDF, or raw text.
    - For URLs and PDFs, it performs content fetching and text extraction.
    - The result is a normalized text representation (normalized_text) used by downstream nodes.
2) Retrieval via MCP
    - A retrieval query is built from the normalized text.
    - The agent queries the MCP server using the search_articles tool.
    - Retrieved results are enriched with additional context using get_article_content.
    - The query and the top retrieved hits are stored in the agent state for debugging and traceability.
3) Classification
    - The agent classifies the input article into one of the three configured scientific areas (for example, Mathematics, Medicine, or Economics).
    - The decision is based on a combination of similarity-based retrieval evidence and the article content itself.
    - The classifier outputs both the selected area and a textual rationale explaining the decision.
4) Structured extraction
    - The agent extracts information from the article into the exact JSON format required by the challenge.
    - This step enforces exact key names (including intentional typos when configured) and preserves the original language of the article.
    - If the language model produces invalid or malformed JSON, an automatic repair mechanism is applied.
5) Critical review
    - The agent generates a critical review in Portuguese, covering strengths, potential weaknesses or methodological limitations, and final remarks.
    - Both the extracted structured data and the article text are used as context.
    - Validation and hardening steps ensure that the review follows a minimal expected structure.

At the end of execution, the agent returns in the ```out/``` folder:
    - The predicted scientific area;
    - The extracted JSON object;
    - The critical review in Markdown format.

### MAIN AGENT SCRIPT

The entry point for the agent is:
```python -m scripts.run_agent```

The main script (```scripts/run_agent.py```) is responsible for parsing command-line arguments, initializing the LangGraph workflow, executing the agent, and persisting the outputs to disk.

The core execution logic is:

```python
state = AgentState(input_kind=args.input_kind, input_value=args.input)
final_state = graph.invoke(state, config={"configurable": {"cfg": cfg}})
```

#### SUPPORTED ARGUMENTS

The agent supports the following command-line arguments:
- ```--input-kind```
    Specifies the type of input. Allowed values are:
    - ```text``` for raw text input,
    - ```url``` for an article URL (HTML page or PDF),
    - ```pdf``` for a local PDF file path.
- ```--input``` for the input value itself: text, URL, or file path.
- ```--out-dir``` (optional). The output directory where results are written. Default is ```out/```.

### HOW TO RUN

The recommended execution workflow uses an environment setup script and an arguments file.

First, configure the environment by editing ```scripts/env.sh``` to set API keys and any required environment variables.

Second, define the agent arguments in ```inputs/agent_args.txt```, for example:

```text
--input-kind url
--input https://sample_url
--out-dir out
```

If ```--input``` is a local pdf file, add its path. For example:

```text
--input-kind url
--input samples/sample_article.pdf
--out-dir out
```

Finally, run the agent:

```bash
source scripts/env.sh
python -m scripts.run_agent $(cat inputs/agent_args.txt)
```

After execution, the output directory contains:
- ```extraction_1.json```
  A structured JSON file containing the extracted - information from the article.
- ```review_1.md```
A critical review written in Portuguese.
- ```agent_output.json```
A consolidated version of the agent output containing the area, extraction JSON, and review.

In addition, the script prints a verbose result to standard output, including warnings and debugging information useful during development and evaluation.

#### DESIGN NOTES

- The agent is multi-agent by design, with separate nodes for ingestion, retrieval, classification, extraction, and review.

- Access to the vector store is exclusively mediated by MCP, ensuring a clean separation between the agent logic and storage layers.

- The pipeline is designed to be robust to failures, incorporating JSON schema validation, automatic repair loops, and explicit warnings when extraction or classification is degraded.