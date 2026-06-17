# FaaSWarden

This project focuses on detecting attacks in a serverless environment. Currently we focus into Denial of Wallet (DoW)

**Publications used**:
- [Generation of a dataset for DoW attack detection in serverless architectures](https://www.researchgate.net/publication/376254601_Generation_of_a_dataset_for_DoW_attack_detection_in_serverless_architectures)
- [Data augmentation with Generative AI for DoW attack detection in serverless architectures](https://zenodo.org/records/13758901)

## Current Results

### 1. Classification Performance

Both models achieved an outstanding overall **Accuracy of 99%**. Detailed metrics from the classification reports indicate highly stable predictive power across both classes:

| Model | Class | Precision | Recall | F1-Score | Inference Time (s) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **XGBoost** | 0.0 (Human)<br>1.0 (Bot) | 1.00<br>0.96 | 0.99<br>0.99 | 0.99<br>0.97 | **2.3078s** |
| **Transformer** | 0.0 (Human)<br>1.0 (Bot) | 0.99<br>0.98 | 0.99<br>0.98 | 0.99<br>0.98 | **16.6050s** |

---

### 2. Confusion Matrix Comparison

The distribution of true positives, true negatives, and misclassifications highlights subtle differences in trade-offs between precision and recall:

#### XGBoost Model
* **True Human detected**: ~2.1M | **False Bots (False Alarms)**: 28,490
* **True Bot detected**: 665,408 | **Missed Bots (False Negatives)**: 8,474

#### Transformer Model
* **True Human detected**: ~2.1M | **False Bots (False Alarms)**: 12,023
* **True Bot detected**: 659,877 | **Missed Bots (False Negatives)**: 14,005

---

### 3. Key Takeaways & Operational Efficiency

> 🚀 **Inference Speed Breakthrough:** While the Transformer model provides slightly better precision on the Bot class (0.98 vs 0.96), **XGBoost processed the entire test suite ~7.2x faster** than the Transformer architecture (2.31s vs 16.61s).