import torch
import torch.nn as nn

# Đặt seed để kết quả cố định
torch.manual_seed(42)

print("=== BƯỚC 1: CHUẨN BỊ TENSOR (DỮ LIỆU ĐẦU VÀO) ===")
# PyTorch yêu cầu dữ liệu có chiều: (Batch_Size, Số_Từ, Số_Chiều_Vector)
# Ta có 1 câu (batch=1), 3 từ, mỗi từ 4 chiều.
X = torch.tensor([[
    [1.0, 0.0, 1.0, 0.0],  # "tôi"
    [0.0, 2.0, 0.0, 2.0],  # "uống"
    [1.0, 1.0, 1.0, 1.0]   # "đường"
]], dtype=torch.float32)

print("Kích thước đầu vào X:", X.shape)  # Output: torch.Size([1, 3, 4])

print("\n=== BƯỚC 2: KHỞI TẠO LỚP TRANSFORMER ATTENTION ===")
embed_dim = 4   # Số chiều của mỗi từ (phải khớp với X)
num_heads = 1   # Số luồng Attention (dùng 1 để giống ví dụ Numpy trước)

# Lớp MultiheadAttention này đã tự động giấu các ma trận W_q, W_k, W_v ở bên trong
attention_layer = nn.MultiheadAttention(
    embed_dim=embed_dim,
    num_heads=num_heads,
    batch_first=True  # Khai báo để PyTorch biết Batch_Size nằm ở chiều đầu tiên
)

print("\n=== BƯỚC 3: THỰC THI SELF-ATTENTION ===")
# Vì đây là "Self-Attention" (Tự chú ý), ta truyền X vào cả 3 vị trí: Query, Key, và Value.
# PyTorch sẽ tự động nhân X với các trọng số nội bộ để tạo ra Q, K, V và tính toán điểm số.
attn_output, attn_weights = attention_layer(query=X, key=X, value=X)

print("\n1. MA TRẬN PHẦN TRĂM (Attention Weights):")
# Hiển thị tỷ lệ phần trăm các từ chú ý vào nhau (giống Bước 4 Numpy)
print(torch.round(attn_weights * 100) / 100)
# Ví dụ Output dòng 3: [0.18, 0.62, 0.20] -> "đường" chú ý 62% vào "uống"

print("\n2. VECTOR Ý NGHĨA CUỐI CÙNG (Output):")
# Đây là kết quả đã được trộn lẫn ý nghĩa (giống Bước 5 Numpy)
print(torch.round(attn_output * 100) / 100)
