"""Check fixed candidate strings with the pinned Windows llama.cpp grammar sampler and vocabulary only."""
import argparse
import ctypes as c
import hashlib
import json
import math
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIBRARY_SHA = "965a15d74cdbb1a38cda5b717a6eca9015527c21af7a141d4e32624820f49a21"
VOCAB_SOURCE_SHA = "6a1a2eb6d15622bf3c96857206351ba97e1af16c30d7a74ee38970e434e9407e"


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


# Public ABI at ggml-org/llama.cpp 1f8baae28d096624bd47d33d2d179ec479d47720, include/llama.h.
class ModelParams(c.Structure):
    _fields_ = [
        ("devices", c.c_void_p), ("tensor_buft_overrides", c.c_void_p),
        ("n_gpu_layers", c.c_int32), ("split_mode", c.c_int), ("load_mode", c.c_int),
        ("lazy_mode", c.c_int), ("main_gpu", c.c_int32), ("tensor_split", c.c_void_p),
        ("progress_callback", c.c_void_p), ("progress_callback_user_data", c.c_void_p), ("kv_overrides", c.c_void_p),
        ("vocab_only", c.c_bool), ("check_tensors", c.c_bool), ("use_extra_bufts", c.c_bool),
        ("no_host", c.c_bool), ("no_alloc", c.c_bool), ("load_mtp", c.c_bool),
    ]


class Candidate(c.Structure):
    _fields_ = [("id", c.c_int32), ("logit", c.c_float), ("p", c.c_float)]


class Candidates(c.Structure):
    _fields_ = [("data", c.POINTER(Candidate)), ("size", c.c_size_t), ("selected", c.c_int64), ("sorted", c.c_bool)]


def native_checks(library, gguf, grammar, fixtures):
    if os.name != "nt" or digest(library) != LIBRARY_SHA or digest(gguf) != VOCAB_SOURCE_SHA:
        raise ValueError("This binding requires the pinned Windows DLL and vocabulary file")
    with os.add_dll_directory(str(library.resolve().parent)):
        dll = c.CDLL(str(library.resolve()))
        signatures = {
            "model_default_params": (ModelParams, []),
            "model_load_from_file": (c.c_void_p, [c.c_char_p, ModelParams]),
            "model_get_vocab": (c.c_void_p, [c.c_void_p]), "model_free": (None, [c.c_void_p]),
            "vocab_eos": (c.c_int32, [c.c_void_p]),
            "tokenize": (c.c_int32, [c.c_void_p, c.c_char_p, c.c_int32, c.POINTER(c.c_int32), c.c_int32, c.c_bool, c.c_bool]),
            "sampler_init_grammar": (c.c_void_p, [c.c_void_p, c.c_char_p, c.c_char_p]),
            "sampler_apply": (None, [c.c_void_p, c.POINTER(Candidates)]),
            "sampler_accept": (None, [c.c_void_p, c.c_int32]), "sampler_free": (None, [c.c_void_p]),
        }
        for name, (result, args) in signatures.items():
            function = getattr(dll, "llama_" + name)
            function.restype, function.argtypes = result, args
        params = dll.llama_model_default_params()
        params.vocab_only = True
        params.n_gpu_layers = 0
        model = dll.llama_model_load_from_file(os.fsencode(gguf), params)
        if not model:
            raise RuntimeError("Could not load the pinned vocabulary")
        try:
            vocab = dll.llama_model_get_vocab(model)
            end = dll.llama_vocab_eos(vocab)
            if end < 0:
                raise RuntimeError("Vocabulary has no end token")
            return {item["name"]: accepts(dll, vocab, end, grammar, item["text"]) for item in fixtures}
        finally:
            dll.llama_model_free(model)


def accepts(dll, vocab, end, grammar, text):
    raw = text.encode("utf-8")
    tokens = (c.c_int32 * (len(raw) + 1))()
    count = dll.llama_tokenize(vocab, raw, len(raw), tokens, len(tokens), False, False)
    if count < 0:
        raise RuntimeError("Tokenization failed")
    sampler = dll.llama_sampler_init_grammar(vocab, grammar, b"root")
    if not sampler:
        raise ValueError("Invalid grammar")
    try:
        # Test membership by walking the supplied prefix, including its end token. No sampling or decode.
        for token in [*tokens[:count], end]:
            candidate = Candidate(token, 0.0, 0.0)
            allowed = Candidates(c.pointer(candidate), 1, -1, False)
            dll.llama_sampler_apply(sampler, c.byref(allowed))
            if not math.isfinite(candidate.logit):
                return False
            dll.llama_sampler_accept(sampler, token)
        return True
    finally:
        dll.llama_sampler_free(sampler)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("library", type=Path)
    parser.add_argument("vocabulary", type=Path)
    options = parser.parse_args()
    fixture_text = (HERE / "grammar-cases.json").read_text(encoding="utf-8")
    fixtures = json.loads(fixture_text)
    grammar = (HERE / "decision.gbnf").read_text(encoding="utf-8").encode("utf-8")
    observed = native_checks(options.library, options.vocabulary, grammar, fixtures)
    print(json.dumps({"llama_commit": "1f8baae28d096624bd47d33d2d179ec479d47720",
                      "library_sha256": LIBRARY_SHA, "vocabulary_file_sha256": VOCAB_SOURCE_SHA,
                      "grammar_sha256_lf": hashlib.sha256(grammar).hexdigest(),
                      "fixture_sha256_lf": hashlib.sha256(fixture_text.encode("utf-8")).hexdigest(),
                      "model_inference_calls": 0, "result": observed}, indent=2))
    if observed != {item["name"]: item["accepted"] for item in fixtures}:
        raise SystemExit("Observed grammar membership differs from the expected fixtures")
