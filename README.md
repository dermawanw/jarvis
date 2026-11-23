# JARVIS — Local Voice & Obsidian RAG Assistant

A fully local, offline personal assistant built with Python, Ollama, ChromaDB, and a QLoRA fine-tuned `Qwen3-8B` model. Designed to run concurrently within an **8 GB VRAM** budget (RTX 4060 Laptop GPU) by keeping LLM inference and embeddings 100% on GPU while offloading audio pipelines to CPU.

## Architecture & Resource Budget

```text
[Mic / Wake Word: openWakeWord (CPU)]
        │
        ▼
[STT: faster-whisper small int8 (CPU)]
        │
        ▼
[brain.py: RAG + Tool Loop + Confirmation Gate] ◄──► [ChromaDB + nomic-embed-text (GPU)]
        │                                                    ▲
        ├──► [Ollama: jarvis Q4_K_M (GPU)]                   │
        ├──► [skills.py: 7 Local Obsidian Tools] ────────────┘
        ▼
[TTS: Kokoro-82M (CPU)]  /  [Web UI: Gradio 127.0.0.1:7860]
```

| Component | Model / Library | Device | Measured Footprint |
| :--- | :--- | :--- | :--- |
| LLM | `jarvis` (fine-tuned `Qwen3-8B`, `Q4_K_M` GGUF) | GPU (100%) | 5.4 GB VRAM |
| Embeddings | `nomic-embed-text` | GPU (100%) | 335 MB VRAM |
| Vector Store | ChromaDB (persistent `./memory_db`) | Local Disk | — |
| Wake Word | `openWakeWord` (`hey_jarvis`, ONNX) | CPU | Lightweight |
| Speech-to-Text | `faster-whisper` (`small`, `int8`) | CPU | Avoids VRAM spill |
| Text-to-Speech | `Kokoro-82M` | CPU | Avoids VRAM spill |

*Keeping Whisper, Kokoro, and openWakeWord on CPU leaves enough VRAM headroom on an 8 GB GPU so `llama.cpp` never spills LLM layers into system RAM.*

## Core Capabilities & Safety

* **Obsidian Vault RAG (`memory.py`):** Indexes local Markdown notes into ChromaDB and retrieves grounded context per turn to avoid hallucinating personal facts.
* **7 Local Tools (`skills.py`):**
  * Read-only: `get_time`, `list_tasks`, `search_notes`, `list_files`
  * Write actions: `add_task`, `complete_task`, `remember_note`
* **Human-in-the-Loop Confirmation Gate (`brain.py`):** Every write tool (`NEEDS_CONFIRM`) pauses execution and requires explicit approval across CLI (`y/n`), Gradio UI, and voice confirmation (`wake.py`) before modifying vault files.
* **Vault Security:** File tools resolve paths and enforce boundary checks to block path traversal outside the Obsidian vault.
* **Three Interfaces:** Terminal CLI (`brain.py`), local Gradio dashboard (`app.py`), and hands-free wake-word listener (`wake.py`).

## Fine-Tuning Case Study: Multi-Turn Tool Calling (QLoRA v1 → v3)

Fine-tuning `Qwen3-8B` with Unsloth QLoRA (Colab L4, `r=8`, `lora_alpha=16`, 1 epoch) exposed a subtle failure mode in multi-turn tool execution:

1. **Failure Mode:** Single-turn smoke tests passed 5/5, but in consecutive multi-turn tool calls (`Add task alpha` → `Add task beta` → `Add task gamma`), the model skipped `<tool_call>` on Turn 3 and hallucinated the confirmation text directly.
2. **Root Cause (Train/Inference Mismatch):**
   * Initially, `brain.py` dropped `tool_calls` and `role: "tool"` messages from conversation history, turning past turns into few-shot examples that omitted tool calls.
   * After fixing `brain.py` history and adding 60 multi-turn conversations (300 total examples), Turn 3 *still* failed. A next-token logit check isolated the cause: during multi-turn SFT, Qwen3's `<think>\n\n</think>\n\n` boundary was injected before every historical assistant turn, whereas Qwen3's inference template only places it on the active generation turn.

| Diagnostic Condition (Turn-3 Next-Token Probability) | `P(<tool_call>)` | `P("Added")` |
| :--- | :---: | :---: |
| Base `Qwen3-8B` (inference format) | `0.999` | `0.001` |
| QLoRA v2 (with historical `<think>`, matching training) | `1.000` | `0.000` |
| QLoRA v2 (inference format, no historical `<think>`) | `0.314` | `0.665` |
| **QLoRA v3 (turn-unrolled, inference format)** | **`0.996`** | **`0.004`** |

3. **Fix (Turn Unrolling):** Unrolled each assistant turn in `finetune/jarvis_train.jsonl` into an independent training sample via `apply_chat_template(..., add_generation_prompt=True, enable_thinking=False)` with `train_on_responses_only` (`lr=4e-5`). Historical turns then matched inference formatting 1:1. Combined with `temperature=0.1` in Ollama, local `Q4_K_M` inference passed 3/3 consecutive tool calls at 100% GPU.

## Project Structure

```text
jarvis/
├── brain.py                  # Core chat loop, RAG injection, tool history & confirmation gate
├── memory.py                 # Obsidian vault chunking, ChromaDB indexing & semantic search
├── skills.py                 # 7 Obsidian/system tools with path safety checks
├── voice.py                  # faster-whisper STT and Kokoro TTS wrappers
├── wake.py                   # Hands-free openWakeWord ("Hey Jarvis") loop
├── app.py                    # Local Gradio web dashboard (127.0.0.1:7860)
├── test_confirm.py           # Unit tests for confirmation gate & multi-turn tool history
├── test_skills.py            # Unit tests for tool security & task matching
└── finetune/
    ├── build_dataset.py      # Reproducible 300-row dataset generator (240 single + 60 multi-turn)
    ├── test_dataset.py       # Schema parity & data quality validation against skills.py
    ├── jarvis_train.jsonl    # Generated SFT training dataset
    └── Modelfile             # Ollama model definition for jarvis-q4_k_m.gguf
```

## Setup & Usage

### Prerequisites
* Windows (tested on native Windows, Python 3.11)
* [`uv`](https://docs.astral.sh/uv/) package manager
* [Ollama](https://ollama.com/) running locally (`ollama serve` or Ollama Desktop)
* `espeak-ng` installed for Kokoro TTS on Windows

### 1. Install Dependencies & Models

```powershell
uv sync
ollama pull nomic-embed-text
```

The `jarvis-q4_k_m.gguf` weight file (~5 GB) is excluded from Git. You have two options for the LLM:
* **Use the fine-tuned model:** Export `jarvis-q4_k_m.gguf` using `finetune/jarvis_train.jsonl`, place it in `finetune/`, and build it in Ollama:
  ```powershell
  cd finetune
  ollama create jarvis -f Modelfile
  cd ..
  ```
* **Run directly with the base model:** Pull `ollama pull qwen3:8b` and set `MODEL = "qwen3:8b"` in `brain.py`.

Point your Obsidian vault path in `memory.py` / `skills.py` to your local vault directory before launching.

### 2. Run Interfaces

```powershell
# Terminal CLI (commands: /v, /remember <text>, /reindex, exit)
uv run brain.py

# Local Gradio Dashboard ([http://127.0.0.1:7860](http://127.0.0.1:7860))
uv run app.py

# Hands-free Voice Listener ("Hey Jarvis")
uv run wake.py
```

### 3. Run Tests

```powershell
uv run python test_confirm.py
uv run python test_skills.py
uv run python finetune/test_dataset.py
```

## Known Limitations & Roadmap

* **Single confirmation per turn:** If a prompt triggers multiple write tools in one turn, the confirmation gate currently pauses on the first write action.
* **English-only voice pipeline:** Kokoro and `hey_jarvis` are currently configured for English. Planned next branch (`bahasa-indonesia`) will integrate Piper TTS for Indonesian voice support.
* **Manual Obsidian edits mid-session:** Repeated queries about tasks may rely on recent conversation history; run `/reindex` or start a new session after editing `tasks.md` manually outside JARVIS.