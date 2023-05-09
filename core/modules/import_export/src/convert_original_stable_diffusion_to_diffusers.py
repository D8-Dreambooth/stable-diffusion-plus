# coding=utf-8
# Copyright 2023 The HuggingFace Inc. team.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
""" Conversion script for the LDM checkpoints. """

import argparse

import torch

from diffusers.pipelines.stable_diffusion.convert_from_ckpt import download_from_original_stable_diffusion_ckpt

import argparse
from typing import Optional

from core.handlers.status import StatusHandler


def extract_checkpoint(checkpoint_path: str,
                       dump_path: str,
                       original_config_file: Optional[str] = None,
                       num_in_channels: Optional[int] = None,
                       scheduler_type: str = "pndm",
                       pipeline_type: Optional[str] = None,
                       image_size: Optional[int] = None,
                       prediction_type: Optional[str] = None,
                       extract_ema: bool = False,
                       upcast_attention: bool = False,
                       from_safetensors: bool = False,
                       to_safetensors: bool = False,
                       device: Optional[str] = None,
                       stable_unclip: Optional[str] = None,
                       stable_unclip_prior: Optional[str] = None,
                       clip_stats_path: Optional[str] = None,
                       controlnet: Optional[bool] = False,
                       half: Optional[bool] = False,
                       status_handler: StatusHandler = None) -> None:
    """
    Extracts the checkpoint from the specified path and saves it to the specified dump path.

    Args:
        checkpoint_path (str): Path to the checkpoint to convert.
        original_config_file (str, optional): The YAML config file corresponding to the original architecture. Defaults to None.
        num_in_channels (int, optional): The number of input channels. If `None` number of input channels will be automatically inferred. Defaults to None.
        scheduler_type (str, optional): Type of scheduler to use. Should be one of ['pndm', 'lms', 'ddim', 'euler', 'euler-ancestral', 'dpm']. Defaults to "pndm".
        pipeline_type (str, optional): The pipeline type. One of 'FrozenOpenCLIPEmbedder', 'FrozenCLIPEmbedder', 'PaintByExample'. If `None` pipeline will be automatically inferred. Defaults to None.
        image_size (int, optional): The image size that the model was trained on. Use 512 for Stable Diffusion v1.X and Stable Siffusion v2 Base. Use 768 for Stable Diffusion v2. Defaults to None.
        prediction_type (str, optional): The prediction type that the model was trained on. Use 'epsilon' for Stable Diffusion v1.X and Stable Diffusion v2 Base. Use 'v_prediction' for Stable Diffusion v2. Defaults to None.
        extract_ema (bool, optional): Only relevant for checkpoints that have both EMA and non-EMA weights. Whether to extract the EMA weights or not. Defaults to `False`. Add `--extract_ema` to extract the EMA weights. EMA weights usually yield higher quality images for inference. Non-EMA weights are usually better to continue fine-tuning.
        upcast_attention (bool, optional): Whether the attention computation should always be upcasted. This is necessary when running stable diffusion 2.1. Defaults to False.
        from_safetensors (bool, optional): If `checkpoint_path` is in `safetensors` format, load checkpoint with safetensors instead of PyTorch. Defaults to False.
        to_safetensors (bool, optional): Whether to store pipeline in safetensors format or not. Defaults to False.
        dump_path (str): Path to the output model.
        device (str, optional): Device to use (e.g. cpu, cuda:0, cuda:1, etc.). Defaults to None.
        stable_unclip (str, optional): Set if this is a stable unCLIP model. One of 'txt2img' or 'img2img
        stable_unclip_prior (str, optional): Set if this is a stable unCLIP txt2img model. Selects which prior to use. If `stable_unclip` is set to `txt2img`, the karlo prior (https://huggingface.co/kakaobrain/karlo-v1-alpha/tree/main/prior) is selected by default. Defaults to None.
        clip_stats_path (str, optional): Path to the clip stats file. Only required if the stable unclip model's config specifies `model.params.noise_aug_config.params.clip_stats_path`. Defaults to None.
        controlnet (bool, optional): Set flag if this is a controlnet checkpoint. Defaults to False.
        half (bool, optional): Save weights in half precision. Defaults to False.
        status_handler (StatusHandler, optional): Status handler to use. Defaults to None.
    """
    if status_handler:
        status_handler.update("status", "Loading checkpoint...")

    pipe = download_from_original_stable_diffusion_ckpt(
        checkpoint_path=checkpoint_path,
        original_config_file=original_config_file,
        image_size=image_size,
        prediction_type=prediction_type,
        model_type=pipeline_type,
        extract_ema=extract_ema,
        scheduler_type=scheduler_type,
        num_in_channels=num_in_channels,
        upcast_attention=upcast_attention,
        from_safetensors=from_safetensors,
        device=device,
        stable_unclip=stable_unclip,
        stable_unclip_prior=stable_unclip_prior,
        clip_stats_path=clip_stats_path,
        load_safety_checker=False,
        controlnet=controlnet,
    )

    if half:
        pipe.to(torch_dtype=torch.float16)

    if controlnet:
        # only save the controlnet model
        pipe.controlnet.save_pretrained(dump_path, safe_serialization=to_safetensors)
    else:
        if status_handler:
            status_handler.update("status", "Saving checkpoint...")
        pipe.save_pretrained(dump_path, safe_serialization=to_safetensors)

    if status_handler:
        status_handler.update("status", "Extraction complete.")
