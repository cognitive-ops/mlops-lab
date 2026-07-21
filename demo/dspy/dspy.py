import dspy

# 1. Cấu hình LLM (Bạn có thể đổi sang OpenAI, Anthropic, Ollama, v.v.)
# Ở đây ta giả định dùng GPT-4o qua API
lm = dspy.LM('openai/gpt-4o', api_key='your-api-key-here')
dspy.configure(lm=lm)

# =====================================================================
# STEP 2: ĐỊNH NGHĨA SIGNATURE (BÀI TOÁN)
# =====================================================================
# Thay vì viết prompt "Hãy đóng vai...", ta chỉ khai báo Input và Output.
class ExplainLikeImFive(dspy.Signature):
    """Giải thích các khái niệm công nghệ phức tạp bằng ngôn từ cực kỳ đơn giản cho trẻ 5 tuổi."""
    
    concept = dspy.InputField(desc="Thuật ngữ hoặc khái niệm công nghệ cần giải thích")
    explanation = dspy.OutputField(desc="Lời giải thích đơn giản, dễ hiểu, kèm ví dụ ẩn dụ thực tế")

# =====================================================================
# STEP 3: ĐỊNH NGHĨA MODULE (LUỒNG XỬ LÝ)
# =====================================================================
# Module này sẽ bọc Signature lại và ép LLM phải suy luận từng bước (Chain of Thought)
class TechExplainer(dspy.Module):
    def __init__(self):
        super().__init__()
        # Thay vì dspy.Predict, ta dùng dspy.ChainOfThought để tăng độ logic
        self.prog = dspy.ChainOfThought(ExplainLikeImFive)
    
    def forward(self, concept):
        # Gọi module xử lý và trả về kết quả
        return self.prog(concept=concept)

# Khởi tạo chương trình
explainer = TechExplainer()

# Test thử khi CHƯA QUA TỐI ƯU HÓA (Zero-shot)
print("--- KẾT QUẢ CHƯA OPTIMIZE ---")
pred_before = explainer(concept="API")
print(pred_before.explanation)


# =====================================================================
# STEP 4: TỰ ĐỘNG TỐI ƯU HÓA PROMPT (OPTIMIZATION)
# =====================================================================
# Giả sử chúng ta chuẩn bị một tập dữ liệu mẫu cực kỳ nhỏ (Training data) 
# để "dạy" DSPy biết thế nào là một câu trả lời tốt.
trainset = [
    dspy.Example(concept="Cloud Computing (Điện toán đám mây)", 
                 explanation="Giống như việc con không giữ đồ chơi ở nhà mà gửi ở một kho khổng lồ, khi nào cần thì bấm nút là đồ chơi bay tới."),
    dspy.Example(concept="Database (Cơ sở dữ liệu)", 
                 explanation="Nó giống như một tủ đựng đồ chơi có rất nhiều ngăn kéo ngăn nắp, giúp con tìm lại siêu nhân hay ô tô trong 1 nốt nhạc."),
    dspy.Example(concept="Encryption (Mã hóa)", 
                 explanation="Là việc con giấu bức thư vào một chiếc hộp khóa lại bằng mật mã bí mật, chỉ có bạn thân của con có chìa khóa mới mở được.")
]
# Gắn nhãn Input cho tập train
trainset = [x.with_inputs('concept')]

# Sử dụng BootstrapFewShot - Bộ tối ưu hóa cơ bản của DSPy
# Nó sẽ tự chạy thử, chấm điểm và tự chọn ra các ví dụ tốt nhất để gộp vào prompt ngầm
from dspy.teleprompt import BootstrapFewShot

# Định nghĩa một metric đơn giản (Ở đây ta tạm để mặc định là check xem có output hay không, 
# trong thực tế bạn có thể viết hàm kiểm tra độ dài, kiểm tra từ khóa...)
def simple_metric(gold, pred, trace=None):
    return len(pred.explanation) > 0

# Cấu hình bộ Optimizer
config = dict(max_bootstrapped_demos=2, max_labeled_demos=2)
optimizer = BootstrapFewShot(metric=simple_metric, **config)

# Tiến hành "Compile" (Tối ưu hóa hệ thống)
optimized_explainer = optimizer.compile(TechExplainer(), trainset=trainset)

# =====================================================================
# STEP 5: TEST KẾT QUẢ SAU KHI COMPILE
# =====================================================================
print("\n--- KẾT QUẢ SAU KHI OPTIMIZE (COMPILED) ---")
pred_after = optimized_explainer(concept="Blockchain")
print(pred_after.explanation)

# Bạn có thể xem ngầm DSPy đã sinh ra prompt "khủng" như thế nào bằng lệnh:
# lm.inspect_history(n=1)