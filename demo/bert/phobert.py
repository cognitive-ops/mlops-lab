from pyvi import ViTokenizer, ViPosTagger

text = "Tôi rất thích ăn phở với nem rán"

# 1. Thực hiện tách từ
segmented_text = ViTokenizer.tokenize(text)
print("Tách từ:", segmented_text)
# Output: Trường đại_học bách_khoa Hà_Nội

# 2. Thực hiện gán nhãn từ loại
pos_tags = ViPosTagger.postagging(segmented_text)
print("Gán nhãn từ loại:", pos_tags)
# Output: (['Trường', 'đại_học', 'bách_khoa', 'Hà_Nội'], ['N', 'N', 'A', 'Np'])
print