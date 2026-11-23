import os
import threading

import ctranslate2
import sentencepiece


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, "translation_models")

MODELS = {
    ("ar", "en"): {
        "directory": "ar-en",
        "prefix": "",
    },
    ("en", "ar"): {
        "directory": "en-ar",
        "prefix": ">>ara<<",
    },
}

_loaded_models = {}
_model_lock = threading.RLock()


def _load_model(source_language, target_language):
    key = (source_language, target_language)

    if key not in MODELS:
        raise ValueError("Unsupported translation direction.")

    with _model_lock:
        if key in _loaded_models:
            return _loaded_models[key]

        config = MODELS[key]
        directory = os.path.join(
            MODEL_DIR,
            config["directory"]
        )

        required_files = (
            "model.bin",
            "source.spm",
            "target.spm",
            "config.json",
        )

        for filename in required_files:
            path = os.path.join(directory, filename)
            if not os.path.isfile(path):
                raise FileNotFoundError(
                    "Translation model file missing: "
                    + path
                )

        source_tokenizer = sentencepiece.SentencePieceProcessor(
            model_file=os.path.join(directory, "source.spm")
        )

        target_tokenizer = sentencepiece.SentencePieceProcessor(
            model_file=os.path.join(directory, "target.spm")
        )

        translator = ctranslate2.Translator(
            directory,
            device="cpu",
            compute_type="int8",
            inter_threads=1,
            intra_threads=2,
        )

        loaded = {
            "translator": translator,
            "source_tokenizer": source_tokenizer,
            "target_tokenizer": target_tokenizer,
            "prefix": config["prefix"],
        }

        _loaded_models[key] = loaded
        return loaded


def translate_batch(
    texts,
    source_language,
    target_language,
    batch_size=16,
):
    if source_language == target_language:
        return list(texts)

    loaded = _load_model(
        source_language,
        target_language
    )

    originals = list(texts)
    if not originals:
        return []

    source_tokenizer = loaded["source_tokenizer"]
    target_tokenizer = loaded["target_tokenizer"]

    tokenized = []

    for text in originals:
        prepared = loaded["prefix"] + str(text)
        tokens = source_tokenizer.encode(
            prepared,
            out_type=str
        )
        tokenized.append(tokens)

    translated_texts = []

    with _model_lock:
        for start in range(0, len(tokenized), batch_size):
            batch = tokenized[start:start + batch_size]

            results = loaded["translator"].translate_batch(
                batch,
                batch_type="tokens",
                max_batch_size=batch_size,
                beam_size=2,
            )

            for result in results:
                hypotheses = result.hypotheses

                if not hypotheses or not hypotheses[0]:
                    translated_texts.append("")
                    continue

                translated = target_tokenizer.decode(
                    hypotheses[0]
                ).strip()

                translated_texts.append(translated)

    return translated_texts
