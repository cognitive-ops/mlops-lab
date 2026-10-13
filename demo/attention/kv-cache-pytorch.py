import time
import torch
import torch.nn as nn

torch.manual_seed(42)

print("=== KV CACHE DEMO: SINH TỪNG TOKEN CÓ CACHE vs KHÔNG CACHE ===")

embed_dim = 4
seq_len_full = 5  # giả sử ta sẽ sinh ra 5 token

# Trọng số W_q, W_k, W_v dùng chung cho cả 2 cách (để so sánh kết quả phải giống nhau)
W_q = nn.Linear(embed_dim, embed_dim, bias=False)
W_k = nn.Linear(embed_dim, embed_dim, bias=False)
W_v = nn.Linear(embed_dim, embed_dim, bias=False)

# Toàn bộ chuỗi token (batch=1, 5 token, 4 chiều) - dùng để giả lập input sinh dần
X_full = torch.randn(1, seq_len_full, embed_dim)


def attention(q, k, v):
    # q: (1, 1, d) - chỉ 1 token query (token đang sinh)
    # k, v: (1, T, d) - toàn bộ token đã thấy tới giờ (từ cache hoặc tính lại)
    scores = torch.matmul(q, k.transpose(-2, -1)) / (embed_dim ** 0.5)
    weights = torch.softmax(scores, dim=-1)
    return torch.matmul(weights, v)


print("\n--- CÁCH 1: KHÔNG CACHE (mỗi bước tính lại K,V từ đầu) ---")
outputs_no_cache = []
for t in range(1, seq_len_full + 1):
    x_so_far = X_full[:, :t, :]          # phải đưa lại toàn bộ token cũ mỗi lần
    k_all = W_k(x_so_far)                # tính lại K cho cả chuỗi -> tốn O(T^2) qua các bước
    v_all = W_v(x_so_far)
    q_last = W_q(x_so_far[:, -1:, :])    # chỉ cần Q của token mới nhất
    out = attention(q_last, k_all, v_all)
    outputs_no_cache.append(out)


print("\n--- CÁCH 2: CÓ KV CACHE (chỉ tính K,V cho token mới, nối vào cache) ---")
k_cache = None  # sẽ có shape (1, T, d), lớn dần theo từng bước
v_cache = None
outputs_with_cache = []

for t in range(seq_len_full):
    x_new = X_full[:, t:t + 1, :]        # chỉ 1 token mới, KHÔNG cần token cũ
    q_new = W_q(x_new)
    k_new = W_k(x_new)                   # chỉ tính K,V cho đúng 1 token mới
    v_new = W_v(x_new)

    # Nối K,V mới vào cache (đây chính là "KV cache")
    k_cache = k_new if k_cache is None else torch.cat([k_cache, k_new], dim=1)
    v_cache = v_new if v_cache is None else torch.cat([v_cache, v_new], dim=1)

    out = attention(q_new, k_cache, v_cache)
    outputs_with_cache.append(out)


print("\n=== KIỂM TRA: 2 CÁCH CHO KẾT QUẢ GIỐNG NHAU ===")
for t in range(seq_len_full):
    same = torch.allclose(outputs_no_cache[t], outputs_with_cache[t], atol=1e-6)
    print(f"Bước {t + 1}: khớp = {same}")

print("\nGhi chú:")
print("- Không cache: mỗi bước phải nhân lại W_k, W_v với TOÀN BỘ token cũ -> lãng phí.")
print("- Có cache: mỗi bước chỉ nhân W_k, W_v với 1 token mới, K/V cũ lấy từ cache có sẵn.")
print("- Đây là lý do LLM sinh text nhanh hơn nhiều khi bật KV cache (dùng trong HuggingFace")
print("  generate(use_cache=True), vLLM, etc).")


print("\n=== BENCHMARK: ĐO THỜI GIAN THỰC TẾ (chuỗi dài hơn) ===")
bench_seq_len = 300   # chuỗi dài hơn để thấy rõ chênh lệch tốc độ
bench_embed_dim = 256
bench_W_q = nn.Linear(bench_embed_dim, bench_embed_dim, bias=False)
bench_W_k = nn.Linear(bench_embed_dim, bench_embed_dim, bias=False)
bench_W_v = nn.Linear(bench_embed_dim, bench_embed_dim, bias=False)
X_bench = torch.randn(1, bench_seq_len, bench_embed_dim)


def bench_attention(q, k, v, dim):
    scores = torch.matmul(q, k.transpose(-2, -1)) / (dim ** 0.5)
    weights = torch.softmax(scores, dim=-1)
    return torch.matmul(weights, v)


def run_no_cache():
    for t in range(1, bench_seq_len + 1):
        x_so_far = X_bench[:, :t, :]
        k_all = bench_W_k(x_so_far)
        v_all = bench_W_v(x_so_far)
        q_last = bench_W_q(x_so_far[:, -1:, :])
        bench_attention(q_last, k_all, v_all, bench_embed_dim)


def run_with_cache():
    k_cache = None
    v_cache = None
    for t in range(bench_seq_len):
        x_new = X_bench[:, t:t + 1, :]
        q_new = bench_W_q(x_new)
        k_new = bench_W_k(x_new)
        v_new = bench_W_v(x_new)
        k_cache = k_new if k_cache is None else torch.cat([k_cache, k_new], dim=1)
        v_cache = v_new if v_cache is None else torch.cat([v_cache, v_new], dim=1)
        bench_attention(q_new, k_cache, v_cache, bench_embed_dim)


with torch.no_grad():
    # chạy thử 1 lần trước để "làm nóng" (loại trừ overhead khởi tạo)
    run_no_cache()
    run_with_cache()

    start = time.perf_counter()
    run_no_cache()
    time_no_cache = time.perf_counter() - start

    start = time.perf_counter()
    run_with_cache()
    time_with_cache = time.perf_counter() - start

print(f"Chuỗi dài {bench_seq_len} token, embed_dim={bench_embed_dim}")
print(f"- Không cache : {time_no_cache * 1000:.2f} ms")
print(f"- Có KV cache : {time_with_cache * 1000:.2f} ms")
print(f"- Nhanh hơn   : {time_no_cache / time_with_cache:.2f}x")
