# Try the sample workspace

Build and start PaperMind from the repository root:

```sh
make build
make start
```

1. Open <http://127.0.0.1:8000> and select **Try sample notes**. The three notes are illustrative fixtures.
2. Open **Questions** and ask “How does BM25 rank passages?” Expand a cited source to read the passage alongside the answer.
3. Open **Research** and ask how retrieval uses evidence. Empty comparison cells mean the workspace did not extract evidence for that cell.
4. Open **Graph** to see links based on recognized terms. A link does not establish agreement between sources.
5. Restart the server and reopen the library to verify persistence. Mount a persistent volume if you run PaperMind in a container.

The walkthrough works without an API key. If you enable a language model, PaperMind sends selected passages and questions to the configured provider. Review generated answers and citation judgments against the original passages.
