import gc
import glob
import pandas as pd

# Load the dataset
file_paths = glob.glob("menor%bots_*/*bot/2000000samples2000epochs.csv") 
sampled_dfs = []
for file in file_paths:
    print(f"Đang xử lý: {file}...")
    # 1. Đọc 1 file 2 triệu dòng vào RAM
    df = pd.read_csv(file)
    # 2. Lưu file này vào một file tạm để giải phóng RAM
    sampled_dfs.append(df)
    # 3. QUAN TRỌNG: Ép xóa file gốc để giải phóng RAM ngay lập tức
    del df
    gc.collect()

print("Đang gộp 7 bộ data nhỏ...")
# 4. Gom 7 cái dataframe (tổng 14 triệu dòng) lại thành 1
df = pd.concat(sampled_dfs, ignore_index=True)

# 5. Xuất ra file chốt hạ
df.to_csv("dow_raw_dataset.csv", index=False)
print("Xong! Đã lưu dataset mới vào: dow_raw_dataset.csv.")