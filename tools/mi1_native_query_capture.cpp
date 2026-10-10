// MI1 Appendix-C calibration capture; performs prompt prefill only, no decode.
#include "ggml-backend.h"
#include "ggml.h"
#include "llama.h"
#include "llama-mi1.h"

#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
struct LayerCapture {
    int32_t layer = -1;
    ggml_type q_type = GGML_TYPE_COUNT;
    std::array<int64_t, 4> q_shape{};
    std::vector<uint8_t> q_bytes;
    ggml_type p_type = GGML_TYPE_COUNT;
    std::array<int64_t, 4> p_shape{};
    std::vector<uint8_t> p_bytes;
};

struct CaptureState {
    std::map<int32_t, LayerCapture> layers;
    std::string error;
};

bool capture_eval(ggml_tensor * tensor, bool ask, void * opaque) {
    auto & state = *static_cast<CaptureState *>(opaque);
    const std::string name(tensor->name);
    // Do not replace normalized Q/softmax nodes with later attention views.
    if (name.find(" (view)") != std::string::npos) {
        return true;
    }
    const bool query = name.rfind("Qcur_normed-", 0) == 0;
    const bool probabilities = name.rfind("kq_soft_max-", 0) == 0;
    if (!query && !probabilities) {
        return true;
    }
    const auto delimiter = name.find_last_of('-');
    if (delimiter == std::string::npos) {
        state.error = "captured tensor lacks layer suffix: " + name;
        return false;
    }
    int32_t layer = -1;
    try {
        layer = std::stoi(name.substr(delimiter + 1));
    } catch (const std::exception &) {
        state.error = "invalid tensor layer suffix: " + name;
        return false;
    }
    if (ask) {
        return true;
    }
    auto & record = state.layers[layer];
    record.layer = layer;
    auto & type = query ? record.q_type : record.p_type;
    auto & shape = query ? record.q_shape : record.p_shape;
    auto & bytes = query ? record.q_bytes : record.p_bytes;
    type = tensor->type;
    for (int i = 0; i < 4; ++i) {
        shape[static_cast<size_t>(i)] = i < ggml_n_dims(tensor) ? tensor->ne[i] : 1;
    }
    bytes.resize(ggml_nbytes(tensor));
    ggml_backend_tensor_get(tensor, bytes.data(), 0, bytes.size());
    return true;
}

std::string read_file(const std::string & path) {
    std::ifstream in(path, std::ios::binary);
    if (!in) throw std::runtime_error("cannot read prompt file");
    return {std::istreambuf_iterator<char>(in), {}};
}

template <typename T>
void write_value(std::ofstream & out, const T & value) {
    out.write(reinterpret_cast<const char *>(&value), sizeof(value));
    if (!out) throw std::runtime_error("failed writing capture");
}

void write_record(const std::string & path, const CaptureState & state,
        const std::vector<llama_token> & tokens) {
    std::ofstream out(path, std::ios::binary | std::ios::trunc);
    if (!out) throw std::runtime_error("cannot create capture output");
    out.write("MI1QRY01", 8);
    write_value<uint32_t>(out, 1);
    write_value<uint32_t>(out, static_cast<uint32_t>(state.layers.size()));
    write_value<uint32_t>(out, static_cast<uint32_t>(tokens.size()));
    out.write(reinterpret_cast<const char *>(tokens.data()),
            static_cast<std::streamsize>(tokens.size() * sizeof(llama_token)));
    for (const auto & entry : state.layers) {
        const auto & layer = entry.second;
        if (layer.q_bytes.empty() || layer.p_bytes.empty()) {
            throw std::runtime_error("missing Q or attention-probability capture at layer " +
                    std::to_string(layer.layer));
        }
        write_value<int32_t>(out, layer.layer);
        write_value<uint32_t>(out, static_cast<uint32_t>(layer.q_type));
        out.write(reinterpret_cast<const char *>(layer.q_shape.data()), sizeof(layer.q_shape));
        write_value<uint64_t>(out, layer.q_bytes.size());
        out.write(reinterpret_cast<const char *>(layer.q_bytes.data()), layer.q_bytes.size());
        write_value<uint32_t>(out, static_cast<uint32_t>(layer.p_type));
        out.write(reinterpret_cast<const char *>(layer.p_shape.data()), sizeof(layer.p_shape));
        write_value<uint64_t>(out, layer.p_bytes.size());
        out.write(reinterpret_cast<const char *>(layer.p_bytes.data()), layer.p_bytes.size());
    }
}
} // namespace

int main(int argc, char ** argv) {
    if (argc != 5) {
        std::cerr << "usage: mi1-native-query-capture MODEL.gguf PROMPT.txt BANK.mi1|- OUTPUT.mi1qry\n";
        return 2;
    }
    try {
        const std::string prompt = read_file(argv[2]);
        if (prompt.empty()) throw std::runtime_error("prompt text is empty");
        const bool bank_attached = std::string(argv[3]) != "-";
        if (bank_attached && !llama_mi1_attach_bank(argv[3])) {
            throw std::runtime_error(llama_mi1_last_error());
        }
        ggml_backend_load_all();
        auto model_params = llama_model_default_params();
        model_params.n_gpu_layers = -1;
        auto * model = llama_model_load_from_file(argv[1], model_params);
        if (!model) throw std::runtime_error("pinned model load failed");
        const auto * vocab = llama_model_get_vocab(model);
        int32_t count = -llama_tokenize(vocab, prompt.data(), static_cast<int32_t>(prompt.size()),
                nullptr, 0, true, false);
        if (count <= 0) throw std::runtime_error("prompt tokenization failed");
        std::vector<llama_token> tokens(static_cast<size_t>(count));
        count = llama_tokenize(vocab, prompt.data(), static_cast<int32_t>(prompt.size()),
                tokens.data(), count, true, false);
        if (count <= 0) throw std::runtime_error("prompt tokenization failed");
        tokens.resize(static_cast<size_t>(count));
        auto params = llama_context_default_params();
        params.n_ctx = static_cast<uint32_t>(std::max<size_t>(512, tokens.size() + 8));
        params.n_batch = params.n_ctx;
        params.n_ubatch = params.n_ctx;
        params.flash_attn_type = LLAMA_FLASH_ATTN_TYPE_DISABLED;
        params.n_threads = 4;
        params.n_threads_batch = 4;
        CaptureState capture;
        params.cb_eval = capture_eval;
        params.cb_eval_user_data = &capture;
        auto * context = llama_init_from_model(model, params);
        if (!context) throw std::runtime_error("context initialization failed");
        const int status = llama_decode(context, llama_batch_get_one(tokens.data(), count));
        if (status != 0 || !capture.error.empty()) {
            throw std::runtime_error(capture.error.empty() ? "prompt prefill failed" : capture.error);
        }
        write_record(argv[4], capture, tokens);
        std::cout << "prefill_only=true generated_tokens=0 bank_attached="
                  << (bank_attached ? "true" : "false")
                  << " layers=" << capture.layers.size()
                  << " prompt_tokens=" << tokens.size()
                  << " output=" << argv[4] << "\n";
        llama_free(context);
        llama_model_free(model);
        llama_backend_free();
        return 0;
    } catch (const std::exception & error) {
        std::cerr << "mi1-native-query-capture: " << error.what() << "\n";
        return 1;
    }
}
