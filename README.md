# document-rag-prototype
Retrieval-first RAG prototype for TXT and PDF documents


# document-rag-prototype

A retrieval-first RAG prototype for TXT and PDF documents, built to understand what actually breaks when moving from clean examples to real files. The project is modular, notebook-driven, and focused on practical document handling: extraction quality, chunking, embedding-based retrieval, reranking, and grounded answer generation.

## Why this project exists

Most small RAG examples look fine because the documents are clean and the questions are easy. Real PDFs are not like that. Some are structured reports, some are slide decks, and some mix headings, captions, tables, repeated headers, short fragments, and broken reading order.

This project started from that problem: not just to retrieve text from documents, but to see how retrieval quality changes when the source itself is noisy.

## Current direction

The current version is a retrieval-first baseline for:

- TXT files
- PDF files
- Mixed PDF structure, including narrative pages and slide-like pages

The project is not frozen as a finished QA system. It is a working baseline that already shows practical progress, but still needs more tuning in retrieval precision and answer quality.

## Tech stack

- Python
- PyTorch
- Hugging Face Transformers
- sentence-transformers
- scikit-learn
- PyMuPDF
- PyPDF2

## Current pipeline

1. Load TXT and PDF files
2. Extract PDF text page by page
3. Clean repeated lines and obvious junk pages
4. Assign simple text behavior labels such as paragraph, line, and low-text
5. Chunk text differently depending on extracted structure
6. Filter junk chunks before embedding
7. Generate embeddings with Hugging Face models
8. Retrieve top relevant chunks
9. Rerank retrieved chunks
10. Build a grounded answer from the top retrieved text

## Project structure

```text
document-rag-prototype/
│
├── src/
│   ├── config.py
│   ├── loader.py
│   ├── chunker.py
│   ├── embedder.py
│   ├── search.py
│   ├── generator.py
│   └── reranker.py
│
├── rag_prototype.ipynb
├── requirements.txt
└── README.md
```

## What changed during development

The first versions were much weaker than the current one. The project went through several rounds of tuning to isolate what was actually hurting performance.

### 1. Basic retrieval was not enough

The earliest version treated extracted PDF text too uniformly. That worked poorly on messy PDFs, especially slide-based ones. Retrieval often returned front matter, navigation text, or weakly related fragments.

### 2. Junk had to be filtered earlier

Penalizing junk at search time was not enough. Once contents-like pages or declaration pages were chunked and embedded, they still polluted retrieval. This led to stronger filtering in both the loader and the chunker.

### 3. PDF structure mattered more than expected

A report page and a slide page should not be chunked in the same way. That led to simple structure-aware chunking:

- paragraph-style chunking for narrative text
- line-based chunking for short, broken, or slide-like text

### 4. Stronger embeddings helped only partly

The embedding model was upgraded, but that alone did not solve retrieval issues on noisy slide-style PDFs. This made it clear that source quality and chunk quality were still larger bottlenecks than model size in some cases.

### 5. Validation outside the main development files mattered

A separate validation PDF was used to check whether the improvements were only helping the known development files or whether they generalized at least a little. The result was mixed, but useful: the system did not completely collapse on unseen input.

## Development files and validation file

### Development

- `Master_thesis_saksham_shah.pdf`
- `03_E3.1_AAL2_InverseDynamics_SS2024.pdf`

### Validation

- `Data Science Ethics Introduction (1).pdf`

The purpose of this split was simple: stop tuning only on the same visible examples and check whether the pipeline still behaves at least somewhat reasonably on a separate file.

## Current observations

### Strengths

- The pipeline is much cleaner than the first versions.
- Obvious junk no longer dominates retrieval in the same way.
- The thesis-style PDF benefits more from the improvements than the slide-style PDF.
- Validation on a separate ethics PDF showed that the pipeline is not only tied to the original development files.

### Weaknesses

- Slide-heavy PDFs are still difficult.
- The final answer can still be awkward or only partially aligned with the question.
- Retrieval is better than before, but not consistently sharp enough to always surface the best answer-bearing chunk.
- Reranking improved the workflow, but not enough to call the output reliable yet.

## Development examples

These examples are not presented as proof of perfection. They are here to show what the current system can do, where it improved, and where it still struggles.

### Development QA 1

**Question:** How does the thesis model holiday effects differently from standard dummy variables?

**Answer:**

This reflects the modelling assumption that nearby holidays may jointly influence activity and is consistent with standard additive regression formulations for calendar effects. Long-run level is absorbed by the intercept rather than by the holiday regressor, a standard identifiability device for dummy variables in time series regression.

**Sources used:**

- `Master_thesis_saksham_shah.pdf | page 33 | chunk 1`
- `Master_thesis_saksham_shah.pdf | page 97 | chunk 0`
- `Master_thesis_saksham_shah.pdf | page 36 | chunk 3`

**Note:** This is one of the better thesis-side outputs because it retrieves the distinction between structured holiday modelling and standard dummy-style treatment.

### Development QA 2

**Question:** What problem does the proposed method try to solve?

**Answer:**

While Appendix A Supplementary Implementation Figures and Diagnostics This appendix collects supporting figures and minimal code excerpts that illustrate key steps of the experimental pipeline described in Chapter 3. The same scheme is applied on validation for model selection, after which the chosen configuration is refit on train+validation and applied once to the held out test span.

**Sources used:**

- `Master_thesis_saksham_shah.pdf | page 43 | chunk 0`
- `Master_thesis_saksham_shah.pdf | page 44 | chunk 2`

**Note:** This is still a weak result. It shows that retrieval is cleaner than before, but the final answer is still not precise enough for every conceptual question.

### Development QA 3

**Question:** What are the main steps of inverse dynamics?

**Answer:**

slide 9 Inverse Dynamics – Determination of muscle forces & moments What do the different muscles do? INVERSE DYNAMICS – DYNAMIC EXAMPLE Active and Assisted Living 2 slide 44 Estimation of muscles forces and joint moments INVERSE DYNAMICS – STATIC EXAMPLE Active and Assisted Living 2 slide 29 Estimation of muscles forces and joint moments

**Sources used:**

- `03_E3.1_AAL2_InverseDynamics_SS2024.pdf | page 9 | chunk 0`
- `03_E3.1_AAL2_InverseDynamics_SS2024.pdf | page 43 | chunk 0`
- `03_E3.1_AAL2_InverseDynamics_SS2024.pdf | page 28 | chunk 0`

**Note:** This is relevant, but still messy. It shows the remaining weakness of slide-heavy PDFs where extraction and chunk quality are harder to control.

### Development QA 4

**Question:** What is calculated in inverse dynamics?

**Answer:**

INVERSE DYNAMICS – DYNAMIC EXAMPLE Active and Assisted Living 2 slide 44 Estimation of muscles forces and joint moments INVERSE DYNAMICS – STATIC EXAMPLE Active and Assisted Living 2 slide 29 Estimation of muscles forces and joint moments slide 9 Inverse Dynamics – Determination of muscle forces & moments What do the different muscles do?

**Sources used:**

- `03_E3.1_AAL2_InverseDynamics_SS2024.pdf | page 9 | chunk 0`
- `03_E3.1_AAL2_InverseDynamics_SS2024.pdf | page 43 | chunk 0`
- `03_E3.1_AAL2_InverseDynamics_SS2024.pdf | page 28 | chunk 0`

**Note:** Similar to the previous one: partially relevant, but still far from a clean answer. This is one of the clearest signs that slide-style sources remain the hardest part of the pipeline.

## Validation examples

### Validation QA 1

**Question:** How does the document explain fairness and bias in data science?

**Answer:**

This leads to an equilibrium of data science somewhat similar to that of the top of Figure 1.2, with practices that typically do not use gender in the prediction model, include inherently comprehensible models and have stringent privacy policies. Next to this fairness issue at the feature dimension, fairness also relates to the instance dimension.

**Sources used:**

- `Data Science Ethics Introduction (1).pdf | page 10 | chunk 0`
- `Data Science Ethics Introduction (1).pdf | page 16 | chunk 1`
- `Data Science Ethics Introduction (1).pdf | page 11 | chunk 4`

**Note:** This output is messy, but it is still meaningfully aligned with fairness, discrimination, and privacy. That matters because it came from a validation PDF, not the development pair.

### Validation QA 2

**Question:** How does the document describe the social impact of data science?

**Answer:**

However, just as with any technology, data science has also come with some negative consequences: an increase of privacy invasion, data-driven discrimination against sensitive groups, and data-driven decision making without explanations. The importance and potential impact of data science ethics follows directly from that.

**Sources used:**

- `Data Science Ethics Introduction (1).pdf | page 5 | chunk 1`
- `Data Science Ethics Introduction (1).pdf | page 9 | chunk 0`
- `Data Science Ethics Introduction (1).pdf | page 5 | chunk 6`

**Note:** This is one of the more convincing validation outputs because it picks up the document’s negative consequences and broader ethical impact.

## What this project currently shows

This repository is useful as a record of practical work on:

- document ingestion problems
- PDF extraction limitations
- chunking strategy
- embedding-based retrieval
- reranking
- grounded answer generation
- validation discipline during iterative development

It is not a finished product, but it is already a practical baseline with visible iteration and concrete improvement points.

## What remains in the pipeline

The next steps are already clear:

1. Improve final answer extraction from reranked chunks
2. Improve ranking precision further
3. Improve slide-heavy PDF handling
4. Revisit stronger embedding and reranking setups later
5. Add vector database infrastructure only after retrieval quality is stable enough to justify it

