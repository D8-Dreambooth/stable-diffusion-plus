# extract approximating LoRA by svd from two SD models
# The code is based on https://github.com/cloneofsimo/lora/blob/develop/lora_diffusion/cli_svd.py
# Thanks to cloneofsimo!
import gc
import os

import torch
from safetensors.torch import save_file
from tqdm import tqdm

from core.dataclasses.model_data import ModelData
from core.handlers.models import ModelHandler
from core.handlers.status import StatusHandler
from core.modules.import_export.src import lora
from helpers.mytqdm import mytqdm

CLAMP_QUANTILE = 0.99
MIN_DIFF = 1e-6


def save_to_file(file_name, model, state_dict, dtype):
    if dtype is not None:
        for key in list(state_dict.keys()):
            if type(state_dict[key]) == torch.Tensor:
                state_dict[key] = state_dict[key].to(dtype)

    if os.path.splitext(file_name)[1] == '.safetensors':
        save_file(model, file_name)
    else:
        torch.save(model, file_name)


async def extract_lora(model_org: ModelData, model_tuned: ModelData, model_handler: ModelHandler, save_precision=None, dim=4, conv_dim=None, device=None):
    def str_to_dtype(p):
        if p == 'float':
            return torch.float
        if p == 'fp16':
            return torch.float16
        if p == 'bf16':
            return torch.bfloat16
        return None

    save_dtype = str_to_dtype(save_precision)
    user = model_handler.user_name
    sh = StatusHandler(user_name=user)
    print(f"loading Model : {model_org}")
    model_path = model_tuned.path
    model_name = os.path.basename(model_path)
    if "." in model_name:
        model_name = model_name.split(".")[0]
    sh.update(f"loading Model : {model_org}")
    org_pipe = model_handler.load_model("diffusers", model_org, False)
    sh.update("status", f"loading Model : {model_tuned}")
    tuned_pipe = model_handler.load_model("diffusers", model_tuned, False)
    text_encoder_o = org_pipe.text_encoder
    unet_o = org_pipe.unet
    text_encoder_t = tuned_pipe.text_encoder
    unet_t = tuned_pipe.unet

    # create LoRA network to extract weights: Use dim (rank) as alpha
    if conv_dim is None:
        kwargs = {}
    else:
        kwargs = {"conv_dim": conv_dim, "conv_alpha": conv_dim}
    sh.update(f"creating LoRA network 1")
    lora_network_o = lora.create_network(1.0, dim, dim, None, text_encoder_o, unet_o, **kwargs)
    sh.update(f"creating LoRA network 2")
    lora_network_t = lora.create_network(1.0, dim, dim, None, text_encoder_t, unet_t, **kwargs)

    assert len(lora_network_o.text_encoder_loras) == len(
        lora_network_t.text_encoder_loras), f"model version is different (SD1.x vs SD2.x) / " \
                                            f"それぞれのモデルのバージョンが違います（SD1.xベースとSD2.xベース）"

    # get diffs
    diffs = {}
    text_encoder_different = False
    sh.update("status", "Checking tenc")
    for i, (lora_o, lora_t) in enumerate(zip(lora_network_o.text_encoder_loras, lora_network_t.text_encoder_loras)):
        lora_name = lora_o.lora_name
        module_o = lora_o.org_module
        module_t = lora_t.org_module
        diff = module_t.weight - module_o.weight

        # Text Encoder might be same
        if torch.max(torch.abs(diff)) > MIN_DIFF:
            text_encoder_different = True

        diff = diff.float()
        diffs[lora_name] = diff

    if not text_encoder_different:
        print("Text encoder is same. Extract U-Net only.")
        lora_network_o.text_encoder_loras = []
        diffs = {}

    sh.update("status", "Checking unet")
    for i, (lora_o, lora_t) in enumerate(zip(lora_network_o.unet_loras, lora_network_t.unet_loras)):
        lora_name = lora_o.lora_name
        module_o = lora_o.org_module
        module_t = lora_t.org_module
        diff = module_t.weight - module_o.weight
        diff = diff.float()

        if device:
            diff = diff.to(device)

        diffs[lora_name] = diff

    # make LoRA with svd
    print("calculating by svd")
    sh.update("status", "calculating by svd")
    lora_weights = {}
    with torch.no_grad():
        for lora_name, mat in mytqdm(list(diffs.items()), user=user, target="io"):
            # if conv_dim is None, diffs do not include LoRAs for conv2d-3x3
            conv2d = (len(mat.size()) == 4)
            kernel_size = None if not conv2d else mat.size()[2:4]
            conv2d_3x3 = conv2d and kernel_size != (1, 1)

            rank = dim if not conv2d_3x3 or conv_dim is None else conv_dim
            out_dim, in_dim = mat.size()[0:2]

            if device:
                mat = mat.to(device)

            # print(lora_name, mat.size(), mat.device, rank, in_dim, out_dim)
            rank = min(rank, in_dim, out_dim)  # LoRA rank cannot exceed the original dim

            if conv2d:
                if conv2d_3x3:
                    mat = mat.flatten(start_dim=1)
                else:
                    mat = mat.squeeze()

            U, S, Vh = torch.linalg.svd(mat)

            U = U[:, :rank]
            S = S[:rank]
            U = U @ torch.diag(S)

            Vh = Vh[:rank, :]

            dist = torch.cat([U.flatten(), Vh.flatten()])
            hi_val = torch.quantile(dist, CLAMP_QUANTILE)
            low_val = -hi_val

            U = U.clamp(low_val, hi_val)
            Vh = Vh.clamp(low_val, hi_val)

            if conv2d:
                U = U.reshape(out_dim, rank, 1, 1)
                Vh = Vh.reshape(rank, in_dim, kernel_size[0], kernel_size[1])

            U = U.to("cpu").contiguous()
            Vh = Vh.to("cpu").contiguous()

            lora_weights[lora_name] = (U, Vh)

    # make state dict for LoRA
    lora_sd = {}
    sh.update("status", "making state dict for LoRA")
    for lora_name, (up_weight, down_weight) in lora_weights.items():
        lora_sd[lora_name + '.lora_up.weight'] = up_weight
        lora_sd[lora_name + '.lora_down.weight'] = down_weight
        lora_sd[lora_name + '.alpha'] = torch.tensor(down_weight.size()[0])

    # load state dict to LoRA and save it
    lora_network_save, lora_sd = lora.create_network_from_weights(1.0, None, None, text_encoder_o, unet_o,
                                                                  weights_sd=lora_sd)
    lora_network_save.apply_to(text_encoder_o, unet_o)  # create internal module references for state_dict

    info = lora_network_save.load_state_dict(lora_sd, False)
    print(f"Loading extracted LoRA weights: {info}")
    sh.update("status", "saving LoRA weights")
    model_dir = model_handler.models_path[0]
    loras_dir = os.path.join(model_dir, "loras")
    dir_name = loras_dir
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)
    model_name += "_lora"
    save_to = os.path.join(dir_name, f"{model_name}.safetensors")
    # minimum metadata
    metadata = {"ss_network_module": "networks.lora", "ss_network_dim": str(dim),
                "ss_network_alpha": str(dim)}

    lora_network_save.save_weights(save_to, save_dtype, metadata)
    del tuned_pipe
    del org_pipe
    del lora_network_o
    del lora_network_t
    del lora_network_save
    del lora_sd
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()
    model_handler.refresh("loras", save_to, model_name)
    sh.end(desc="LoRA weights are saved to: " + save_to)
    print(f"LoRA weights are saved to: {save_to}")
