import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# from highlight.mistral_npu_monkey_patch import (
#     replace_with_torch_npu_flash_attention,
#     replace_with_torch_npu_rmsnorm
# )

# replace_with_torch_npu_flash_attention()
# replace_with_torch_npu_rmsnorm()

from highlight.train_mt import train
import torch_npu
from torch_npu.contrib import transfer_to_npu

if __name__ == "__main__":
    train()
