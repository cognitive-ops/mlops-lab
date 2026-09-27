import numpy as np

# Đặt hạt giống ngẫu nhiên để kết quả code luôn cố định mỗi lần chạy
np.random.seed(42)

print("=== BƯỚC 0: CHUẨN BỊ DỮ LIỆU ĐẦU VÀO ===")
# Giả sử chúng ta có câu 3 từ: "tôi uống đường".
# Mỗi từ đã được chuyển thành một vector (embedding) có độ dài 4 con số.
# Ma trận X có kích thước (3 từ, 4 chiều).
X = np.array([
    [1.0, 0.0, 1.0, 0.0],  # "tôi"
    [0.0, 2.0, 0.0, 2.0],  # "uống"
    [1.0, 1.0, 1.0, 1.0]   # "đường" (Từ đang cần xác định rõ nghĩa)
])
print("Ma trận từ gốc (X):\n", X)

print("\n=== BƯỚC 1: TẠO MA TRẬN TRỌNG SỐ (W_q, W_k, W_v) ===")
# Trong thực tế, AI phải "học" (training hàng tháng trời) để tìm ra các con số này.
# Ở đây ta khởi tạo ngẫu nhiên. Ma trận trọng số có kích thước (4 chiều, 3 chiều_ẩn).
W_Q = np.random.randn(4, 3)
W_K = np.random.randn(4, 3)
W_V = np.random.randn(4, 3)

print("\n=== BƯỚC 2: MỖI TỪ TỰ BIẾN HÌNH THÀNH Q, K, V ===")
# Toán học: Nhân ma trận (Dot product giữa X và W)
# X (3x4) nhân W (4x3) = Kết quả (3x3)
Q = np.dot(X, W_Q)  # Tạo ra "Cái Loa"
K = np.dot(X, W_K)  # Tạo ra "Bảng Tên"
V = np.dot(X, W_V)  # Tạo ra "Hộp Quà"

print("Query - Cái Loa (Q):\n", np.round(Q, 2))
print("Key - Bảng Tên (K):\n", np.round(K, 2))
print("Value - Hộp Quà (V):\n", np.round(V, 2))

print("\n=== BƯỚC 3: TÍNH ĐIỂM SỐ (Attention Scores) ===")
# Lấy "Cái Loa" của tất cả các từ, đập vào "Bảng Tên" của tất cả các từ khác.
# Toán học: Q nhân với ma trận chuyển vị của K (K.T)
# Kích thước: (3x3) nhân (3x3) -> Trả về ma trận điểm số (3 từ x 3 từ)
scores = np.dot(Q, K.T)

# Để số không bị quá to gây lỗi toán học, người ta chia cho căn bậc 2 của chiều_ẩn (sqrt(3))
d_k = K.shape[1]
scores = scores / np.sqrt(d_k)

print("Ma trận điểm số thô:\n", np.round(scores, 2))
# Giải thích kết quả:
# Dòng thứ 3 (của từ "đường") đang chứa 3 điểm số khi nó "hỏi" 3 từ: [tôi, uống, đường].
# Hãy chú ý xem điểm số nào cao nhất!

print("\n=== BƯỚC 4: CHUẨN HÓA THÀNH PHẦN TRĂM (Softmax) ===")
# Biến các điểm số thô thành tỷ lệ phần trăm (tổng mỗi dòng = 1.0 hay 100%)


def softmax(x):
    e_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
    return e_x / np.sum(e_x, axis=-1, keepdims=True)


attention_weights = softmax(scores)
print("Ma trận phần trăm Attention (Weights):\n", np.round(attention_weights, 2))

# Giải thích kết quả:
# Dòng 3 (từ "đường"): [0.15, 0.70, 0.15]
# Nghĩa là từ "đường" đang dồn 70% sự chú ý vào từ "uống", 15% vào "tôi", và 15% vào chính nó.

print("\n=== BƯỚC 5: HẤP THỤ Ý NGHĨA (Output cuối cùng) ===")
# Nhân tỷ lệ phần trăm vừa có với "Hộp Quà" (Value) của các từ để pha trộn ý nghĩa.
# (3x3) nhân với V (3x3) -> Trả về (3x3)
output = np.dot(attention_weights, V)

print("Vector ý nghĩa ĐÃ ĐƯỢC CẬP NHẬT NGỮ CẢNH:\n", np.round(output, 2))
