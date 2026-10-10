// MI1 research-only Gemma bank encoder for the pinned llama.cpp runtime.
// Captures per-token, normalized, pre-RoPE Gemma4 K/V at KV-producing layers.

#include "ggml-backend.h"
#include "ggml.h"
#include "llama.h"

#include <algorithm>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

struct LayerCapture {
    int32_t layer = -1;
    int32_t head_dim = 0;
    int32_t kv_heads = 0;
    int32_t slots = 0;
    std::vector<float> keys;
    std::vector<float> values;
};

struct CaptureState {
    std::map<int32_t, LayerCapture> layers;
    int32_t expected_slots = 0;
    std::string error;
};

bool capture_eval(struct ggml_tensor * tensor, bool ask, void * opaque) {
    auto & state = *static_cast<CaptureState *>(opaque);
    const std::string name(tensor->name);
    // The scheduler also invokes callbacks for downstream aliases such as
    // `Vcur_normed-0 (view)`. Those are attention-layout views, not the
    // normalized per-token source tensor, and must never replace its capture.
    if (name.find(" (view)") != std::string::npos) {
        return true;
    }
    const bool is_key = name.rfind("Kcur_normed-", 0) == 0;
    const bool is_value = name.rfind("Vcur_normed-", 0) == 0;
    if (!is_key && !is_value) {
        return true;
    }

    const size_t split = name.find_last_of('-');
    if (split == std::string::npos) {
        state.error = "captured tensor has no layer suffix: " + name;
        return false;
    }
    int32_t layer = -1;
    try {
        layer = std::stoi(name.substr(split + 1));
    } catch (const std::exception &) {
        state.error = "invalid layer suffix in captured tensor: " + name;
        return false;
    }
    if (ask) {
        return true;
    }

    if (ggml_n_dims(tensor) != 3 ||
            tensor->ne[2] != state.expected_slots ||
            tensor->type != GGML_TYPE_F32) {
        state.error = "unexpected capture shape/type for " + name +
                " dims=" + std::to_string(ggml_n_dims(tensor)) +
                " ne=" + std::to_string(tensor->ne[0]) + "," +
                std::to_string(tensor->ne[1]) + "," +
                std::to_string(tensor->ne[2]) +
                " nb=" + std::to_string(tensor->nb[0]) + "," +
                std::to_string(tensor->nb[1]) + "," +
                std::to_string(tensor->nb[2]) +
                " type=" + std::to_string(tensor->type) +
                " op=" + std::to_string(tensor->op) +
                " view_src=" + (tensor->view_src ? tensor->view_src->name : "<none>");
        return false;
    }

    const int32_t head_dim = static_cast<int32_t>(tensor->ne[0]);
    const int32_t kv_heads = static_cast<int32_t>(tensor->ne[1]);
    if (head_dim <= 0 || kv_heads <= 0 || tensor->nb[0] != sizeof(float)) {
        state.error = "unexpected logical element layout for " + name;
        return false;
    }

    // Kcur_normed/Vcur_normed may be views. Backend tensor_get is a raw copy,
    // not a strided gather, so read each logical [head_dim] row by its byte
    // strides and pack it into canonical [dim, kv_head, token] order.
    std::vector<float> data(static_cast<size_t>(head_dim) *
            static_cast<size_t>(kv_heads) *
            static_cast<size_t>(state.expected_slots));
    const size_t row_bytes = static_cast<size_t>(head_dim) * sizeof(float);
    for (int32_t token = 0; token < state.expected_slots; ++token) {
        for (int32_t head = 0; head < kv_heads; ++head) {
            const size_t src_offset = static_cast<size_t>(token) * tensor->nb[2] +
                    static_cast<size_t>(head) * tensor->nb[1];
            const size_t dst_offset = (static_cast<size_t>(token) *
                    static_cast<size_t>(kv_heads) +
                    static_cast<size_t>(head)) *
                    static_cast<size_t>(head_dim);
            ggml_backend_tensor_get(tensor, data.data() + dst_offset,
                    src_offset, row_bytes);
        }
    }

    auto & record = state.layers[layer];
    record.layer = layer;
    record.head_dim = head_dim;
    record.kv_heads = kv_heads;
    record.slots = state.expected_slots;
    if (is_key) {
        record.keys = std::move(data);
    } else {
        record.values = std::move(data);
    }
    return true;
}

std::string read_text(const std::string & path) {
    std::ifstream input(path, std::ios::binary);
    if (!input) {
        throw std::runtime_error("cannot open source text: " + path);
    }
    return std::string(std::istreambuf_iterator<char>(input), {});
}

template <typename T>
void write_scalar(std::ofstream & output, T value) {
    output.write(reinterpret_cast<const char *>(&value), sizeof(value));
    if (!output) {
        throw std::runtime_error("failed writing encoder output");
    }
}

void write_capture(const std::string & path, const CaptureState & state,
        const std::vector<llama_token> & tokens) {
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    if (!output) {
        throw std::runtime_error("cannot create capture output: " + path);
    }
    const char magic[8] = {'M', 'I', '1', 'C', 'A', 'P', '0', '1'};
    output.write(magic, sizeof(magic));
    write_scalar<uint32_t>(output, 1);
    write_scalar<uint32_t>(output, static_cast<uint32_t>(state.layers.size()));
    write_scalar<uint32_t>(output, static_cast<uint32_t>(tokens.size()));
    for (const auto token : tokens) {
        write_scalar<int32_t>(output, token);
    }
    for (const auto & entry : state.layers) {
        const auto & layer = entry.second;
        if (layer.keys.empty() || layer.values.empty()) {
            throw std::runtime_error("incomplete K/V capture for layer " +
                    std::to_string(layer.layer));
        }
        write_scalar<int32_t>(output, layer.layer);
        write_scalar<int32_t>(output, layer.head_dim);
        write_scalar<int32_t>(output, layer.kv_heads);
        write_scalar<int32_t>(output, layer.slots);
        output.write(reinterpret_cast<const char *>(layer.keys.data()),
                static_cast<std::streamsize>(layer.keys.size() * sizeof(float)));
        output.write(reinterpret_cast<const char *>(layer.values.data()),
                static_cast<std::streamsize>(layer.values.size() * sizeof(float)));
    }
    output.flush();
    if (!output) {
        throw std::runtime_error("failed flushing encoder output");
    }
}

} // namespace

int main(int argc, char ** argv) {
    if (argc != 4) {
        std::cerr << "usage: mi1_native_encode MODEL.gguf SOURCE.txt OUTPUT.mi1cap\n";
        return 2;
    }
    try {
        const std::string model_path = argv[1];
        const std::string source_path = argv[2];
        const std::string output_path = argv[3];
        const std::string source_text = read_text(source_path);
        if (source_text.empty()) {
            throw std::runtime_error("source text must not be empty");
        }

        llama_backend_init();
        ggml_backend_load_all();
        auto model_params = llama_model_default_params();
        model_params.n_gpu_layers = -1;
        llama_model * model = llama_model_load_from_file(model_path.c_str(), model_params);
        if (model == nullptr) {
            throw std::runtime_error("pinned model could not be loaded");
        }
        const llama_vocab * vocab = llama_model_get_vocab(model);
        int32_t token_count = -llama_tokenize(vocab, source_text.data(),
                static_cast<int32_t>(source_text.size()), nullptr, 0, true, false);
        if (token_count <= 0) {
            throw std::runtime_error("source text tokenization failed");
        }
        std::vector<llama_token> tokens(static_cast<size_t>(token_count));
        token_count = llama_tokenize(vocab, source_text.data(),
                static_cast<int32_t>(source_text.size()), tokens.data(), token_count,
                true, false);
        if (token_count <= 0) {
            throw std::runtime_error("source text tokenization failed");
        }
        tokens.resize(static_cast<size_t>(token_count));

        auto context_params = llama_context_default_params();
        context_params.n_ctx = static_cast<uint32_t>(std::max<size_t>(512, tokens.size() + 8));
        context_params.n_batch = context_params.n_ctx;
        context_params.n_ubatch = context_params.n_ctx;
        context_params.n_threads = 4;
        context_params.n_threads_batch = 4;
        CaptureState capture;
        capture.expected_slots = token_count;
        context_params.cb_eval = capture_eval;
        context_params.cb_eval_user_data = &capture;
        llama_context * context = llama_init_from_model(model, context_params);
        if (context == nullptr) {
            llama_model_free(model);
            throw std::runtime_error("could not create capture context");
        }

        const int decode_status = llama_decode(context,
                llama_batch_get_one(tokens.data(), token_count));
        if (decode_status != 0 || !capture.error.empty()) {
            llama_free(context);
            llama_model_free(model);
            throw std::runtime_error(capture.error.empty() ?
                    "teacher-forced bank encode failed" : capture.error);
        }
        if (capture.layers.empty()) {
            llama_free(context);
            llama_model_free(model);
            throw std::runtime_error("no Gemma4 KV tensors were captured");
        }
        write_capture(output_path, capture, tokens);
        std::cout << "captured_slots=" << tokens.size()
                  << " kv_layers=" << capture.layers.size()
                  << " output=" << output_path << "\n";
        llama_free(context);
        llama_model_free(model);
        llama_backend_free();
        return 0;
    } catch (const std::exception & error) {
        std::cerr << "mi1_native_encode: " << error.what() << "\n";
        return 1;
    }
}
